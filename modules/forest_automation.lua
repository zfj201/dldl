-- Three daily defenders; only an owned, confirmed defeat permits a lower star.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function validList(d)
 if type(d)~='table' or type(d.wood_defender_base)~='table' or #d.wood_defender_base~=3 or type(d.use_partner_list)~='table' then return end
 local out={}
 for _,v in ipairs(d.wood_defender_base) do
  if not uint(v.defender_id) or v.defender_id<1 or v.defender_id>3 or out[v.defender_id] or not uint(v.now_star) or v.now_star>5
   or not uint(v.rid) or type(v.srv_id)~='string' then return end
  out[v.defender_id]=v
 end
 for _,v in ipairs(d.use_partner_list) do
  if not out[v.defender_id] or type(v.partner_list)~='table' then return end
  for _,h in ipairs(v.partner_list) do if not uint(h.partner_id) then return end end
 end
 return out
end
local function target(v) return tostring(v.rid)..':'..v.srv_id end
function M.new(env)
 local self={env=env}
 function self:changed() local a=self.active;if a.changed then a.changed(a) end end
 function self:save() env.save(self.active.record) end
 function self:phase(p,seconds) local a=self.active;a.phase=p;a.deadline=env.now()+(seconds or 25) end
 function self:finish(status,reason)
  local a=self.active;if not a then return end;self.active=nil;a.status=status;a.reason=reason
  if a.done then a.done(a) end
 end
 function self:valid()
  local a=self.active;if not a then return end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return end
  local why=env.guard();if why then self:finish(a.record.pending and 'uncertain' or 'skipped',why);return end
  return true
 end
 function self:queryBase()
  local a=self.active;a.base=nil;a.info=nil;a.list=nil;a.form=nil;a.started=nil;a.result=nil;a.skip_sent=nil
  self:phase('base');env.query('base')
 end
 function self:start(star,done,changed)
  if self.active then return false,'busy' end
  if not uint(star) or star<1 or star>5 then return false,'invalid_star' end
  if not env.identity() then return false,'no_role' end
  local r=env.load() or {};if type(r)~='table' then return false,'invalid_state' end
  if r.day~=env.day() then r={day=env.day(),defenders={}} end
  if type(r.defenders)~='table' then return false,'invalid_state' end
  self.active={identity=env.identity(),day=env.day(),star=star,done=done,changed=changed,record=r,entries={},attempts={}}
  if self:valid() then self:queryBase() end;return true
 end
 function self:onPacket(id,d)
  if not self:valid() then return end
  local a=self.active
  if id==31900 and a.phase=='base' then a.base=d
  elseif id==31901 and a.phase=='info' then a.info=d
  elseif id==31903 and (a.phase=='info' or a.phase=='verify') then a.list=d
  elseif id==11211 and (a.phase=='form' or a.phase=='form_verify') and d.type==env.formType(a.id) then a.form=d
  elseif id==11212 and a.phase=='save' and d.type==env.formType(a.id) then
   if d.code~=1 then self:finish('error','formation_rejected');return end
   a.form=nil;self:phase('form_verify');env.query('form',a.id)
  elseif id==20060 and a.phase=='view' and d.combat_type==82 then
   if d.type~=0 then self:finish('skipped','battle_busy');return end
   self:phase('challenge_ready')
  elseif id==31906 and a.phase=='battle' and not a.started then
   if d.code~=1 then a.record.pending=nil;self:save();self:finish('error','challenge_rejected') end
  end
 end
 function self:onBattleStart(d)
  local a=self.active
  if a and self:valid() and a.phase=='battle' and d.combat_type==82 then
   a.started=true;a.skip_sent=nil;self:changed()
  end
 end
 function self:onBattleEnd(d)
  local a=self.active
  if a and self:valid() and a.phase=='battle' and a.started and d.combat_type==82 then
   if d.result~=1 and d.result~=2 and d.result~=0 then self:finish('uncertain','invalid_result');return end
   a.result=d.result;a.list=nil;self:phase('settle');a.poll_at=env.now()+1;self:changed()
  end
 end
 function self:select()
  local a=self.active;local list=validList(a.list)
  if not list or not a.info or not uint(a.info.level) or type(a.info.partner_bids)~='table' then self:finish('error','invalid_state');return end
  for _,h in ipairs(a.info.partner_bids) do if not uint(h.bid) then self:finish('error','invalid_state');return end end
  local pending=a.record.pending
  if pending then
   local v=list[pending.id]
   if not v or pending.target~=target(v) or not uint(pending.star) or pending.star<1 or pending.star>5 then self:finish('uncertain','request_unresolved');return end
   if v.now_star<pending.star then self:finish('uncertain','request_unresolved');return end
   a.record.defenders[tostring(pending.id)]={target=target(v),won=v.now_star};a.record.pending=nil;self:save()
  end
  a.entries={}
  local chosen
  for i=1,3 do
   local v=list[i];local r=a.record.defenders[tostring(i)]
   if r and r.target~=target(v) then self:finish('skipped','opponents_changed');return end
   local won=v.now_star>0 or (r and r.won)
   local exhausted=r and r.next_star==0
   a.entries[i]={id=i,star=v.now_star,status=won and 'won' or exhausted and 'exhausted' or 'waiting'}
   if not chosen and not won and not exhausted then chosen=i end
  end
  self:changed()
  if not chosen then self:finish('confirmed','forest_complete');return end
  a.id=chosen;a.target=target(list[chosen]);a.before=list[chosen].now_star
  local r=a.record.defenders[tostring(chosen)];a.current_star=math.min(a.star,r and r.next_star or a.star)
  if not uint(a.current_star) or a.current_star<1 then self:finish('error','invalid_state');return end
  a.form=nil;self:phase('form');env.query('form',a.id)
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if env.now()>=a.deadline then self:finish(a.record.pending and 'uncertain' or 'error',a.phase..'_timeout');return end
  if a.phase=='base' and a.base then
   local b=a.base
   if not uint(b.state) or b.state>3 or not uint(b.start_time) or not uint(b.end_time) then self:finish('error','invalid_state');return end
   if b.state~=2 then self:finish('skipped','non_battle_period');return end
   if b.start_time>env.now() or b.end_time<=env.now() then self:finish('skipped','non_battle_period');return end
   if a.record.season and a.record.season~=b.start_time then self:finish('skipped','season_changed');return end
   a.record.season=b.start_time;self:phase('info');env.query('info')
  elseif a.phase=='info' and a.info and a.list then self:select()
  elseif a.phase=='form' and a.form then
   local expected,why=env.fill(a.form,a.info,a.list,a.id)
   if not expected then self:finish('skipped',why or 'formation_insufficient');return end
   a.expected=expected
   if env.sameForm(a.form,expected) then self:phase('ready',180)
   else self:phase('save');env.saveForm(expected);self:changed() end
  elseif a.phase=='form_verify' and a.form then
   if not env.sameForm(a.form,a.expected) then self:finish('error','formation_mismatch');return end
   self:phase('ready',180)
  elseif a.phase=='ready' then
   if a.base.end_time<=env.now() then self:finish('skipped','non_battle_period');return end
   local form=env.fill(a.expected,a.info,a.list,a.id)
   if not form or not env.sameForm(form,a.expected) then self:finish('skipped','formation_changed');return end
   if not env.battleReady() then return end
   self:phase('view');env.enter()
  elseif a.phase=='challenge_ready' then
   if not env.battleReady() then self:finish('skipped','battle_busy');return end
   a.record.pending={id=a.id,star=a.current_star,target=a.target};self:save()
   a.entries[a.id]={id=a.id,star=a.current_star,status='fighting'}
   self:phase('battle',180);env.challenge(a.id,a.current_star);self:changed()
  elseif a.phase=='battle' and a.started then env.skip(a)
  elseif a.phase=='settle' and env.now()>=a.poll_at then
   self:phase('verify');a.list=nil;env.query('list')
  elseif a.phase=='verify' and a.list then
   local l=validList(a.list);local v=l and l[a.id]
   if not v or target(v)~=a.target then self:finish('uncertain','opponents_changed');return end
   if (a.result==1 and v.now_star<a.current_star) or (a.result~=1 and v.now_star~=a.before) then
    -- A stale query may race settlement. Retry reads, never repeat the fight.
    a.list=nil;a.poll_at=env.now()+2;self:phase('settle',15);a.verify_retries=(a.verify_retries or 0)+1
    if a.verify_retries>=6 then self:finish('uncertain','result_mismatch') end;return
   end
   a.verify_retries=0
   local r={target=a.target}
   if a.result==1 then r.won=v.now_star else r.next_star=a.current_star-1 end
   a.record.defenders[tostring(a.id)]=r;a.record.pending=nil;self:save()
   a.attempts[#a.attempts+1]={id=a.id,star=a.current_star,result=a.result}
   a.entries[a.id]={id=a.id,star=a.current_star,status=a.result==1 and 'won' or r.next_star==0 and 'exhausted' or 'downgrade'}
   self:phase('cleanup');self:changed()
  elseif a.phase=='cleanup' and env.cleanup() then self:queryBase() end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 return self
end
return M
