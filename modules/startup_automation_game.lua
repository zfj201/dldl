-- 由 GL 线程驱动。只关闭已确认的普通登录公告，不全局屏蔽 Dialog/弹窗。
local M={}
function M.bind(Startup,root)
    local function read(name)
        local f=io.open(root..name,'r');if not f then return end
        local s=f:read(513);f:close();return s
    end
    local function write(name,text)
        local f=assert(io.open(root..name..'.tmp','w'));f:write(text);f:close()
        assert(os.rename(root..name..'.tmp',root..name))
    end
    local function instance(name)
        local c=rawget(_G,name)
        if type(c)=='table' and type(c.getInstance)=='function' then return c:getInstance() end
    end
    local panel
    local env={now=os.time,
        cancelled=function(id) return read('cancel.tsv')==id..'\n' end,
        report=function(id,status,reason)
            reason=tostring(reason):gsub('[\t\r\n]',' ')
            local line=table.concat({'v1',id,status,reason,os.time()},'\t')..'\n'
            write('startup.tsv',line)
            local f=io.open(root..'startup.log','a');if f then f:write(line);f:close() end
        end,
        inspect=function()
            if read('java-block.tsv') then return {blocked='required_update_or_sdk_changed'} end
            if not package.loaded.game_start or not GAME_INITED then return {} end
            local login=instance('LoginController')
            local v=login and login.loginView
            local model=login and login:getModel()
            panel=v and v.selected_view
            local role=instance('RoleController')
            local r=role and role:getRoleVo()
            local helper=instance('OneKeyBurdenController')
            local main=instance('MainuiController')
            local ui=main and main:getMainUi()
            local net=instance('GameNet')
            local loader=rawget(_G,'DLDL_EXTENSION_LOADER')
            local installed=loader and loader.installation
            local notice=instance('NoticeController')
            -- 服务器连接本身不代表主城完成；原生主UI、登录窗消失和助手适配均需就绪。
            if r and r.rid and tonumber(r.rid)~=0 and r.srv_id and net and net:IsServerConnect()==true and not v then
                local m=helper and helper:getModel()
                return {role=r,ready=ui and ui:isOpen() and m and m:getTypeOperateList()~=nil
                    and m.type_func_list~=nil and installed and installed.automation~=nil}
            end
            if notice and notice.notice_view then
                -- forceOpen 是官方强制公告，保留给用户处理。
                if notice.notice_view.forceOpen then return {blocked='mandatory_notice'} end
                return {notice=true}
            end
            if v and LoginController.type and v.view_index==LoginController.type.enter_game and panel then
                local d=model and model:getLoginData()
                local valid=panel.root_wnd and not tolua.isnull(panel.root_wnd)
                return {login=true,server=d and d.srv_id,agreed=panel.is_agree==true,
                    canEnter=valid and panel.btn_enter and panel.btn_enter:isVisible()
                        and panel.btn_enter:isTouchEnabled() and d and d.usrName~='' and d.ip and #d.ip>0
                        and not d.isClose and type(panel.onEnterGame)=='function'}
            end
            return {}
        end,
        closeNotice=function() NoticeController:getInstance():closeNoticeView() end,
        enter=function() panel:onEnterGame() end,
        submit=function(a)
            local day=math.floor((os.time()+3*3600)/86400)
            write('request.tsv',table.concat({'v1',a.id,a.rid,a.srv,day,os.time(),os.time()+240,'run_all'},'\t')..'\n')
        end,
        result=function(id)
            local s=read('result.tsv')
            if not s then return end
            local rid,status,reason=s:match('^v1\t([^\t]+)\t([^\t]+)\t([^\t]+)\t')
            if rid==id then return {status=status,reason=reason} end
        end}
    local runner=Startup.new(env)
    function runner:poll()
        local ok,err=pcall(function() self:tick(read('launch.tsv')) end)
        if not ok and self.active then self:stop('blocked','startup_api_error:'..tostring(err)) end
    end
    return runner
end
return M
