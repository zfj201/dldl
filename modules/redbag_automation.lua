-- Serial guild redbag collection. Query fresh lists and quotas before each claim.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
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
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_guild_or_day_changed');return false end
  local why=env.guard();if why then self:finish(a.pending and 'uncertain' or 'skipped',why);return false end
  return true
 end
 function self:query()
  local a=self.active;a.phase='query';a.deadline=env.now()+20;a.quota=nil;a.bags=nil
  env.query()
 end
 function self:start(done)
  if self.active then return false,'busy' end
  local why=env.guard();if why then done({status='skipped',reason=why,entries={}});return true end
  if not env.identity() then return false,'no_role' end
  local last=env.load()
  self.active={identity=env.identity(),day=env.day(),status='running',entries={},attempted={},done=done,started=env.now(),pending=last and last.pending}
  self:query();return true
 end
 function self:quotas(list)
  if type(list)~='table' then return end
  local q={}
  for _,v in ipairs(list) do
   if not uint(v.type) or not uint(v.day_recv_num) or not uint(v.day_recv_max_num) or q[v.type] then return end
   q[v.type]={used=v.day_recv_num,max=v.day_recv_max_num}
  end
  return q
 end
 function self:onPacket(id,d)
  if not self:valid() or type(d)~='table' then return end
  local a=self.active
  if id==13536 and a.phase=='reply' and a.pending and d.id==a.pending.id then
   if d.code~=0 and d.code~=1 then self:finish('uncertain','invalid_reply');return end
   if d.code==1 then
    if d.type~=a.pending.type or not uint(d.val) or not self:quotas(d.list) then self:finish('uncertain','invalid_reply');return end
    a.entries[#a.entries+1]={id=d.id,type=d.type,val=d.val,asset=a.pending.asset}
   else a.rejected=(a.rejected or 0)+1 end
   a.pending=nil;env.save(a);a.phase='pause';a.deadline=env.now()+1.2
  elseif a.phase=='query' and id==13523 then
   a.quota=self:quotas(d.list)
   if not a.quota then self:finish('error','invalid_quota') end
  elseif a.phase=='query' and id==13534 then
   if (d.type~=0 and d.type~=1) or type(d.list)~='table' then self:finish('error','invalid_list');return end
   if d.type==0 then a.bags={} elseif not a.bags then return end
   for _,b in ipairs(d.list) do
    if not uint(b.id) or b.id==0 or not uint(b.type) or not uint(b.time) or not uint(b.num) or not uint(b.max_num)
     or (b.flag~=0 and b.flag~=1) then self:finish('error','invalid_list');return end
    a.bags[b.id]=b
   end
  end
 end
 function self:select()
  local a=self.active
  if a.pending and a.pending.expires and a.pending.expires<=env.now() then
   a.unverified=(a.unverified or 0)+1;a.pending=nil;env.save(a)
  end
  if a.pending then
   local b=a.bags[a.pending.id]
   if b and b.flag==1 then
    a.entries[#a.entries+1]={id=b.id,type=b.type,recovered=true}
    a.attempted[b.id]=true;a.pending=nil;env.save(a)
   else self:finish('uncertain','previous_request_unresolved');return end
  end
  local candidates={};local limited=false
  for _,b in pairs(a.bags) do
   if not a.attempted[b.id] and b.flag==0 and b.num<b.max_num and b.time>env.now() then
    local eligible,why=env.eligible(b,a.quota)
    if eligible==nil then self:finish('error',why or 'invalid_config');return end
    if eligible then candidates[#candidates+1]=b else limited=true end
   end
  end
  table.sort(candidates,function(x,y) if x.time~=y.time then return x.time<y.time end;return x.id<y.id end)
  local b=candidates[1]
  if not b then
   self:finish(#a.entries>0 and 'confirmed' or 'skipped',limited and 'quota_reached' or 'no_claimable_redbag');return
  end
  local cfg=env.config(b.type)
  a.attempted[b.id]=true;a.pending={id=b.id,type=b.type,asset=cfg.assets,expires=b.time};a.phase='reply';a.deadline=env.now()+20
  env.save(a) -- Persist ownership before sending a claim; do not retry unknown results.
  env.claim(b.id)
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if env.now()-a.started>=300 then self:finish(a.pending and 'uncertain' or 'confirmed','run_limit');return end
  if a.phase=='pause' then if env.now()>=a.deadline then self:query() end;return end
  if env.now()>=a.deadline then self:finish(a.pending and 'uncertain' or 'error',a.phase..'_timeout');return end
  if a.phase=='query' and a.quota and a.bags then self:select() end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 function self:fail() self:finish(self.active and self.active.pending and 'uncertain' or 'error','runtime_error') end
 return self
end
return M
