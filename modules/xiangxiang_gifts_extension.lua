-- 香香小助手的界面与队列接入层：完整发布包加入17项本地任务。
-- install 只加条目、保存原方法并包装回调；实际任务从 requestTask 开始，不在挂载时执行。
local M = {}
local active_install
function M.install(Gifts, Actions, GameActions, Training, GameTraining, Quests, GameQuests, Extras, GameExtras)
    if active_install then return active_install end
    assert(OneKeyBurdenMainWindow and OneKeyBurdenAutoWindow and OneKeyBurdenAutoItem, 'helper classes missing')
    local helper = OneKeyBurdenController:getInstance()
    local vip = VipController:getInstance()
    assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window, 'close helper windows first')
    local TYPE = OneKeyBurdenConst.SimplifyType.DAILY_TASK
    local specs = {
        {pos = -2101802, kind = 1, title = '斗罗集市·每日礼包领取'},
        {pos = -2101801, kind = 6, title = '学院活动·每日特惠领取'}
    }
    if Actions then
        specs[#specs+1] = {pos=-2101800,kind=2,title='斗罗集市·每周礼包领取'}
        specs[#specs+1] = {pos=-2101799,kind=3,title='斗罗集市·每月礼包领取'}
        specs[#specs+1] = {pos=-2101798,kind='sweep',title='乾坤问情谷·免费扫荡'}
        specs[#specs+1] = {pos=-2101797,kind='pantheon',title='众神殿·自动膜拜'}
        specs[#specs+1] = {pos=-2101796,kind='domain',title='魂域之境·自动膜拜'}
        specs[#specs+1] = {pos=-2101795,kind='summon',title='镜之屋·每日契约召唤'}
    end
    if Training then
        specs[#specs+1]={pos=-2101794,kind='arena_free',title='积分赛·每日免费挑战',training=true}
        specs[#specs+1]={pos=-2101791,kind='arena_tickets',title='积分赛·挑战券挑战',training=true}
        specs[#specs+1]={pos=-2101793,kind='hero',title='魂师·1级升五级',training=true}
        specs[#specs+1]={pos=-2101792,kind='bone',title='魂骨·背包单石强化',training=true}
    end
    if Quests then
        specs[#specs+1]={pos=-2101790,kind='guild_wish',title='宗门祈愿·冒险者奖励',quest=true}
        specs[#specs+1]={pos=-2101787,kind='ruins',title='至高遗迹·奖励次数挑战',quest=true}
    end
    if Extras then
        specs[#specs+1]={pos=-2101786,kind='guild_trial',title='联盟幻境·每日挑战一次',extra=true}
        specs[#specs+1]={pos=-2101785,kind='temple_duel',title='决战武魂殿·每日挑战一次',extra=true}
        specs[#specs+1]={pos=-2101784,kind='workshop_gift',title='魂导器工坊·每日免费礼包',extra=true}
    end
    -- Retired local IDs are swallowed if an old queue/save still contains
    -- them.  Their preferences and journals are never read or modified.
    local retired = {[-2101789]=true,[-2101788]=true}
    local COUNT_KEY = 9020
    local TICKET_KEY = 9021
    local custom, patches, clock = {}, {}, GlobalTimeTicket:getInstance()
    local function roleKey()
        local role = RoleController:getInstance():getRoleVo()
        if not role or not role.rid or not role.srv_id then return nil end
        return tostring(role.srv_id) .. ':' .. tostring(role.rid), role
    end
    local function identity()
        local key, role = roleKey()
        return key and key .. ':' .. tostring(role) or nil
    end
    local function prefKey(pos)
        local key = roleKey()
        return key and 'dldl_gifts_v1:' .. key .. ':' .. pos or nil
    end
    local function now() return GameNet:getInstance():getTime() end
    local function connected() return GameNet:getInstance():IsServerConnect()==true end
    local function patch(obj, key, wrap)
        -- 记录自身字段而不只记录继承结果，卸载时才能恢复原来的继承关系。
        local old = obj[key]; assert(type(old) == 'function', key)
        local own = rawget(obj,key)
        local new = wrap(old); obj[key] = new
        patches[#patches+1] = {obj = obj, key = key, old = old, own = own, new = new}
    end
    local list = OneKeyBurdenConst.SimplifyTypeList[TYPE]
    for index, spec in ipairs(specs) do
        spec.order=index
        for _, row in ipairs(list) do assert(row.id ~= spec.pos, 'local ID collision') end
        custom[spec.pos] = spec
        spec.row = {id = spec.pos, title = TI18N(spec.title), is_title = true, is_single_select = true,
            option_list = {{TI18N('开启'), TRUE}, {TI18N('关闭'), FALSE}}, default_option = FALSE}
        if spec.kind == 'summon' then
            spec.row.close_subitem_list = {{},{1}}
            spec.row.subitem_list = {{{title=TI18N('每日次数（仅灵魂契约）'),is_title=false,
                is_single_select=true,proto_key_args=COUNT_KEY,
                option_list={{TI18N('10次'),TRUE,10},{TI18N('20次'),TRUE,20}}}}}
        end
        if spec.kind=='arena_tickets' then
            spec.row.close_subitem_list={{},{1}}
            spec.row.subitem_list={{{title=TI18N('每日用券次数（仅挑战券）'),is_title=false,
                is_single_select=true,proto_key_args=TICKET_KEY,
                option_list={{TI18N('10次'),TRUE,10},{TI18N('20次'),TRUE,20}}}}}
        end
    end
    local timer, owner, internal_claim, manual_until = nil, nil, false, 0
    local runner = Gifts.new({identity = identity, now = now, timeout = 10,
        refresh = function(kind) vip:sender21017(kind) end,
        freeId = function(kind)
            if kind >= 1 and kind <= 3 then return 9990 + kind end
            local _, _, id = vip:getModel():getCurDailyData(); return id
        end,
        isFree = function(kind, id)
            local cfg = ChargeLoopData.data_award_name[id]
            if not cfg or cfg.is_free ~= 1 or cfg.gift_type ~= kind or cfg.buy_charge_id ~= 0 then return false end
            if kind >= 1 and kind <= 3 then return id == 9990 + kind end
            return kind == 6 and vip:getModel():checkFreeDailyGift(id)
        end,
        claim = function(id)
            internal_claim = true
            local ok, err = pcall(function() vip:sender21018(id) end)
            internal_claim = false
            if not ok then error(err) end
        end})
    local action_runner, action_pending
    local training_runner, training_pending
    local quest_runner, quest_pending
    local extra_runner, extra_pending
    local function gift_pending(kind)
        if runner.active then return true end
        -- Gift replies have no charge ID: unresolved different gift kinds
        -- share a response channel. Own kind may perform read-only recovery.
        for key, pending in pairs(runner.uncertain or {}) do
            if pending and tonumber(key:match(':(%d+):%d+:%d+$'))~=kind then return true end
        end
        return false
    end
    local function cleanup()
        if timer then clock:remove(timer); timer = nil end
        owner = nil
    end
    local function safe(fn)
        local ok, err = pcall(fn)
        if not ok then
            print('[dldl_daily] '..tostring(err))
            if runner.active then runner:finish('error','runtime_error') end
            if action_runner and action_runner.active then action_runner:finish('uncertain','runtime_error') end
            if training_runner and training_runner.active then training_runner:finish('uncertain','runtime_error') end
            if quest_runner and quest_runner.active then quest_runner:finish('uncertain','runtime_error') end
            if extra_runner and extra_runner.active then extra_runner:finish('uncertain','runtime_error') end
        end
    end
    local install_ok, install_result = pcall(function()
    if Extras then
        extra_runner,extra_pending=GameExtras.bind(Extras,{roleKey=roleKey,identity=identity,now=now,
            patch=patch,busy=function() return owner~=nil end,safe=safe,connected=connected})
    end
    if Training then
        training_runner,training_pending=GameTraining.bind(Training,{roleKey=roleKey,identity=identity,now=now,
            patch=patch,busy=function() return owner~=nil end,safe=safe,connected=connected})
    end
    if Quests then
        quest_runner,quest_pending=GameQuests.bind(Quests,{roleKey=roleKey,identity=identity,now=now,
            patch=patch,busy=function() return owner~=nil end,safe=safe})
    end
    if Actions then
        action_runner, action_pending = GameActions.bind(Actions,{roleKey=roleKey,identity=identity,now=now,
            patch=patch,busy=function() return owner~=nil end,safe=safe})
    end
    patch(vip, 'sender21018', function(old)
        return function(self, id)
            if owner and not internal_claim then
                message(TI18N('免费礼包任务正在核实，请稍后手动领取')); return
            end
            if not internal_claim then manual_until = now() + 15 end
            return old(self, id)
        end
    end)
    patch(vip, 'handle21017', function(old)
        return function(self, data)
            old(self, data)
            safe(function() for _, group in ipairs(data and data.gift_loop_list or {}) do runner:onInfo(group) end end)
        end
    end)
    patch(vip, 'handle21018', function(old)
        return function(self, data)
            old(self, data)
            if not runner.active then manual_until = 0 end
            safe(function() runner:onReply(data) end)
        end
    end)
    patch(OneKeyBurdenMainWindow, 'getPosExecuteData', function(old)
        return function(self, key, cfg)
            local data = old(self, key, cfg)
            if custom[cfg.id] then
                local pref = prefKey(cfg.id)
                data.is_open = pref and cc.UserDefault:getInstance():getBoolForKey(pref, false) and TRUE or FALSE
                if custom[cfg.id].kind=='summon' and pref then
                    local count=cc.UserDefault:getInstance():getIntegerForKey(pref..':count',10)
                    if count~=10 and count~=20 then count=10 end
                    for _,arg in ipairs(data.args) do if arg.args_key==COUNT_KEY then arg.args_val=count end end
                end
                if custom[cfg.id].kind=='arena_tickets' and pref then
                    local count=cc.UserDefault:getInstance():getIntegerForKey(pref..':tickets',10)
                    if count~=10 and count~=20 then count=10 end
                    for _,arg in ipairs(data.args) do if arg.args_key==TICKET_KEY then arg.args_val=count end end
                end
            end
            return data
        end
    end)
    -- 自定义负数 ID 只在客户端使用：设置存本地，过滤后才交给官方设置协议。
    patch(helper, 'sender31601', function(old)
        return function(self, values)
            local filtered, ud = {}, cc.UserDefault:getInstance()
            for _, group in ipairs(values) do
                local copy = {type = group.type, type_list = {}}
                for _, row in ipairs(group.type_list) do
                    if custom[row.pos] then
                        local key = prefKey(row.pos)
                        if key then
                            ud:setBoolForKey(key, row.is_open == TRUE)
                            if custom[row.pos].kind=='summon' then
                                for _,arg in ipairs(row.args or {}) do
                                    if arg.args_key==COUNT_KEY and (arg.args_val==10 or arg.args_val==20) then
                                        ud:setIntegerForKey(key..':count',arg.args_val)
                                    end
                                end
                            end
                            if custom[row.pos].kind=='arena_tickets' then
                                for _,arg in ipairs(row.args or {}) do
                                    if arg.args_key==TICKET_KEY and (arg.args_val==10 or arg.args_val==20) then
                                        ud:setIntegerForKey(key..':tickets',arg.args_val)
                                    end
                                end
                            end
                        end
                    elseif not retired[row.pos] then copy.type_list[#copy.type_list+1] = row end
                end
                if #copy.type_list > 0 then filtered[#filtered+1] = copy end
            end
            ud:flush()
            if #filtered > 0 then return old(self, filtered) end
        end
    end)
    patch(helper, 'sender31602', function(old)
        return function(self, kind, pos)
            if retired[pos] then return end
            assert(not custom[pos], 'local task cannot use native task protocol')
            return old(self, kind, pos)
        end
    end)
    patch(OneKeyBurdenMainWindow,'saveOperateRequest',function(old)
        return function(self,is_all)
            local queue=old(self,is_all)
            for i=#queue,1,-1 do if retired[queue[i].pos] then table.remove(queue,i) end end
            -- Native queues carry only type/pos. Snapshot local args for this run.
            for _,row in ipairs(queue) do
                if custom[row.pos] then
                    local source=self.operate_list[row.type] and self.operate_list[row.type][row.pos]
                    assert(source and type(source.args)=='table','local task settings missing')
                    row.args={}
                    for _,arg in ipairs(source.args) do
                        row.args[#row.args+1]={args_key=arg.args_key,args_val=arg.args_val,args_str=arg.args_str}
                    end
                end
            end
            -- Keep preserved preference IDs while running free before tickets/养成.
            local indices,rows={},{}
            for i,row in ipairs(queue) do if custom[row.pos] then indices[#indices+1]=i;rows[#rows+1]=row end end
            table.sort(rows,function(a,b) return custom[a.pos].order<custom[b.pos].order end)
            for i,index in ipairs(indices) do queue[index]=rows[i] end
            return queue
        end
    end)
    local advance = OneKeyBurdenAutoWindow.updateDataList
    patch(OneKeyBurdenAutoWindow, 'updateDataList', function(old)
        return function(self, data)
            local row = self.execute_request_list[self.execute_index]
            if not row or custom[row.pos] then return end
            if not data or data.type ~= row.type or data.pos ~= row.pos then return end
            return old(self, data)
        end
    end)
    -- 真正的执行入口：官方条目仍走原方法，自定义条目分派给对应业务状态机。
    patch(OneKeyBurdenAutoWindow, 'requestTask', function(old)
        return function(self)
            local row = self.execute_request_list[self.execute_index]
            if row and retired[row.pos] then
                if owner then return end
                row.local_result,row.local_reason='skipped','task_removed'
                advance(self,{args={}});return
            end
            local spec = row and custom[row.pos]
            if not spec then return old(self) end
            if owner then return end
            owner = self
            local function done(result)
                if Actions then
                    pcall(function()
                        local fu=cc.FileUtils:getInstance()
                        local f=assert(io.open(fu:getWritablePath()..'dldl_daily_results.log','a'))
                        f:write(tostring(os.time()),'|',spec.title,'|',result.status,'|',tostring(result.reason),'|',tostring(result.count or 0),'\n');f:close()
                    end)
                end
                if result.status=='deferred' and result.job then
                    result.job.window=self
                    result.job.done=function(later)
                        row.local_result,row.local_reason=later.status,later.reason
                        if self.updateLoopList then self:updateLoopList() end
                    end
                end
                if quest_runner then
                    if quest_runner.active then quest_runner.active.done=function() end end
                    quest_runner:cancel()
                end
                cleanup(); row.local_result, row.local_reason = result.status, result.reason
                -- 单项失败或结果不明也推进后续任务，避免整个助手挂住。
                -- 消费请求的 pending 记录仍保留，下一轮不会盲目重发造成重复消费。
                if result.status == 'confirmed' or result.status == 'skipped'
                    or result.status == 'error' or result.status == 'uncertain' or result.status=='deferred' then
                    advance(self, {args = {}})
                else
                    self.is_execute_finish = true
                    helper:sender31604(self.operate_type, 0)
                    self.stop_btn_lb:setString(TI18N('关闭'))
                    self:updateLoopList()
                end
            end
            if not connected() then done({status='error',reason='connection_unavailable'});return end
            if type(spec.kind)=='number' and gift_pending(spec.kind) then done({status='uncertain',reason='gift_request_unresolved'});return end
            if (type(spec.kind)=='number' and now()<manual_until)
                or (not spec.training and not spec.quest and not spec.extra and type(spec.kind)~='number' and action_pending and action_pending(spec.kind))
                or (spec.training and training_pending and training_pending(spec.kind))
                or (spec.quest and quest_pending and quest_pending(spec.kind))
                or (spec.extra and extra_pending and extra_pending(spec.kind)) then
                done({status='error',reason='manual_claim_pending'});return
            end
            local selected = spec.extra and extra_runner or spec.quest and quest_runner or spec.training and training_runner or (type(spec.kind)=='number' and runner or action_runner)
            local count=10
            local found=0
            for _,arg in ipairs(row.args or {}) do if arg.args_key==(spec.kind=='arena_tickets' and TICKET_KEY or COUNT_KEY) then count=arg.args_val;found=found+1 end end
            if spec.kind=='arena_tickets' and (found~=1 or (count~=10 and count~=20)) then
                done({status='error',reason='invalid_ticket_target'});return
            elseif spec.kind=='summon' and (found~=1 or (count~=10 and count~=20)) then
                done({status='error',reason='invalid_summon_count'});return
            end
            -- tick 驱动查询、等待回复和超时；start 才启动用户本次选中的任务。
            timer = clock:add(function() safe(function() selected:tick() end) end, 0.5)
            safe(function()
                local ok, why = selected:start(spec.kind, done, count)
                if not ok then done({status = 'error', reason = why}) end
            end)
        end
    end)
    patch(OneKeyBurdenAutoItem, 'setData', function(old)
        return function(self, data, index)
            old(self, data, index)
            if custom[data.pos] and data.local_result then
                local labels = {confirmed = '已核实完成', skipped = '已完成或无可用次数', uncertain = '结果未确认',
                    error = '执行失败，已跳过', cancelled = '已停止'}
                local daily_done={summon='今日召唤已完成',arena_free='今日免费挑战已完成',
                    arena_tickets='今日用券目标已完成',hero='今日养成已完成',bone='今日养成已完成'}
                self.un_finish_node:setVisible(true)
                local reasons={challenge_started='已发起挑战，继续后续任务',challenge_deferred='等待可发起挑战，其余任务继续',deferred_timeout='暂未能发起挑战，请稍后核实',gift_config_changed='免费礼包配置已变化，已跳过本项',wish_already_claimed='今日祈愿奖励已领取',no_guild='尚未加入宗门',ruins_defeat='遗迹挑战失败，已跳过本项',
                    empty_quest_formation='请先保存对应进攻阵容',invalid_quest_formation='对应进攻阵容无效',
                    ruins_no_boss='暂无可挑战遗迹首领',
                    ruins_boss_defeated='当前遗迹首领已击败，已跳过本项',
                    insufficient_contracts='灵魂契约不足，已跳过本项',hero_bag_full='魂师背包空间不足',
                    daily_target_done=daily_done[custom[data.pos].kind] or '今日任务已完成',previous_request_unresolved='上次结果待核实，已跳过本项',
                    manual_claim_pending='正在手动操作，已跳过本项',gift_request_unresolved='礼包请求待核实，已跳过本项',
                    connection_unavailable='连接不可用，已跳过本项',query_timeout='状态查询超时，已跳过本项',
                    form_timeout='阵容查询超时，已跳过本项',details_timeout='详情查询超时，已跳过本项',
                    reply_timeout='请求未收到回复，待核实',hero_recovery_timeout='升级结果查询超时，待核实',
                    hero_recovered_completed='已核实上次升级完成',hero_recovered_unchanged='已核实等级未变，可再次执行',
                    hero_recovery_changed='等级核对不一致，已跳过本项',hero_target_changed='魂师状态已变，已跳过本项',
                    hero_details_unverified='魂师详情未确认，已跳过本项',
                    already_claimed='礼包已领取',gift_unavailable='暂无可领取礼包',no_remaining_action='今日免费次数已完成',
                    inventory_timeout='背包未同步，已停止',summon_busy='正在召唤，请稍后',not_open='暂未开放',
                    insufficient_tickets='斗魂挑战券不足，已阻断',empty_attack_formation='请先保存积分赛进攻阵容',
                    free_challenges_remaining='免费次数尚未用完，请先执行免费挑战',
                    skip_unavailable='无法启用原生跳过战斗，已停止',insufficient_hero_materials='升五级所需金币或魂力不足',
                    insufficient_stones='普通魂骨强化石不足',insufficient_coin='魂骨养成所需金币不足',
                    no_eligible_target='暂无符合条件的养成对象',battle_busy='其他战斗未结束，已停止'}
                self.un_finish_lb:setString(TI18N(reasons[data.local_reason] or labels[data.local_result] or '结果未确认'))
                self.un_finish_lb:setFontSize(24)
            end
        end
    end)
    patch(OneKeyBurdenAutoWindow, 'close_callback', function(old)
        return function(self, ...)
            local deferred_owner=extra_runner and extra_runner.active and extra_runner.active.window==self
            if extra_runner then for _,a in pairs(extra_runner.deferred) do if a.window==self then deferred_owner=true end end end
            if owner == self or deferred_owner then
                if runner.active then runner.active.done = function() end end
                runner:cancel()
                if action_runner then
                    if action_runner.active then action_runner.active.done=function() end end
                    action_runner:cancel()
                end
                if training_runner then
                    if training_runner.active then training_runner.active.done=function() end end
                    training_runner:cancel()
                end
                if extra_runner then
                    if extra_runner.active then extra_runner.active.done=function() end end
                    extra_runner:cancel()
                end
                if quest_runner then
                    if quest_runner.active then quest_runner.active.done=function() end end
                    quest_runner:cancel()
                end
                cleanup()
            end
            return old(self, ...)
        end
    end)
    -- 将扩展条目放到日常页顶部，沿用游戏原有设置窗口与执行窗口。
    for i = #specs, 1, -1 do table.insert(list, 1, specs[i].row) end
    local installation = {runner = runner, specs = specs, actions=action_runner,training=training_runner,quests=quest_runner,extras=extra_runner, version = Extras and 'daily_extras_v1' or Quests and 'daily_quests_v3' or Training and 'daily_training_v8' or (Actions and 'daily_actions_v2' or 'daily_gifts_v1')}
    -- 自动重挂只撤销仍属于我们的包装/条目，不覆盖后来接入的其他包装。
    -- 停止回调，但保留用户设置和未确认消费记录。
    function installation.detach()
        for _,r in pairs({runner,action_runner,training_runner,quest_runner,extra_runner}) do
            if r then
                if r.active then r.active.done=function() end end
                for _,a in pairs(r.deferred or {}) do a.done=function() end end
                r:cancel()
            end
        end
        cleanup()
        for i=#patches,1,-1 do
            local p=patches[i]
            if rawget(p.obj,p.key)==p.new then rawset(p.obj,p.key,p.own) end
        end
        for i=#list,1,-1 do
            local spec=custom[list[i].id]
            if spec and list[i]==spec.row then table.remove(list,i) end
        end
        active_install=nil
    end
    function installation.uninstall()
        assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window, 'close helper windows first')
        local checked={}
        for i=#patches,1,-1 do
            local p=patches[i];checked[p.obj]=checked[p.obj] or {}
            if not checked[p.obj][p.key] then
                assert(p.obj[p.key]==p.new,'patch changed: '..p.key);checked[p.obj][p.key]=true
            end
        end
        if runner.active then runner.active.done = function() end end
        runner:cancel()
                if action_runner then
                    if action_runner.active then action_runner.active.done=function() end end
                    action_runner:cancel()
                end
                if training_runner then
                    if training_runner.active then training_runner.active.done=function() end end
                    training_runner:cancel()
                end
                if extra_runner then
                    if extra_runner.active then extra_runner.active.done=function() end end
                    extra_runner:cancel()
                end
                if quest_runner then
                    if quest_runner.active then quest_runner.active.done=function() end end
                    quest_runner:cancel()
                end
                cleanup()
        for i = #patches, 1, -1 do local p = patches[i]; rawset(p.obj,p.key,p.own) end
        for i = #list, 1, -1 do if custom[list[i].id] then table.remove(list, i) end end
        active_install = nil
    end
    active_install = installation
    return installation
    end)
    if not install_ok then
        -- 安装中途失败也撤销已完成的改动，避免留下一半可见、一半不可用的助手。
        for i=#patches,1,-1 do
            local p=patches[i]
            if rawget(p.obj,p.key)==p.new then rawset(p.obj,p.key,p.own) end
        end
        for i=#list,1,-1 do
            local spec=custom[list[i].id]
            if spec and list[i]==spec.row then table.remove(list,i) end
        end
        cleanup()
        error(install_result)
    end
    return install_result
end
return M
