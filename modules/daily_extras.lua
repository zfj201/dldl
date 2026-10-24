-- Optional once-daily tasks. Challenge acceptance completes the task, never settlement.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.new(env)
 local self={env=env,deferred={}}
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  self.active=nil
  if env.log then env.log('finish',a.kind..'|'..status..'|'..tostring(reason)) end
  a.done({status=status,reason=reason,count=status=='confirmed' and 1 or 0})
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  return true
 end
 function self:phase(p) local a=self.active;a.phase=p;a.deadline=env.now()+20 end
 function self:start(kind,done)
  if self.active then return false,'busy' end
  if kind~='guild_trial' and kind~='temple_duel' and kind~='workshop_gift' then return false,'unknown_task' end
  if not env.identity() then return false,'no_role' end
  self.active={kind=kind,done=done,identity=env.identity(),day=env.day()}
  if self.deferred[kind] or env.pending(kind) then self:finish('uncertain','previous_request_unresolved');return true end
  if env.completed(kind) then self:finish('skipped','daily_target_done');return true end
  local why=env.guard(kind);if why then self:finish('skipped',why);return true end
  if kind=='workshop_gift' then self:phase('base');env.query(kind)
  else self:phase('form');env.query('form',kind) end
  return true
 end
 function self:mutate()
  if not self:valid() then return end
  local a=self.active;local why=env.guard(a.kind)
  if why then self:finish('error',why);return end
  -- Flush before sending; a timeout, crash or close must never resend blindly.
  env.save(a.kind,'pending',a);a.mutated=true;self:phase('reply');env.act(a.kind)
 end
 function self:confirm(reason)
  local a=self.active;env.save(a.kind,'completed',a)
  if reason=='challenge_started' and env.accepted then env.accepted(a.kind) end
  self:finish('confirmed',reason)
 end
 function self:defer()
  local a=self.active
  -- Code zero is an explicit rejection. Only this known unaccepted attempt
  -- may release pending; the later retry writes a new pending before sending.
  env.save(a.kind,'rejected',a);a.mutated=false;self.active=nil
  a.defer_deadline=env.now()+180;a.retry=true;self.deferred[a.kind]=a
  a.done({status='deferred',reason='challenge_deferred',job=a,count=0})
 end
 function self:hasDeferred()
  return next(self.deferred)~=nil or (self.active~=nil and self.active.background==true)
 end
 function self:pollDeferred()
  if self.active then if self.active.background then self:tick() end;return end
  for k,a in pairs(self.deferred) do
   if a.identity~=env.identity() or a.day~=env.day() or env.now()>=a.defer_deadline then
    self.deferred[k]=nil;a.done({status='uncertain',reason='deferred_timeout',count=0});return
   end
   -- This only resumes an explicitly rejected request, after our other combat ends.
   -- A missing response never creates a deferred job or authorizes a retry.
   if not env.queueBusy() and not env.conflict(k) then
    self.deferred[k]=nil;self.active=a;a.background=true;a.base=nil;a.personal=nil
    local why=env.guard(k);if why then self:finish('uncertain',why);return end
    self:phase('form');env.query('form',k);return
   end
  end
 end
 function self:workshop(data)
  local a=self.active
  if data.type~=2 or data.bid~=0 then return end
  if data.id~=23 or type(data.gift_list)~='table' or not env.freeGift() then self:finish(a.mutated and 'uncertain' or 'error','gift_config_changed');return end
  local gift
  for _,v in ipairs(data.gift_list) do if v.gift_id==2301 then
   if gift then self:finish('error','invalid_shop_state');return end;gift=v
  end end
  if not gift or not uint(gift.buy_num) or gift.buy_num>1 then self:finish(a.mutated and 'uncertain' or 'error','invalid_shop_state');return end
  if a.phase=='verify' then
   if gift.buy_num==1 then self:confirm('state_confirmed') end
  elseif gift.buy_num==1 then self:finish('skipped','already_claimed')
  else self:mutate() end
 end
 function self:challengeBase()
  local a=self.active
  if a.kind=='guild_trial' then
   local d=a.base;if not d then return end
   if not uint(d.boss_id) or not uint(d.used_time) or not uint(d.buy_time) or not uint(d.day_combat_time)
    or not env.guildBoss(d.boss_id) or (d.is_last_boss~=0 and d.is_last_boss~=1) then self:finish('error','invalid_challenge_state');return end
   if d.used_time>0 or d.day_combat_time>0 then
    if a.retry then env.save(a.kind,'completed',a) end
    self:finish('skipped','daily_target_done');return
   end
   if not env.guildAvailable(d) then self:finish('skipped','no_remaining_action');return end
  else
   if not a.base or not a.personal then return end
   local d=a.personal;local max=env.templeDailyCount()
   if not uint(d.day_num) or not uint(max) or max==0 or d.day_num>max then self:finish('error','invalid_challenge_state');return end
   if a.base.status~=1 then self:finish('skipped','not_open');return end
   if d.day_num<max then
    if a.retry then env.save(a.kind,'completed',a) end
    self:finish('skipped','daily_target_done');return
   end
  end
  self:mutate()
 end
 function self:onPacket(id,data)
  if not self:valid() or type(data)~='table' then return end
  local a=self.active
  if a.phase=='form' and id==11211 and data.type==env.formType(a.kind) then
   local why=env.checkForm(data);if why then self:finish('error',why);return end
   self:phase('base');env.query(a.kind)
  elseif a.phase=='base' and a.kind=='guild_trial' and id==29720 then a.base=data;self:challengeBase()
  elseif a.phase=='base' and a.kind=='temple_duel' and (id==28700 or id==28703) then
   if id==28700 then a.base=data else a.personal=data end;self:challengeBase()
  elseif a.kind=='workshop_gift' and id==10572 and (a.phase=='base' or a.phase=='verify') then self:workshop(data)
  elseif a.phase=='reply' and ((a.kind=='guild_trial' and id==29721) or (a.kind=='temple_duel' and id==28702)) then
   if data.code==1 then self:confirm('challenge_started')
   elseif data.code==0 and not a.retry and env.conflict(a.kind) then self:defer()
   else self:finish('uncertain','action_rejected') end
  elseif a.phase=='reply' and a.kind=='workshop_gift' and id==10573 then
   if data.type~=2 or data.bid~=0 or data.id~=23 or data.gift_id~=2301 then return end
   if data.code~=1 or data.buy_num~=1 then self:finish('uncertain','action_rejected');return end
   self:phase('verify');env.query(a.kind)
  end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if a.phase=='verify' and env.now()>=(a.poll_at or 0) then a.poll_at=env.now()+2;env.query(a.kind) end
  if self.active and env.now()>=a.deadline then self:finish(a.mutated and 'uncertain' or 'error',a.phase..'_timeout') end
 end
 function self:cancel()
  self:finish('cancelled','cancelled')
  local jobs=self.deferred;self.deferred={}
  for _,a in pairs(jobs) do a.done({status='cancelled',reason='cancelled',count=0}) end
 end
 return self
end
return M
