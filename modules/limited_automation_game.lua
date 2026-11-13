-- Local limited-event category. The activity's own protocol settles each stage.
local M={TYPE=-2101770,POS=-2101769}
local reasons={available_complete='当前可执行关卡与奖励已处理',not_open='活动未开放或已结束',no_attempts='挑战次数不足',
 unknown_config='当前活动配置未确认',invalid_state='活动状态未确认',manual_game_pending='存在手动未结算挑战，已跳过',
 request_unresolved='上次挑战结果待核实',reward_unconfirmed='奖励领取结果待核实',action_rejected='游戏未接受操作',
 activity_changed='活动期已变化',connection_unavailable='连接不可用',manual_operation_pending='正在手动操作活动',
 role_or_day_changed='角色或游戏日已变化',response_timeout='等待游戏响应超时',runtime_error='执行异常',cancelled='已停止'}
function M.bind(Limited,installed)
 local TYPE,POS=M.TYPE,M.POS
 local helper=OneKeyBurdenController:getInstance();local ac=ActionController:getInstance();local pm=ProtoMgr:getInstance()
 local ud=cc.UserDefault:getInstance();local clock=GlobalTimeTicket:getInstance()
 local patches={};local runner,timer,window,internal;local manual_until=0
 local category={id=TYPE,sort_id=SimplifyData.data_list[16].sort_id+0.625,name='限时活动',key='',limit={},type=0}
 local row={id=POS,title='三炮冒险·自动通关与领奖',is_title=true,is_single_select=true,
  option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE};local rows={row}
 local function now() return GameNet:getInstance():getTime() end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function roleKey() local r=role();return r and r.rid and r.srv_id and tostring(r.srv_id)..':'..r.rid end
 local function identity() local k=roleKey();return k and k..':'..tostring(role()) end
 local function pref() return 'dldl_sanpao_v1:'..assert(roleKey()) end
 local function day() return math.floor((now()+3*3600)/86400) end
 local function guard()
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  local v=ac:getActionSubTabVo(93005)
  if not v or not v.end_time or v.end_time<=now() then return 'not_open' end
  if now()<manual_until or ac.action_jfcz_window or ac.action_jfcz_result_window or ac.action_jfcz_reward_window then return 'manual_operation_pending' end
 end
 local function patch(obj,k,wrap)
  local old=obj[k];assert(type(old)=='function',k);local p={obj=obj,k=k,own=rawget(obj,k)};p.new=wrap(old);obj[k]=p.new;patches[#patches+1]=p
 end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function safe(fn)
  local ok,e=pcall(fn);if not ok then print('[dldl_sanpao] '..tostring(e));if runner and runner.active then runner:finish('uncertain','runtime_error') end end
 end
 local function restore()
  stopTimer();window=nil
  if runner and runner.active then runner.active.done=nil;runner.active.changed=nil;runner:cancel() end
  for i=#patches,1,-1 do local p=patches[i];if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end end
  if SimplifyData.data_list[TYPE]==category then SimplifyData.data_list[TYPE]=nil end
  if OneKeyBurdenConst.SimplifyTypeList[TYPE]==rows then OneKeyBurdenConst.SimplifyTypeList[TYPE]=nil end
 end
 local ok,e=pcall(function()
  assert(not SimplifyData.data_list[TYPE] and not OneKeyBurdenConst.SimplifyTypeList[TYPE],'limited category collision')
  runner=Limited.new({now=now,identity=identity,day=day,guard=guard,config=function() return HolidayBitData end,
   level=function() return role().lev end,
   load=function() local s=ud:getStringForKey(pref()..':last','');if s~='' then return json.decode(s) end end,
   save=function(a) assert(a.identity==identity(),'role changed');ud:setStringForKey(pref()..':last',json.encode({pending=a.pending}));ud:flush() end,
   query=function() ac:sender16413() end,
   act=function(kind,p)
    internal=true;local success,err=pcall(function()
     if kind=='start' then ac:sender16414()
     elseif kind=='settle' then ac:sender16415(p.chapter,TRUE,p.score,p.round)
     elseif kind=='claim' then ac:sender16416() end
    end);internal=false;if not success then error(err) end
   end})
  patch(ac,'SendProtocal',function(old) return function(obj,id,...)
   if id>=16414 and id<=16416 and not internal then
    if runner.active then message('三炮冒险自动化正在执行，请先中断');return end;manual_until=now()+20
   end;return old(obj,id,...)
  end end)
  -- Suppress only the result window owned by this automation; retain the
  -- controller's normal cleanup and all manually played result windows.
  patch(ac,'openActionJfczResultWindow',function(old) return function(obj,shown,...)
   if shown and runner.active and runner.active.phase=='settle' then return end;return old(obj,shown,...)
  end end)
  patch(pm,'cmd_callback',function(old) return function(obj,id,d)
   old(obj,id,d)
   if runner.active then safe(function()
    if id==16413 then runner:onInfo(d)
    elseif id==16414 then runner:onReply('start',d)
    elseif id==16415 then runner:onReply('settle',d)
    elseif id==16416 then runner:onReply('claim',d) end
   end) end
  end end)
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,t,c)
   local d=old(w,t,c);if c.id==POS then d.is_open=roleKey() and ud:getBoolForKey(pref()..':enabled',false) and TRUE or FALSE end;return d
  end end)
  patch(helper,'sender31601',function(old) return function(obj,groups)
   local filtered={};for _,g in ipairs(groups) do if g.type==TYPE then
    for _,r in ipairs(g.type_list) do if r.pos==POS and roleKey() then ud:setBoolForKey(pref()..':enabled',r.is_open==TRUE) end end
   else filtered[#filtered+1]=g end end
   ud:flush();if #filtered>0 then return old(obj,filtered) end
  end end)
  patch(helper,'sender31602',function(old) return function(obj,t,p) assert(t~=TYPE and p~=POS,'limited task is local');return old(obj,t,p) end end)
  for _,method in ipairs({'sender31609','sender31604'}) do patch(helper,method,function(old) return function(obj,t,id,...)
   if (method=='sender31609' and id==TYPE) or (method=='sender31604' and t==TYPE) then return end;return old(obj,t,id,...)
  end end) end
  patch(helper:getModel(),'getTipsTypeRed',function(old) return function(obj,t,id) if id==TYPE then return false end;return old(obj,t,id) end end)
  patch(OneKeyBurdenAutoWindow,'updateDataList',function(old) return function(w,d)
   local r=w.execute_request_list[w.execute_index];if r and r.pos==POS then return end;return old(w,d)
  end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   local r=w.execute_request_list[w.execute_index];if not r or r.type~=TYPE or r.pos~=POS then return old(w) end
   if runner.active then return end;window=w
   local function changed(a) r.limited=a;w.other_progress=(w.other_progress or 0)+1;w:updateLoopList() end
   local function done(a)
    stopTimer();window=nil;r.limited=a;r.local_result=a.status;r.local_reason=a.reason
    if a.status=='cancelled' then w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else installed.voyage.advance(w,{type=TYPE,pos=POS,args={}}) end
   end
   timer=clock:add(function() safe(function() runner:tick() end) end,0.5)
   safe(function() local success,why=runner:start(done,changed);if not success then done({status='error',reason=why}) end end)
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then if runner.active then runner.active.done=nil;runner.active.changed=nil;runner:cancel() end;stopTimer();window=nil end
   return old(w,...)
  end end)
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.limited_label then cell.limited_label:setVisible(false) end;old(cell,d,index);if d.pos~=POS then return end
   cell.title_lb:setFontSize(24);cell.title_lb:setString(row.title);cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.limited_label then cell.limited_label=createRichLabel(19,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-48),2,nil,570):addTo(cell.root_wnd) end
   local a=d.limited or {};local text=reasons[a.reason] or '执行中';local stages={}
   for _,v in ipairs(a.entries or {}) do stages[#stages+1]='第'..v.chapter..'关 '..v.score..'分' end
   if #stages>0 then text=text..'\n'..table.concat(stages,'；') end
   text=text..'\n累计积分：'..(a.score or 0)..'，已领取 '..(a.claimed or 0)..' 档奖励'
   cell.limited_label:setVisible(true);cell.limited_label:setString(text)
  end end)
  SimplifyData.data_list[TYPE]=category;OneKeyBurdenConst.SimplifyTypeList[TYPE]=rows
 end)
 if not ok then restore();error(e) end
 local detach,uninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();detach() end
 installed.uninstall=function() assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first');restore();uninstall() end
 installed.limited={runner=runner,row=row,type=TYPE,pos=POS};return runner
end
return M
