-- Historical prototype: cultivation supplies only; NOT the requested daily free gifts. See modules/README.md.
-- Reversible runtime prototype for APK 1.3.8 / 215; live injection not validated.
-- Load after the original helper classes, before opening its windows.
-- Usage: extension = require(...).install(require(...daily_sign))
-- Unload with extension.uninstall() after closing helper windows.
local M = {}
local active_install
function M.install(Sign)
    assert(not active_install, 'extension already installed')
    assert(OneKeyBurdenMainWindow and OneKeyBurdenAutoWindow and OneKeyBurdenAutoItem)
    local controller = OneKeyBurdenController:getInstance()
    local welfare = WelfareController:getInstance()
    assert(not controller.onekeyburden_main_window and not controller.onekeyburden_auto_window,
        'close helper windows before installing')
    local bus, clock = GlobalEvent:getInstance(), GlobalTimeTicket:getInstance()
    local POS, TYPE = -14101, OneKeyBurdenConst.SimplifyType.DAILY_TASK
    local list = OneKeyBurdenConst.SimplifyTypeList[TYPE]
    for _, v in ipairs(list) do assert(v.id ~= POS, 'local task ID collision') end
    local item = {id = POS, title = TI18N('自定义：每日签到'), is_title = true,
        is_single_select = true, option_list = {{TI18N('开启'), TRUE}, {TI18N('关闭'), FALSE}}}
    table.insert(list, item)
    local function identity()
        local role = RoleController:getInstance():getRoleVo()
        if not role or not role.rid or not role.srv_id then return nil end
        return tostring(role.srv_id) .. ':' .. tostring(role.rid) .. ':' .. tostring(role)
    end
    local runner = Sign.new({identity = identity, timeout = 10,
        now = function() return GameNet:getInstance():getTime() end,
        refresh = function() welfare:sender14100() end,
        claim = function() welfare:sender14101() end})
    local patches, bindings = {}, {}
    local timer, owner
    local function patch(object, key, wrap)
        local old = object[key]; assert(type(old) == 'function', key)
        local new = wrap(old); object[key] = new
        table.insert(patches, {object = object, key = key, old = old, new = new})
    end
    local function cleanup()
        if timer then clock:remove(timer); timer = nil end
        for _, token in ipairs(bindings) do bus:UnBind(token) end
        bindings = {}; owner = nil
    end
    patch(OneKeyBurdenMainWindow, 'getPosExecuteData', function(old)
        return function(self, key, cfg)
            local data = old(self, key, cfg)
            if cfg.id == POS then data.is_open = FALSE end -- opt-in, session only
            return data
        end
    end)
    patch(controller, 'sender31601', function(old)
        return function(self, values)
            local filtered = {}
            for _, group in ipairs(values) do
                local copy = {type = group.type, type_list = {}}
                for _, row in ipairs(group.type_list) do
                    if row.pos ~= POS then table.insert(copy.type_list, row) end
                end
                if #copy.type_list > 0 then table.insert(filtered, copy) end
            end
            if #filtered > 0 then return old(self, filtered) end
        end
    end)
    local original_update = OneKeyBurdenAutoWindow.updateDataList
    patch(OneKeyBurdenAutoWindow, 'updateDataList', function(old)
        return function(self, data)
            local row = self.execute_request_list[self.execute_index]
            if not row or row.pos == POS then return end
            if not data or data.type ~= row.type or data.pos ~= row.pos then return end
            return old(self, data)
        end
    end)
    patch(OneKeyBurdenAutoWindow, 'requestTask', function(old)
        return function(self)
            local row = self.execute_request_list[self.execute_index]
            if not row or row.pos ~= POS then return old(self) end
            if owner then return end
            owner = self
            local function done(result)
                cleanup(); row.local_result = result.status
                if result.status == 'success' or result.status == 'confirmed' or result.status == 'skipped' then
                    original_update(self, {args = {}})
                else
                    self.is_execute_finish = true
                    self.stop_btn_lb:setString(TI18N('关闭'))
                    self:updateLoopList()
                end
            end
            bindings = {
                bus:Bind(WelfareEvent.Update_Sign_Info, function() runner:onInfo(welfare:getModel():getSignData()) end),
                bus:Bind(WelfareEvent.Sign_Success, function(day) runner:onSuccess(day, welfare:getModel():getSignData()) end)
            }
            timer = clock:add(function() runner:tick() end, 0.5)
            local ok, why = runner:start(done)
            if not ok then done({status = 'error', reason = why}) end
        end
    end)
    patch(OneKeyBurdenAutoItem, 'setData', function(old)
        return function(self, data, index)
            old(self, data, index)
            if data.pos == POS and data.local_result then
                local text = {success = '签到成功', confirmed = '已核实签到', skipped = '已跳过',
                    uncertain = '结果未确认', error = '执行失败', cancelled = '已停止'}
                self.un_finish_lb:setString(TI18N(text[data.local_result] or '结果未确认'))
            end
        end
    end)
    patch(OneKeyBurdenAutoWindow, 'close_callback', function(old)
        return function(self, ...)
            if owner == self then
                -- Detach callbacks before cancel, so closing does not redraw a deleted window.
                if runner.active then runner.active.done = function() end end
                runner:cancel(); cleanup()
            end
            return old(self, ...)
        end
    end)
    local installation = {runner = runner}
    function installation.uninstall()
        assert(not controller.onekeyburden_main_window and not controller.onekeyburden_auto_window,
            'close helper windows before uninstalling')
        for _, p in ipairs(patches) do assert(p.object[p.key] == p.new, 'another patch replaced '..p.key) end
        runner:cancel(); cleanup()
        for i = #patches, 1, -1 do local p = patches[i]; p.object[p.key] = p.old end
        for i, v in ipairs(list) do if v == item then table.remove(list, i); break end end
        active_install = nil
    end
    active_install = installation
    return installation
end
return M
