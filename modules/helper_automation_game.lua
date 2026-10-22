-- 运行在游戏 GL 线程内。指令目录由 Java 创建，仅 Root 自动化工具与游戏进程读写。
local M={}
function M.bind(Automation)
    local root
    local helper=OneKeyBurdenController:getInstance()
    local ud=cc.UserDefault:getInstance()
    local function write(name,text)
        local path=root..name;local f=assert(io.open(path..'.tmp','w'));f:write(text);f:close()
        assert(os.rename(path..'.tmp',path))
    end
    local function role() return RoleController:getInstance():getRoleVo() end
    local function connected() return GameNet:getInstance():IsServerConnect()==true end
    local function day() return math.floor((os.time()+3*3600)/86400) end -- 北京时间05:00游戏日刷新。
    local function ready()
        local r=role();local m=helper:getModel()
        return r and r.rid and r.srv_id and connected() and m:getTypeOperateList()~=nil and m.type_func_list~=nil
    end
    local env={now=os.time,day=day,role=role,connected=connected,ready=ready,
        cancelled=function(id)
            local f=io.open(root..'cancel.tsv','r');if not f then return false end
            local s=f:read(100);f:close();return s==id..'\n'
        end,
        recall=function(k) return ud:getStringForKey(k,'') end,
        remember=function(k,v) ud:setStringForKey(k,v);ud:flush() end,
        report=function(text) write('result.tsv',text) end,
        busy=function()
            return helper.onekeyburden_main_window~=nil or helper.onekeyburden_auto_window~=nil
                or BattleController:getInstance():isInFight()
        end,
        open=function() helper:openOneKeyBurdenMainWindow(true) end,
        opened=function()
            local w=helper.onekeyburden_main_window
            return w and w:isOpen() and w.onekey_btn and type(w.task_list)=='table' and type(w.operate_list)=='table'
        end,
        queue=function() return helper.onekeyburden_main_window:saveOperateRequest(true) end,
        start=function(rows) helper:openOnekeyburdenAutoWindow(true,rows,0) end,
        cancel=function()
            if helper.onekeyburden_auto_window then helper:openOnekeyburdenAutoWindow(false) end
            if helper.onekeyburden_main_window then helper:openOneKeyBurdenMainWindow(false) end
        end,
        snapshot=function()
            local w=helper.onekeyburden_auto_window;if not w then return end
            local rows=w.execute_request_list;local all=#rows>0
            for _,row in ipairs(rows) do if not row.is_execute then all=false end end
            return {index=w.execute_index,total=#rows,finished=w.is_execute_finish==true,all_executed=all,rows=rows}
        end,
        results=function(rows)
            local out={}
            for _,r in ipairs(rows) do
                out[#out+1]=table.concat({r.type,r.pos,r.local_result or (r.is_execute and 'executed' or 'pending'),
                    tostring(r.local_reason or ''):gsub('[\t\r\n]',' ')},'\t')
            end
            write('tasks.tsv',table.concat(out,'\n')..'\n')
        end}
    local runner=Automation.new(env)
    function runner:poll(directory)
        root=directory
        local r=role()
        write('ready.tsv',table.concat({'v1',ready() and 'ready' or 'waiting',r and r.rid or '-',r and r.srv_id or '-',day(),os.time()},'\t')..'\n')
        local f=io.open(root..'request.tsv','r');local text
        if f then text=f:read(513);f:close() end
        -- 终态不被残留请求覆盖；新进程通过持久化记录返回已完成或未确认。
        if self.last and text and text:match('^v1\t([^\t]+)\t')==self.last.id and not self.active and self.status~='waiting' then return end
        local ok,err=pcall(function() self:tick(text) end)
        if not ok then self:fail('automation_error:'..tostring(err)) end
    end
    return runner
end
return M
