-- Uses native formation, challenge and delayed skip actions; no screen coordinates.
local M={POS=-2101771,STAR=9024}
local fields={'type','formation_type','pos_info','hallows_id','hidden_id','domain_id','fusion_skill','god_palace_skill','war_souls_skill','common_list'}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function equal(a,b)
 if type(a)~=type(b) then return false end
 if type(a)~='table' then return a==b end
 -- Server sorts slot/skill arrays on save; compare their values as multisets.
 if #a>0 or #b>0 then
  if #a~=#b then return false end
  local matched={}
  for _,v in ipairs(a) do
   local found
   for i,w in ipairs(b) do if not matched[i] and equal(v,w) then found=i;break end end
   if not found then return false end;matched[found]=true
  end
  return true
 end
 for k,v in pairs(a) do if not equal(v,b[k]) then return false end end
 for k in pairs(b) do if a[k]==nil then return false end end
 return true
end
local function formCopy(d)
 local out={};for _,k in ipairs(fields) do out[k]=deepCopy(d[k]) end
 table.sort(out.pos_info,function(a,b) return a.pos<b.pos end);return out
end
function M.sameForm(a,b) return equal(formCopy(a),formCopy(b)) end
function M.fill(d,info,list,id,heroes,positions,banRank)
 if type(d)~='table' or type(d.pos_info)~='table' or type(positions)~='table' or #positions~=6 or not uint(banRank) then return nil,'invalid_formation' end
 for _,k in ipairs(fields) do if d[k]==nil then return nil,'invalid_formation' end end
 local allowed,used,bans={},{},{}
 for _,p in ipairs(positions) do if not uint(p[1]) or allowed[p[1]] then return nil,'invalid_formation' end;allowed[p[1]]=true end
 for _,v in ipairs(info.partner_bids) do bans[v.bid]=true end
 for _,v in ipairs(list.use_partner_list) do for _,h in ipairs(v.partner_list) do if v.defender_id~=id then used[h.partner_id]=true end end end
 local function eligible(h)
  if not h or not uint(h.partner_id) or h.partner_id==0 or not uint(h.bid) or not uint(h.power) or used[h.partner_id] then return false end
  if info.level>=banRank then
   if bans[h.bid] then return false end
   if h.isDoubleCampHero and h:isDoubleCampHero() and (bans[h.main_camp_id] or bans[h.sub_camp_id]) then return false end
  end
  return true
 end
 local function compatible(h,chosen)
  for _,v in ipairs(chosen) do
   if h.partner_id==v.partner_id or h.bid==v.bid
    or (h.getCanChangeBid and h:getCanChangeBid()==v.bid) or (v.getCanChangeBid and v:getCanChangeBid()==h.bid)
    or (h.getLinkPartnerId and h:getLinkPartnerId()==v.partner_id) or (v.getLinkPartnerId and v:getLinkPartnerId()==h.partner_id) then return false end
  end;return true
 end
 local out=formCopy(d);out.pos_info={};local chosen,occupied={},{}
 local current=deepCopy(d.pos_info);table.sort(current,function(a,b) return a.pos<b.pos end)
 for _,p in ipairs(current) do
  if not uint(p.pos) or not allowed[p.pos] or occupied[p.pos] or not uint(p.id) then return nil,'invalid_formation' end
  occupied[p.pos]=true;local h=heroes[p.id]
  if eligible(h) and compatible(h,chosen) then out.pos_info[#out.pos_info+1]={pos=p.pos,id=h.partner_id};chosen[#chosen+1]=h else occupied[p.pos]=nil end
 end
 local candidates={};for _,h in pairs(heroes) do if eligible(h) then candidates[#candidates+1]=h end end
 table.sort(candidates,function(a,b) if a.power~=b.power then return a.power>b.power end;return a.partner_id<b.partner_id end)
 for _,p in ipairs(positions) do if not occupied[p[1]] then
  local found
  for _,h in ipairs(candidates) do if compatible(h,chosen) then found=h;break end end
  if not found then return nil,'formation_insufficient' end
  chosen[#chosen+1]=found;out.pos_info[#out.pos_info+1]={pos=p[1],id=found.partner_id};occupied[p[1]]=true
 end end
 table.sort(out.pos_info,function(a,b) return a.pos<b.pos end);return out
end
local reasons={forest_complete='三名对手已处理',non_battle_period='非战斗期，已跳过',not_open='巨木之森尚未开放',
 formation_insufficient='可用魂师不足六名',invalid_formation='阵容数据未确认',formation_rejected='阵容保存被拒绝',formation_mismatch='阵容保存核对不符',
 battle_busy='存在未归属的战斗，已停止',battle_view_changed='战斗页面已切换，已停止',formation_changed='可用阵容已变化',challenge_rejected='游戏未接受挑战',invalid_state='玩法数据未确认',request_unresolved='上次战斗结果待核实',
 result_mismatch='胜负与对手进度不符',invalid_result='战斗结果未确认',opponents_changed='对手已变化，停止本项',season_changed='赛季已变化',
 connection_unavailable='连接不可用',manual_operation_pending='手动操作正在处理',manual_window_open='请先关闭手动布阵或巨木之森界面',
 role_or_day_changed='角色或游戏日已变化',cancelled='已停止',runtime_error='执行异常',invalid_star='星级设置无效',no_role='角色尚未就绪'}
function M.bind(Forest,installed)
 local TYPE=OneKeyBurdenConst.SimplifyType.DAILY_TASK;local helper=OneKeyBurdenController:getInstance()
 local gc=GiantWoodForestController:getInstance();local hc=HeroController:getInstance();local bc=BattleController:getInstance()
 local clock=GlobalTimeTicket:getInstance();local ud=cc.UserDefault:getInstance();local pm=ProtoMgr:getInstance()
 local main=MainuiController:getInstance();local view_context,reply_registration
 local patches={};local runner,timer,window,internal;local manual_until=0
 local row={id=M.POS,title='巨木之森·每日自动挑战',is_title=true,is_single_select=true,
  option_list={{'开启',TRUE},{'关闭',FALSE}},default_option=FALSE,close_subitem_list={{},{1}},
  subitem_list={{{title='起始难度（失败后逐级降星）',is_title=false,is_single_select=true,proto_key_args=M.STAR,
   option_list={{'五星',TRUE,5},{'四星',TRUE,4},{'三星',TRUE,3},{'二星',TRUE,2},{'一星',TRUE,1}}}}}}
 local function now() return GameNet:getInstance():getTime() end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function roleKey() local r=role();return r and r.rid and r.srv_id and tostring(r.srv_id)..':'..r.rid end
 local function identity() local k=roleKey();return k and k..':'..tostring(role()) end
 local function pref() return 'dldl_forest_v1:'..assert(roleKey()) end
 local function day() return math.floor((now()+3*3600)/86400) end
 local function own(fn) internal=true;local ok,e=pcall(fn);internal=false;if not ok then error(e) end end
 local function leaveView()
  if not view_context then return end
  local c=view_context;view_context=nil
  if main:getUIFightType()==BattleConst.getUIFightByFightType(82) then
   main:setUIFightType(c.ui);bc:send20060(c.fight or 0)
  end
 end
 local function guard()
  if not GameNet:getInstance():IsServerConnect() then return 'connection_unavailable' end
  if not SysController:getInstance():checkIsOpenByKey('god_wood_open',false) then return 'not_open' end
  if now()<manual_until then return 'manual_operation_pending' end
  if view_context and main:getUIFightType()~=BattleConst.getUIFightByFightType(82) then return 'battle_view_changed' end
  if hc.form_go_fight_panel or gc.giantwoodforest_main_window then return 'manual_window_open' end
 end
 local function patch(obj,k,wrap)
  local old=obj[k];assert(type(old)=='function',k);local p={obj=obj,k=k,own=rawget(obj,k)};p.new=wrap(old);obj[k]=p.new;patches[#patches+1]=p
 end
 local function stopTimer() if timer then clock:remove(timer);timer=nil end end
 local function safe(fn)
  local ok,e=pcall(fn);if not ok then
   print('[dldl_forest] '..tostring(e))
   if runner and runner.active then runner:finish('uncertain','runtime_error') end
  end
 end
 local function battleReady()
  return not bc:getWatchReplayStatus() and not bc:isInFight() and not bc:getFightTypeInfo(82)
   and not (bc.finish_result_view_list and bc.finish_result_view_list[82]) and not (bc.finish_fail_view_list and bc.finish_fail_view_list[82])
 end
 local function restore()
  stopTimer();window=nil
  if reply_registration then
   pm:UnRegisterCmdCallback(31906,'dldl_forest_reply')
   if pm.cmd_callback_table[31906] and not next(pm.cmd_callback_table[31906]) then pm.cmd_callback_table[31906]=nil end
   reply_registration=nil
  end
  leaveView()
  if runner and runner.active then runner.active.done=nil;runner.active.changed=nil;runner:cancel() end
  for i=#patches,1,-1 do local p=patches[i];if rawget(p.obj,p.k)==p.new then rawset(p.obj,p.k,p.own) end end
  local list=OneKeyBurdenConst.SimplifyTypeList[TYPE];for i=#list,1,-1 do if list[i]==row then table.remove(list,i) end end
 end
 local ok,e=pcall(function()
  -- GameNet drops unregistered replies before the dispatcher. The stock
  -- controller has no 31906 handler, so register a scoped no-op observer.
  if not pm:hasReg(31906) then
   pm:RegisterCmdCallback(31906,'dldl_forest_reply',function() end);reply_registration=true
  end
  runner=Forest.new({identity=identity,day=day,now=now,guard=guard,
   load=function() local s=ud:getStringForKey(pref()..':last','');if s~='' then return json.decode(s) end end,
   save=function(r) assert(r.day==day(),'game day changed');ud:setStringForKey(pref()..':last',json.encode(r));ud:flush() end,
   formType=function(id) return assert(PartnerConst.Fun_Form['GiantWoodForest_'..id]) end,
   query=function(kind,id)
    if kind=='base' then gc:send31900()
    elseif kind=='info' then gc:send31901();gc:send31903()
    elseif kind=='list' then gc:send31903()
    elseif kind=='form' then hc:sender11211(PartnerConst.Fun_Form['GiantWoodForest_'..id]) end
   end,
   fill=function(d,info,list,id)
    if d.type~=PartnerConst.Fun_Form['GiantWoodForest_'..id] then return nil,'invalid_formation' end
    local cfg=FormationData.data_form_data[d.formation_type];local ban=WoodData.data_const.ban_rank
    return M.fill(d,info,list,id,hc:getModel():getHeroList(),cfg and cfg.pos,ban and ban.val)
   end,sameForm=M.sameForm,
   saveForm=function(d) own(function() hc:sender11212(d.type,d.formation_type,d.pos_info,d.hallows_id,d.hidden_id,d.domain_id,d.fusion_skill,d.god_palace_skill,d.war_souls_skill,d.common_list) end) end,
   challenge=function(id,star) own(function() gc:send31906(id,star) end) end,
   battleReady=battleReady,
   enter=function()
    if not view_context then view_context={ui=main:getUIFightType(),fight=bc:getCurFightType()} end
    main:setUIFightType(BattleConst.getUIFightByFightType(82))
    bc:send20060(82)
   end,
   skip=function(a)
    if a.skip_sent or bc:getWatchReplayStatus() or not bc:isInFight() or not bc:getIsSameBattleType(82) then return end
    local p=bc:getBattleUIPanel();local cfg=CombatTypeData.data_fight_list[82]
    if not cfg or cfg.is_skip~='true' or not p or not p.root_wnd or p.battle_type~=82 or not p.skip_btn or not p.skip_btn:isVisible() or not p.onClickSkipBtn then return end
    a.skip_sent=true;own(function() p:onClickSkipBtn() end)
   end,
   cleanup=function()
    if bc:getWatchReplayStatus() then return false end
    local won=bc.finish_result_view_list and bc.finish_result_view_list[82];local lost=bc.finish_fail_view_list and bc.finish_fail_view_list[82]
    if won or lost then
     local v=won or lost
     if v.fight_type~=82 or not v.isOpen or not v:isOpen() or not v.root_wnd then return false end
     if won and v.onCloseBtn then own(function() v:onCloseBtn() end)
     elseif lost and v.close then own(function() v:close() end) end
     return false
    end
    if gc.giantwoodforest_levup_window then gc:openGiantWoodForestLevupWindow(false);return false end
    return battleReady()
   end})
  patch(gc,'SendProtocal',function(old) return function(obj,id,...)
   if (id==31906 or id==31908 or id==31909 or id==31913) and not internal then
    if runner.active then message('巨木之森自动化正在执行，请先中断');return end;manual_until=now()+25
   end;return old(obj,id,...)
  end end)
  patch(hc,'sender11212',function(old) return function(obj,t,...)
   if PartnerConst.isGiantWoodForestFun(t) and not internal then
    if runner.active then message('巨木之森自动化正在执行，请先中断');return end;manual_until=now()+25
   end;return old(obj,t,...)
  end end)
  patch(pm,'cmd_callback',function(old) return function(obj,id,d)
   old(obj,id,d)
   if runner.active and (id==31900 or id==31901 or id==31903 or id==31906 or id==11211 or id==11212 or id==20060) then safe(function() runner:onPacket(id,d) end) end
  end end)
  for _,k in ipairs({'scInitFightStart','scReBattleFight'}) do patch(bc,k,function(old) return function(obj,d)
   local t=d.combat_type;old(obj,d);if t==82 then safe(function() runner:onBattleStart(d) end) end
  end end) end
  patch(bc,'scFightEnd',function(old) return function(obj,d)
   -- Inspect before the game removes the replay offset from combat_type.
   if d.combat_type==82 then safe(function() runner:onBattleEnd(d) end) end
   return old(obj,d)
  end end)
  patch(OneKeyBurdenMainWindow,'getPosExecuteData',function(old) return function(w,t,c)
   local d=old(w,t,c);if c.id==M.POS then
    d.is_open=roleKey() and ud:getBoolForKey(pref()..':enabled',false) and TRUE or FALSE
    local star=roleKey() and ud:getIntegerForKey(pref()..':star',5) or 5
    if not uint(star) or star<1 or star>5 then star=5 end
    d.args={{args_key=M.STAR,args_val=star}}
   end;return d
  end end)
  patch(helper,'sender31601',function(old) return function(obj,groups)
   local filtered={}
   for _,g in ipairs(groups) do local copy={type=g.type,type_list={}}
    for _,r in ipairs(g.type_list) do if r.pos==M.POS then
     if roleKey() then
      ud:setBoolForKey(pref()..':enabled',r.is_open==TRUE)
      for _,a in ipairs(r.args or {}) do if a.args_key==M.STAR and uint(a.args_val) and a.args_val>=1 and a.args_val<=5 then ud:setIntegerForKey(pref()..':star',a.args_val) end end
     end
    else copy.type_list[#copy.type_list+1]=r end end
    if #copy.type_list>0 then filtered[#filtered+1]=copy end
   end;ud:flush();if #filtered>0 then return old(obj,filtered) end
  end end)
  patch(helper,'sender31602',function(old) return function(obj,t,p) assert(p~=M.POS,'forest is local');return old(obj,t,p) end end)
  patch(OneKeyBurdenMainWindow,'saveOperateRequest',function(old) return function(w,all)
   local q=old(w,all)
   for _,r in ipairs(q) do if r.pos==M.POS then r.args=deepCopy(assert(w.operate_list[r.type][r.pos]).args) end end
   return q
  end end)
  patch(OneKeyBurdenAutoWindow,'updateDataList',function(old) return function(w,d)
   local r=w.execute_request_list[w.execute_index];if r and r.pos==M.POS then return end;return old(w,d)
  end end)
  patch(OneKeyBurdenAutoWindow,'requestTask',function(old) return function(w)
   local r=w.execute_request_list[w.execute_index];if not r or r.pos~=M.POS then return old(w) end
   if runner.active then return end;window=w
   local function done(a)
    stopTimer();window=nil;leaveView();r.forest=a;r.local_result=a.status;r.local_reason=a.reason
    if a.status=='cancelled' then w.is_execute_finish=true;helper:sender31604(w.operate_type,0);w.stop_btn_lb:setString('关闭');w:updateLoopList()
    else installed.voyage.advance(w,{type=TYPE,pos=M.POS,args={}}) end
   end
   timer=clock:add(function() safe(function() runner:tick() end) end,0.5)
   safe(function()
    local star,n=5,0;for _,v in ipairs(r.args or {}) do if v.args_key==M.STAR then star=v.args_val;n=n+1 end end
    if n~=1 then done({status='error',reason='invalid_star'});return end
    local success,why=runner:start(star,done,function(a) r.forest=a;w.other_progress=(w.other_progress or 0)+1;w:updateLoopList() end)
    if not success then done({status='error',reason=why}) end
   end)
  end end)
  patch(OneKeyBurdenAutoWindow,'close_callback',function(old) return function(w,...)
   if window==w then if runner.active then runner.active.done=nil;runner.active.changed=nil;runner:cancel() end;stopTimer();window=nil;leaveView() end
   return old(w,...)
  end end)
  patch(OneKeyBurdenAutoItem,'setData',function(old) return function(cell,d,index)
   if cell.forest_label then cell.forest_label:setVisible(false) end
   old(cell,d,index);if d.pos~=M.POS then return end
   cell.title_lb:setFontSize(24);cell.title_lb:setString(row.title);cell.un_finish_node:setVisible(false);cell.item_scrollview:setVisible(false)
   if not cell.forest_label then cell.forest_label=createRichLabel(19,cc.c4b(101,77,70,255),cc.p(0,1),cc.p(20,cell.Height-48),2,nil,570):addTo(cell.root_wnd) end
   local a=d.forest or {};local text=reasons[a.reason] or (a.reason and a.reason:find('_timeout') and '等待游戏响应超时') or '执行中'
   for _,v in ipairs(a.entries or {}) do
    local state=v.status=='won' and ('已通过 '..v.star..' 星') or v.status=='exhausted' and '一星仍失败' or v.status=='downgrade' and '准备降星' or v.status=='fighting' and ('挑战 '..v.star..' 星') or '待挑战'
    local trace={};for _,t in ipairs(a.attempts or {}) do if t.id==v.id then trace[#trace+1]=t.star..(t.result==1 and '胜' or '败') end end
    text=text..'\n对手'..v.id..'：'..state..(#trace>0 and ('（'..table.concat(trace,'→')..'）') or '')
   end
   cell.forest_label:setVisible(true);cell.forest_label:setString(text)
  end end)
  local list=OneKeyBurdenConst.SimplifyTypeList[TYPE];for _,v in ipairs(list) do assert(v.id~=M.POS,'forest row collision') end
  table.insert(list,math.min(22,#list+1),row)
 end)
 if not ok then restore();error(e) end
 local detach,uninstall=installed.detach,installed.uninstall
 installed.detach=function() restore();detach() end
 installed.uninstall=function() assert(not helper.onekeyburden_main_window and not helper.onekeyburden_auto_window,'close helper windows first');restore();uninstall() end
 installed.forest={runner=runner,row=row,pos=M.POS,type=TYPE}
 return runner
end
return M
