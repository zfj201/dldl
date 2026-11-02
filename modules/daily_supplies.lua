-- Serial purchases/claims. Persist before mutation and verify with a fresh server snapshot.
local M={}
function M.new(env)
 local self={env=env}
 function self:finish(status,reason)
  local a=self.active;if not a then return end;self.active=nil
  local result={status=status,reason=reason,entries=a.entries,count=#a.entries}
  if a.identity==env.identity() then pcall(env.report,a.kind,result) end
  a.done(result)
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard(a.kind);if why then self:finish(a.pending and 'uncertain' or 'skipped',why);return false end
  return true
 end
 function self:query(phase)
  local a=self.active;a.phase=phase;a.deadline=env.now()+20
  env.query(a.kind)
 end
 function self:start(kind,done,option)
  if self.active then return false,'busy' end
  if not env.identity() then return false,'no_role' end
  self.active={kind=kind,done=done,option=option,identity=env.identity(),day=env.day(),entries={},steps=0}
  if not self:valid() then return true end
  self.active.pending=env.load(kind);self:query('query');return true
 end
 function self:onPacket(id,d)
  if not self:valid() then return end
  local a=self.active
  env.receive(a.kind,id,d,a.phase)
  if a.phase=='reply' then
   local accepted=env.reply(a.pending,id,d)
   if accepted==false then self:finish('uncertain','supply_rejected')
   elseif accepted==true then self:query('verify') end
  end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if env.now()>=a.deadline then self:finish(a.pending and 'uncertain' or 'error',a.phase..'_timeout');return end
  if a.phase~='query' and a.phase~='verify' then return end
  if not env.ready(a.kind) then return end
  if a.pending then
   local ok,why=env.verify(a.pending)
   if ok then
    a.entries[#a.entries+1]={name=a.pending.name,num=a.pending.amount or 1,recovered=a.phase=='query'}
    env.clear(a.kind);a.pending=nil
   elseif why=='new_period' then env.clear(a.kind);a.pending=nil
   else self:finish('uncertain',why or 'previous_request_unresolved');return end
  end
  if a.steps>=60 then self:finish('error','supply_step_limit');return end
  local target,why=env.select(a.kind,a.option)
  if not target then self:finish(#a.entries>0 and 'confirmed' or 'skipped',why or 'supply_complete');return end
  env.save(a.kind,target);a.pending=target;a.steps=a.steps+1
  a.phase='reply';a.deadline=env.now()+20;env.act(target)
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 return self
end
return M
