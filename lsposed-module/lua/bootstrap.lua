-- Invoked after nativeRender, in the engine GL thread. Returns an integer for JNI.
local source=debug.getinfo(1,'S').source
local root=assert(source:match('^@(.*/)'),'bootstrap path missing')
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
local names={'OneKeyBurdenController','VipController','GlobalTimeTicket','RoleController','GameNet',
 'DungeonstoneController','PantheonController','SoulDomainController','PartnersummonController',
 'ElitematchController','HeroController','BackpackController','BattleController','GuildController','GodRuinsController'}
local ok,result=pcall(function()
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
    local same=state.refs and #state.refs==#refs
    if same then for i,v in ipairs(refs) do if state.refs[i]~=v then same=false;break end end end
    local disabled=exists(root..'../disabled')
    if same and state.installation and not disabled then return 0 end
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
    -- An old game_start payload must be migrated, never installed twice.
    if rawget(_G,'DLDL_DAILY_GIFTS') then status('legacy_payload_present');return 3 end
    for _,row in ipairs(list) do
        if type(row.id)=='number' and row.id>=-2101802 and row.id<=-2101787 then
            status('custom_id_collision');state.failed=true;return -1
        end
    end
    local factory=assert(loadfile(root..'payload.lua'))()
    state.generation=state.generation+1
    local installed=factory()
    assert(installed and #installed.specs==14,'unexpected entry count')
    state.installation=installed;_G.DLDL_DAILY_GIFTS=installed
    status('installed:14:version=0.2.0')
    return 0
end)
if not ok then state.failed=true;status('failed:'..tostring(result));return -1 end
return result
