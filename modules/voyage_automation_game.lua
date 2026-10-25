-- Local category, normal voyage senders, durable result history and display projection.
local M={TYPE=-2101803,POS=-2101783,HISTORY=-2101782}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function clean(v) return tostring(v or ''):gsub('[\r\n\t<>]',' ') end
local quality={[0]='白',[1]='绿',[2]='蓝',[3]='紫',[4]='橙',[5]='红'}
local reasons={insufficient_intelligence='情报不足，已停止',energy_cache_unavailable='缓存情报尚不可用，已停止',
 no_refreshable_orders='暂无可刷新的任务',insufficient_diamonds='钻石不足，已停止',refresh_limit='今日刷新次数已达上限',
 request_unresolved='请求结果待核实，已停止',previous_request_recovered='已恢复上次请求结果',action_rejected='游戏拒绝操作，已停止',
 cancelled='已停止',role_or_day_changed='角色或游戏日已变化',manual_operation_pending='正在手动操作，请稍后运行',
 dispatch_conditions_unmet='没有满足派遣条件的魂师',connection_unavailable='连接不可用',query_timeout='查询超时，已停止',
 runtime_error='执行异常，已停止',not_open='敏堂尚未开放',invalid_order_state='任务数据未确认，已停止',
 invalid_assets='资产数据未确认，已停止',invalid_cost_config='情报消耗配置已变化',invalid_refresh_config='刷新配置已变化',
 no_history='暂无派遣记录'}
function M.bind(Voyage,installed)
 local TYPE,POS,HISTORY=M.TYPE,M.POS,M.HISTORY
 local helper=OneKeyBurdenController:getInstance();local vc=VoyageController:getInstance()
 local patches={};local clock=GlobalTimeTicket:getInstance();local ud=cc.UserDefault:getInstance()
 assert(json and type(json.encode)=='function' and type(json.decode)=='function','json library missing')
 assert(not SimplifyData.data_list[TYPE] and not OneKeyBurdenConst.SimplifyTypeList[TYPE],'automation category collision')
 local category={id=TYPE,sort_id=SimplifyData.data_list[16].sort_id+0.5,name='其他自动化',key='',limit={},type=0}
 local setting={id=POS,title='敏堂·自动派遣与刷新',is_title=true,is_single_select=true,
  option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE}
 local history={id=HISTORY,title='查看最近派遣结果',is_title=true,item_funname='createVoyageHistoryItem',default_option=FALSE}
 local rows={setting,history}
 local runner,timer,window,row,internal,manual_until=nil,nil,nil,nil,false,0
 local complete,advance
 local function role() return RoleController:getInstance():getRoleVo() end
 local function key()
  local r=role();if r and r.rid and r.srv_id then return tostring(r.srv_id)..':'..tostring(r.rid) end
 end
 local function identity() local k=key();return k and k..':'..tostring(role()) end
 local function now() return GameNet:getInstance():getTime() end
 local function day() return math.floor((now()+3*3600)/86400) end
 local function pref() return 'dldl_voyage_v1:'..assert(key())..':enabled' end
 local function prefix()
  local k=assert(key()):gsub('.',function(c) return string.format('%02x',string.byte(c)) end)
  return cc.FileUtils:getInstance():getWritablePath()..'dldl_voyage_'..k..'_'
 end
 local function read(path)
  local f=io.open(path,'r');if not f then return end
  local text=f:read('*a');f:close();return text
 end
 local function write(path,text)
  local f=assert(io.open(path..'.tmp','w'));assert(f:write(text));assert(f:close());assert(os.rename(path..'.tmp',path))
 end
 local function load()
  local text=read(prefix()..'latest.json');if not text then return end
  local d=json.decode(text)
  assert(type(d)=='table' and d.role==key() and type(d.entries)=='table' and type(d.refresh)=='table','invalid voyage journal')
  return d
 end
 local function save(a)
  -- Never save a callback, UI object or another role's journal.
  assert(a.identity==identity(),'voyage journal role changed')
  local d={role=key(),id=a.id,day=a.day,entries=a.entries,refresh=a.refresh,pending=a.pending,
   progress=a.progress,status=a.status,reason=a.reason,remaining=a.remaining}
  local text=json.encode(d)
  write(prefix()..a.id..'.json',text);write(prefix()..'latest.json',text)
 end
 local function patch(obj,k,wrap,optional)
  local old=obj[k];if not optional then assert(type(old)=='function',k) end
  local own=rawget(obj,k);local new=wrap(old);obj[k]=new
  patches[#patches+1]={obj=obj,k=k,own=own,new=new}
 end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function safe(fn)
  local ok,e=pcall(fn)
  if not ok then
   print('[dldl_voyage] '..tostring(e))
   if runner and runner.active then
    local a=runner.active
    local done=a.done;local result,err=pcall(function() runner:fail() end)
    if not result then runner.active=nil;a.status='uncertain';a.reason='runtime_error';if done then done(a) end end
   elseif complete then complete({status='error',reason='runtime_error',entries={},refresh={}}) end
  end
 end
 local function balance()
  local r=role();local bm=BackpackController:getInstance():getModel()
  return {energy=r.energy,cache=r.energy_cache or 0,tickets=bm:getItemNumByBid(10014),diamonds=bm:getItemNumByBid(3),manual_epoch=ud:getIntegerForKey(pref()..':manual_epoch',0)}
 end
 local function discount() return ShippingData.data_const.discount.val end
 local function costFloor(activity)
  local min
  for _,c in pairs(ShippingData.data_order) do
   if Voyage.select(c) then
    local n=runner:cost(c,activity);if not n then return end
    if not min or n<min then min=n end
   end
  end
  return min
 end
 local function payment(info,b)
  local c=ShippingData.data_refresh[role().vip_lev];local t=ShippingData.data_const.refresh_cost
  if not c or not uint(c.free_times) or not uint(c.all_times) or not t or type(t.val)~='table' or #t.val~=1
   or t.val[1][1]~=10014 or not uint(t.val[1][2]) or t.val[1][2]==0
   or type(c.expend)~='table' or #c.expend~=1 or c.expend[1][1]~=3 or not uint(c.expend[1][2]) or c.expend[1][2]==0 then
   return nil,'invalid_refresh_config'
  end
  if info.free_times<c.free_times then return {kind='free',num=0} end
  if b.tickets>=t.val[1][2] then return {kind='ticket',num=t.val[1][2]} end
  if info.coin_times>=c.all_times then return nil,'refresh_limit' end
  if b.diamonds<c.expend[1][2] then return nil,'insufficient_diamonds' end
  return {kind='diamond',num=c.expend[1][2]}
 end
 local function assign(level,c)
  if level>=ShippingData.data_const.shipping_lev.val then return {} end
  local conditions=VoyageModel.resetConditionData(c.condition)
  if #conditions~=#c.condition then return nil,'dispatch_conditions_unmet' end
  local heroes;VoyageModel.getOneKeyHeroList(conditions,function(list) heroes=list end)
  if not heroes or #heroes>c.limit_num or not VoyageModel.checkIsMeetAllCondition(conditions,heroes) then return nil,'dispatch_conditions_unmet' end
  local ids,seen={},{}
  for _,h in ipairs(heroes) do
   if seen[h.partner_id] or vc:getModel():checkHeroIsInTaskById(h.partner_id) then return nil,'dispatch_conditions_unmet' end
   seen[h.partner_id]=true;ids[#ids+1]={partner_id=h.partner_id}
  end
  return ids
 end
 local function guard()
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  if now()<manual_until then return 'manual_operation_pending' end
  if not SysController:getInstance():checkIsOpenByKey('mingtang_build',false) then return 'not_open' end
 end
 local function showHistory()
  if window or helper.onekeyburden_auto_window then message('请先关闭执行结果');return end
  local ok,d=pcall(load)
  if not ok then message('派遣记录读取失败');return end
  local r={type=TYPE,pos=POS,is_execute=true,voyage=d or {entries={},refresh={},reason='no_history'},voyage_history=true}
  helper:openOnekeyburdenAutoWindow(true,{r},0)
 end
 local function display(w)
  local out={}
  for i=1,math.min(w.execute_index,#w.execute_request_list) do
   local r=w.execute_request_list[i];out[#out+1]={data=r,index=i}
   for _,e in ipairs(r.voyage and r.voyage.entries or {}) do out[#out+1]={data={type=TYPE,pos=POS,is_execute=true,voyage_entry=e},index=i} end
  end
  return out
 end
 local function rewardText(award)
  local out={}
  for _,v in ipairs(award or {}) do
   local c=ItemData.data_get_data(v[1]);out[#out+1]=clean(c and c.name or v[1])..'×'..clean(v[2])
  end
  return table.concat(out,'、')
 end
 local function restore()
  stopTimer();complete=nil
  if runner and runner.active then runner.active.done=nil;runner.active.changed=nil;safe(function() runner:cancel() end) end
  for i=#patches,1,-1 do local p=patches[i]
   if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end
  end
  if SimplifyData.data_list[TYPE]==category then SimplifyData.data_list[TYPE]=nil end
  if OneKeyBurdenConst.SimplifyTypeList[TYPE]==rows then OneKeyBurdenConst.SimplifyTypeList[TYPE]=nil end
 end
 local ok,err=pcall(function()
  runner=Voyage.new({identity=identity,day=day,now=now,load=load,save=save,balance=balance,
   config=function(bid) return ShippingData.data_order[bid] end,discount=discount,costFloor=costFloor,payment=payment,assign=assign,guard=guard,
   runId=function()
    local k=pref()..':sequence';local n=ud:getIntegerForKey(k,0)+1;ud:setIntegerForKey(k,n);ud:flush()
    return tostring(os.time())..'_'..n
   end,
   query=function() vc:requestVoyageInfo();vc:requestActivityStatus() end,
   act=function(kind,p,ids)
    internal=true
    local success,e=pcall(function()
     if kind=='dispatch' then vc:requestReceiveOrder(p.order_id,ids) else vc:requestRefreshOrder() end
    end)
    internal=false;if not success then error(e) end
   end})
  for _,method in ipairs({'requestReceiveOrder','requestRefreshOrder','requestFinishOrder','requestQuickReceiveOrder'}) do
   patch(vc,method,function(old) return function(obj,...)
    if not internal and runner.active then message('敏堂自动化正在执行，请先中断');return end
    if not internal then
     manual_until=now()+20;ud:setIntegerForKey(pref()..':manual_epoch',ud:getIntegerForKey(pref()..':manual_epoch',0)+1);ud:flush()
    end
    return old(obj,...)
   end end)
  end
  for _,id in ipairs({23800,23801,23802,23804,23805}) do
   patch(vc,'handle'..id,function(old) return function(obj,d)
    old(obj,d);if runner.active then safe(function() runner:onPacket(id,d) end) end
   end end)
  end
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,k,c)
   local d=old(w,k,c)
   if c.id==POS then d.is_open=key() and ud:getBoolForKey(pref(),false) and TRUE or FALSE end
   return d
  end end)
  patch(OneKeyBurdenMainWindow,'createVoyageHistoryItem',function() return function(w,d)
   local node=w:createTopbg(d,30);node.toggle_list={};node:setTouchEnabled(true)
   registerButtonEventListener(node,function() safe(showHistory) end,true)
   return node
  end end,true)
  patch(helper,'sender31601',function(old) return function(obj,groups)
   local filtered={}
   for _,g in ipairs(groups) do
    if g.type==TYPE then
     for _,r in ipairs(g.type_list) do if r.pos==POS and key() then ud:setBoolForKey(pref(),r.is_open==TRUE) end end
    else filtered[#filtered+1]=g end
   end
   ud:flush();if #filtered>0 then return old(obj,filtered) end
  end end)
  patch(helper,'sender31602',function(old) return function(obj,t,p)
   assert(t~=TYPE and p~=POS and p~=HISTORY,'local voyage ID cannot reach native protocol')
   if p==13 then
    if runner.active then return end
    ud:setIntegerForKey(pref()..':manual_epoch',ud:getIntegerForKey(pref()..':manual_epoch',0)+1);ud:flush()
   end
   return old(obj,t,p)
  end end)
  patch(helper,'sender31609',function(old) return function(obj,t,id)
   if id==TYPE then return end;return old(obj,t,id)
  end end)
  patch(helper,'sender31604',function(old) return function(obj,t,op)
   if t==TYPE then return end;return old(obj,t,op)
  end end)
  patch(helper:getModel(),'getTipsTypeRed',function(old) return function(obj,t,id)
   if id==TYPE then return false end;return old(obj,t,id)
  end end)
  patch(OneKeyBurdenMainWindow,'saveOperateRequest',function(old) return function(w,all)
   local queue=old(w,all);local selected=false
   for _,r in ipairs(queue) do if r.type==TYPE and r.pos==POS then selected=true end end
   for i=#queue,1,-1 do if queue[i].pos==HISTORY or (selected and queue[i].pos==13) then table.remove(queue,i) end end
   return queue
  end end)
  advance=OneKeyBurdenAutoWindow.updateDataList
  patch(OneKeyBurdenAutoWindow,'updateDataList',function(old) return function(w,d)
   local r=w.execute_request_list[w.execute_index]
   if r and r.type==TYPE then return end;return old(w,d)
  end end)
  patch(OneKeyBurdenAutoWindow,'openRootWnd',function(old) return function(w,list,op)
   if list[1] and list[1].voyage_history then
    w.voyage_history=true;w.operate_type=op;w.execute_request_list=list;w.execute_index=1;w.is_execute_finish=true
    w.stop_btn_lb:setString('关闭');w:updateLoopList();return
   end
   return old(w,list,op)
  end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   if w.voyage_history then return end
   local r=w.execute_request_list[w.execute_index]
   if not r or r.type~=TYPE or r.pos~=POS then return old(w) end
   if runner.active then return end
   window=w;row=r
   local function changed(a) r.voyage=a;w.voyage_progress=runner.progress;w:updateLoopList() end
   local function done(a)
    stopTimer();complete=nil;r.voyage=a;r.local_result=a.status;r.local_reason=a.reason;window=nil;row=nil
    -- Invoke the underlying official advance, not its native-reply filter.
    if a.status=='cancelled' then
     w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else advance(w,{type=TYPE,pos=POS,args={}}) end
   end
   complete=done
   timer=clock:add(function() safe(function() runner:tick() end) end,0.5)
   safe(function() local success,why=runner:start(done,changed)
    if not success then done({status='error',reason=why,entries={},refresh={}}) end
   end)
  end end)
  patch(OneKeyBurdenAutoWindow,'numberOfCells',function(old) return function(w)
   return #display(w)
  end end)
  patch(OneKeyBurdenAutoWindow,'updateCellByIndex',function(old) return function(w,cell,i)
   local v=display(w)[i];if not v then return end
   cell:setData(v.data,v.index)
   if w.new_execute and v.index==w.execute_index and not v.data.voyage_entry then cell:playEnterAnim();w.new_execute=false end
  end end)
  patch(OneKeyBurdenAutoWindow,'updateLoopList',function(old) return function(w)
   if w.task_scrollview then w.task_scrollview:reloadData(#display(w)) else return old(w) end
  end end)
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.voyage_label then cell.voyage_label:setVisible(false) end
   cell.title_lb:setFontSize(30);old(cell,d,index)
   if d.type~=TYPE or d.pos~=POS then return end
   cell.title_lb:setFontSize(24);cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.voyage_label then
    cell.voyage_label=createRichLabel(21,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-52),4,nil,570):addTo(cell.root_wnd)
   end
   cell.voyage_label:setVisible(true)
   if d.voyage_entry then
    local e=d.voyage_entry
    cell.title_lb:setString(string.format('敏堂 #%d · %s · %s',e.sequence,quality[e.quality] or tostring(e.quality),clean(e.name)))
    cell.voyage_label:setString('已派遣｜预计：'..rewardText(e.award)..'\n情报消耗 '..clean(e.cost)..'｜结束 '..os.date('%m-%d %H:%M',e.end_time))
   else
    local a=d.voyage or {};local r=a.refresh or {}
    cell.title_lb:setString('其他自动化 · 敏堂自动派遣与刷新')
    local status=reasons[a.reason] or (a.status=='running' and '执行中' or a.status=='uncertain' and '结果待核实' or a.status=='error' and '执行失败' or '等待执行')
    cell.voyage_label:setString(string.format('%s｜派遣 %d 个｜剩余情报 %s\n刷新：免费 %d / 券 %d / 钻石 %d\n消耗：刷新券 %d，钻石 %d',status,#(a.entries or {}),clean(a.remaining or '-'),r.free or 0,r.ticket or 0,r.diamond or 0,r.tickets or 0,r.diamonds or 0))
   end
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then
    if runner.active then runner.active.done=nil;runner.active.changed=nil;safe(function() runner:cancel() end) end
    stopTimer();complete=nil;window=nil;row=nil
   end
   return old(w,...)
  end end)
  SimplifyData.data_list[TYPE]=category;OneKeyBurdenConst.SimplifyTypeList[TYPE]=rows
 end)
 if not ok then restore();error(err) end
 local oldDetach,oldUninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();oldDetach() end
 installed.uninstall=function()
  assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first')
  restore();oldUninstall()
 end
 local binding={runner=runner,type=TYPE,pos=POS,setting=setting,history=history,category=category,
  load=load,showHistory=showHistory,display=display,rewardText=rewardText,advance=advance}
 function binding:export()
  local a=runner.active or runner.last
  if not a or a.identity~=identity() then a=load() end
  local lines={}
  for _,e in ipairs(a and a.entries or {}) do
   lines[#lines+1]=table.concat({e.sequence,quality[e.quality] or e.quality,clean(e.name),rewardText(e.award),e.cost,e.end_time,'已派遣'},'\t')
  end
  return table.concat(lines,'\n')..'\n'
 end
 installed.voyage=binding
 return binding
end
return M
