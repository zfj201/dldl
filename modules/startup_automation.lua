-- 仅由模块私有 launch.tsv 启动；普通游戏启动没有副作用。
local M={}
function M.parse(text,now)
    if type(text)~='string' or #text>512 then return end
    local id,rid,srv,created,expires,mode=text:match('^v1\t([%w_-]+)\t([%w_-]+)\t([%w_-]+)\t(%d+)\t(%d+)\t([%w_]+)\n?$')
    created=tonumber(created);expires=tonumber(expires)
    if not id or #id>80 or (mode~='run_all' and mode~='verify') or expires<created
        or expires-created>300 or now<created-5 or now>expires then return end
    return {id=id,rid=rid,srv=srv,created=created,expires=expires,mode=mode}
end
function M.new(env)
    local self={}
    function self:report(status,reason)
        if self.status==status and self.reason==reason then return end
        self.status=status;self.reason=reason
        env.report(self.active.id,status,reason)
    end
    function self:stop(status,reason)
        self:report(status,reason);self.done=true
    end
    function self:tick(text)
        if not self.active then self.active=M.parse(text,env.now());if not self.active then return end end
        local a=self.active
        if self.done then
            local nextRun=M.parse(text,env.now())
            if not nextRun or nextRun.id==a.id then return end
            self.active=nextRun;self.done=false;self.entered=false;self.stable=nil;self.submitted=false
            a=nextRun
        end
        if env.cancelled(a.id) then self:stop('cancelled','user_cancelled');return end
        if env.now()>a.expires and not self.submitted then self:stop('blocked','startup_timeout');return end
        local s=env.inspect()
        if s.blocked then self:stop('blocked',s.blocked);return end
        if s.role then
            if tostring(s.role.rid)~=a.rid or tostring(s.role.srv_id)~=a.srv then
                self:stop('blocked','role_or_server_mismatch');return
            end
            if not self.submitted then
                if not s.ready then self.stable=nil;self:report('waiting','waiting_city_and_helper');return end
                self.stable=self.stable or env.now()
                if env.now()-self.stable<3 then self:report('waiting','confirming_city');return end
                if a.mode=='verify' then self:stop('verified','city_and_role_ready');return end
                self.submitted=true
                env.submit(a)
                self:report('submitted','helper_requested')
            end
            -- 助手运行会隐藏主UI；提交后只检查连接/角色和业务回执，不能再等待主城可见。
            local result=env.result(a.id)
            if result then
                if result.status=='completed' or result.status=='already_completed' then
                    self:stop(result.status,result.reason)
                elseif result.status=='failed' or result.status=='uncertain' or result.status=='rejected' then
                    self:stop(result.status,result.reason)
                else self:report('running',result.reason) end
            end
            return
        end
        self.stable=nil
        if self.submitted then self:stop('uncertain','role_lost_after_submit');return end
        if s.notice then env.closeNotice();self:report('waiting','notice_closed');return end
        if s.login then
            if tostring(s.server)~=a.srv then self:stop('blocked','selected_server_mismatch');return end
            if not s.agreed then self:stop('blocked','agreement_requires_user');return end
            if not s.canEnter then self:report('waiting','waiting_server');return end
            if not self.entered then
                -- 先占位再调用；慢登录/断线时不重复发送进入请求。
                self.entered=true;self:report('entering','start_adventure');env.enter()
            else self:report('waiting','waiting_login_result') end
            return
        end
        self:report('waiting','waiting_sdk_or_login')
    end
    return self
end
return M
