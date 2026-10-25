-- 定时工具与助手之间的串行执行状态机。相同角色同一游戏日只启动一次自动整队执行。
-- 持久化占位早于任何执行动作：进程退出后保留未确认状态，不自动重跑消费请求。
local M = {}
function M.new(env)
    local self = {env=env}
    local function clean(v) return tostring(v or ''):gsub('[\t\r\n]',' ') end
    function self:report(status, reason, index, total)
        self.status=status;self.reason=reason
        local a=self.active or self.last
        env.report(table.concat({'v1',a and a.id or '-',status,clean(reason),index or 0,total or 0,env.now()},'\t')..'\n')
    end
    function self:finish(status,reason)
        local a=self.active
        if a then
            env.remember(a.key,a.id..'|'..status)
            self.last=a
        end
        self:report(status,reason,a and a.index,a and a.total)
        self.active=nil
    end
    function self:accept(text)
        if self.active then return end
        if type(text)~='string' or #text>512 then return end
        local id,rid,srv,day,created,expires,mode=text:match('^v1\t([%w_-]+)\t([%w_-]+)\t([%w_-]+)\t(%d+)\t(%d+)\t(%d+)\t(run_all)\n?$')
        if not id or #id>80 then return end
        local a={id=id,rid=rid,srv=srv,day=tonumber(day),created=tonumber(created),expires=tonumber(expires),mode=mode}
        self.last=a
        if env.cancelled and env.cancelled(id) then self:report('rejected','user_cancelled');return end
        if env.now()<a.created-5 or env.now()>a.expires or a.expires-a.created>300 or a.expires<a.created then
            self:report('rejected','expired_request');return
        end
        local role=env.role()
        if not role or tostring(role.rid)~=rid or tostring(role.srv_id)~=srv or env.day()~=a.day then
            self:report('rejected','role_or_day_mismatch');return
        end
        a.key='dldl_automation_v1:'..srv..':'..rid..':'..day
        local previous=env.recall(a.key)
        if previous and previous~='' then
            local oldid,status=previous:match('^([^|]+)|(.+)$')
            self:report(status=='completed' and 'already_completed' or 'uncertain',
                status=='completed' and 'daily_run_completed' or 'previous_run_unresolved');return
        end
        if not env.ready() then self:report('waiting','game_not_ready');return end
        if env.busy() then self:report('rejected','helper_or_battle_busy');return end
        self.active=a;a.phase='opening';a.start=env.now();a.progress_at=a.start
        env.remember(a.key,a.id..'|started')
        self:report('opening','opening_helper')
        env.open()
    end
    function self:tick(text)
        if not self.active then self:accept(text);return end
        local a=self.active
        if env.cancelled and env.cancelled(a.id) then
            env.cancel();self:finish('uncertain','user_cancelled');return
        end
        local role=env.role()
        if not role or tostring(role.rid)~=a.rid or tostring(role.srv_id)~=a.srv or env.day()~=a.day or not env.connected() then
            env.cancel();self:finish('uncertain','connection_or_role_changed');return
        end
        if a.phase=='opening' then
            if env.now()-a.start>30 then env.cancel();self:finish('failed','helper_open_timeout');return end
            if not env.opened() then return end
            -- saveOperateRequest(true) 与原生“一键执行”一致，包含所有已开启类别。
            a.phase='starting';self:report('starting','building_all_categories')
            local rows=env.queue()
            a.total=#rows;a.index=0
            if #rows==0 then self:finish('completed','empty_enabled_list');return end
            a.phase='running';a.progress_at=env.now()
            self:report('running','all_categories_started',0,a.total)
            env.start(rows)
            return
        end
        local snapshot=env.snapshot()
        if not snapshot then self:finish('uncertain','execution_window_closed');return end
        a.index=snapshot.index;a.total=snapshot.total
        if snapshot.finished then
            if snapshot.all_executed then
                env.results(snapshot.rows);self:finish('completed','queue_finished')
            else self:finish('uncertain','queue_stopped_early') end
            return
        end
        local progress=snapshot.progress or 0
        if a.index~=a.last_index or progress~=(a.last_progress or 0) then a.last_index=a.index;a.last_progress=progress;a.progress_at=env.now() end
        if env.now()-a.progress_at>180 then
            env.cancel();self:finish('uncertain','queue_progress_timeout');return
        end
        self:report('running','executing',a.index,a.total)
    end
    function self:fail(reason)
        -- 在打开/保存/执行中出现异常，保持当天占位；消费结果不会被误认为尚未开始。
        if self.active then pcall(env.cancel);self:finish('uncertain',reason) end
    end
    return self
end
return M
