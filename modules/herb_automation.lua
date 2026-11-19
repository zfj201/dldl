local M = {MAX_MATCHES = 11, MAX_SECONDS = 600, MATCH_BUDGET = 100}

function M.rewardKind(items)
    local kind
    for _, item in ipairs(items or {}) do
        local k = item.item_bid == 63566 and 'zero' or item.item_bid == 63567 and 'full' or nil
        if k and type(item.item_num) == 'number' and item.item_num > 0 then
            if kind and kind ~= k then return end
            kind = k
        end
    end
    return kind
end

local function uint(n) return type(n) == 'number' and n >= 0 and n % 1 == 0 end

function M.daily(info, tiers, count)
    if type(info.day_list) ~= 'table' or type(tiers) ~= 'table' or #tiers == 0 or not uint(count) then return end
    local claimed, ids, total, ready, got = {}, {}, 0, 0, 0
    for _, v in ipairs(info.day_list) do claimed[v.day_id] = true end
    for _, v in ipairs(tiers) do
        if not uint(v.reward_id) or not uint(v.day_limit) or ids[v.reward_id] then return end
        ids[v.reward_id] = true
        total = total + 1
        if claimed[v.reward_id] then got = got + 1
        elseif count >= v.day_limit then ready = ready + 1 end
    end
    return {total = total, claimed = got, ready = ready, count = count}
end

function M.new(env)
    local self = {}

    function self:finish(status, reason)
        local a = self.active
        if not a then return end
        self.active = nil
        a.phase, a.status, a.reason = nil, status, reason
        if a.done then a.done(a) end
    end

    function self:start(scope, done, changed)
        if self.active then return false end
        local now = env.now()
        self.active = {scope=scope, done=done, changed=changed, attempts=0, matches=0,
            until_time=now + M.MAX_SECONDS, status='running'}
        self:query()
        return true
    end

    function self:query()
        local a = self.active
        a.phase, a.deadline, a.info = 'query', env.now() + 15, nil
        env.query()
    end

    function self:onInfo(info)
        local a = self.active
        if a and info.camp_id == a.scope.camp and type(info.end_time) == 'number'
            and (not a.scope.ends or info.end_time == a.scope.ends) then
            a.scope.ends = info.end_time
            a.activity_status = info.status
            if a.phase == 'query' then a.info = info end
        elseif a and a.scope.ends and info.camp_id == a.scope.camp and type(info.end_time) == 'number' then
            a.scope_changed = true
        end
    end

    function self:onReply(action, code)
        local a = self.active
        if a and a.phase == action then a.reply = code end
    end

    function self:onReady(data)
        local a = self.active
        if not a or a.phase ~= 'matching' or type(data.end_time) ~= 'number' then return end
        for _, v in ipairs(data.match_list or {}) do
            if env.isSelf(v) then
                if v.is_ready == 0 and not a.ready_sent then a.invite_end = data.end_time end
                return
            end
        end
    end

    function self:onRound(data)
        local a = self.active
        if not a or (a.phase ~= 'matching' and a.phase ~= 'playing') then return end
        if not uint(data.round) or data.round == 0 or type(data.end_time) ~= 'number' then return end
        if not a.round or data.round > a.round.round then
            a.phase, a.round = 'playing', data
            a.changed(a)
        end
    end

    function self:onResult(data)
        local a = self.active
        if not a or (a.phase ~= 'playing' and (a.phase ~= 'matching' or not a.ready_sent)) then return end
        for _, player in ipairs(data.list or {}) do
            if env.isSelf(player) then
                a.matches = a.matches + 1
                a.phase, a.deadline = 'settled', env.now() + 1
                a.outcome = player.num
                a.changed(a)
                return
            end
        end
    end

    function self:tick()
        local a = self.active
        if not a then return end
        local now = env.now()
        local why = env.guard(a.scope)
        if why or a.scope_changed then return self:finish('uncertain', why or 'scope_changed') end
        if now >= a.until_time then return self:stop('partial', 'run_limit') end

        if a.phase == 'query' and a.info then
            local info = a.info
            local daily = env.daily(a.scope, info)
            if not daily then return self:finish('uncertain', 'invalid_state') end
            a.daily = daily
            a.eggs = env.load(a.scope)
            a.changed(a)
            if a.claim_pending then
                if daily.claimed < a.claim_pending then return self:finish('uncertain', 'claim_unconfirmed') end
                a.claim_pending = nil
            end
            if info.status ~= 0 then return self:finish('skipped', 'manual_game') end
            if daily.ready > 0 then
                a.phase, a.deadline, a.reply = 'claim', now + 15, nil
                a.claim_pending = daily.claimed + daily.ready
                env.claim()
            elseif daily.claimed == daily.total and a.eggs.zero and a.eggs.full then
                return self:finish('done', 'all_done')
            elseif a.attempts >= M.MAX_MATCHES or now + M.MATCH_BUDGET >= a.until_time then
                return self:finish('partial', 'run_limit')
            elseif env.matchClosed(a.scope) then
                return self:finish('partial', 'matching_closed')
            else
                -- Secure daily progress first; then alternate between unconfirmed goals.
                local hunt_zero = not a.eggs.zero and (a.eggs.full or a.attempts % 2 == 0)
                a.target = daily.claimed == daily.total and hunt_zero and 'zero' or 'full'
                a.attempts = a.attempts + 1
                a.phase, a.deadline, a.reply = 'matching', now + M.MATCH_BUDGET, nil
                a.invite_end, a.ready_sent, a.round, a.selected, a.result_window = nil, nil, nil, nil, nil
                env.match()
                a.changed(a)
            end
        elseif a.phase == 'claim' and (a.reply ~= nil or now >= a.deadline) then
            if a.reply ~= nil and a.reply ~= 1 then return self:finish('partial', 'action_rejected') end
            self:query() -- Read back once even when the acknowledgement was lost.
        elseif now >= a.deadline and a.phase ~= 'settled' then
            return self:stop('uncertain', 'response_timeout')
        elseif a.phase == 'matching' and a.reply ~= nil and a.reply ~= 1 then
            return self:finish('partial', 'action_rejected')
        elseif a.phase == 'matching' and a.invite_end and now < a.invite_end and not a.ready_sent then
            a.ready_sent = true
            env.ready()
        elseif a.phase == 'playing' and a.round and a.selected ~= a.round.round and now < a.round.end_time then
            local field = env.field(a.target, a.round)
            if field then
                a.selected = a.round.round
                env.select(field)
            end
        elseif a.phase == 'settled' and now >= a.deadline then
            env.closeResult()
            self:query()
        end
    end

    function self:stop(status, reason)
        local a = self.active
        if a and not a.scope_changed and a.phase == 'matching' and a.activity_status == 1 and not a.ready_sent and not env.guard(a.scope) then
            env.cancelMatch()
        end
        self:finish(status or 'cancelled', reason or 'cancelled')
    end
    return self
end

return M
