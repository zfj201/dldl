-- One material-only recast per game day. Preserve the equipped attributes and pending safety.
local M={}
function M.new(env)
 local self={env=env}
 function self:finish(status,reason)
  local a=self.active;if not a then return end;self.active=nil
  a.done({status=status,reason=reason,count=status=='confirmed' and 1 or 0,target=a.target})
 end
 function self:phase(p) self.active.phase=p;self.active.deadline=env.now()+20 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard();if why then self:finish(a.sent and 'uncertain' or 'skipped',why);return false end
  return true
 end
 function self:start(kind,done)
  if self.active then return false,'busy' end
  if kind~='artifact_recast' then return false,'unknown_task' end
  if not env.identity() then return false,'no_role' end
  self.active={identity=env.identity(),day=env.day(),done=done}
  if not self:valid() then return true end
  local record=env.load()
  if record.pending then self:finish('uncertain','previous_request_unresolved');return true end
  if record.completed_day==env.day() then self.active.target=record.target;self:finish('skipped','daily_target_done');return true end
  self:phase('query');env.query();return true
 end
 function self:onPacket(id,d)
  if not self:valid() then return end
  local a=self.active
  if id==11033 and a.phase=='reply' then
   if d.result~=1 then self:finish('uncertain','recast_rejected');return end
   self:phase('verify');env.detail(a.target.id)
  elseif a.phase=='query' then env.receive(id,d)
  elseif a.phase=='verify' and id==10506 then env.receive(id,d) end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if env.now()>=a.deadline then self:finish(a.sent and 'uncertain' or 'error',a.phase..'_timeout');return end
  if a.phase=='query' then
   local target,why=env.select()
   if why=='awaiting_details' then return end
   if not target then self:finish('skipped',why or 'no_eligible_target');return end
   a.target=target
   local problem=env.recheck(target);if problem then self:finish('skipped',problem);return end
   env.savePending(a);a.sent=true;self:phase('reply');env.act(target)
  elseif a.phase=='verify' then
   local confirmed,why=env.verify(a.target)
   if confirmed then env.saveCompleted(a);self:finish('confirmed','recast_confirmed')
   elseif why then self:finish('uncertain',why) end
  end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 return self
end
return M
