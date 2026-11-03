-- Daily orders: refresh first, then cast and deliver serially. Never retry an
-- unacknowledged resource-consuming request without authoritative evidence.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.types(text)
 local out={}
 if text==nil then return {[1]=true,[3]=true} end
 if type(text)~='string' then return out end
 for n in text:gmatch('[^|]+') do n=tonumber(n);if n and n>=1 and n<=4 and n%1==0 then out[n]=true end end
 return out
end
function M.category(c,fish)
 if not c then return end
 if c.type==2 then return c.condition end
 if c.type==1 then local f=fish(c.condition);return f and f.type end
end
function M.new(env)
 local self={env=env}
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  self.active=nil;a.status=status;a.reason=reason;self.last=a
  if a.identity==env.identity() then env.save(a) end
  if a.done then a.done(a) end
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard();if why then self:finish(a.pending and 'uncertain' or 'skipped',why);return false end
  return true
 end
 function self:query()
  local a=self.active;a.phase='query';a.deadline=env.now()+20;a.base=nil;env.query()
 end
 function self:changed()
  local a=self.active;a.progress=a.progress+1;env.save(a);if a.changed then a.changed(a) end
 end
 function self:start(types,done,changed)
  if self.active then return false,'busy' end
  local why=env.guard();if why then done({status='skipped',reason=why});return true end
  if not env.identity() then return false,'no_role' end
  if not next(types) then done({status='skipped',reason='no_selected_types'});return true end
  local prev=env.load()
  self.active={identity=env.identity(),day=env.day(),status='running',types=types,done=done,changed=changed,
   casts=0,deliveries=0,chests=0,refreshes=0,claimed=0,progress=0,orders={},next_cast=env.now(),
   pending=prev and prev.day==env.day() and prev.pending or nil}
  local p=self.active.pending
  if p and p.kind=='cast' and type(p.sent_at)=='number' then self.active.next_cast=math.max(env.now(),p.sent_at+7) end
  self:query();return true
 end
 function self:act(kind,p)
  local a=self.active;p=p or {};p.kind=kind;p.sent_at=env.now()
  a.pending=p;a.phase='reply';a.deadline=env.now()+25
  if kind=='cast' then a.next_cast=env.now()+7 end
  env.save(a);env.act(kind,p)
 end
 function self:orders(base)
  if type(base.quest_list)~='table' or #base.quest_list~=3 then return end
  local rows,seen={},{}
  for _,o in ipairs(base.quest_list) do
   local c=env.order(o.order_id)
   if not uint(o.id) or o.id==0 or seen[o.id] or not c or not uint(o.value) or not uint(o.target_val)
    or o.target_val==0 or (o.finish~=0 and o.finish~=1 and o.finish~=2) then return end
   seen[o.id]=true
   rows[#rows+1]={id=o.id,order_id=o.order_id,finish=o.finish,value=o.value,target_val=o.target_val,
    category=M.category(c,env.fish),fishery=c.fishery_id,name=env.orderName(c)}
  end
  table.sort(rows,function(a,b) return a.id<b.id end);return rows
 end
 function self:reconcile(b)
  local a=self.active;local p=a.pending;if not p then return true end
  -- A fresh query after a timeout is evidence, not permission to replay.
  local found
  for _,o in ipairs(a.orders) do if o.id==p.id then found=o end end
  local ok=p.acked or (p.kind=='deliver' and b.fish_id==0)
   or (p.kind=='claim' and found and found.finish==2)
   or (p.kind=='refresh' and found and found.order_id~=p.order_id)
   or (p.kind=='cast' and b.fish_id~=0)
   or (p.kind=='fishery' and b.cur_fishery_id==p.id)
   or (p.kind=='bait' and b.bait_id==p.id)
  if p.kind=='deliver' and b.fish_id==p.id then ok=false end
  if p.kind=='claim' and (not found or found.finish~=2) then ok=false end
  if p.kind=='fishery' and b.cur_fishery_id~=p.id then ok=false end
  if p.kind=='bait' and b.bait_id~=p.id then ok=false end
  if not ok then self:finish('uncertain','request_unresolved');return false end
  if p.kind=='cast' then a.casts=a.casts+1
  elseif p.kind=='refresh' then a.refreshes=a.refreshes+1
  elseif p.kind=='claim' then a.claimed=a.claimed+1
  elseif p.kind=='deliver' then a.deliveries=a.deliveries+1;if p.chest then a.chests=a.chests+1 end end
  a.pending=nil;self:changed();return true
 end
 function self:select()
  local a=self.active;local b=a.base
  local rows=self:orders(b)
  if not rows or not uint(b.fish_id) or not uint(b.free_quest_times) then self:finish('error','invalid_state');return end
  a.orders=rows
  if not self:reconcile(b) then return end
  -- Deliver any hook catch before claiming/stopping, including a final chest.
  if b.fish_id~=0 then
   local c=env.fish(b.fish_bid);if not c then self:finish('error','invalid_state');return end
   self:act('deliver',{id=b.fish_id,chest=c.type==7});return
  end
  local finished,first,refresh=0,nil,nil
  for _,o in ipairs(rows) do
   if o.finish==1 then self:act('claim',{id=o.id});return end
   if o.finish==2 then finished=finished+1
   else
    first=first or o
    if not a.types[o.category] then refresh=refresh or o end
   end
  end
  if finished==3 then self:finish('confirmed','orders_complete');return end
  if refresh then
   local allowed,why=env.canRefresh(b)
   if not allowed then self:finish('skipped',why);return end
   self:act('refresh',{id=refresh.id,order_id=refresh.order_id});return
  end
  local can,why=env.canCast(b);if not can then self:finish('skipped',why);return end
  local bait=env.bait(b)
  if bait then self:act('bait',{id=bait});return end
  -- Species orders must be fished in their configured, already unlocked area.
  local target=env.fishery(first,b)
  if not target then self:finish('skipped','fishery_locked');return end
  if target~=b.cur_fishery_id then self:act('fishery',{id=target});return end
  if env.now()<a.next_cast then a.phase='pace';a.deadline=a.next_cast;return end
  self:act('cast')
 end
 function self:onPacket(id,d)
  if not self:valid() or type(d)~='table' then return end
  local a=self.active
  if id==12000 and a.phase=='query' then a.base=d;return end
  local p=a.pending;if a.phase~='reply' or not p then return end
  local expect={cast=12004,deliver=12013,claim=12015,refresh=12026,fishery=12002,bait=12022}
  if id~=expect[p.kind] then return end
  if p.kind=='deliver' and d.type~=2 then return end
  if p.kind=='bait' and d.bait_id~=p.id then return end
  if p.kind=='fishery' and d.code==1 and d.cur_fishery_id~=p.id then return end
  local success=p.kind=='bait' or (p.kind=='cast' and uint(d.code) and d.code>0 and d.code<=9) or d.code==1
  if not success then
   if d.code==0 then a.pending=nil;env.save(a);self:finish('skipped','action_rejected')
   else self:finish('uncertain','invalid_reply') end
   return
  end
  p.acked=true;env.save(a);a.phase='pause';a.deadline=math.max(env.now()+1,p.kind=='cast' and a.next_cast or 0)
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if a.phase=='pause' or a.phase=='pace' then if env.now()>=a.deadline then self:query() end;return end
  if a.phase=='query' and a.base then self:select();return end
  if env.now()>=a.deadline then
   if a.phase=='reply' then self:query() else self:finish(a.pending and 'uncertain' or 'error','query_timeout') end
  end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 function self:fail() self:finish(self.active and self.active.pending and 'uncertain' or 'error','runtime_error') end
 return self
end
return M
