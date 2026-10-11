-- Bind only verified original query/action methods. No purchase or diamond sender.
local M={}
function M.bind(Actions, context)
    local c={sweep=DungeonstoneController:getInstance(),pantheon=PantheonController:getInstance(),
        domain=SoulDomainController:getInstance(),summon=PartnersummonController:getInstance()}
    local defs={
        sweep={'send13030','handle13030','send13032','handle13032','resource_dungeon_open'},
        pantheon={'sender13250','handle13250','sender13251','handle13251','pantheon_open'},
        domain={'send21800','on21800','send21809','on21809','domain_boss_open'},
        summon={'send23200','handle23200','send23201','handle23201'}
    }
    local runner,internal,manual_until=nil,false,0
    local function day()
        local t=context.now();local d=TimeTool.getDayAnyHourTime(t,5)
        return d>t and d-86400 or d
    end
    local function key(kind)
        return 'dldl_actions_v2:'..assert(context.roleKey())..':'..tostring(day())..':'..kind
    end
    local ud=cc.UserDefault:getInstance()
    local function contracts() return BackpackController:getInstance():getModel():getItemNumByBid(10023) end
    local function query(kind) return c[kind][defs[kind][1]](c[kind]) end
    local function inspect(kind,data,a)
        if type(data)~='table' then return nil end
        if kind=='pantheon' then
            if data.worship_status~=0 and data.worship_status~=1 then return nil end
            return {confirmed=data.worship_status==0,action=data.worship_status==1 and {} or nil}
        elseif kind=='domain' then
            if type(data.last_domain_id)~='number' or (data.is_daily_reward~=0 and data.is_daily_reward~=1) then return nil end
            return {confirmed=data.is_daily_reward==1,action=data.last_domain_id>0 and data.is_daily_reward==0 and {} or nil}
        elseif kind=='sweep' then
            if type(data.list)~='table' or type(data.pass_list)~='table' then return nil end
            local model=c.sweep:getModel()
            if a.phase=='verify' then
                for _,row in ipairs(data.list) do
                    if row.type==a.action.type then
                        return {confirmed=type(row.day_free_num)=='number' and row.day_free_num>=a.action.before+a.action.times}
                    end
                end
                return nil
            end
            local rows={};for _,row in ipairs(data.list) do rows[#rows+1]=row end
            table.sort(rows,function(x,y) return x.type<y.type end)
            local passed={};for _,row in ipairs(data.pass_list) do passed[row.id]=true end
            for _,row in ipairs(rows) do
                if DungeonstoneConst.MiscKey[row.type] and not a.visited[row.type] and model:isDungeonOpen(row.type) then
                    local used=row.day_free_num;local total=model:getFreeCount(row.type)
                    if type(used)~='number' or used<0 or used%1~=0 or type(total)~='number' or total<0 then return nil end
                    local id=model:getNewPassDungeon(row.type)
                    if total>used and passed[id] and model:hasPassDungeonByType(row.type) then
                        return {action={id=id,type=row.type,times=math.min(total-used,10),before=used}}
                    end
                end
            end
            return {}
        end
    end
    runner=Actions.new({identity=context.identity,now=context.now,day=day,query=query,inspect=inspect,contracts=contracts,
        journal=function(kind) local k=key(kind);return ud:getIntegerForKey(k..':used',0),ud:getIntegerForKey(k..':pending',0) end,
        saveJournal=function(kind,used,pending)
            local k=key(kind);ud:setIntegerForKey(k..':used',used);ud:setIntegerForKey(k..':pending',pending);ud:flush()
        end,
        isOpen=function(kind)
            return not defs[kind][5] or SysController:getInstance():checkIsOpenByKey(defs[kind][5])
        end,
        summonGuard=function(needed)
            local cfg=RecruitData.data_partnersummon_data[200]
            if not cfg or cfg.group_id~=200 or cfg.draw_list[2]~=10 or #cfg.item_five~=1
                or cfg.item_five[1][1]~=10023 or cfg.item_five[1][2]~=10 then return 'contract_config_mismatch' end
            if c.summon.req_flag then return 'summon_busy' end
            if contracts()<needed then return 'insufficient_contracts' end
            local max,count=HeroController:getInstance():getModel():getHeroMaxCount()
            if type(max)~='number' or type(count)~='number' or count+needed>max then return 'hero_bag_full' end
        end,
        matches=function(kind,data,action)
            if not data then return false end
            if kind=='summon' then return data.group_id==200 and data.times==10 end
            if kind=='sweep' then return data.id==action.id end
            return true
        end,
        act=function(kind,a)
            internal=true
            local ok,err=pcall(function()
                if kind=='summon' then
                    assert(a.group_id==200 and a.times==10 and a.recruit_type==4 and contracts()>=10,'contract-only guard')
                    c.summon:send23201(200,10,4,false)
                elseif kind=='sweep' then c.sweep:send13032(a.id,a.times)
                else c[kind][defs[kind][3]](c[kind]) end
            end)
            internal=false;if not ok then error(err) end
        end})
    for kind,def in pairs(defs) do
        local task=kind
        context.patch(c[task],def[3],function(old)
            return function(self,...)
                if not internal and context.busy() then message(TI18N('小助手正在核实任务，请稍后操作'));return end
                if not internal then manual_until=context.now()+15 end
                return old(self,...)
            end
        end)
        context.patch(c[task],def[2],function(old)
            return function(self,data) old(self,data);context.safe(function() runner:onInfo(task,data) end) end
        end)
        context.patch(c[task],def[4],function(old)
            return function(self,data) old(self,data);context.safe(function() runner:onReply(task,data) end) end
        end)
    end
    return runner,function(current)
        if context.now()<manual_until then return true end
        -- Keep unresolved mutations as a cross-module queue barrier.  The
        -- caller may record and skip the current row, but must never resend
        -- an action or clear its journal implicitly.
        for kind in pairs(defs) do
            if kind~=current and ud:getIntegerForKey(key(kind)..':pending',0)~=0 then return true end
        end
        return false
    end
end
return M
