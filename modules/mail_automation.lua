-- One native attachment batch, followed by a fresh list verification. No delete.
local M={}
local function key(m) return tostring(m.srv_id)..':'..tostring(m.id) end
function M.new(env)
 local self={}
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  self.active=nil;a.status=status;a.reason=reason;self.last=a
  if a.identity==env.identity() then env.save(a) end
  if a.done then a.done(a) end
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard();if why then self:finish(a.pending and 'uncertain' or 'skipped',why);return false end
  return true
 end
 function self:query()
  local a=self.active;a.phase='query';a.deadline=env.now()+20;a.mail=nil;env.query()
 end
 function self:start(_,done)
  if self.active then return false,'busy' end
  local why=env.guard();if why then done({status='skipped',reason=why});return true end
  if not env.identity() then return false,'no_role' end
  -- Attachment collection is idempotent and spends nothing. A new explicit run
  -- may claim still-unclaimed mail from its fresh list after a partial batch.
  self.active={identity=env.identity(),status='running',count=0,done=done}
  self:query();return true
 end
 function self:onPacket(id,d)
  if not self:valid() or type(d)~='table' then return end
  local a=self.active
  if id==10800 and a.phase=='query' then a.mail=d.mail
  elseif id==10802 and a.phase=='reply' and type(d.ids)=='table' then
   a.ack={};for _,v in ipairs(d.ids) do a.ack[key(v)]=true end
   a.phase='pause';a.deadline=env.now()+1
  end
 end
 function self:select()
  local a=self.active;local map,eligible={},{}
  for _,m in ipairs(a.mail) do
   if type(m.id)~='number' or not m.srv_id or (m.status~=0 and m.status~=1 and m.status~=2) then self:finish('error','invalid_state');return end
   local k=key(m);map[k]=m
   if (m.type==1 or m.type==3) and m.has_items==1 and m.status~=2 then eligible[#eligible+1]=k end
  end
  if a.pending then
   local unresolved=0
   for _,k in ipairs(a.pending) do
    local m=map[k]
    if m and (m.status==2 or m.has_items==0) then a.count=a.count+1
    elseif not m and a.ack and a.ack[k] then a.count=a.count+1
    else unresolved=unresolved+1 end
   end
   if unresolved>0 then self:finish('uncertain','mail_partial');return end
   a.pending=nil;self:finish('confirmed','mail_complete');return
  end
  if #eligible==0 then self:finish('confirmed','mail_empty');return end
  a.pending=eligible;a.phase='reply';a.deadline=env.now()+20;env.save(a);env.claim()
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if a.phase=='pause' then if env.now()>=a.deadline then self:query() end;return end
  if a.phase=='query' and a.mail then self:select();return end
  if env.now()>=a.deadline then
   if a.phase=='reply' then self:query() else self:finish(a.pending and 'uncertain' or 'error','query_timeout') end
  end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 function self:fail() self:finish(self.active and self.active.pending and 'uncertain' or 'error','runtime_error') end
 return self
end
return M
