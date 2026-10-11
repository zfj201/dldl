-- New optional tasks. Every mutation is journaled and never resent after uncertainty.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function copy(t) local o={} for k,v in pairs(t) do o[k]=v end return o end
function M.new(env)
 local self={env=env}
 function self:log(e,d) if env.log then env.log(e,d or '') end end
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  self:log('finish',a.kind..'|'..status..'|'..tostring(reason)..'|'..a.completed)
  if a.recovery and env.reportRecovery then env.reportRecovery(status,reason) end
  self.active=nil;a.done({status=status,reason=reason,count=a.completed})
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  return true
 end
 function self:phase(p,seconds) local a=self.active;a.phase=p;a.deadline=env.now()+(seconds or 20);self:log('phase',a.kind..'|'..p) end
 function self:start(kind,done)
  if self.active then return false,'busy' end
  if not env.identity() then return false,'no_role' end
  if kind~='guild_wish' and kind~='ruins' then return false,'unknown_task' end
  self.active={kind=kind,done=done,identity=env.identity(),day=env.day(),completed=0}
  if env.pending(kind) then
   if kind=='ruins' and env.recoveryRequest and env.recoveryRequest() then
    local a=self.active;a.recovery=true;a.mutated=true
    local baseline,why=env.recoveryBaseline()
    if not baseline then self:finish('uncertain',why or 'recovery_evidence_mismatch');return true end
    if not env.battleReady() then self:finish('uncertain','recovery_battle_busy');return true end
    local guard=env.openGuard(kind);if guard then self:finish('uncertain',guard);return true end
    a.recovery_expected=baseline;self:phase('recovery_verify');env.query(kind)
   else self:finish('uncertain','previous_request_unresolved') end
   return true
  end
  local why=env.openGuard(kind);if why then self:finish('skipped',why);return true end
  if kind=='guild_wish' then self:phase('base');env.query(kind)
  else
   if not env.battleReady() then self:finish('error','battle_busy');return true end
   self:phase('form');env.query('ruins_form')
  end
  return true
 end
 function self:mutate(action)
  if not self:valid() then return end
  local a=self.active;local why=env.guard(a.kind,a,action)
  if why then self:finish(a.mutated and 'uncertain' or 'error',why);return end
  env.savePending(a.kind,true,a);a.mutated=true
  a.operation=action;self:phase(action);env.act(action)
 end
 function self:base(data)
  local a=self.active
  if a.kind=='guild_wish' then
   if not env.guildScope(data) or not uint(data.wish_gift_type) or data.wish_gift_type>2 then self:finish(a.mutated and 'uncertain' or 'error','invalid_guild_state');return end
   if a.phase=='verify' then
    if a.accepted and data.wish_gift_type==2 then env.savePending(a.kind,false);a.completed=1;self:finish('confirmed','state_confirmed') end
   elseif data.wish_gift_type>0 then self:finish('skipped','wish_already_claimed')
   else a.base=copy(data);self:mutate('wish') end
   return
  end
  if not uint(data.kill_time) or not uint(data.boss_id) or not uint(data.hp_per) or data.hp_per>10000
    or not uint(data.fight_time) or not uint(data.end_time) or data.end_time<=env.now() then self:finish(a.mutated and 'uncertain' or 'error','invalid_ruins_state');return end
  if a.phase=='recovery_verify' then
   if env.now()>=a.deadline then self:finish('uncertain','recovery_verify_timeout');return end
   if not env.battleReady() then self:finish('uncertain','recovery_battle_busy');return end
   local expected,why=env.recoveryBaseline()
   if not expected then self:finish('uncertain',why or 'recovery_evidence_mismatch');return end
   for _,f in ipairs({'kill_time','boss_id','hp_per','fight_time','end_time'}) do
    if data[f]~=expected[f] then self:finish('uncertain','recovery_state_mismatch');return end
   end
   if env.diamonds()~=expected.diamonds or not env.ruinsBoss(data.boss_id) then self:finish('uncertain','recovery_state_mismatch');return end
   if not a.recovery_first_at then
    a.recovery_first_at=env.now();a.recovery_query_at=env.now()+2
   elseif a.recovery_second_query and env.now()>=a.recovery_first_at+2 then
    env.savePending(a.kind,false);a.mutated=false;a.completed=1
    self:finish('confirmed','ruins_v2_rotation_reconciled')
   end
   return
  end
  if a.phase=='verify' then
   local b=a.base;local s=a.settlement
   local loss=s and s.result~=1
   local expected=b.kill_time-(loss and 0 or 1)
   local state_matches=loss and data.end_time==b.end_time and data.boss_id==b.boss_id and data.hp_per==s.hp_per
   if s and not loss then
    -- A won boss is automatically replaced, including its expiry time.
    -- Random replacement may draw the same boss ID again.
    state_matches=env.ruinsBoss(data.boss_id) and data.boss_id~=0 and data.hp_per==0
      and data.fight_time==b.fight_time+1
   end
   if a.accepted and s and data.kill_time==expected and env.diamonds()==a.diamonds and state_matches then
    env.savePending(a.kind,false);a.mutated=false;a.completed=a.completed+1;a.stop_loss=loss;self:phase('cleanup',30)
   end
   return
  end
  if data.kill_time==0 then self:finish(a.completed>0 and 'confirmed' or 'skipped','daily_target_done');return end
  if data.boss_id==0 or not env.ruinsBoss(data.boss_id) then self:finish('skipped','ruins_no_boss');return end
  -- The native result view shows remaining HP as 100-hp_per/100.
  -- Zero is an untouched boss; 10000 means fully depleted.
  if data.hp_per>=10000 then self:finish('skipped','ruins_boss_defeated');return end
  a.base=copy(data);a.diamonds=env.diamonds();a.accepted=nil;a.settlement=nil;a.skip_sent=nil;a.battle_started=false;a.team_count=0;self:mutate('ruins_challenge')
 end
 function self:onBattleStart(data)
  local a=self.active
  if not a or a.kind~='ruins' or type(data)~='table' or data.combat_type~=77 then return end
  if a.phase~='ruins_challenge' and a.phase~='battle' and a.phase~='battle_result' then return end
  a.battle_started=true;a.skip_sent=false;a.team_count=(a.team_count or 0)+1
  a.current_wave=data.current_wave;a.total_wave=data.total_wave
  self:log('battle_start','team='..a.team_count..'|wave='..tostring(data.current_wave)..'/'..tostring(data.total_wave))
  self:phase('battle',math.max(120,(a.deadline or env.now())-env.now()))
 end
 function self:onBattleEnd(data)
  local a=self.active
  if not a or a.kind~='ruins' or type(data)~='table' or data.combat_type~=77 then return end
  if a.phase~='ruins_challenge' and a.phase~='battle' and a.phase~='battle_result' then return end
  a.battle_started=false;a.skip_sent=false
  self:log('battle_end','team='..tostring(a.team_count)..'|result='..tostring(data.result)..'|show_panel_type='..tostring(data.show_panel_type))
  self:phase('battle_result',120)
 end
 function self:onPacket(id,data)
  if not self:valid() or type(data)~='table' then return end
  local a=self.active;self:log('packet',id..'|'..a.phase..'|code='..tostring(data.code)..'|result='..tostring(data.result)..'|remaining='..tostring(data.kill_time))
  if a.phase=='form' and a.kind=='ruins' and id==11211 and data.type==92 then
   local why=env.checkForm(data);if why then self:finish('error',why);return end
   a.form=data;self:phase('base');env.query(a.kind)
  elseif (id==13518 and a.kind=='guild_wish') or (id==13100 and a.kind=='ruins') then
   if a.phase=='base' or a.phase=='verify' or a.phase=='recovery_verify' then self:base(data) end
  elseif id==13548 and a.kind=='guild_wish' and a.phase=='wish' then
   if data.code~=1 or data.wish_gift_type~=2 then self:finish('uncertain','action_rejected');return end
   a.accepted=true;self:phase('verify');env.query(a.kind)
  elseif id==13105 and a.kind=='ruins' and not a.accepted
    and (a.phase=='ruins_challenge' or a.phase=='battle' or a.phase=='battle_result') then
   -- A battle start may precede this owned callback.  Its id/code must
   -- still match before any settlement can clear the pending journal.
   if data.code~=1 or data.id~=0 then self:finish('uncertain','action_rejected');return end
   a.accepted=true
   if a.settlement then self:phase('verify');env.query(a.kind)
   elseif a.phase=='ruins_challenge' then self:phase('battle',90) end
  elseif id==13106 and a.kind=='ruins'
    and (a.phase=='ruins_challenge' or a.phase=='battle' or a.phase=='battle_result') then
   if data.result~=1 and data.result~=2 and data.result~=0 then self:finish('uncertain','invalid_settlement');return end
   if data.is_self~=1 or data.combat_type~=77 or not uint(data.hp_per) or data.hp_per>10000 then self:finish('uncertain','foreign_settlement');return end
   a.settlement=data;if a.accepted then self:phase('verify');env.query(a.kind) end
  end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if a.phase=='recovery_verify' and a.recovery_query_at and not a.recovery_second_query and env.now()>=a.recovery_query_at then
   a.recovery_second_query=true;env.query(a.kind)
  elseif a.phase=='battle' and a.battle_started then env.nativeSkip(a)
  elseif a.phase=='cleanup' and env.battleReady() then
   if a.stop_loss then self:finish('skipped','ruins_defeat');return end
   self:phase('base');env.query(a.kind);return
  elseif a.phase=='verify' and env.now()>=(a.poll_at or 0) then
   a.poll_at=env.now()+2;env.query(a.kind)
  end
  if self.active and env.now()>=a.deadline then self:finish(a.mutated and 'uncertain' or 'error',a.phase..'_timeout') end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 return self
end
return M
