-- Free gifts only. Query -> one claim -> verify the same gift and refresh period.
local M = {}
function M.new(env)
    local self = {env = env, active = nil, uncertain = {}}
    function self:finish(status, reason)
        local a = self.active
        if not a then return end
        self.active = nil
        a.done({status = status, reason = reason, charge_id = a.id, gift_type = a.kind})
    end
    function self:identityValid()
        if not self.active then return false end
        if self.env.identity() ~= self.active.identity then
            self:finish('cancelled', 'role_changed'); return false
        end
        return true
    end
    function self:start(kind, done)
        if self.active then return false, 'busy' end
        if kind ~= 1 and kind ~= 2 and kind ~= 3 and kind ~= 6 then return false, 'unsupported_gift' end
        local identity = self.env.identity()
        if not identity then return false, 'no_role' end
        self.active = {kind = kind, identity = identity, phase = 'query', done = done,
            deadline = self.env.now() + self.env.timeout}
        self.env.refresh(kind)
        return true
    end
    function self:verify()
        if not self:identityValid() then return end
        local a = self.active
        a.phase, a.deadline = 'verify', self.env.now() + self.env.timeout
        self.env.refresh(a.kind)
    end
    function self:onInfo(data)
        if not self:identityValid() then return end
        local a = self.active
        if not data or data.gift_type ~= a.kind or a.phase == 'claim' then return end
        if type(data.ref_time) ~= 'number' or type(data.gift_list) ~= 'table' then
            self:finish('error', 'invalid_group'); return
        end
        local id = a.id or self.env.freeId(a.kind)
        if type(id) ~= 'number' or not self.env.isFree(a.kind, id) then
            self:finish('error', 'free_config_mismatch'); return
        end
        local gift
        for _, row in ipairs(data.gift_list) do
            if row.charge_id == id then
                if gift then self:finish('error', 'duplicate_gift'); return end
                gift = row
            end
        end
        if a.phase == 'verify' and data.ref_time ~= a.period then
            self:finish('uncertain', 'period_changed'); return
        end
        if not gift then
            self:finish(a.phase == 'verify' and 'uncertain' or 'skipped', 'gift_unavailable'); return
        end
        if type(gift.buy_count) ~= 'number' or type(gift.limit_count) ~= 'number'
            or gift.buy_count < 0 or gift.limit_count < 0 then
            self:finish('error', 'invalid_count'); return
        end
        local key = a.identity .. ':' .. a.kind .. ':' .. id .. ':' .. data.ref_time
        if a.phase == 'verify' then
            if gift.buy_count > a.before then
                self.uncertain[key] = nil
                self:finish('confirmed', 'count_increased')
            else self:finish('uncertain', 'claim_not_confirmed') end
            return
        end
        if gift.buy_count >= gift.limit_count then
            self.uncertain[key] = nil
            self:finish('skipped', 'already_claimed'); return
        end
        if self.uncertain[key] then self:finish('uncertain', 'previous_request_unresolved'); return end
        a.id, a.period, a.before, a.key = id, data.ref_time, gift.buy_count, key
        a.phase, a.deadline = 'claim', self.env.now() + self.env.timeout
        self.uncertain[key] = true
        self.env.claim(id)
    end
    function self:onReply(data)
        if not self:identityValid() then return end
        if self.active.phase == 'claim' then
            self.active.reply_code = data and data.code
            self:verify() -- code alone never proves reward receipt; failed replies also get one query
        end
    end
    function self:tick()
        if not self:identityValid() then return end
        local a = self.active
        if self.env.now() < a.deadline then return end
        if a.phase == 'claim' then self:verify()
        elseif a.phase == 'verify' then self:finish('uncertain', 'verification_timeout')
        else self:finish('error', 'query_timeout') end
    end
    function self:cancel() self:finish('cancelled', 'cancelled') end
    return self
end
return M
