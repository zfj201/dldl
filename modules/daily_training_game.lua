-- Exact original senders; no diamonds, purchases, formation writes or auto materials.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function arena(kind) return kind=='arena_free' or kind=='arena_tickets' end
function M.bind(Training,ctx)
    local elite=ElitematchController:getInstance()
    local hero=HeroController:getInstance()
    local hm=hero:getModel()
    local bag=BackpackController:getInstance():getModel()
    local backpack=BackpackController:getInstance()
    local battle=BattleController:getInstance()
    local ud=cc.UserDefault:getInstance()
    local runner,internal,manual_until=nil,false,0
    local bone_scan,hero_scan
    local result_views
    local function log(event,detail)
        pcall(function()
            if not runner or not runner.active then return end
            local fu=cc.FileUtils:getInstance();local f=assert(io.open(fu:getWritablePath()..'dldl_training_trace.log','a'))
            f:write(tostring(ctx.now()),'|',event,'|',tostring(detail),'\n');f:close()
        end)
    end
    local function day()
        local t=ctx.now();local d=TimeTool.getDayAnyHourTime(t,5);return d>t and d-86400 or d
    end
    local function key(kind) return 'dldl_training_v1:'..assert(ctx.roleKey())..':'..day()..':'..kind end
    local function num(id) return bag:getItemNumByBid(id) end
    local function refreshInterval() local c=ArenaSoulData.data_const.match_cd_time;return c and uint(c.val) and c.val>0 and c.val or 3 end
    -- GameNet time can be integral: +4 ensures at least three real seconds.
    local function challengeNotBefore()
        local last=ud:getIntegerForKey(key('arena')..':last_sent_at',0)
        local sc=elite:getModel():getSCData()
        return math.max(last>0 and last+math.max(4,refreshInterval()) or 0,sc and tonumber(sc.match_cd_time) or 0)
    end
    local recovery_token='v4_rejected|yinghe_3360:5317|1791666000|1791693165|9|1|47|code0'
    local function recoveryFile(suffix) return cc.FileUtils:getInstance():getWritablePath()..'dldl_arena_v4_reconcile.'..suffix end
    local function sorted(list)
        local out={};for _,v in pairs(list or {}) do out[#out+1]=v end
        table.sort(out,function(a,b) return (a.partner_id or a.id)<(b.partner_id or b.id) end);return out
    end
    local function heroEligible(v)
        return v and uint(v.partner_id) and v.partner_id>0 and v.lev==1 and HeroVo.getNowLevByVo(v)==1
            and (v.end_time or 0)==0 and (v.resonate_lev or 0)==0
            and not (v.is_hire==1 and (v.hire_time or 0)>0)
            and HeroCalculate.getHeroShowLevelStatus(v)==HeroConst.HeroLevStatus.Levup
            and hm:getHeroMaxLevel(v.bid,v.star,v.break_lev)>=6
            and ResonateController:getInstance():getModel():isHeroUpLev(1)
    end
    local function costs()
        local total={}
        for level=1,5 do
            local cfg=PartnerData.data_partner_lev[level]
            if not cfg or type(cfg.expend)~='table' or #cfg.expend==0 then return nil end
            for _,cost in ipairs(cfg.expend) do
                if (cost[1]~=1 and cost[1]~=22) or not uint(cost[2]) then return nil end
                total[cost[1]]=(total[cost[1]] or 0)+cost[2]
            end
        end
        return total
    end
    local function boneState(goods)
        if not goods or not uint(goods.id) or goods.id==0 or not uint(goods.upgrade_lev) or not uint(goods.exp) then return nil end
        local base=PartnerHolyEqmData.data_base_info(goods.base_id)
        if not base then return nil end
        local levels=PartnerHolyEqmData.data_upgrade_info[base.upgrade_id]
        local max=PartnerHolyEqmData.data_upgrade_max_lev[base.upgrade_id]
        local cfg=levels and levels[goods.upgrade_lev]
        if not cfg or not uint(max) or goods.upgrade_lev>=max or goods.exp>=cfg.need_exp then return nil end
        local remaining,exp,level,coin=100,goods.exp,goods.upgrade_lev,0
        while remaining>0 and level<max do
            local c=levels[level]
            if not c or not uint(c.need_exp) or type(c.expend)~='table' or #c.expend~=1 or c.expend[1][1]~=1 or not uint(c.expend[1][2]) then return nil end
            local added=math.min(remaining,c.need_exp-exp)
            if added<=0 then return nil end
            coin=coin+math.ceil(added*c.expend[1][2]);remaining=remaining-added;exp=0;level=level+1
        end
        if remaining>0 then return nil end
        return {total=cfg.val+goods.exp,cost=coin,upgrade_id=base.upgrade_id}
    end
    local function findBone(a)
        return bag:getBagItemById(BackPackConst.Bag_Code.EQUIPS,a.id)
    end
    local function guard(kind,a)
        if ctx.connected and not ctx.connected() then return 'connection_unavailable' end
        if arena(kind) then
            local sc=elite:getModel():getSCData()
            if not sc or sc.state~=1 or sc.day_combat_count~=a.remaining or sc.combat_time~=a.combat then return 'arena_state_changed' end
            if num(10019)~=a.tickets then return 'inventory_changed' end
            if sc.is_skip~=1 then return 'skip_unavailable' end
            if challengeNotBefore()>ctx.now() then return 'challenge_cooldown' end
            if a.free and sc.day_combat_count<=0 or not a.free and sc.day_combat_count~=0 then return 'free_priority_changed' end
            if not a.free and num(10019)<1 then return 'insufficient_tickets' end
            if battle:isInFight() or battle:getFightTypeInfo(23) then return 'battle_busy' end
            local enemy=elite:getModel():getEnemyData()
            if not enemy or enemy.choose_id~=a.index then return 'opponent_not_selected' end
            if enemy.is_match~=0 then return 'opponents_not_ready' end
            local target=enemy.match_list and enemy.match_list[a.index]
            if not target or not a.opponent or target.rid~=a.opponent.rid or target.srv_id~=a.opponent.srv_id
                or target.order_id~=a.opponent.order_id then return 'opponent_changed' end
        elseif kind=='hero' then
            if not hero_scan or not hero_scan.verified or hero_scan.partner_id~=a.partner_id then return 'hero_details_unverified' end
            if not heroEligible(hm:getHeroById(a.partner_id)) then return 'hero_target_changed' end
            local total=costs();if not total then return 'hero_cost_config_mismatch' end
            for id,c in pairs(total) do if c~=a.cost[id] or num(id)<c then return 'insufficient_hero_materials' end end
        elseif kind=='bone' then
            if a.partner_id~=0 then return 'bone_owner_changed' end
            local cfg=PartnerHolyEqmData.data_const.common_strengthen_item
            if not cfg or cfg.val[1]~=10011 or cfg.val[2]~=100 then return 'bone_config_mismatch' end
            local state=boneState(findBone(a))
            if not state or state.total~=a.total or state.cost~=a.cost then return 'bone_target_changed' end
            if num(10011)<1 then return 'insufficient_stones' end
            if num(1)<a.cost then return 'insufficient_coin' end
        end
    end
    local function battleReady()
        local won=battle.finish_result_view_list and battle.finish_result_view_list[23]
        local lost=battle.finish_fail_view_list and battle.finish_fail_view_list[23]
        local owned=runner and runner.active and arena(runner.active.kind) and runner.active.phase=='cleanup'
        if battle.getWatchReplayStatus and battle:getWatchReplayStatus() then return false end
        if owned and result_views and ((won and won~=result_views.won) or (lost and lost~=result_views.lost)) then return false end
        if owned and won and won.fight_type==23 and won.isOpen and won:isOpen() and won.root_wnd and won.onCloseBtn then log('close_result','won');won:onCloseBtn();return false end
        if owned and lost and lost.fight_type==23 and lost.isOpen and lost:isOpen() and lost.root_wnd and lost.item_scroll then log('close_result','lost');lost:close();return false end
        return not battle:isInFight() and not battle:getFightTypeInfo(23) and not won and not lost
    end
    runner=Training.new({identity=ctx.identity,day=day,now=ctx.now,log=log,tickets=function() return num(10019) end,
        journal=function(kind)
            local k=key(kind);local used,pending=ud:getIntegerForKey(k..':used',0),ud:getIntegerForKey(k..':pending',0)
            -- Preserve unresolved legacy combined-arena mutations during migration.
            if arena(kind) then
                if kind=='arena_tickets' then used=math.max(used,ud:getIntegerForKey(key('arena')..':used',0)) end
                for _,name in ipairs({'arena','arena_free','arena_tickets'}) do
                    if ud:getIntegerForKey(key(name)..':pending',0)~=0 then pending=1 end
                end
            end
            return used,pending
        end,
        saveJournal=function(kind,used,pending,a)
            local k=key(kind)
            if a and arena(kind) then
                ud:setIntegerForKey(key('arena')..':last_sent_at',a.sent_at)
                for _,field in ipairs({'remaining','combat','tickets','sent_at','start_time','end_time'}) do
                    ud:setIntegerForKey(k..':before_'..field,type(a[field])=='number' and a[field] or -1)
                end
                ud:setIntegerForKey(k..':explicit_rejected',0)
            elseif a and kind=='hero' then
                for _,field in ipairs({'partner_id','bid','level','sent_at'}) do
                    ud:setIntegerForKey(k..':before_'..field,a[field])
                end
            end
            ud:setIntegerForKey(k..':used',used);ud:setIntegerForKey(k..':pending',pending);ud:flush()
        end,
        queryHeroDetails=function(id) log('query_hero_details','partner='..id..'|protocol=11025');hero:SendProtocal(11025,{}) end,
        heroRecoveryBaseline=function()
            local k=key('hero')
            local a={partner_id=ud:getIntegerForKey(k..':before_partner_id',0),bid=ud:getIntegerForKey(k..':before_bid',0),
                level=ud:getIntegerForKey(k..':before_level',0),sent_at=ud:getIntegerForKey(k..':before_sent_at',0)}
            if a.partner_id>0 and a.bid>0 and a.level==1 and a.sent_at>0 then return a end
            -- Exact migration for the audited disconnected Phase11v3 request;
            -- no generic clearing of old journals without target evidence.
            if ctx.roleKey()~='yinghe_3356:5005' or day()~=1791752400 or ud:getIntegerForKey(k..':used',0)~=0
                or ctx.now()<1791779059+300 then return nil end
            local token='phase11v3|bc73670fab9465e93957e6a11a9001c0ac2727f370d8a7e0b5e98685059eee32|yinghe_3356:5005|1791752400|1791779059|33794|1|reply_timeout'
            local f=io.open(cc.FileUtils:getInstance():getWritablePath()..'dldl_hero_reconcile.request','r')
            if not f then return nil end;local value=f:read('*a');f:close()
            if value:match('^%s*(.-)%s*$')~=token then return nil end
            log('hero_recovery_baseline',token)
            return {partner_id=33794,level=1,sent_at=1791779059,legacy=true}
        end,
        heroRecoveryLevel=function(data,a)
            if ctx.connected and not ctx.connected() then return nil,'connection_unavailable' end
            for _,v in ipairs(data.partners or {}) do
                if v.partner_id==a.partner_id then
                    log('hero_recovery_snapshot','partner='..v.partner_id..'|level='..tostring(v.lev))
                    if (a.bid and v.bid~=a.bid) or (v.end_time or 0)~=0 or (v.resonate_lev or 0)~=0 then return nil,'hero_target_changed' end
                    if v.lev==6 or (a.legacy and v.lev==1) then return v.lev end
                    return nil,'previous_request_unresolved'
                end
            end
        end,
        markRejected=function(kind) ud:setIntegerForKey(key(kind)..':explicit_rejected',1);ud:flush() end,
        refreshInterval=refreshInterval,challengeNotBefore=challengeNotBefore,
        legacyRequest=function()
            if ctx.roleKey()~='yinghe_3360:5317' or day()~=1791666000 then return false end
            local ok,token=pcall(function() local f=io.open(recoveryFile('request'),'r');if not f then return nil end;local s=f:read('*a');f:close();return s:match('^%s*(.-)%s*$') end)
            return ok and token==recovery_token
        end,
        legacyEvidence=function(data)
            return {role_key=ctx.roleKey(),day=day(),source_sha256='51cdd97c3de5b774bcc93564fc1d58e7ef47651304a073c38c09e56ed5ee0d78',
                sent_at=1791693165,free=9,combat=1,tickets=47,code=0,start_time=data.start_time,end_time=data.end_time}
        end,
        reportRecovery=function(status,reason)
            pcall(function()
                if runner.active and runner.active.kind=='hero' then
                    local path=cc.FileUtils:getInstance():getWritablePath()..'dldl_hero_reconcile.'
                    local f=assert(io.open(path..'result','a'));f:write(ctx.now(),'|',ctx.roleKey(),'|',day(),'|',status,'|',reason,'\n');f:close()
                    if reason=='hero_recovered_completed' or reason=='hero_recovered_unchanged' then os.remove(path..'request') end
                    return
                end
                local f=assert(io.open(recoveryFile('result'),'a'));f:write(tostring(ctx.now()),'|',ctx.roleKey(),'|',tostring(day()),'|',status,'|',tostring(reason),'\n');f:close()
                if reason=='action_rejected_unchanged' then os.remove(recoveryFile('request')) end
            end)
        end,
        recoveryBaseline=function(kind,e)
            local k=key(kind);local a={}
            if ud:getIntegerForKey(k..':pending',0)~=1 then return nil,'pending_kind_mismatch' end
            for _,field in ipairs({'remaining','combat','tickets','sent_at','start_time','end_time'}) do a[field]=ud:getIntegerForKey(k..':before_'..field,-1) end
            if a.sent_at<0 then
                -- The sole audited v4 rejection: no generic baseline override or blind clearing.
                if kind~='arena_free' or type(e)~='table' or e.role_key~='yinghe_3360:5317' or e.day~=1791666000
                    or e.role_key~=ctx.roleKey() or e.day~=day()
                    or e.source_sha256~='51cdd97c3de5b774bcc93564fc1d58e7ef47651304a073c38c09e56ed5ee0d78'
                    or e.sent_at~=1791693165 or e.free~=9 or e.combat~=1 or e.tickets~=47 or e.code~=0
                    or not uint(e.start_time) or not uint(e.end_time) or e.start_time>=e.end_time
                    or e.sent_at<e.start_time or e.sent_at>=e.end_time then return nil,'legacy_evidence_required' end
                for _,name in ipairs({'arena','arena_tickets'}) do
                    if ud:getIntegerForKey(key(name)..':pending',0)~=0 then return nil,'other_pending' end
                end
                a={remaining=9,combat=1,tickets=47,sent_at=1791693165,start_time=e.start_time,end_time=e.end_time,legacy=true}
                log('legacy_reconcile','source='..e.source_sha256..'|role='..e.role_key..'|day='..e.day..'|sent_at='..e.sent_at)
            elseif ud:getIntegerForKey(k..':explicit_rejected',0)~=1 then return nil,'explicit_rejection_required' end
            for _,field in ipairs({'remaining','combat','tickets','sent_at','start_time','end_time'}) do if not uint(a[field]) then return nil,'missing_pending_baseline' end end
            a.free=a.remaining>0
            return a
        end,
        isOpen=function(kind) return not arena(kind) or elite:getModel():checkElitematchIsOpen(true) end,
        query=function(kind)
            log('query',kind)
            if kind=='hero' then
                hero_scan={verified=false}
                -- 11026 contains attributes, not level. 11025 is the game's
                -- read-only base list and carries partner_id/bid/lev.
                log('query_hero_details','protocol=11025');hero:SendProtocal(11025,{})
            end
            if kind=='form' then result_views=nil;hero:sender11211(45)
            elseif kind=='base' then elite:sender29400()
            elseif kind=='opponents' then elite:sender29401()
            elseif kind=='match' then internal=true;elite:sender29402();internal=false end
            if kind=='bone' then
                bone_scan={wait=false,bag_done=false,verified={}}
                local ids={}
                for _,v in pairs(bag:getBagItemList(BackPackConst.Bag_Code.EQUIPS) or {}) do
                    if v.config and BackPackConst.checkIsHolyEquipment(v.config.type) then ids[#ids+1]={id=v.id} end
                end
                if #ids>0 then
                    table.sort(ids,function(a,b) return a.id<b.id end);bone_scan.wait=true;bone_scan.wait_kind='bag';bone_scan.requested=ids
                    log('query_details','bag_count='..#ids);backpack:send10506(BackPackConst.Bag_Code.EQUIPS,ids)
                else bone_scan.bag_done=true end
            end
        end,
        prepare=function(kind)
            if kind=='hero' then
                if not hero_scan then return nil,'no_eligible_target' end
                if not hero_scan.verified then return nil,hero_scan.reason or 'awaiting_details' end
                local v=hm:getHeroById(hero_scan.partner_id)
                if not heroEligible(v) then return nil,'hero_target_changed' end
                local total=costs();if not total then return nil,'hero_cost_config_mismatch' end
                for id,c in pairs(total) do if num(id)<c then return nil,'insufficient_hero_materials' end end
                log('hero_selected','partner='..v.partner_id..'|level=1|coin='..tostring(total[1])..'|hero_exp='..tostring(total[22]))
                return {partner_id=v.partner_id,bid=v.bid,level=1,cost=total}
            else
                if bone_scan and bone_scan.wait then return nil,'awaiting_details' end
                local cfg=PartnerHolyEqmData.data_const.common_strengthen_item
                if not cfg or cfg.val[1]~=10011 or cfg.val[2]~=100 then return nil,'bone_config_mismatch' end
                if num(10011)<1 then return nil,'insufficient_stones' end
                local all={}
                for _,v in pairs(bag:getBagItemList(BackPackConst.Bag_Code.EQUIPS) or {}) do
                    if v.config and BackPackConst.checkIsHolyEquipment(v.config.type) and bone_scan and bone_scan.verified[v.id] then all[#all+1]={goods=v,partner_id=0} end
                end
                table.sort(all,function(x,y) if x.partner_id~=y.partner_id then return x.partner_id<y.partner_id end return x.goods.id<y.goods.id end)
                local coin_short=false
                for _,v in ipairs(all) do
                    local s=boneState(v.goods)
                    if s and num(1)>=s.cost then
                        log('bone_selected','bone='..v.goods.id..'|partner='..v.partner_id..'|before_exp='..s.total..'|stone=1|coin='..s.cost)
                        return {partner_id=v.partner_id,id=v.goods.id,total=s.total,cost=s.cost,upgrade_id=s.upgrade_id,stones=num(10011)}
                    elseif s then coin_short=true end
                end
                if coin_short then return nil,'insufficient_coin' end
            end
            return nil,'no_eligible_target'
        end,
        guard=guard,battleReady=battleReady,isSkip=function() local d=elite:getModel():getSCData();return d and d.is_skip==1 end,
        arenaGuard=function(data)
            if data.state~=1 then return 'arena_closed' end
            if not elite:getModel():checkElitematchIsOpen(true) then return 'not_open' end
            if ArenaSoulData.data_const.arena_ticket.val~=10019 then return 'ticket_config_mismatch' end
            for _,c in ipairs(ArenaSoulData.data_const.skip_cond.val) do
                if c[1]~='combat_time' or not uint(c[2]) then return 'skip_config_mismatch' end
                if data.combat_time<c[2] then return 'skip_unavailable' end
            end
            if not battleReady() then return 'battle_busy' end
        end,
        checkForm=function(data)
            if data.type~=45 or not uint(data.formation_type) or not FormationData.data_form_data[data.formation_type]
                or type(data.pos_info)~='table' or #data.pos_info==0 then return 'empty_attack_formation' end
            local positions,ids={},{}
            local allowed={}
            for _,row in ipairs(FormationData.data_form_data[data.formation_type].pos or {}) do allowed[row[1]]=true end
            for _,v in ipairs(data.pos_info) do
                if not uint(v.pos) or not allowed[v.pos] or positions[v.pos] or not uint(v.id) or v.id==0 or ids[v.id] or not hm:getHeroById(v.id) then return 'invalid_attack_formation' end
                positions[v.pos]=true;ids[v.id]=true
            end
        end,
        checkOpponents=function(data)
            if data.is_match~=0 then return 'opponents_not_ready' end
            for _,v in ipairs(data.match_list) do if type(v)~='table' or not uint(v.rid) or v.rid==0 or type(v.srv_id)~='string' then return 'invalid_opponents' end end
        end,
        verify=function(kind,a)
            if kind=='hero' then
                local v=hm:getHeroById(a.partner_id);local level=v and HeroVo.getNowLevByVo(v)
                log('hero_verify','partner='..a.partner_id..'|level='..tostring(level)..'|target=6')
                if level==6 and v.lev==6 then return true end
                if level and level~=1 then return false,'unexpected_hero_level' end
            else
                if a.partner_id~=0 then return false,'bone_owner_changed' end
                local g=findBone(a)
                local levels=PartnerHolyEqmData.data_upgrade_info[a.upgrade_id]
                local c=g and levels[g.upgrade_lev]
                if c and uint(g.exp) then
                    local total=c.val+g.exp;local stones=num(10011)
                    log('bone_verify','bone='..a.id..'|exp='..a.total..'->'..total..'|stones='..a.stones..'->'..stones)
                    if total==a.total+100 and stones==a.stones-1 then return true end
                    if total>a.total+100 or stones<a.stones-1 then return false,'unexpected_bone_consumption' end
                end
            end
        end,
        act=function(name,a)
            log('act',name..'|now='..ctx.now())
            internal=true
            local ok,err=pcall(function()
                if arena(name) then elite:sender29403()
                elseif name=='choose' then elite:sender29446(a.index)
                elseif name=='skip' then elite:sender29450(1)
                elseif name=='hero' then hero:sender11003(a.partner_id)
                elseif name=='bone' then hero:sender11083(a.partner_id,a.id,{{common_type=0,num=1}},{}) end
            end)
            internal=false;if not ok then error(err) end
        end})
    for _,pair in ipairs({{elite,'sender29402'},{elite,'sender29403'},{elite,'sender29404'},{elite,'sender29446'},{elite,'sender29450'},
        {hero,'sender11003'},{hero,'sender11083'},{hero,'sender11212'},{hero,'sender11093'}}) do
        ctx.patch(pair[1],pair[2],function(old) return function(obj,...)
            if not internal and (ctx.busy() or runner.active) then message(TI18N('小助手正在核实任务，请稍后操作'));return end
            if not internal then manual_until=ctx.now()+15 end
            return old(obj,...)
        end end)
    end
    for _,pair in ipairs({{backpack,'handle10506'}}) do
        ctx.patch(pair[1],pair[2],function(old) return function(obj,data)
            old(obj,data)
            ctx.safe(function()
                if runner.active and runner.active.kind=='bone' and runner.active.phase=='prepare' and bone_scan then
                    if bone_scan.wait_kind=='bag' and data.storage==BackPackConst.Bag_Code.EQUIPS then
                        for _,row in ipairs(data.list or {}) do
                            if uint(row.upgrade_lev) and uint(row.exp) then bone_scan.verified[row.id]=true end
                        end
                        local all=true;for _,row in ipairs(bone_scan.requested) do if not bone_scan.verified[row.id] then all=false end end
                        if all then bone_scan.wait=false;runner:phase('prepare');log('details_ready','bag') end
                    end
                end
            end)
        end end)
    end
    -- Capture original toast text only while this runner owns an arena operation.
    ctx.patch(_G,'message',function(old) return function(text,...)
        if runner.active and arena(runner.active.kind) then log('message',tostring(text):gsub('[\r\n]',' ')) end
        return old(text,...)
    end end)
    for _,pair in ipairs({{elite,29400},{elite,29401},{elite,29402},{elite,29403},{elite,29406},{elite,29446},{elite,29450},{hero,11211},{hero,11003},{hero,11083},{hero,11025}}) do
        local id=pair[2]
        ctx.patch(pair[1],'handle'..id,function(old) return function(obj,data)
            old(obj,data);ctx.safe(function()
                if id==11025 and runner.active and runner.active.kind=='hero' and runner.active.phase=='prepare' and hero_scan then
                    hero_scan.reason='no_eligible_target'
                    for _,v in ipairs(sorted(data.partners)) do
                        if v.lev==1 and heroEligible(hm:getHeroById(v.partner_id)) then
                            hero_scan.partner_id=v.partner_id;hero_scan.verified=true;hero_scan.reason=nil;break
                        end
                    end
                end
                if id==29406 and runner.active and arena(runner.active.kind)
                    and (runner.active.phase=='reply' or runner.active.phase=='battle') and (not data.combat_type or data.combat_type==23) then
                    result_views={won=battle.finish_result_view_list and battle.finish_result_view_list[23],
                        lost=battle.finish_fail_view_list and battle.finish_fail_view_list[23]}
                end
                runner:onPacket(id,data)
            end)
        end end)
    end
    return runner,function(current)
        if ctx.now()<manual_until then return true end
        -- Own start/journal protects unresolved actions (arena free/tickets
        -- remain coupled); unrelated tasks use their fresh server state.
        return false
    end
end
return M
