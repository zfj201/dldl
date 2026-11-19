local M = {POS = -2101768}
local BID = 93111
local reasons = {
    all_done='今日奖励与本期彩蛋已全部确认', run_limit='已达本次运行上限', not_open='活动未开放或已结束',
    matching_closed='活动已停止匹配', manual_game='已有对局或活动窗口，已跳过',
    invalid_state='活动数据待核实', connection='连接中断', scope_changed='角色、游戏日或活动期已变化',
    action_rejected='游戏未接受操作', claim_unconfirmed='领取结果待核实',
    response_timeout='等待游戏响应超时', runtime_error='执行异常', cancelled='已中断',
}

function M.bind(Herb, installed)
    local TYPE, POS = installed.limited.type, M.POS
    local rows = OneKeyBurdenConst.SimplifyTypeList[TYPE]
    local helper = OneKeyBurdenController:getInstance()
    local clock = GlobalTimeTicket:getInstance()
    local pm, ud = ProtoMgr:getInstance(), cc.UserDefault:getInstance()
    local row = {id=POS, title='仙草大作战·每日奖励与彩蛋', is_title=true, is_single_select=true,
        option_list={{'开启',TRUE},{'关闭',FALSE}}, default_option=FALSE}
    local patches, runner, timer, owner, observed = {}
    local function game() return CatchFairyGrassController and CatchFairyGrassController:getInstance() end
    local function now() return GameNet:getInstance():getTime() end
    local function day() return math.floor((now() + 3 * 3600) / 86400) end
    local function role() return RoleController:getInstance():getRoleVo() end
    local function isSelf(v) local r=role(); return r and r:isSameRole(v.srv_id, v.rid) end
    local function roleKey()
        local r = role()
        if r and r.rid and r.srv_id then return 'dldl_herb_v1:' .. r.srv_id .. ':' .. r.rid end
    end
    local function activity()
        return ActionController:getInstance():getActionSubTabVo(BID)
    end
    local function stopTimer()
        if timer then clock:remove(timer); timer = nil end
    end
    local function key(s, kind) return s.key .. ':' .. s.camp .. ':' .. s.ends .. ':' .. kind end
    local function load(s)
        if not s.ends then return {} end
        return {zero=ud:getBoolForKey(key(s, 'zero'), false), full=ud:getBoolForKey(key(s, 'full'), false)}
    end
    local function guard(s)
        if not GameNet:getInstance():IsServerConnect() then return 'connection' end
        local v = activity()
        if s.role ~= role() or s.key ~= roleKey() or s.day ~= day() or s.ctrl ~= game() then return 'scope_changed' end
        if not v or v.camp_id ~= s.camp or (s.ends and now() >= s.ends) then return 'not_open' end
    end
    local function safe(fn)
        local ok, err = pcall(fn)
        if ok then return end
        print('[dldl_herb] ' .. tostring(err))
        if runner and runner.active then runner:finish('uncertain', 'runtime_error') end
    end
    local function patch(obj, name, wrap)
        local old = assert(obj[name], name)
        local p = {obj=obj, name=name, own=rawget(obj, name), new=wrap(old)}
        obj[name] = p.new
        patches[#patches+1] = p
    end
    local function release()
        stopTimer()
        owner = nil
        if runner and runner.active then runner.active.done = nil; safe(function() runner:stop() end) end
    end
    local function restore()
        release()
        for i = #patches, 1, -1 do
            local p = patches[i]
            if rawget(p.obj, p.name) == p.new then rawset(p.obj, p.name, p.own) end
        end
        for i = #rows, 1, -1 do if rows[i] == row then table.remove(rows, i) end end
    end

    local ok, err = pcall(function()
        runner = Herb.new({now=now, isSelf=isSelf, load=load, guard=guard,
            daily=function(s, info)
                local cfg = HolidayHerbGameData
                local p = cfg and cfg.data_project_data and cfg.data_project_data[s.camp]
                local tiers = p and cfg.data_day_list and cfg.data_day_list[p.project_id]
                local n = p and BackpackController:getInstance():getModel():getItemNumByBid(p.herb_bid)
                return Herb.daily(info, tiers, n)
            end,
            matchClosed=function(s)
                local constants = HolidayHerbGameData and HolidayHerbGameData.data_constant
                local cfg = constants and constants.end_time
                local seconds = cfg and cfg.val
                return type(seconds) ~= 'number' or now() + seconds >= s.ends
            end,
            field=function(target, data)
                local const = CatchFairyGrassConst
                if not const or not const.checkPlayerSelectList then return end
                local seat
                for _, v in ipairs(data.field_list or {}) do if isSelf(v) then seat = v.field_id; break end end
                if seat ~= 2 and seat ~= 4 and seat ~= 6 and seat ~= 8 then return end
                local allowed = const.checkPlayerSelectList(seat)
                if target == 'zero' then return allowed[5] and 5 or nil end
                local best, count
                for _, v in ipairs(data.field_list) do
                    if allowed[v.field_id] and v.field_id ~= 5 and type(v.num) == 'number'
                        and (not count or v.num > count) then best, count = v.field_id, v.num end
                end
                return best
            end,
            query=function() game():sender15100() end,
            match=function() game():sender15101() end,
            cancelMatch=function() game():sender15102() end,
            ready=function() game():sender15103() end,
            select=function(id) game():sender15105(id) end,
            claim=function() game():sender15106(CatchFairyGrassConst.RewardType.day, 0) end,
            closeResult=function()
                local a, ctrl = runner.active, game()
                if a.result_window and ctrl.catchfairygrass_end_window == a.result_window then
                    ctrl:openCatchFairyGrassEndWindow(false)
                end
            end,
        })

        patch(pm, 'cmd_callback', function(old) return function(obj, id, d, ...)
            local result = old(obj, id, d, ...)
            if type(d) ~= 'table' then return result end
            if id == 15100 or id == 16436 then safe(function()
                local v, r, k = activity(), role(), roleKey()
                if id == 15100 then
                    if v and r and k and v.camp_id == d.camp_id and type(d.end_time) == 'number' and now() < d.end_time then
                        observed = {role=r, key=k, camp=d.camp_id, ends=d.end_time}
                    end
                elseif observed and d.bid == BID and v and v.camp_id == observed.camp and r == observed.role
                    and k == observed.key and now() < observed.ends then
                    -- A diamond amount alone cannot identify an egg.
                    local kind = Herb.rewardKind(d.item_list)
                    if kind then ud:setBoolForKey(key(observed, kind), true); ud:flush() end
                end
            end) end
            local a = runner.active
            if a and id >= 15100 and id <= 15110 then safe(function()
                if a.scope_changed or guard(a.scope) then return end
                if id == 15100 then runner:onInfo(d)
                elseif id == 15101 then runner:onReply('matching', d.code)
                elseif id == 15106 then runner:onReply('claim', d.code)
                elseif id == 15109 then runner:onReady(d)
                elseif id == 15110 then runner:onRound(d)
                elseif id == 15108 then
                    runner:onResult(d)
                    if a.phase == 'settled' then a.result_window = a.scope.ctrl.catchfairygrass_end_window end
                end
            end) end
            return result
        end end)

        patch(OneKeyBurdenMainWindow, 'getPosExecuteData', function(old) return function(w, t, c)
            local d = old(w, t, c)
            local k = roleKey()
            if c.id == POS then d.is_open = k and ud:getBoolForKey(k .. ':enabled', false) and TRUE or FALSE end
            return d
        end end)
        patch(helper, 'sender31601', function(old) return function(obj, groups)
            local filtered = {}
            for _, g in ipairs(groups) do
                if g.type == TYPE then
                    local keep, k = {}, roleKey()
                    for _, r in ipairs(g.type_list) do
                        if r.pos == POS then
                            if k then ud:setBoolForKey(k .. ':enabled', r.is_open == TRUE); ud:flush() end
                        else keep[#keep+1] = r end
                    end
                    if #keep > 0 then filtered[#filtered+1] = {type=g.type, type_list=keep} end
                else filtered[#filtered+1] = g end
            end
            if #filtered > 0 then return old(obj, filtered) end
        end end)
        patch(OneKeyBurdenAutoWindow, 'updateDataList', function(old) return function(w, ...)
            local r = w.execute_request_list[w.execute_index]
            if r and r.type == TYPE and r.pos == POS then return end
            return old(w, ...)
        end end)
        patch(OneKeyBurdenAutoWindow, 'requestTask', function(old) return function(w)
            local r = w.execute_request_list[w.execute_index]
            if not r or r.type ~= TYPE or r.pos ~= POS then return old(w) end
            if owner then return end
            owner = w
            local function done(a)
                stopTimer(); owner = nil
                r.herb, r.local_result, r.local_reason = a, a.status, a.reason
                installed.voyage.advance(w, {type=TYPE, pos=POS, args={}})
            end
            local function changed(a)
                r.herb = a; w.other_progress = (w.other_progress or 0) + 1; w:updateLoopList()
            end
            local v, ctrl, k = activity(), game(), roleKey()
            if not v or not ctrl or not k then return done({status='skipped', reason='not_open'}) end
            if ctrl.catchfairygrass_matching_window or ctrl.catchfairygrass_game_window or ctrl.catchfairygrass_end_window then
                return done({status='skipped', reason='manual_game'})
            end
            local s = {key=k, role=role(), day=day(), camp=v.camp_id, ctrl=ctrl}
            local why = guard(s)
            if why then return done({status='skipped', reason=why}) end
            timer = clock:add(function() safe(function() runner:tick() end) end, 0.25)
            safe(function() runner:start(s, done, changed) end)
        end end)
        patch(OneKeyBurdenAutoWindow, 'close_callback', function(old) return function(w, ...)
            if owner == w then release() end
            return old(w, ...)
        end end)
        patch(OneKeyBurdenAutoItem, 'setData', function(old) return function(cell, d, index)
            if cell.herb_label then cell.herb_label:setVisible(false) end
            old(cell, d, index)
            if d.pos ~= POS then return end
            cell.title_lb:setFontSize(24); cell.title_lb:setString(row.title)
            cell.un_finish_node:setVisible(false); cell.item_scrollview:setVisible(false)
            if not cell.herb_label then
                cell.herb_label = createRichLabel(18, cc.c4b(101,77,70,255), cc.p(0,1), cc.p(20,cell.Height-43),
                    1, nil, 565):addTo(cell.root_wnd)
            end
            local a = d.herb or {}
            local daily, eggs = a.daily, a.eggs or {}
            local progress = daily and ('已领 ' .. daily.claimed .. '/' .. daily.total .. ' 档') or '待核对'
            local function egg(ok) return ok and '已确认' or '本期未确认' end
            cell.herb_label:setString((reasons[a.reason] or (a.status and '执行中' or '等待执行')) .. '｜已完成 ' .. (a.matches or 0) .. ' 局'
                .. '\n每日奖励：' .. progress .. '\n全撞：' .. egg(eggs.zero) .. '　全不撞：' .. egg(eggs.full))
            cell.herb_label:setVisible(true)
        end end)
        rows[#rows+1] = row
    end)
    if not ok then restore(); error(err) end
    local detach, uninstall = installed.detach, installed.uninstall
    installed.detach = function() restore(); detach() end
    installed.uninstall = function()
        assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window, 'close helper windows first')
        restore(); uninstall()
    end
    installed.herb = {runner=runner, pos=POS, row=row}
end

return M
