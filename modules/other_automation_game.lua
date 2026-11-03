-- Local fishing/mail rows. Protocol observers run after the game's own handlers.
local M={FISH=-2101773,MAIL=-2101772,TYPES=9023}
local reasons={orders_complete='三个每日订单已完成',mail_complete='邮件奖励已领取',mail_empty='暂无可领取的邮件奖励',
 no_selected_types='请至少选择一种订单类型',insufficient_refresh='免费次数和刷新券不足',insufficient_energy='特制香肠不足',
 action_rejected='游戏未接受操作，已停止',request_unresolved='上次操作结果待核实，已停止',mail_partial='部分邮件结果待核实',
 invalid_state='游戏数据未确认',invalid_reply='操作回执未确认',invalid_config='消耗配置已变化',fishery_locked='订单所需渔场尚未解锁',
 native_auto='原生钓鱼委托正在运行',fishing_window_open='请先关闭手动钓鱼界面',manual_operation_pending='手动操作正在处理',
 connection_unavailable='连接不可用',not_open='钓鱼尚未开放',query_timeout='查询超时',role_or_day_changed='角色或游戏日已变化',
 cancelled='已停止',runtime_error='执行异常，已停止',no_role='角色尚未就绪'}
local function clean(s) return tostring(s or ''):gsub('[<>\r\n\t]',' ') end
function M.bind(Fishing,Mail,installed)
 local TYPE=assert(installed.voyage).type
 local helper=OneKeyBurdenController:getInstance();local fc=FishingController:getInstance();local mc=MailController:getInstance()
 local clock=GlobalTimeTicket:getInstance();local ud=cc.UserDefault:getInstance();local pm=ProtoMgr:getInstance()
 local patches,rows,runners={}, {}, {};local internal=false;local manual={fishing=0,mail=0};local timer,window,complete
 local function now() return GameNet:getInstance():getTime() end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function roleKey() local r=role();return r and r.rid and r.srv_id and tostring(r.srv_id)..':'..r.rid end
 local function identity() local k=roleKey();return k and k..':'..tostring(role()) end
 local function day() return math.floor((now()+3*3600)/86400) end
 local function key(kind) return 'dldl_'..kind..'_v1:'..assert(roleKey()) end
 local function load(kind)
  local s=ud:getStringForKey(key(kind)..':last','');if s=='' then return end
  local d=json.decode(s);assert(type(d)=='table','invalid automation journal');return d
 end
 local function save(kind,a)
  assert(a.identity==identity(),'role changed')
  local d={status=a.status,reason=a.reason,day=a.day,pending=a.pending,orders=a.orders,casts=a.casts,
   deliveries=a.deliveries,chests=a.chests,refreshes=a.refreshes,claimed=a.claimed,count=a.count}
  ud:setStringForKey(key(kind)..':last',json.encode(d));ud:flush()
 end
 local function guard(kind)
  if not roleKey() then return 'no_role' end
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  if now()<manual[kind] then return 'manual_operation_pending' end
  if kind=='fishing' then
   if not SysController:getInstance():checkIsOpenByKey('fish_open',false) then return 'not_open' end
   if fc:getAutoFishingTicket() then return 'native_auto' end
   if fc.FishingMainWindow then return 'fishing_window_open' end
  end
 end
 local function own(fn)
  internal=true;local ok,e=pcall(fn);internal=false;if not ok then error(e) end
 end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function safe(kind,fn)
  local ok,e=pcall(fn);if ok then return end
  print('[dldl_'..kind..'] '..tostring(e))
  local r=runners[kind];local a=r and r.active
  if a then
   local success=pcall(function() r:fail() end)
   if not success then r.active=nil;a.status='uncertain';a.reason='runtime_error';if a.done then a.done(a) end end
  elseif complete then complete({status='error',reason='runtime_error'}) end
 end
 local function patch(obj,k,wrap)
  local old=obj[k];assert(type(old)=='function',k);local own=rawget(obj,k);local new=wrap(old);obj[k]=new
  patches[#patches+1]={obj=obj,k=k,own=own,new=new}
 end
 local function balance(bid) return BackpackController:getInstance():getModel():getItemNumByBid(bid) end
 local function configCost(name,bid)
  local c=FishData.data_const[name];local v=c and c.val
  if type(v)~='table' or #v~=1 or v[1][1]~=bid or type(v[1][2])~='number' or v[1][2]<=0 then return end
  return v[1][2]
 end
 local function restore()
  stopTimer();complete=nil;window=nil
  for kind,r in pairs(runners) do if r.active then r.active.done=nil;r.active.changed=nil;safe(kind,function() r:cancel() end) end end
  for i=#patches,1,-1 do local p=patches[i];if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end end
  local list=OneKeyBurdenConst.SimplifyTypeList[TYPE]
  for i=#list,1,-1 do if list[i]==rows.fishing or list[i]==rows.mail then table.remove(list,i) end end
 end
 local ok,e=pcall(function()
  runners.fishing=Fishing.new({identity=identity,day=day,now=now,guard=function() return guard('fishing') end,
   load=function() return load('fishing') end,save=function(a) save('fishing',a) end,
   query=function() fc:reqBase() end,order=function(id) return FishData.data_order[id] end,
   fish=function(id) return FishData.data_fish_info[id] end,
   orderName=function(c)
    local f=c.type==1 and FishData.data_fish_info[c.condition]
    local t=FishData.data_const['type_tips_'..tostring(c.condition)]
    return (c.name or '')..'：'..(f and f.name or t and t.desc or '')
   end,
   canRefresh=function(b)
    local n=configCost('flush_quest_loss',11010);if not n then return false,'invalid_config' end
    if b.free_quest_times>0 or balance(11010)>=n then return true end;return false,'insufficient_refresh'
   end,
   canCast=function()
    local n=configCost('loss_energy',127);if not n then return false,'invalid_config' end
    if balance(127)<n then return false,'insufficient_energy' end;return true
   end,
   bait=function(b)
    local default=FishData.data_const.default_bait.val;local c=FishData.data_bait[b.bait_id]
    assert(c and FishData.data_bait[default],'invalid bait config')
    -- Keep the chosen bait while available, then use the game's unlimited bait.
    if b.bait_id~=default and balance(c.item_bid)<1 then return default end
   end,
   fishery=function(order,b)
    local target=order.fishery
    for _,f in ipairs(b.fishery_id_list or {}) do if f.fishery_id==target and f.is_unlock==2 then return target end end
   end,
   act=function(kind,p) own(function()
    if kind=='cast' then fc:reqFishing()
    elseif kind=='deliver' then fc:reqSellFish(p.id,2)
    elseif kind=='refresh' then fc:reqResetOrder(p.id)
    elseif kind=='claim' then fc:reqOrderReward(p.id)
    elseif kind=='bait' then fc:send12022(p.id)
    elseif kind=='fishery' then fc:reqGoFishery(p.id) end
   end) end})
  runners.mail=Mail.new({identity=identity,now=now,guard=function() return guard('mail') end,
   load=function() return load('mail') end,save=function(a) save('mail',a) end,
   query=function() mc:SendProtocal(10800,{}) end,claim=function() own(function() mc:getAllGoods() end) end})
  local fishWrites={[12002]=true,[12004]=true,[12012]=true,[12013]=true,[12015]=true,[12020]=true,[12021]=true,[12022]=true,[12026]=true}
  local mailWrites={[10801]=true,[10802]=true,[10804]=true}
  for kind,c in pairs({fishing=fc,mail=mc}) do
   local name=kind;local writes=kind=='fishing' and fishWrites or mailWrites
   patch(c,'SendProtocal',function(old) return function(obj,id,...)
    if writes[id] and not internal then
     if runners[name].active then message('自动化正在执行，请先中断');return end
     manual[name]=now()+25
    end
    return old(obj,id,...)
   end end)
  end
  -- Observing the dispatcher also covers protocols with one-shot callbacks.
  patch(pm,'cmd_callback',function(old) return function(obj,id,d)
   old(obj,id,d)
   local kind=(id>=12000 and id<=12027) and 'fishing' or (id==10800 or id==10802) and 'mail'
   if kind and runners[kind].active then safe(kind,function() runners[kind]:onPacket(id,d) end) end
  end end)
  for _,spec in ipairs({{'mail',M.MAIL,'邮件·一键领取奖励'},{'fishing',M.FISH,'自动钓鱼·每日订单'}}) do
   local kind,pos,title=unpack(spec)
   rows[kind]={id=pos,title=title,is_title=true,is_single_select=true,
    option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE}
  end
  rows.fishing.close_subitem_list={{},{1}}
  rows.fishing.subitem_list={{{title='保留的订单类型（多选）',is_title=false,is_single_select=false,proto_key_args=M.TYPES,
   option_list={{'大型鱼',TRUE,4},{'中型鱼',TRUE,3},{'小型鱼',TRUE,2},{'水中生物',TRUE,1}}}}}
  local function kindOf(pos) return pos==M.FISH and 'fishing' or pos==M.MAIL and 'mail' end
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,t,c)
   local d=old(w,t,c);local kind=kindOf(c.id)
   if kind then
    d.is_open=roleKey() and ud:getBoolForKey(key(kind)..':enabled',false) and TRUE or FALSE
    if kind=='fishing' then
     local s=roleKey() and ud:getStringForKey(key(kind)..':types','3|1') or '3|1'
     d.args={{args_key=M.TYPES,args_val=0,args_str=s}}
    end
   end;return d
  end end)
  patch(helper,'sender31601',function(old) return function(obj,groups)
   for _,g in ipairs(groups) do if g.type==TYPE then for _,r in ipairs(g.type_list) do
    local kind=kindOf(r.pos)
    if kind and roleKey() then
     ud:setBoolForKey(key(kind)..':enabled',r.is_open==TRUE)
     if kind=='fishing' then for _,v in ipairs(r.args or {}) do if v.args_key==M.TYPES then ud:setStringForKey(key(kind)..':types',v.args_str or '') end end end
    end
   end end end
   ud:flush();return old(obj,groups)
  end end)
  patch(helper,'sender31602',function(old) return function(obj,t,p)
   assert(not kindOf(p),'local automation cannot enter native task protocol');return old(obj,t,p)
  end end)
  patch(OneKeyBurdenMainWindow,'saveOperateRequest',function(old) return function(w,all)
   local q=old(w,all);local fi,mi
   for i,r in ipairs(q) do
    if kindOf(r.pos) then
     local src=assert(w.operate_list[r.type][r.pos]);r.args={}
     for _,v in ipairs(src.args or {}) do r.args[#r.args+1]={args_key=v.args_key,args_val=v.args_val,args_str=v.args_str} end
     if r.pos==M.FISH then fi=i else mi=i end
    end
   end
   if fi and mi and mi>fi then q[fi],q[mi]=q[mi],q[fi] end
   return q
  end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   local r=w.execute_request_list[w.execute_index];local kind=r and r.type==TYPE and kindOf(r.pos)
   if not kind then return old(w) end
   if runners[kind].active then return end
   window=w
   local function changed(a)
    r.other=a;w.other_progress=(w.other_progress or 0)+1;w:updateLoopList()
   end
   local function done(a)
    stopTimer();complete=nil;window=nil;r.other=a;r.local_result=a.status;r.local_reason=a.reason
    if a.status=='cancelled' then
     w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else installed.voyage.advance(w,{type=TYPE,pos=r.pos,args={}}) end
   end
   complete=done
   timer=clock:add(function() safe(kind,function() runners[kind]:tick() end) end,0.5)
   safe(kind,function()
    local types
    for _,v in ipairs(r.args or {}) do if v.args_key==M.TYPES then types=v.args_str end end
    local success,why=runners[kind]:start(Fishing.types(types),done,changed)
    if not success then done({status='error',reason=why}) end
   end)
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then
    for kind,r in pairs(runners) do if r.active then r.active.done=nil;r.active.changed=nil;safe(kind,function() r:cancel() end) end end
    stopTimer();complete=nil;window=nil
   end;return old(w,...)
  end end)
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.other_label then cell.other_label:setVisible(false) end
   old(cell,d,index);local kind=d.type==TYPE and kindOf(d.pos);if not kind then return end
   cell.title_lb:setFontSize(24);cell.title_lb:setString(rows[kind].title)
   cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.other_label then cell.other_label=createRichLabel(19,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-48),2,nil,570):addTo(cell.root_wnd) end
   local a=d.other or {};local text=reasons[a.reason] or '执行中'
   if kind=='mail' then text=text..'｜已核实 '..(a.count or 0)..' 封'
   else
    text=text..'｜钓鱼 '..(a.casts or 0)..' 次｜刷新 '..(a.refreshes or 0)..' 次\n交付 '..(a.deliveries or 0)..' 个（宝箱 '..(a.chests or 0)..'）'
    for _,o in ipairs(a.orders or {}) do text=text..'\n'..clean(o.name)..' '..o.value..'/'..o.target_val..(o.finish==2 and ' 已领奖' or o.finish==1 and ' 待领奖' or '') end
   end
   cell.other_label:setVisible(true);cell.other_label:setString(text)
  end end)
  local list=OneKeyBurdenConst.SimplifyTypeList[TYPE]
  for _,r in ipairs(list) do assert(not kindOf(r.id),'automation row collision') end
  table.insert(list,#list,rows.mail);table.insert(list,#list,rows.fishing)
 end)
 if not ok then restore();error(e) end
 local detach,uninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();detach() end
 installed.uninstall=function()
  assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first');restore();uninstall()
 end
 installed.fishing={runner=runners.fishing,pos=M.FISH,row=rows.fishing,load=function() return load('fishing') end}
 installed.mail={runner=runners.mail,pos=M.MAIL,row=rows.mail,load=function() return load('mail') end}
 return runners
end
return M
