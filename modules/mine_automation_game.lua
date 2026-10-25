-- Extend the local Other Automation category; use saved three-team MineAtk.
local M={POS=-2101781}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.bind(Mine,installed)
 local voyage=assert(installed.voyage);local TYPE,POS=voyage.type,M.POS
 local helper=OneKeyBurdenController:getInstance();local mc=MineController:getInstance()
 local hc=HeroController:getInstance();local bc=BattleController:getInstance()
 local ud=cc.UserDefault:getInstance();local clock=GlobalTimeTicket:getInstance()
 local patches,timer,window,complete,runner,internal,manual_until={},nil,nil,nil,nil,false,0
 local details={}
 local row={id=POS,title='极地矿场·每日挑战（50层1区）',is_title=true,is_single_select=true,
  option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE}
 local function now() return GameNet:getInstance():getTime() end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function roleKey() local r=role();return r and r.rid and r.srv_id and tostring(r.srv_id)..':'..tostring(r.rid) end
 local function identity() local k=roleKey();return k and k..':'..tostring(role()) end
 local function key() return 'dldl_mine_v1:'..assert(roleKey()) end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function load()
  local s=ud:getStringForKey(key()..':last','');if s=='' then return end
  local d=json.decode(s);assert(type(d)=='table' and uint(d.day) and type(d.status)=='string','invalid mine journal');return d
 end
 local function save(a)
  assert(a.identity==identity(),'mine role changed')
  ud:setStringForKey(key()..':last',json.encode({day=a.day,status=a.status,reason=a.reason,pending=a.pending,completed=a.completed,
   floor_id=50,area_id=1,mine_id=a.mine_id}));ud:flush()
 end
 local function safe(fn)
  local ok,e=pcall(fn)
  if not ok then
   print('[dldl_mine] '..tostring(e))
   if runner.active then
    local a=runner.active;local success=pcall(function() runner:fail() end)
    if not success then runner.active=nil;a.status='uncertain';a.reason='runtime_error';if a.done then a.done(a) end end
   elseif complete then complete({status='error',reason='runtime_error'}) end
  end
 end
 local function patch(obj,k,wrap)
  local old=obj[k];assert(type(old)=='function',k)
  local own=rawget(obj,k);local new=wrap(old);obj[k]=new
  patches[#patches+1]={obj=obj,k=k,own=own,new=new}
 end
 local function config()
  local c=ArenaMineData.data_base_info[50]
  assert(c and c.team_num==3 and uint(c.area_mine_num) and c.area_mine_num>0 and c.is_safe_area==0,'mine config changed')
  return c
 end
 local function conflict()
  local x=installed.extras
  return x and (x.env.conflict('guild_trial') or x.env.conflict('temple_duel')) or false
 end
 local function guard(a)
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  if now()<manual_until then return 'manual_operation_pending' end
  if not SysController:getInstance():checkIsOpenByKey('arena_mine_open_limit',false) then return 'not_open' end
  if (bc:getFightTypeInfo(BattleConst.Fight_Type.Mine) and not (a and a.pending)) or bc:getWatchReplayStatus() then return 'battle_busy' end
  config()
 end
 local function target(t,base)
  if t.combat_state~=0 or (t.mine_id==base.mine_id and base.mine_floor_id==50 and base.mine_area_id==1) then return false end
  local r=role();if t.rid==r.rid and t.srv_id==r.srv_id then return false end
  local min=ArenaMineData.data_const.rob_time_min.val
  assert(uint(min),'mine protection config changed')
  return now()-t.start_time>=min*60 and (t.rid==0 or t.end_time>now())
 end
 local function restore()
  stopTimer();complete=nil
  if runner and runner.active then runner.active.done=nil;safe(function() runner:cancel() end) end
  for i=#patches,1,-1 do local p=patches[i];if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end end
  local rows=OneKeyBurdenConst.SimplifyTypeList[TYPE]
  for i=#rows,1,-1 do if rows[i]==row then table.remove(rows,i) end end
 end
 local ok,e=pcall(function()
  runner=Mine.new({identity=identity,day=function() return math.floor((now()+3*3600)/86400) end,now=now,
   load=load,save=save,guard=guard,conflict=conflict,mineCount=function() return config().area_mine_num end,target=target,
   formType=function() return PartnerConst.Fun_Form.MineAtk end,
   checkForm=function(d)
    if type(d.formations)~='table' or #d.formations~=config().team_num then return 'invalid_mine_formation' end
    local orders,heroes={},{}
    for _,f in ipairs(d.formations) do
     local c=FormationData.data_form_data[f.formation_type]
     if not uint(f.order) or f.order<1 or f.order>3 or orders[f.order] or not c
      or type(f.pos_info)~='table' or #f.pos_info==0 then return 'invalid_mine_formation' end
     orders[f.order]=true;local positions,allowed={},{};for _,p in ipairs(c.pos or {}) do allowed[p[1]]=true end
     for _,p in ipairs(f.pos_info) do
      if not allowed[p.pos] or positions[p.pos] or not uint(p.id) or p.id==0 or heroes[p.id] or not hc:getModel():getHeroById(p.id) then return 'invalid_mine_formation' end
      positions[p.pos]=true;heroes[p.id]=true
     end
    end
   end,
   query=function(phase,id)
    internal=true
    local ok,err=pcall(function()
     if phase=='base' then mc:sender30300()
     elseif phase=='form' then hc:send11251(PartnerConst.Fun_Form.MineAtk,{{key=1,str='',val=50}})
     elseif phase=='area' then mc:sender30301(50,1)
     elseif phase=='detail' then details[id]=now()+40;mc:sender30302(50,1,id) end
    end)
    internal=false;if not ok then error(err) end
   end,
   act=function(id)
    internal=true;local ok,err=pcall(function() mc:sender30307(50,1,id) end);internal=false;if not ok then error(err) end
   end})
  for _,method in ipairs({'sender30307','sender30311','sender30316','sender30302'}) do
   patch(mc,method,function(old) return function(obj,...)
    if not internal and runner.active then message('极地矿场自动化正在执行，请稍后操作');return end
    if not internal then manual_until=now()+20 end
    return old(obj,...)
   end end)
  end
  for _,id in ipairs({30300,30301,30302,30307,11251}) do
   local obj=id==11251 and hc or mc
   patch(obj,'handle'..id,function(old) return function(self,d)
    local owned=id==30302 and d.floor_id==50 and d.area_id==1 and details[d.mine_id] and details[d.mine_id]>=now()
    if owned then details[d.mine_id]=nil else old(self,d) end
    if runner.active then safe(function() runner:onPacket(id,d) end) end
   end end)
  end
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,t,c)
   local d=old(w,t,c);if c.id==POS then d.is_open=roleKey() and ud:getBoolForKey(key()..':enabled',false) and TRUE or FALSE end;return d
  end end)
  patch(helper,'sender31601',function(old) return function(self,groups)
   for _,g in ipairs(groups) do if g.type==TYPE then for _,r in ipairs(g.type_list) do
    if r.pos==POS and roleKey() then ud:setBoolForKey(key()..':enabled',r.is_open==TRUE);ud:flush() end
   end end end
   return old(self,groups)
  end end)
  patch(helper,'sender31602',function(old) return function(self,t,p) assert(p~=POS,'local mine task cannot enter native protocol');return old(self,t,p) end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   local r=w.execute_request_list[w.execute_index]
   if not r or r.type~=TYPE or r.pos~=POS then return old(w) end
   if runner.active then return end
   window=w
   local function done(a)
    stopTimer();complete=nil;window=nil;r.mine=a;r.local_result=a.status;r.local_reason=a.reason
    if a.status=='cancelled' then
     w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else voyage.advance(w,{type=TYPE,pos=POS,args={}}) end
   end
   complete=done;timer=clock:add(function() safe(function() runner:tick() end) end,0.5)
   safe(function() local ok,why=runner:start(done);if not ok then done({status='error',reason=why}) end end)
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then
    if runner.active then runner.active.done=nil;safe(function() runner:cancel() end) end
    stopTimer();complete=nil;window=nil
   end
   return old(w,...)
  end end)
  local reasons={challenge_started='已发起挑战',daily_target_done='今日已发起，已跳过',previous_request_unresolved='上次挑战结果待核实',
   no_challengeable_mine='50层1区暂无可挑战矿点',floor_50_locked='50层尚未解锁',mine_cooldown='休整或掠夺冷却中',
   invalid_mine_formation='请先配置完整的三队伍进攻阵容',not_open='矿场尚未开放',battle_busy='矿场战斗或录像占用中',
   connection_unavailable='连接不可用',manual_operation_pending='手动操作正在处理',invalid_mine_state='矿场数据未确认',
   role_or_day_changed='角色或游戏日已变化',runtime_error='执行异常，已停止',cancelled='已停止'}
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.mine_label then cell.mine_label:setVisible(false) end
   old(cell,d,index)
   if d.type~=TYPE or d.pos~=POS then return end
   cell.title_lb:setFontSize(24);cell.title_lb:setString('极地矿场 · 每日挑战一次')
   cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.mine_label then cell.mine_label=createRichLabel(22,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-52),4,nil,570):addTo(cell.root_wnd) end
   local a=d.mine or {};cell.mine_label:setVisible(true)
   cell.mine_label:setString((reasons[a.reason] or (a.reason and '结果未确认：'..a.reason or '执行中'))..'\n目标：50层1区'..(a.mine_id and '，矿点 '..a.mine_id or '')..'｜只发起，不等待结算')
  end end)
  for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[TYPE]) do assert(r.id~=POS,'mine row collision') end
  table.insert(OneKeyBurdenConst.SimplifyTypeList[TYPE],2,row)
 end)
 if not ok then restore();error(e) end
 local detach,uninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();detach() end
 installed.uninstall=function()
  assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first')
  restore();uninstall()
 end
 installed.mine={runner=runner,pos=POS,row=row,load=load}
 return installed.mine
end
return M
