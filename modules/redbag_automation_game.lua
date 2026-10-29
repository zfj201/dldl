-- Guild redbag row in Other Automation; no requests are sent during binding.
local M={POS=-2101780}
function M.bind(Redbag,installed)
 local voyage=assert(installed.voyage);local TYPE,POS=voyage.type,M.POS
 local helper=OneKeyBurdenController:getInstance();local rc=RedbagController:getInstance()
 local ud=cc.UserDefault:getInstance();local clock=GlobalTimeTicket:getInstance()
 local patches,timer,window,complete,runner,internal,manual_until={},nil,nil,nil,nil,false,0
 local owned={}
 local row={id=POS,title='联盟红包·自动领取',is_title=true,is_single_select=true,
  option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE}
 local function now() return GameNet:getInstance():getTime() end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function roleKey() local r=role();return r and r.rid and r.srv_id and tostring(r.srv_id)..':'..r.rid end
 local function guildKey() local r=role();return roleKey() and roleKey()..':'..tostring(r.gsrv_id)..':'..tostring(r.gid) end
 local function identity() local k=guildKey();return k and k..':'..tostring(role()) end
 local function pref() return 'dldl_redbag_v1:'..assert(roleKey())..':enabled' end
 local function key() return 'dldl_redbag_v1:'..assert(guildKey())..':last' end
 local function load()
  local s=ud:getStringForKey(key(),'');if s=='' then return end
  local d=json.decode(s);assert(type(d)=='table' and type(d.entries)=='table','invalid redbag journal');return d
 end
 local function save(a)
  assert(a.identity==identity(),'redbag role or guild changed')
  ud:setStringForKey(key(),json.encode({day=a.day,status=a.status,reason=a.reason,pending=a.pending,entries=a.entries,rejected=a.rejected,unverified=a.unverified}));ud:flush()
 end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function safe(fn)
  local ok,e=pcall(fn)
  if not ok then
   print('[dldl_redbag] '..tostring(e))
   if runner.active then
    local a=runner.active;local success=pcall(function() runner:fail() end)
    if not success then runner.active=nil;a.status='uncertain';a.reason='runtime_error';if a.done then a.done(a) end end
   elseif complete then complete({status='error',reason='runtime_error',entries={}}) end
  end
 end
 local function patch(obj,k,wrap)
  local old=obj[k];assert(type(old)=='function',k)
  local own=rawget(obj,k);local new=wrap(old);obj[k]=new
  patches[#patches+1]={obj=obj,k=k,own=own,new=new}
 end
 local function guard()
  local r=role();if not r then return 'no_role' end
  if not r.gid or r.gid==0 or not r.gsrv_id or r.gsrv_id=='' then return 'no_guild' end
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  if not rc:isRedBagOpen(false) then return 'not_open' end
  if now()<manual_until then return 'manual_operation_pending' end
 end
 local function eligible(b,q)
  local cfg=GuildData.data_guild_red_bag[b.type]
  if not cfg or (cfg.assets~='gold' and cfg.assets~='coin') then return nil,'invalid_config' end
  local special=rc:getModel():getSpecialRedID()
  local quota
  if cfg.id==special then
   quota=q[cfg.id] or {used=0,max=0}
   return quota.max==0 or quota.used<quota.max
  elseif cfg.type==RedbagCoust.redType[RedbagCoust.type.send] then return true
  elseif cfg.type==RedbagCoust.redType[RedbagCoust.type.special] then quota=q[cfg.id]
  elseif cfg.type==RedbagCoust.redType[RedbagCoust.type.welfare] then quota=q[0]
  else return nil,'invalid_config' end
  if not quota then return nil,'invalid_quota' end
  return quota.used<quota.max
 end
 local function restore()
  stopTimer();complete=nil
  if runner and runner.active then runner.active.done=nil;safe(function() runner:cancel() end) end
  for i=#patches,1,-1 do local p=patches[i];if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end end
  local rows=OneKeyBurdenConst.SimplifyTypeList[TYPE]
  for i=#rows,1,-1 do if rows[i]==row then table.remove(rows,i) end end
 end
 local ok,e=pcall(function()
  runner=Redbag.new({identity=identity,day=function() return math.floor((now()+3*3600)/86400) end,now=now,
   load=load,save=save,guard=guard,eligible=eligible,config=function(t) return GuildData.data_guild_red_bag[t] end,
   query=function() rc:sender13523();rc:sender13534() end,
   claim=function(id)
    owned[id]={identity=identity(),until_time=now()+60};internal=true
    local success,err=pcall(function() rc:sender13536(id) end);internal=false;if not success then error(err) end
   end})
  patch(rc,'sender13536',function(old) return function(self,id)
   if not internal and runner.active then message('联盟红包自动领取正在执行，请稍后操作');return end
   if not internal then manual_until=now()+20;owned[id]=nil end
   return old(self,id)
  end end)
  for _,id in ipairs({13523,13534,13536}) do
   patch(rc,'handle'..id,function(old) return function(self,d)
    local o=id==13536 and owned[d.id]
    local own=o and o.identity==identity() and o.until_time>=now()
    if own then
     -- Preserve the original quota update, omit only our own reward animation.
     if d.code==TRUE then self:getModel():updateRedBagReceiveData(d.list) end
    else old(self,d) end
    if runner.active then safe(function() runner:onPacket(id,d) end) end
   end end)
  end
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,t,c)
   local d=old(w,t,c);if c.id==POS then d.is_open=roleKey() and ud:getBoolForKey(pref(),false) and TRUE or FALSE end;return d
  end end)
  patch(helper,'sender31601',function(old) return function(self,groups)
   for _,g in ipairs(groups) do if g.type==TYPE then for _,r in ipairs(g.type_list) do
    if r.pos==POS and roleKey() then ud:setBoolForKey(pref(),r.is_open==TRUE);ud:flush() end
   end end end
   return old(self,groups)
  end end)
  patch(helper,'sender31602',function(old) return function(self,t,p) assert(p~=POS,'local redbag task cannot enter native protocol');return old(self,t,p) end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   local r=w.execute_request_list[w.execute_index]
   if not r or r.type~=TYPE or r.pos~=POS then return old(w) end
   if runner.active then return end
   window=w
   local function done(a)
    stopTimer();complete=nil;window=nil;r.redbag=a;r.local_result=a.status;r.local_reason=a.reason
    if a.status=='cancelled' then
     w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else voyage.advance(w,{type=TYPE,pos=POS,args={}}) end
   end
   complete=done;timer=clock:add(function() safe(function() runner:tick() end) end,0.5)
   safe(function() local success,why=runner:start(done);if not success then done({status='error',reason=why,entries={}}) end end)
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then
    if runner.active then runner.active.done=nil;safe(function() runner:cancel() end) end
    stopTimer();complete=nil;window=nil
   end
   return old(w,...)
  end end)
  local reasons={no_claimable_redbag='当前可领取红包已处理完毕',quota_reached='剩余红包已达领取上限',previous_request_unresolved='上次领取结果待核实',
   no_guild='尚未加入联盟',not_open='联盟红包尚未开放',connection_unavailable='连接不可用',manual_operation_pending='手动领取正在处理',
   invalid_quota='领取额度未确认',invalid_list='红包列表未确认',invalid_config='红包配置已变化',invalid_reply='领取回执未确认',
   query_timeout='查询超时',reply_timeout='领取结果待核实',role_guild_or_day_changed='角色、联盟或游戏日已变化',
   runtime_error='执行异常，已停止',cancelled='已停止',run_limit='本次运行时间已达上限',no_role='角色尚未就绪'}
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.redbag_label then cell.redbag_label:setVisible(false) end
   old(cell,d,index)
   if d.type~=TYPE or d.pos~=POS then return end
   cell.title_lb:setFontSize(24);cell.title_lb:setString('联盟红包 · 自动领取')
   cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.redbag_label then cell.redbag_label=createRichLabel(22,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-52),4,nil,570):addTo(cell.root_wnd) end
   local a=d.redbag or {};local gold,coin,recovered=0,0,0
   for _,e in ipairs(a.entries or {}) do
    if e.recovered then recovered=recovered+1 elseif e.asset=='gold' then gold=gold+e.val elseif e.asset=='coin' then coin=coin+e.val end
   end
   cell.redbag_label:setVisible(true)
   cell.redbag_label:setString((reasons[a.reason] or '执行中')..'\n已领取 '..#(a.entries or {})..' 个｜钻石 '..gold..'｜金币 '..coin
    ..(recovered>0 and '（含已核实历史领取 '..recovered..' 个）' or '')..((a.unverified or 0)>0 and '\n上次红包已过期，领取金额未确认' or '')..((a.rejected or 0)>0 and '\n失效或被抢先领取 '..a.rejected..' 个' or ''))
  end end)
  local rows=OneKeyBurdenConst.SimplifyTypeList[TYPE]
  for _,r in ipairs(rows) do assert(r.id~=POS,'redbag row collision') end
  table.insert(rows,#rows,row) -- Keep the voyage history link at the end.
 end)
 if not ok then restore();error(e) end
 local detach,uninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();detach() end
 installed.uninstall=function()
  assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first')
  restore();uninstall()
 end
 installed.redbag={runner=runner,pos=POS,row=row,load=load}
 return installed.redbag
end
return M
