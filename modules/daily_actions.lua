-- Serialized daily actions. Every mutation is journaled before send; never retry it.
local M = {}
local function integer(v) return type(v)=='number' and v>=0 and v==math.floor(v) end
function M.new(env)
    local self = {env=env}
    function self:finish(status, reason)
        local a=self.active; if not a then return end
        self.active=nil; a.done({status=status,reason=reason,count=a.completed or 0})
    end
    function self:valid()
        local a=self.active; if not a then return false end
        if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
        return true
    end
    function self:phase(p)
        self.active.phase=p;self.active.deadline=env.now()+12
    end
    function self:query()
        self:phase('query');env.query(self.active.kind)
    end
    function self:start(kind, done, count)
        if self.active then return false,'busy' end
        if not env.identity() then return false,'no_role' end
        if kind~='sweep' and kind~='pantheon' and kind~='domain' and kind~='summon' then return false,'unknown_task' end
        if kind=='summon' and count~=10 and count~=20 then return false,'invalid_summon_count' end
        self.active={kind=kind,done=done,identity=env.identity(),day=env.day(),target=count,completed=0,visited={}}
        if not env.isOpen(kind) then self:finish('skipped','not_open');return true end
        local used,pending=env.journal(kind)
        if pending~=0 then self:finish('uncertain','previous_request_unresolved');return true end
        if kind=='summon' then
            if not integer(used) or used>20 or used%10~=0 then self:finish('error','invalid_journal');return true end
            self.active.used=used
            if used>=count then self:finish('skipped','daily_target_done');return true end
            local why=env.summonGuard(count-used)
            if why then self:finish(why=='insufficient_contracts' and 'skipped' or 'error',why);return true end
        end
        self:query();return true
    end
    function self:send(action)
        if not self:valid() then return end
        local a=self.active;a.action=action
        env.saveJournal(a.kind,a.used or 0,1)
        self:phase('reply');env.act(a.kind,action)
    end
    function self:summon()
        local a=self.active
        local why=env.summonGuard(a.target-a.used)
        if why then self:finish(why=='insufficient_contracts' and 'skipped' or 'error',why);return end
        a.inventory=env.contracts()
        self:send({group_id=200,times=10,recruit_type=4})
    end
    function self:onInfo(kind,data)
        if not self:valid() then return end
        local a=self.active
        if a.kind~=kind or (a.phase~='query' and a.phase~='verify') then return end
        if kind=='summon' then self:summon();return end
        local state,why=env.inspect(kind,data,a)
        if not state then self:finish(a.phase=='verify' and 'uncertain' or 'error',why or 'invalid_state');return end
        if a.phase=='verify' then
            if not state.confirmed then self:finish('uncertain','action_not_confirmed');return end
            env.saveJournal(kind,0,0);a.completed=a.completed+1
            if kind=='sweep' then
                a.visited[a.action.type]=true;self:query()
            else self:finish('confirmed','state_confirmed') end
        elseif state.action then self:send(state.action)
        else self:finish(a.completed>0 and 'confirmed' or 'skipped','no_remaining_action') end
    end
    function self:onReply(kind,data)
        if not self:valid() then return end
        local a=self.active
        if a.kind~=kind or a.phase~='reply' then return end
        if not env.matches(kind,data,a.action) then return end
        if kind=='summon' then
            -- An explicit failure is still not automatically resent.
            if data.code~=1 then self:finish('uncertain','summon_rejected');return end
            a.used=a.used+10;a.completed=a.completed+10
            env.saveJournal(kind,a.used,0)
            if a.used>=a.target then self:finish('confirmed','summon_confirmed')
            else self:phase('inventory') end
        else self:phase('verify');env.query(kind) end
    end
    function self:tick()
        if not self:valid() then return end
        local a=self.active
        if a.phase=='inventory' and env.contracts()<=a.inventory-10 then self:summon();return end
        if env.now()<a.deadline then return end
        if a.phase=='reply' and a.kind~='summon' then self:phase('verify');env.query(a.kind)
        else self:finish(a.phase=='query' and 'error' or 'uncertain',a.phase..'_timeout') end
    end
    function self:cancel() self:finish('cancelled','cancelled') end
    return self
end
return M
