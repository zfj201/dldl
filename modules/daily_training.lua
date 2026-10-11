-- Resource operations are serialized and journaled before sending. Never resend.
local M={}
local function uint(n) return type(n)=='number' and n>=0 and n%1==0 end
local function arena(kind) return kind=='arena_free' or kind=='arena_tickets' end
function M.new(env)
    local self={env=env}
    function self:log(event,detail) if env.log then env.log(event,detail or '') end end
    function self:finish(status,reason)
        local a=self.active;if not a then return end
        self:log('finish',a.kind..'|'..status..'|'..tostring(reason)..'|'..a.completed)
        if a.reconcile_only and env.reportRecovery then env.reportRecovery(status,reason) end
        self.active=nil;a.done({status=status,reason=reason,count=a.completed})
    end
    function self:valid()
        local a=self.active;if not a then return false end
        if a.identity~=env.identity() or a.day~=env.day() then
            self:finish('cancelled','role_or_day_changed');return false
        end
        return true
    end
    function self:phase(name,seconds)
        self.active.phase=name;self.active.deadline=env.now()+(seconds or 15)
        self:log('phase',self.active.kind..'|'..name)
    end
    function self:start(kind,done,target)
        if self.active then return false,'busy' end
        if not env.identity() then return false,'no_role' end
        if not arena(kind) and kind~='hero' and kind~='bone' then return false,'unknown_task' end
        if kind=='arena_tickets' and target~=10 and target~=20 then return false,'invalid_ticket_target' end
        local used,pending=env.journal(kind)
        self.active={kind=kind,done=done,target=kind=='arena_free' and 0 or (target or 1),used=used,completed=0,identity=env.identity(),day=env.day()}
        if not uint(used) or (arena(kind) and used>20) or (not arena(kind) and used>1) then self:finish('error','invalid_journal');return true end
        if pending~=0 then
            if kind=='arena_free' and env.legacyRequest and env.legacyRequest() then
                self.active.reconcile_only=true;self:phase('legacy_scope');env.query('base');return true
            end
            self:finish('uncertain','previous_request_unresolved');return true
        end
        if not env.isOpen(kind) then self:finish('skipped','not_open');return true end
        if arena(kind) then self:phase('form');env.query('form')
        elseif used==1 then self:finish('skipped','daily_target_done')
        else
            self:phase('prepare');env.query(kind);self:prepare()
        end
        return true
    end
    function self:prepare()
        if not self:valid() then return end
        local a=self.active
        local action,why=env.prepare(a.kind)
        if not action then
            if why=='awaiting_details' then return end
            self:finish(why=='no_eligible_target' and 'skipped' or 'error',why);return
        end
        a.action=action
        self:mutate(a.kind,action)
    end
    function self:mutate(name,data)
        if not self:valid() then return end
        local a=self.active
        self:log('send',a.kind..'|'..name..'|free='..tostring(data and data.free)..'|index='..tostring(data and data.index))
        local why=env.guard(a.kind,a.action)
        if arena(a.kind) and why=='challenge_cooldown' then
            a.wait_until=env.challengeNotBefore();self:phase('cooldown',math.min(a.wait_until-env.now()+15,300));return
        end
        if why then self:finish('error',why);return end
        if arena(a.kind) then a.action.sent_at=env.now();a.action.start_time=a.base.start_time;a.action.end_time=a.base.end_time end
        env.saveJournal(a.kind,a.used,1,arena(a.kind) and a.action or nil)
        self:phase('reply');env.act(name,data)
    end
    function self:arenaBase(data)
        local a=self.active
        if not uint(data.day_combat_count) or not uint(data.combat_time) then self:finish('error','invalid_arena_state');return end
        local why=env.arenaGuard(data)
        if why then self:finish('error',why);return end
        if a.kind=='arena_tickets' and data.day_combat_count>0 then self:finish('error','free_challenges_remaining');return end
        if data.day_combat_count==0 and a.used>=a.target then
            self:finish(a.completed>0 and 'confirmed' or 'skipped','daily_target_done');return
        end
        local tickets=env.tickets()
        self:log('arena_base','free='..data.day_combat_count..'|combat='..data.combat_time..'|tickets='..tostring(tickets))
        if not uint(tickets) then self:finish('error','invalid_inventory');return end
        if data.day_combat_count==0 and tickets<a.target-a.used then self:finish('error','insufficient_tickets');return end
        local until_time=math.max(tonumber(data.match_cd_time) or 0,env.challengeNotBefore())
        if until_time>env.now() then
            a.wait_until=until_time;self:phase('cooldown',math.min(until_time-env.now()+15,300));return
        end
        a.base=data;a.action={free=data.day_combat_count>0,tickets=tickets,remaining=data.day_combat_count,combat=data.combat_time}
        self:phase('opponents');env.query('opponents')
    end
    function self:rejectedVerify(data)
        local a=self.active;local b=a.action;local tickets=env.tickets()
        local same=data.day_combat_count==b.remaining and data.combat_time==b.combat and tickets==b.tickets
        local consumed=data.day_combat_count==b.remaining-(b.free and 1 or 0) and data.combat_time==b.combat+1
            and tickets==b.tickets-(b.free and 0 or 1)
        local scoped=uint(b.start_time) and uint(b.end_time) and b.start_time<=b.sent_at and b.sent_at<b.end_time
            and data.state==1 and data.start_time==b.start_time and data.end_time==b.end_time and env.now()<b.end_time
            and env.battleReady() and env.now()>=b.sent_at and (env.now()-b.sent_at<300 or (a.reconcile_only and same))
        if b.legacy and not same then scoped=false end
        self:log('reject_verify','free='..tostring(data.day_combat_count)..'|combat='..tostring(data.combat_time)..'|tickets='..tostring(tickets)..'|same='..tostring(same)..'|consumed='..tostring(consumed)..'|scoped='..tostring(scoped))
        if not scoped or (not same and not consumed) then a.reject_snapshot=nil;a.reject_retry=env.now()+env.refreshInterval();return end
        local outcome=consumed and 'consumed' or 'unchanged'
        if a.reject_snapshot==outcome then
            if consumed then a.completed=a.completed+1;if not b.free then a.used=a.used+1 end end
            env.saveJournal(a.kind,a.used,0)
            self:finish(consumed and 'confirmed' or 'error',consumed and 'rejected_but_consumption_confirmed' or 'action_rejected_unchanged');return
        end
        a.reject_snapshot=outcome;a.wait_until=env.now()+env.refreshInterval()
        self:phase('reject_wait',math.max(0,a.reject_deadline-env.now()))
    end
    -- Explicit recovery only: startup never clears or resends an unresolved mutation.
    function self:reconcilePending(kind,done,evidence)
        if self.active then return false,'busy' end
        if not arena(kind) or not env.identity() then return false,'invalid_reconciliation' end
        local used,pending=env.journal(kind)
        local baseline,why=env.recoveryBaseline(kind,evidence)
        if pending~=1 or not baseline then return false,why or 'no_pending' end
        self.active={kind=kind,done=done,used=used,completed=0,identity=env.identity(),day=env.day(),action=baseline,reconcile_only=true}
        self:log('recovery','kind='..kind..'|day='..env.day()..'|sent_at='..baseline.sent_at..'|legacy='..tostring(baseline.legacy))
        local a=self.active;a.reject_deadline=env.now()+30
        self:phase('reject_verify',30);env.query('opponents');env.query('base');return true
    end
    function self:arenaVerify()
        local a=self.active;if not a.verify then return end
        local v=a.verify;local before=a.action
        local tickets=env.tickets()
        local expected=before.free and before.tickets or before.tickets-1
        if v.combat_time==before.combat+1 and v.day_combat_count==before.remaining-(before.free and 1 or 0) and tickets==expected then
            self:log('arena_confirm','free='..before.remaining..'->'..v.day_combat_count..'|combat='..before.combat..'->'..v.combat_time..'|tickets='..before.tickets..'->'..tickets)
            a.completed=a.completed+1;if not before.free then a.used=a.used+1 end
            env.saveJournal(a.kind,a.used,0);a.verify=nil;a.settled=nil;a.accepted=nil
            -- Requery each fight: never reuse the cleared enemy list or old free quota.
            self:phase('cleanup',30)
        end
    end
    function self:onPacket(id,data)
        if not self:valid() or type(data)~='table' then return end
        local a=self.active
        local fields={};for _,k in ipairs({'code','result','choose_id','day_combat_count','combat_time','match_cd_time','is_match','state','state_time','start_time','end_time','is_skip','msg'}) do
            if data[k]~=nil then fields[#fields+1]=k..'='..tostring(data[k]) end
        end
        if data.match_list then fields[#fields+1]='list_count='..#data.match_list end
        self:log('reply',tostring(id)..'|phase='..a.phase..'|now='..env.now()..'|'..table.concat(fields,'|'))
        if not arena(a.kind) then
            local reply=a.kind=='hero' and 11003 or 11083
            if id==reply and a.phase=='reply' then
                -- Hero's result encoding is not authoritative; only the level push proves success.
                if a.kind=='bone' and data.code~=1 then self:finish('uncertain','action_rejected');return end
                self:phase('inventory');self:tick()
            end
            return
        end
        if id==11211 and a.phase=='form' and data.type==45 then
            local why=env.checkForm(data)
            if why then self:finish('error',why);return end
            a.form=data;self:phase('base');env.query('base')
        elseif id==29400 and a.phase=='base' then self:arenaBase(data)
        elseif id==29400 and a.phase=='legacy_scope' then
            local baseline,why=env.recoveryBaseline(a.kind,env.legacyEvidence(data))
            if not baseline then self:finish('uncertain',why);return end
            a.action=baseline;a.reject_deadline=env.now()+30
            self:log('recovery','legacy_v4|role=yinghe_3360:5317|day=1791666000|sent_at=1791693165|baseline=9/1/47')
            self:phase('reject_verify',30);env.query('opponents');env.query('base')
        elseif id==29400 and a.phase=='reject_verify' then self:rejectedVerify(data)
        elseif id==29400 and a.phase=='verify' then a.verify=data;self:arenaVerify()
        elseif id==29402 and a.phase=='refresh_reply' then
            if data.code~=1 then self:finish('error','refresh_rejected');return end
            self:phase('matching');a.match_query_at=env.now()+env.refreshInterval();env.query('opponents')
        elseif id==29401 and (a.phase=='opponents' or a.phase=='matching') then
            if a.phase=='opponents' then
                local until_time=math.max(tonumber(data.match_cd_time) or 0,a.last_refresh and a.last_refresh+env.refreshInterval() or 0)
                if until_time>env.now() then
                    a.wait_until=until_time;self:phase('refresh_wait',math.min(until_time-env.now()+15,300));return
                end
                a.last_refresh=env.now();self:phase('refresh_reply');env.query('match');return
            end
            if data.is_match==1 then
                -- Refresh acknowledgement precedes completion; this may still be the old list.
                self:log('matching_wait','is_match=1|list_count='..tostring(data.match_list and #data.match_list));return
            end
            if data.is_match~=0 then self:finish('error','invalid_match_state');return end
            if data.code~=1 or type(data.match_list)~='table' or #data.match_list==0 then
                self:finish('error','no_opponents');return
            end
            local why=env.checkOpponents(data)
            if why then self:finish('error',why);return end
            a.opponents=data;a.action.index=#data.match_list;a.action.opponent=data.match_list[a.action.index]
            self:log('opponent','index='..a.action.index..'|rid='..a.action.opponent.rid..'|srv='..a.action.opponent.srv_id..'|order='..tostring(a.action.opponent.order_id))
            if env.isSkip() then self:phase('choose');env.act('choose',{index=a.action.index})
            else self:phase('skip');env.act('skip') end
        elseif id==29450 and a.phase=='skip' then
            if data.code~=1 or data.is_skip~=1 then self:finish('error','skip_unavailable');return end
            self:phase('choose');env.act('choose',{index=a.action.index})
        elseif id==29446 and a.phase=='choose' then
            if data.code~=1 or data.choose_id~=a.action.index then self:finish('error','opponent_not_selected');return end
            self:mutate(a.kind,a.action)
        elseif id==29403 and a.phase=='reply' then
            if data.code~=1 then
                if data.code~=0 then self:finish('uncertain','action_rejected');return end
                env.markRejected(a.kind);a.reject_deadline=env.now()+30;self:phase('reject_verify',30);env.query('opponents');env.query('base');return
            end
            a.accepted=true;self:phase('battle',60)
            if a.settled then self:phase('verify');env.query('base') end
        elseif id==29406 and (a.phase=='reply' or a.phase=='battle') and (not data.combat_type or data.combat_type==23) then
            a.settled=true
            if a.accepted then self:phase('verify');env.query('base') end
        end
    end
    function self:tick()
        if not self:valid() then return end
        local a=self.active
        if a.phase=='cooldown' and env.now()>=a.wait_until then self:phase('base');env.query('base');return
        elseif a.phase=='matching' and env.now()<a.deadline and env.now()>=a.match_query_at then
            a.match_query_at=env.now()+env.refreshInterval();env.query('opponents');return
        elseif a.phase=='refresh_wait' and env.now()>=a.wait_until then self:phase('opponents');env.query('opponents');return
        elseif a.phase=='reject_wait' and env.now()>=a.wait_until and env.now()<a.reject_deadline then self:phase('reject_verify',a.reject_deadline-env.now());env.query('opponents');env.query('base');return
        elseif a.phase=='reject_verify' and a.reject_retry and env.now()>=a.reject_retry and env.now()<a.reject_deadline then
            a.reject_retry=nil;env.query('opponents');env.query('base');return
        elseif a.phase=='cleanup' and env.battleReady() then self:phase('base');env.query('base');return
        elseif a.phase=='prepare' then
            if env.now()>=a.deadline then self:finish('error','details_timeout');return end
            self:prepare();return
        elseif a.phase=='inventory' then
            local state,why=env.verify(a.kind,a.action)
            if state then
                env.saveJournal(a.kind,1,0);a.completed=1;self:finish('confirmed','state_confirmed');return
            elseif why then self:finish('uncertain',why);return end
        elseif a.phase=='verify' then self:arenaVerify();if not self.active then return end end
        if env.now()>=a.deadline then
            local sent=a.phase=='reply' or a.phase=='battle' or a.phase=='verify' or a.phase=='inventory' or a.phase=='reject_verify' or a.phase=='reject_wait'
            self:finish(sent and 'uncertain' or 'error',a.phase..'_timeout')
        end
    end
    function self:cancel() self:finish('cancelled','cancelled') end
    return self
end
return M
