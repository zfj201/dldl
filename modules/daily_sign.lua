-- Historical prototype: cultivation supplies only; NOT the requested daily free gifts. See modules/README.md.
-- Daily ordinary sign-in state machine. No networking at module load time.
-- env: identity(), refresh(), claim(), now(), timeout; caller forwards events.
local M = {}
function M.new(env)
    local self = {env = env, active = nil, uncertain = {}}
    function self:finish(status, reason)
        local a = self.active
        if not a then return end
        self.active = nil
        a.done({status = status, reason = reason})
    end
    function self:start(done)
        if self.active then return false, 'busy' end
        local identity = self.env.identity()
        if not identity then return false, 'no_role' end
        self.active = {identity = identity, phase = 'query', done = done,
            deadline = self.env.now() + self.env.timeout}
        self.env.refresh()
        return true
    end
    function self:checkIdentity()
        if not self.active then return false end
        if self.env.identity() ~= self.active.identity then
            self:finish('cancelled', 'role_changed')
            return false
        end
        return true
    end
    function self:onInfo(data)
        if not self:checkIdentity() then return end
        local a = self.active
        if not data or type(data.day) ~= 'number' or type(data.month) ~= 'number'
            or type(data.endTime) ~= 'number' or type(data.status) ~= 'number' then
            self:finish('error', 'invalid_state'); return
        end
        local key = a.identity .. ':' .. data.endTime .. ':' .. data.month .. ':' .. data.day
        if a.phase == 'claim' then return end -- unsolicited state is not a claim acknowledgement
        if a.phase == 'verify' then
            if key ~= a.key then self:finish('uncertain', 'period_changed'); return end
            if data.status == 1 or data.status == 2 then
                self.uncertain[key] = nil
                self:finish('confirmed', 'state_verified')
            else self:finish('uncertain', 'claim_not_confirmed') end
            return
        end
        if data.status == 1 or data.status == 2 then
            self.uncertain[key] = nil
            self:finish('skipped', 'already_signed'); return
        end
        if data.status ~= 0 then self:finish('skipped', 'unsupported_status'); return end
        if self.uncertain[key] then self:finish('uncertain', 'previous_request_unresolved'); return end
        a.key, a.day, a.month, a.endTime = key, data.day, data.month, data.endTime
        a.phase, a.deadline = 'claim', self.env.now() + self.env.timeout
        self.uncertain[key] = true -- retained across cancellation and retry in this session
        self.env.claim()
    end
    function self:onSuccess(day, data)
        if not self:checkIdentity() then return end
        local a = self.active
        if a.phase ~= 'claim' and a.phase ~= 'verify' then return end
        if day == a.day and data and data.day == a.day and data.month == a.month
            and data.endTime == a.endTime and (data.status == 1 or data.status == 2) then
            self.uncertain[a.key] = nil
            self:finish('success', 'sign_success_event')
        end
    end
    function self:tick()
        if not self:checkIdentity() then return end
        local a = self.active
        if self.env.now() < a.deadline then return end
        if a.phase == 'claim' then
            a.phase, a.deadline = 'verify', self.env.now() + self.env.timeout
            self.env.refresh() -- never automatically resend a claim
        elseif a.phase == 'verify' then self:finish('uncertain', 'verification_timeout')
        else self:finish('error', 'query_timeout') end
    end
    function self:cancel()
        self:finish('cancelled', 'cancelled')
    end
    return self
end
return M
