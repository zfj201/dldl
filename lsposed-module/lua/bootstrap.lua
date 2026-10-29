-- Java 在原渲染结束后的 GL 线程调用本文件。返回码供 JNI 记录状态：
-- 0=已挂载，1=等待，2=停用，3=发现旧组合包，-1=失败。
local source=debug.getinfo(1,'S').source
local root=assert(source:match('^@(.*/)'),'bootstrap path missing')
-- dofile 每秒重读本文件，用游戏全局表保存状态，避免每次重新安装。
local state=rawget(_G,'DLDL_EXTENSION_LOADER')
if not state then state={generation=0};rawset(_G,'DLDL_EXTENSION_LOADER',state) end
local function status(value)
    if state.status==value then return end
    state.status=value
    pcall(function()
        local f=assert(io.open(root..'status.log','a'))
        f:write(tostring(os.time()),'|',value,'|generation=',state.generation,'\n');f:close()
        f=assert(io.open(root..'status.txt','w'));f:write(value,'\ngeneration=',state.generation,'\n');f:close()
    end)
end
local function exists(path) local f=io.open(path,'r');if f then f:close();return true end;return false end
-- 登录早于 GAME_INITED；启动状态机须先于业务挂载检查运行。
-- 没有显式指令或模块已停用时不加载、不操作游戏页面。
if not exists(root..'../disabled') and exists(root..'../automation/launch.tsv') then
    local ok,err=pcall(function()
        if not state.startup then state.startup=assert(loadfile(root..'startup.lua'))()(root..'../automation/') end
        state.startup:poll()
    end)
    if not ok then status('startup_failed:'..tostring(err)) end
end
local names={'OneKeyBurdenController','VipController','GlobalTimeTicket','RoleController','GameNet',
 'DungeonstoneController','PantheonController','SoulDomainController','PartnersummonController',
 'ElitematchController','HeroController','BackpackController','BattleController','GuildController','GodRuinsController','GuildbossController','JiaLingPassController','CommonGiftShopController','VoyageController','MineController','RedbagController'}
local function pollAutomation()
    if state.installation.extras then state.installation.extras:pollDeferred() end
    if state.installation.automation then state.installation.automation:poll(root..'../automation/') end
end
local ok,result=pcall(function()
    -- game_start 只用来判断官方启动是否完成；本方案不修改或替换它。
    if not package.loaded.game_start or not GAME_INITED then status('waiting_game_start');return 1 end
    local refs={beginGame,OneKeyBurdenMainWindow,OneKeyBurdenAutoWindow,OneKeyBurdenAutoItem,OneKeyBurdenConst,package.loaded.game_start}
    for _,name in ipairs(names) do
        local cls=rawget(_G,name)
        if type(cls)~='table' or type(cls.getInstance)~='function' then status('waiting:'..name);return 1 end
        refs[#refs+1]=cls;refs[#refs+1]=cls:getInstance()
    end
    local helper=OneKeyBurdenController:getInstance()
    local list=OneKeyBurdenConst and OneKeyBurdenConst.SimplifyTypeList[OneKeyBurdenConst.SimplifyType.DAILY_TASK]
    if type(list)~='table' then status('waiting_helper_list');return 1 end
    refs[#refs+1]=list
    -- “同一代”指运行中的函数、类、控制器实例及列表仍是同一对象，不是游戏版本或日期。
    -- 对象被重新初始化时才拆旧挂新，适应可观察到的业务对象重建。
    local same=state.refs and #state.refs==#refs
    if same then for i,v in ipairs(refs) do if state.refs[i]~=v then same=false;break end end end
    local disabled=exists(root..'../disabled')
    -- 常规每秒回调到此立即结束；重复检查不会新增条目或发任务请求。
    if same and state.installation and not disabled then pollAutomation();return 0 end
    -- 窗口打开时先等关闭，避免拆挂过程中破坏正在执行的助手队列。
    if helper.onekeyburden_main_window or helper.onekeyburden_auto_window then
        status(disabled and 'disable_waiting_helper_close' or 'waiting_helper_close');return 1
    end
    if state.installation then
        state.installation.detach()
        if rawget(_G,'DLDL_DAILY_GIFTS')==state.installation then _G.DLDL_DAILY_GIFTS=nil end
        state.installation=nil
    end
    if disabled then status('disabled');return 2 end
    if same and state.failed then return -1 end
    state.refs=refs;state.failed=false
    -- 旧 game_start 组合包若还在运行，拒绝再挂一份，需先迁移回对应版本官方启动文件。
    if rawget(_G,'DLDL_DAILY_GIFTS') then status('legacy_payload_present');return 3 end
    for _,row in ipairs(list) do
        if type(row.id)=='number' and row.id>=-2101802 and row.id<=-2101784 then
            status('custom_id_collision');state.failed=true;return -1
        end
    end
    -- payload 返回安装工厂：这里只加菜单和方法包装；用户点“执行”后才发送业务请求。
    local factory=assert(loadfile(root..'payload.lua'))()
    state.generation=state.generation+1
    local installed=factory()
    assert(installed and #installed.specs==17,'unexpected entry count')
    state.installation=installed;_G.DLDL_DAILY_GIFTS=installed
    status('installed:17+voyage+mine+redbag:version=0.6.2')
    pollAutomation()
    return 0
end)
if not ok then state.failed=true;status('failed:'..tostring(result));return -1 end
return result
