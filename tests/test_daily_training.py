#!/usr/bin/env python3
"""Offline training integration using original senders, dispatch and configurations."""
import os,runpy,json
from pathlib import Path
os.environ.setdefault('DLDL_TEST_PHASE','phase8')
ROOT=Path(__file__).resolve().parents[1]
ns=runpy.run_path(str(ROOT/'tests/test_daily_actions.py'))
lua=ns['lua'];original=ns['original']
lua.execute("BackPackConst.item_type=setmetatable({}, {__index=function(t,k) return k end});ColorData={data_color4=setmetatable({}, {__index=function() return {} end})}")
lua.execute("cc.c4b=function(...) return {...} end;cc.c3b=cc.c4b")
for path in ['game/partner/partner_const.luac','config/arena_soul_data.luac','config/partner_data.luac','config/partner_holy_eqm_data.luac',
             'config/formation_data.luac','game/elitematch/elitematch_event.luac',
             'game/elitematch/elitematch_controller.luac','game/hero/hero_controller.luac','game/hero/hero_const.luac',
             'game/hero/hero_event.luac','game/hero/hero_model.luac','game/backpack/backpack_controller.luac']:
    original(path)
for var,name in [('Training','daily_training.lua'),('GameTraining','daily_training_game.lua')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/name).read_text())
lua.execute('''
-- Real sender/handler methods are retained; rendering and inventory delivery are mocked.
heroList={};bones={};stocks={[1]=100000,[22]=1000,[10011]=10,[10019]=47}
local model=setmetatable({hero_list=heroList,hero_holy_list={}}, {__index=HeroModel})
function model:getHeroMaxCount() return capacity,hero_count end
function model:getHeroMaxLevel() return 100 end
function model:updateHeroVo(v) for k,x in pairs(v) do self.hero_list[v.partner_id][k]=x end end
function model:updateHeroList(list) for _,v in ipairs(list) do self:updateHeroVo(v) end end
function model:isOpenHolyEquipMentByHerovo(v) return v.open_bones==true end
function model:updateHeroVoHolyEquipment(list)
 for _,v in ipairs(list) do
  self.hero_list[v.partner_id].holy_eqm_list=v.holy_eqm
  for _,g in ipairs(v.holy_eqm) do self.hero_holy_list[g.id]=g end
 end
end
hc=setmetatable({model=model,SendProtocal=capture},{__index=HeroController})
function HeroController:getInstance() return hc end
HeroVo={getNowLevByVo=function(v) return v.lev end}
HeroCalculate={getHeroShowLevelStatus=function(v) return v.status or HeroConst.HeroLevStatus.Levup end}
ResonateController={getInstance=function() return {getModel=function() return {isHeroUpLev=function() return true end} end} end}
local bm={getItemNumByBid=function(self,id) if id==10023 then return contracts end return stocks[id] or 0 end,
 getBagItemList=function() return bones end,getBagItemById=function(self,storage,id) return bones[id] end}
function bm:updateItemList(data) for _,v in ipairs(data.list) do for k,x in pairs(v) do bones[v.id][k]=x end end end
BackpackEvent={BATCH_ITEM_DETAIL_INFO=1}
BackPackConst.Bag_Code={EQUIPS=2}
BackPackConst.checkIsHolyEquipment=function(t) return t==99 end
bp=setmetatable({model=bm,SendProtocal=capture},{__index=BackpackController})
function BackpackController:getInstance() return bp end
ProtoMgr:RegisterCmdCallback(10506,'handle10506',bp)
em={scdata=nil,enemy_data=nil}
function em:setSCData(d) self.scdata=d end
function em:getSCData() return self.scdata end
function em:setEnemyData(d) self.enemy_data=d end
function em:getEnemyData() return self.enemy_data end
function em:getRedStatus() end
function em:checkElitematchIsOpen() return opens end
function em:setIsSkip(v) self.scdata.is_skip=v end
ec=setmetatable({model=em,dispather=bus,SendProtocal=capture,openElitematchFightReadyWindow=function() end},{__index=ElitematchController})
function ElitematchController:getInstance() return ec end
fight=false
bc={finish_result_view_list={},finish_fail_view_list={},isInFight=function() return fight end,
 getFightTypeInfo=function() return fight end,
 openFinishView=function(self,open,kind,data)
  assert(kind==23 or kind==55 or kind==77)
  if open then
   local view={isOpen=function() return true end,root_wnd={},item_scroll={},fight_type=23}
   if data.result==1 then
    function view:onCloseBtn() fight=false;bc.finish_result_view_list[23]=nil end
    self.finish_result_view_list[23]=view
   else
    function view:close() fight=false;bc.finish_fail_view_list[23]=nil end
    self.finish_fail_view_list[23]=view
   end
  end
 end}
BattleController={getInstance=function() return bc end}
BattleConst={Fight_Type={EliteMatchWar=23}}
for _,pair in ipairs({{ec,29400},{ec,29401},{ec,29402},{ec,29403},{ec,29406},{ec,29446},{ec,29450},
 {hc,11211},{hc,11003},{hc,11083},{hc,11002},{hc,11007}}) do
 ProtoMgr:RegisterCmdCallback(pair[2],'handle'..pair[2],pair[1])
end
ProtoMgr:RegisterCmdCallback(11092,'handle11092',hc)
function freshTraining()
 resetRole();fight=false;bc.finish_result_view_list={};bc.finish_fail_view_list={};bones={}
 heroList={[1]={partner_id=1,lev=1,bid=21401,star=5,break_lev=0},[2]={partner_id=2,lev=20,bid=21401,star=5,break_lev=0}}
 model.hero_list=heroList;model.hero_holy_list={}
 stocks={[1]=100000,[22]=1000,[10011]=10,[10019]=47};em.scdata=nil;em.enemy_data=nil
end
function trainingTask(kind,count)
 if kind=='arena' then kind=(count or 0)>0 and 'arena_tickets' or 'arena_free' end
 local positions={arena_free=-2101794,arena_tickets=-2101791,hero=-2101793,bone=-2101792}
 return window({{type=1,pos=positions[kind],args={{args_key=9021,args_val=count or 0}}}})
end
function arenaBase(free,combat,skip,cd)
 return {day_combat_count=free,combat_time=combat,is_skip=skip or 1,match_cd_time=cd or 0,state=1,start_time=0,end_time=9999999999}
end
function startArena(count,free,combat)
 local w=trainingTask('arena',count);w:requestTask()
 assert(sent[#sent].id==11211 and sent[#sent].data.type==45)
 receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29400,arenaBase(free,combat));return w
end
function opponents(size)
 local list={};for i=1,size do list[i]={rid=100+i,srv_id='other'} end
 if ext.training.active and ext.training.active.phase=='cooldown' then
  local sc=em.scdata;now=ext.training.active.wait_until;ext.training:tick();receive(29400,sc)
 end
 if ext.training.active and ext.training.active.phase=='opponents' then
  receive(29401,{code=1,is_match=0,match_list=list,match_cd_time=0})
 end
 if ext.training.active and ext.training.active.phase=='refresh_wait' then
  now=ext.training.active.wait_until;ext.training:tick();receive(29401,{code=1,is_match=0,match_list=list,match_cd_time=0})
 end
 if ext.training.active and ext.training.active.phase=='refresh_reply' then receive(29402,{code=1}) end
 receive(29401,{code=1,is_match=0,match_list=list,match_cd_time=0});return list
end
function arenaFight(size,free,combat,result)
 opponents(size);assert(sent[#sent].id==29446 and sent[#sent].data.choose_id==size)
 receive(29446,{code=1,choose_id=size});assert(sent[#sent].id==29403)
 fight=true;receive(29403,{code=1});assert(em.enemy_data==nil)
 receive(29406,{result=result or 1});assert(sent[#sent].id==29400)
 receive(29400,arenaBase(free-((free>0) and 1 or 0),combat+1))
 ext.training:tick();ext.training:tick()
end
local before=#sent
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining)
case('twelve rows preserve original keys; four new rows default off; installation sends nothing',function()
 assert(#ext.specs==12 and #sent==before)
 for i=9,12 do assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[i].row).is_open==0) end
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[10].row).args[1].args_val==10)
end)
case('ticket task has only 10/20 radio options and independent local preference',function()
 local cfg=ext.specs[10].row;local child=cfg.subitem_list[1][1]
 assert(child.is_single_select and not child.is_input_box and #child.option_list==2)
 assert(child.option_list[1][3]==10 and child.option_list[2][3]==20)
 oc:sender31601({{type=1,type_list={{pos=-2101791,is_open=1,args={{args_key=9021,args_val=20}}},{pos=1,is_open=0,args={}}}}})
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,cfg).args[1].args_val==20)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[9].row).is_open==0)
 assert(sent[#sent].id==31601 and #sent[#sent].data.list[1].type_list==1)
end)
case('all server free quota runs first, refreshed final index varies per fight, losses count',function()
 freshTraining();local w=startArena(0,10,20)
 for i=1,10 do
  arenaFight(i%3+1,11-i,19+i,i%2+1)
  receive(29400,arenaBase(10-i,20+i))
 end
 assert(w.execute_request_list[1].local_result=='confirmed' and stocks[10019]==47)
end)
case('ten tickets after zero free verify exact inventory decrease and persist used target',function()
 freshTraining();local w=startArena(10,0,20)
 for i=1,10 do
  opponents(3);receive(29446,{code=1,choose_id=3});receive(29403,{code=1});receive(29406,{result=1})
  receive(29400,arenaBase(0,20+i));local n=#sent;ext.training:tick();assert(#sent==n)
  stocks[10019]=47-i;ext.training:tick();ext.training:tick();ext.training:tick()
  receive(29400,arenaBase(0,20+i))
 end
 assert(w.execute_request_list[1].local_result=='confirmed' and stocks[10019]==37)
 w=startArena(10,0,30);assert(w.execute_request_list[1].local_reason=='daily_target_done')
 w=startArena(20,0,30)
 for i=1,10 do
  opponents(3);receive(29446,{code=1,choose_id=3});receive(29403,{code=1});receive(29406,{result=1})
  stocks[10019]=37-i;receive(29400,arenaBase(0,30+i));ext.training:tick();ext.training:tick();receive(29400,arenaBase(0,30+i))
 end
 assert(w.execute_request_list[1].local_result=='confirmed' and stocks[10019]==27)
end)
case('ticket shortage never buys and skip refusal never challenges',function()
 freshTraining();stocks[10019]=4;local w=startArena(10,0,20)
 assert(w.execute_request_list[1].local_reason=='insufficient_tickets')
 freshTraining();w=trainingTask('arena',0);w:requestTask();receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29400,arenaBase(1,20,0));opponents(3);assert(sent[#sent].id==29450)
 local n=#sent;receive(29450,{code=0,is_skip=0});assert(w.execute_request_list[1].local_reason=='skip_unavailable')
 for i=n+1,#sent do assert(sent[i].id~=29403 and sent[i].id~=29404) end
end)
case('empty formation blocks without writing saved formations; mismatched choose blocks',function()
 freshTraining();local w=trainingTask('arena',0);w:requestTask();local n=#sent
 receive(11211,{type=45,formation_type=1,pos_info={}});assert(w.execute_request_list[1].local_reason=='empty_attack_formation')
 for i=n+1,#sent do assert(sent[i].id~=11212 and sent[i].id~=29403) end
 freshTraining();w=startArena(0,1,20);opponents(3);receive(29446,{code=1,choose_id=2})
 assert(w.execute_request_list[1].local_reason=='opponent_not_selected')
end)
case('matching and cooldown use fresh lists; native skip confirmation gates challenge',function()
 freshTraining();local w=trainingTask('arena',0);w:requestTask();receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29400,arenaBase(1,20,0,now+3));local n=#sent;ext.training:tick();assert(#sent==n)
 now=now+3;ext.training:tick();assert(sent[#sent].id==29400);receive(29400,arenaBase(1,20,0))
 receive(29401,{code=0,match_list={}});assert(sent[#sent].id==29402)
 opponents(4);assert(sent[#sent].id==29450);receive(29450,{code=1,is_skip=1})
 assert(sent[#sent].id==29446 and sent[#sent].data.choose_id==4)
 ext.training:cancel()
end)
case('arena pending survives lost reply, role change and module reinstall without resending',function()
 freshTraining();local w=startArena(0,1,20);opponents(3);receive(29446,{code=1,choose_id=3})
 local n=#sent;now=now+16;ext.training:tick();assert(w.execute_request_list[1].local_result=='uncertain')
 ext.uninstall();ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining)
 w=trainingTask('arena',0);w:requestTask();assert(w.execute_request_list[1].local_reason=='previous_request_unresolved')
 for i=n+1,#sent do assert(sent[i].id~=29403) end
end)
case('single one-level hero request confirms only exact level six push and daily once',function()
 freshTraining();local w=trainingTask('hero');w:requestTask()
 assert(sent[#sent].id==11003 and sent[#sent].data.partner_id==1)
 receive(11003,{result=1,msg='ok'});assert(not w.execute_request_list[1].local_result)
 receive(11002,{ref_partners={{partner_id=1,lev=6}}});ext.training:tick()
 assert(w.execute_request_list[1].local_result=='confirmed')
 local n=#sent;w=trainingTask('hero');w:requestTask();assert(w.execute_request_list[1].local_reason=='daily_target_done')
 for i=n+1,#sent do assert(sent[i].id~=11003) end
end)
case('hero full-five costs required; trial and resonate heroes excluded; unexpected level blocks',function()
 freshTraining();stocks[22]=106;local w=trainingTask('hero');w:requestTask();assert(w.execute_request_list[1].local_reason=='insufficient_hero_materials')
 freshTraining();heroList[1].end_time=now+100;w=trainingTask('hero');w:requestTask();assert(w.execute_request_list[1].local_reason=='no_eligible_target')
 freshTraining();heroList[1].resonate_lev=1;w=trainingTask('hero');w:requestTask();assert(w.execute_request_list[1].local_reason=='no_eligible_target')
 freshTraining();heroList[1].is_hire=1;heroList[1].hire_time=now+100;w=trainingTask('hero');w:requestTask();assert(w.execute_request_list[1].local_reason=='no_eligible_target')
 freshTraining();w=trainingTask('hero');w:requestTask();receive(11003,{result=1});heroList[1].lev=2;ext.training:tick()
 assert(w.execute_request_list[1].local_reason=='unexpected_hero_level')
end)
local boneBid
for id,c in pairs(PartnerHolyEqmData.data_base_info_table) do
 local b=PartnerHolyEqmData.data_base_info(id);if b.upgrade_id==1001 then boneBid=id;break end
end
function addBone(level,exp)
 bones[50]={id=50,base_id=boneBid,upgrade_lev=level or 0,exp=exp or 0,config={type=99}}
end
function boneDetails()
 local list={};for _,v in pairs(bones) do list[#list+1]={id=v.id,upgrade_lev=v.upgrade_lev,exp=v.exp} end
 receive(10506,{storage=2,list=list});ext.training:tick()
end
case('bone sends exactly one common stone, no items, confirms 100exp and exactly one lost stone',function()
 freshTraining();addBone();local w=trainingTask('bone');w:requestTask();assert(sent[#sent].id==10506);boneDetails();local p=sent[#sent]
 assert(p.id==11083 and p.data.partner_id==0 and p.data.holy_eqm_id==50 and #p.data.common_list==1
  and p.data.common_list[1].common_type==0 and p.data.common_list[1].num==1 and #p.data.item_ids==0)
 receive(11083,{code=1});bones[50].upgrade_lev=1;ext.training:tick();assert(not w.execute_request_list[1].local_result)
 stocks[10011]=9;ext.training:tick();assert(w.execute_request_list[1].local_result=='confirmed')
 local n=#sent;w=trainingTask('bone');w:requestTask();assert(w.execute_request_list[1].local_reason=='daily_target_done')
 for i=n+1,#sent do assert(sent[i].id~=11083) end
end)
case('bone full level, overflow, missing detail, missing stone and coin safely block',function()
 for _,mode in ipairs({'full','overflow','detail','stone','coin'}) do
  freshTraining();addBone()
  if mode=='full' then bones[50].upgrade_lev=5
  elseif mode=='overflow' then bones[50].upgrade_lev=4;bones[50].exp=150
  elseif mode=='detail' then bones[50].exp=nil
  elseif mode=='stone' then stocks[10011]=0
  elseif mode=='coin' then stocks[1]=999 end
  local n=#sent;local w=trainingTask('bone');w:requestTask()
  if mode~='detail' then boneDetails() else now=now+16;ext.training:tick() end
  assert(w.execute_request_list[1].local_result)
  for i=n+1,#sent do assert(sent[i].id~=11083) end
 end
end)
case('bone rejected/lost result and extra consumption retain pending; manual collision blocked',function()
 freshTraining();addBone();local w=trainingTask('bone');w:requestTask();boneDetails();local n=#sent
 hc:sender11083(0,50,{{common_type=0,num=2}},{})
 ec:sender29404(1);hc:sender11212(45,1,{})
 assert(#sent==n)
 receive(11083,{code=1});bones[50].upgrade_lev=1;stocks[10011]=8;ext.training:tick()
 assert(w.execute_request_list[1].local_reason=='unexpected_bone_consumption')
 w=trainingTask('bone');w:requestTask();assert(w.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('all training sends prohibit purchases or formation writes and preserve exact payloads',function()
 for _,p in ipairs(sent) do
  assert(p.id~=29404 and p.id~=11212)
  if p.id==11083 then assert(#p.data.common_list==1 and p.data.common_list[1].num==1 and #p.data.item_ids==0) end
 end
end)
case('closed arena and another battle result never challenge or close the manual result',function()
 freshTraining();local w=trainingTask('arena');w:requestTask();receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}})
 local data=arenaBase(10,0);data.state=0;receive(29400,data)
 assert(w.execute_request_list[1].local_reason=='arena_closed')
 freshTraining();local closes=0;bc.finish_result_view_list[23]={fight_type=23,root_wnd={},isOpen=function() return true end,onCloseBtn=function() closes=closes+1 end}
 w=trainingTask('arena');w:requestTask();receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29400,arenaBase(10,0));assert(w.execute_request_list[1].local_reason=='battle_busy' and closes==0)
end)
case('bone detail query rejects stale wrong storage and missing fields before a mutation',function()
 freshTraining();addBone();local w=trainingTask('bone');w:requestTask();local n=#sent
 receive(10506,{storage=1,list={{id=50,upgrade_lev=0,exp=0}}});ext.training:tick()
 for i=n+1,#sent do assert(sent[i].id~=11083) end
 receive(10506,{storage=2,list={{id=50,upgrade_lev=0}}});ext.training:tick()
 for i=n+1,#sent do assert(sent[i].id~=11083) end
 boneDetails();assert(sent[#sent].id==11083);ext.training:cancel()
end)
case('hero response encoding is not assumed; only actual base level six confirms',function()
 freshTraining();local w=trainingTask('hero');w:requestTask();receive(11003,{result=0,msg='unknown encoding'})
 heroList[1].lev=6;ext.training:tick();assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('new tasks cancel across role and day changes and preserve sent pending',function()
 for _,change in ipairs({'role','day'}) do
  freshTraining();local w=trainingTask('hero');w:requestTask()
  if change=='role' then role={rid=role.rid+1,srv_id='srv'} else now=now+86400 end
  ext.training:tick();assert(w.execute_request_list[1].local_result=='cancelled')
 end
end)
case('only worn bones and empty backpack skip with zero detail or strengthen requests',function()
 freshTraining();heroList[2].open_bones=true
 model.hero_holy_list={[75]={id=75,base_id=boneBid,upgrade_lev=0,exp=0}}
 local n=#sent;local w=trainingTask('bone');w:requestTask()
 assert(w.execute_request_list[1].local_result=='skipped')
 for i=n+1,#sent do assert(sent[i].id~=11092 and sent[i].id~=11083 and sent[i].id~=10506) end
end)
case('bone cross-level cost follows original per-experience ceil and does not return stones',function()
 freshTraining();addBone(0,50);stocks[1]=999;local w=trainingTask('bone');w:requestTask();boneDetails()
 assert(w.execute_request_list[1].local_reason=='insufficient_coin')
 freshTraining();addBone(0,50);stocks[1]=1000;w=trainingTask('bone');w:requestTask();boneDetails()
 assert(sent[#sent].id==11083);receive(11083,{code=1});bones[50].upgrade_lev=1;bones[50].exp=50;stocks[10011]=9
 ext.training:tick();assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('bone moved out of backpack before reply never confirms against worn copy',function()
 freshTraining();addBone();local w=trainingTask('bone');w:requestTask();boneDetails()
 local g=bones[50];bones[50]=nil;model.hero_holy_list={[50]=g}
 receive(11083,{code=1});g.upgrade_lev=1;stocks[10011]=9;now=now+16;ext.training:tick()
 assert(w.execute_request_list[1].local_result=='uncertain')
end)
function savedQueue(kind,count,is_all)
 local data={}
 for _,cfg in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do
  data[cfg.id]=OneKeyBurdenMainWindow:getPosExecuteData(1,cfg);data[cfg.id].is_open=0
 end
 local pos=kind=='arena_free' and -2101794 or (kind=='arena' and -2101791 or -2101795)
 data[pos].is_open=1
 local key=kind=='arena' and 9021 or 9020
 for _,arg in ipairs(data[pos].args) do if arg.args_key==key then arg.args_val=count end end
 local main=setmetatable({task_list={{id=1}},select_index=1,operate_list={[1]=data}},{__index=OneKeyBurdenMainWindow})
 return main:saveOperateRequest(is_all),data[pos],main
end
case('real helper save and save-all preserve ten-ticket execution snapshot and run all ten',function()
 for _,is_all in ipairs({false,true}) do
  freshTraining();local queue,setting=savedQueue('arena',10,is_all)
  assert(#queue==1 and queue[1].args[1].args_key==9021 and queue[1].args[1].args_val==10)
  setting.args[1].args_val=0;assert(queue[1].args[1].args_val==10)
  local w=window(queue);w:requestTask();assert(ext.training.active.target==10)
  receive(11211,{type=45,formation_type=1,pos_info={{pos=1,id=2}}});receive(29400,arenaBase(0,0))
  for i=1,10 do
   opponents(5);receive(29446,{code=1,choose_id=5});receive(29403,{code=1});receive(29406,{result=1})
   stocks[10019]=47-i;receive(29400,arenaBase(0,i));ext.training:tick();ext.training:tick()
   receive(29400,arenaBase(0,i))
  end
  assert(w.execute_request_list[1].local_result=='confirmed' and stocks[10019]==37)
 end
end)
case('real helper save and save-all preserve twenty summon target across two tens',function()
 for _,is_all in ipairs({false,true}) do
  freshTraining();local queue,setting=savedQueue('summon',20,is_all)
  assert(#queue==1 and queue[1].args[1].args_key==9020 and queue[1].args[1].args_val==20)
  setting.args[1].args_val=10;assert(queue[1].args[1].args_val==20)
  local w=window(queue);w:requestTask();assert(ext.actions.active.target==20)
  receive(23200,{});response();assert(not w.execute_request_list[1].local_result)
  contracts=10;ext.actions:tick();assert(sent[#sent].id==23201);response()
  assert(w.execute_request_list[1].local_result=='confirmed')
  freshTraining();contracts=19;queue=savedQueue('summon',20,is_all)
  local n=#sent;w=window(queue);w:requestTask();assert(w.execute_request_list[1].local_reason=='insufficient_contracts')
  for i=n+1,#sent do assert(sent[i].id~=23201) end
 end
end)
case('missing duplicate or invalid queued resource target cannot silently default',function()
 for _,kind in ipairs({'arena','summon'}) do
  for _,mode in ipairs({'missing','duplicate','invalid'}) do
   freshTraining();local queue=savedQueue(kind,kind=='arena' and 10 or 20,false)
   if mode=='missing' then queue[1].args={}
   elseif mode=='duplicate' then queue[1].args[2]=queue[1].args[1]
   else queue[1].args[1].args_val=7 end
   local n=#sent;local w=window(queue);w:requestTask()
   assert(w.execute_request_list[1].local_result=='error')
   for i=n+1,#sent do assert(sent[i].id~=29403 and sent[i].id~=23201 and sent[i].id~=11211) end
  end
 end
end)
case('ticket task blocks while free remains; free task with zero quota never uses tickets',function()
 freshTraining();local w=startArena(10,1,0)
 assert(w.execute_request_list[1].local_reason=='free_challenges_remaining')
 freshTraining();local n=#sent;w=startArena(0,0,0)
 assert(w.execute_request_list[1].local_result=='skipped' and stocks[10019]==47)
 for i=n+1,#sent do assert(sent[i].id~=29403 and sent[i].id~=29446) end
end)
case('real save orders free then tickets before training for selected and all tasks',function()
 for _,is_all in ipairs({false,true}) do
  freshTraining();local _,_,main=savedQueue('arena',20,is_all)
  for _,pos in ipairs({-2101794,-2101793,-2101792}) do main.operate_list[1][pos].is_open=1 end
  local queue=main:saveOperateRequest(is_all)
  assert(#queue==4 and queue[1].pos==-2101794 and queue[2].pos==-2101791 and queue[3].pos==-2101793 and queue[4].pos==-2101792)
  assert(queue[2].args[1].args_val==20)
 end
end)
case('every challenge requires successful native refresh and authoritative requery; push cannot bypass ack',function()
 freshTraining();local w=startArena(0,2,1)
 receive(29401,{code=1,is_match=0,match_cd_time=now+3,match_list={{rid=5,srv_id='other'}}})
 local n=#sent;ext.training:tick();assert(#sent==n)
 now=now+3;ext.training:tick();assert(sent[#sent].id==29401)
 receive(29401,{code=1,match_cd_time=now,match_list={{rid=5,srv_id='other'}}});assert(sent[#sent].id==29402)
 receive(29401,{code=1,match_list={{rid=6,srv_id='other'}}});assert(sent[#sent].id==29402)
 receive(29402,{code=1});assert(sent[#sent].id==29401)
 receive(29401,{code=1,is_match=0,match_cd_time=now+3,match_list={{rid=7,srv_id='other'}}})
 assert(sent[#sent].id==29446 and ext.training.active.action.opponent.rid==7)
 ext.training:cancel()
 freshTraining();w=startArena(0,1,1);receive(29401,{code=0});receive(29402,{code=0})
 assert(w.execute_request_list[1].local_reason=='refresh_rejected')
end)
function rejectedArena(count,free,combat)
 local w=startArena(count,free,combat);opponents(3);receive(29446,{code=1,choose_id=3})
 receive(29403,{code=0});assert(sent[#sent].id==29400);return w,#sent
end
function doubleRejectState(free,combat)
 receive(29400,arenaBase(free,combat));now=now+3;ext.training:tick();receive(29400,arenaBase(free,combat))
end
case('explicit rejection reconciles unchanged twice, clears only own journal and never retries',function()
 freshTraining();local w,n=rejectedArena(0,9,1);doubleRejectState(9,1)
 assert(w.execute_request_list[1].local_result=='error' and w.execute_request_list[1].local_reason=='action_rejected_unchanged')
 for i=n+1,#sent do assert(sent[i].id==29400 or sent[i].id==29401 or sent[i].id==31604, 'unexpected packet '..sent[i].id) end
 local used,pending=ext.training.env.journal('arena_free');assert(used==0 and pending==0)
end)
case('explicit rejection consumed exact free or ticket counters counts once and stops',function()
 for _,mode in ipairs({'free','tickets'}) do
  freshTraining();local free=mode=='free' and 9 or 0;local w,n=rejectedArena(mode=='tickets' and 10 or 0,free,1)
  if mode=='tickets' then stocks[10019]=46 end
  doubleRejectState(mode=='free' and 8 or 0,2)
  assert(w.execute_request_list[1].local_result=='confirmed')
  local used,pending=ext.training.env.journal(mode=='free' and 'arena_free' or 'arena_tickets')
  assert(pending==0 and used==(mode=='free' and 0 or 1))
  for i=n+1,#sent do assert(sent[i].id==29400 or sent[i].id==29401 or sent[i].id==31604, 'unexpected packet '..sent[i].id) end
 end
end)
case('contradictory rejected counters or absent season retain pending after bounded read-only verification',function()
 for _,mode in ipairs({'counter','season','battle'}) do
  freshTraining();local w,n=rejectedArena(0,9,1);local data=arenaBase(9,1)
  if mode=='counter' then data.combat_time=3 elseif mode=='season' then data.start_time=nil else fight=true end
  receive(29400,data);now=now+31;ext.training:tick()
  local _,pending=ext.training.env.journal('arena_free');assert(pending==1 and w.execute_request_list[1].local_result=='uncertain')
  for i=n+1,#sent do assert(sent[i].id==29400 or sent[i].id==29401 or sent[i].id==31604, 'unexpected packet '..sent[i].id) end
 end
end)
case('delayed rejection inventory requires two matching snapshots after arrival',function()
 freshTraining();local w,n=rejectedArena(10,0,1)
 receive(29400,arenaBase(0,2));assert(ext.training.active.phase=='reject_verify')
 stocks[10019]=46;now=now+3;ext.training:tick();assert(sent[#sent].id==29400)
 doubleRejectState(0,2);assert(w.execute_request_list[1].local_result=='confirmed')
 for i=n+1,#sent do assert(sent[i].id==29400 or sent[i].id==29401 or sent[i].id==31604, 'unexpected packet '..sent[i].id) end
end)
case('explicit rejected pending can be read-only reconciled after reinstall; lost reply cannot',function()
 freshTraining();rejectedArena(0,9,1);ext.uninstall();ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining)
 local result;assert(ext.training:reconcilePending('arena_free',function(r) result=r end))
 doubleRejectState(9,1);assert(result.reason=='action_rejected_unchanged')
 freshTraining();startArena(0,9,1);opponents(3);receive(29446,{code=1,choose_id=3});ext.training:cancel()
 local ok,why=ext.training:reconcilePending('arena_free',function() end);assert(not ok and why=='explicit_rejection_required')
end)
case('legacy v4 reconciliation accepts only exact audited role day and baseline, only unchanged clears',function()
 local old_day=TimeTool.getDayAnyHourTime;TimeTool.getDayAnyHourTime=function() return 1791666000 end
 for _,mode in ipairs({'unchanged','changed','wrongrole','wrongday','missingperiod','otherpending'}) do
  freshTraining();role={rid=5317,srv_id='yinghe_3360'};now=1791694000
  local key='dldl_training_v1:yinghe_3360:5317:1791666000:'
  ud:setIntegerForKey(key..'arena_free:pending',1)
  local e={role_key='yinghe_3360:5317',day=1791666000,source_sha256='51cdd97c3de5b774bcc93564fc1d58e7ef47651304a073c38c09e56ed5ee0d78',
   sent_at=1791693165,free=9,combat=1,tickets=47,code=0,start_time=1791000000,end_time=1792000000}
  if mode=='wrongrole' then e.role_key='other' elseif mode=='wrongday' then e.day=e.day+1 elseif mode=='missingperiod' then e.end_time=nil
  elseif mode=='otherpending' then ud:setIntegerForKey(key..'arena_tickets:pending',1) end
  local result;local ok,reason=ext.training:reconcilePending('arena_free',function(r) result=r end,e)
  if mode=='unchanged' or mode=='changed' then
   assert(ok, tostring(reason)..' mode='..mode..' day='..ext.training.env.day());local data=arenaBase(mode=='changed' and 8 or 9,mode=='changed' and 2 or 1);data.start_time=e.start_time;data.end_time=e.end_time
   receive(29400,data);now=now+3;ext.training:tick();receive(29400,data)
   if mode=='unchanged' then assert(result and result.reason=='action_rejected_unchanged')
   else now=now+31;ext.training:tick();assert(result and result.status=='uncertain') end
  else assert(not ok) end
  assert(ud:getIntegerForKey(key..'arena_free:pending',0)==(mode=='unchanged' and 0 or 1))
  ud:setIntegerForKey(key..'arena_free:pending',0);ud:setIntegerForKey(key..'arena_tickets:pending',0)
 end
 TimeTool.getDayAnyHourTime=old_day
end)
case('arena diagnostic captures cooldown scalar fields and toast while preserving original message',function()
 ext.uninstall();local calls=0;local old_message=message;message=function() calls=calls+1 end
 ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining)
 local old_fu=cc.FileUtils;local old_open=io.open;local lines={}
 cc.FileUtils={getInstance=function() return {getWritablePath=function() return '/mock/' end} end}
 io.open=function() return {write=function(self,...) local s={...};for i,v in ipairs(s) do s[i]=tostring(v) end;lines[#lines+1]=table.concat(s) end,close=function() end} end
 freshTraining();startArena(0,9,1);message('挑战间隔过短');receive(29401,{code=1,is_match=1,match_cd_time=now+3,match_list={{rid=5,srv_id='other'}}})
 assert(calls==1);local text=table.concat(lines);assert(text:find('挑战间隔过短',1,true) and text:find('match_cd_time=',1,true) and text:find('is_match=1',1,true))
 io.open=old_open;cc.FileUtils=old_fu;ext.uninstall();message=old_message;ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining)
end)
case('shared persisted challenge interval gates next fight and free to ticket transition, server later CD wins',function()
 freshTraining();local w=startArena(0,1,1);opponents(2);receive(29446,{code=1,choose_id=2})
 local first=now;receive(29403,{code=1});receive(29406,{result=1});receive(29400,arenaBase(0,2));ext.training:tick();ext.training:tick();receive(29400,arenaBase(0,2))
 assert(w.execute_request_list[1].local_result=='confirmed')
 w=startArena(10,0,2);assert(ext.training.active.phase=='cooldown' and ext.training.active.wait_until>=first+4)
 local n=#sent;now=first+3;ext.training:tick();assert(#sent==n)
 now=first+4;ext.training:tick();receive(29400,arenaBase(0,2,1,now+5))
 assert(ext.training.active.phase=='cooldown' and ext.training.active.wait_until==now+5)
 opponents(2);receive(29446,{code=1,choose_id=2});assert(sent[#sent].id==29403 and now-first>=9)
 ext.training:cancel()
end)
case('one rejected snapshot and changed second snapshot cannot clear pending',function()
 for _,mode in ipairs({'one','changed'}) do
  freshTraining();local w=rejectedArena(0,9,1);receive(29400,arenaBase(9,1));now=now+3;ext.training:tick()
  if mode=='changed' then receive(29400,arenaBase(9,3)) end
  now=now+31;ext.training:tick();local _,pending=ext.training.env.journal('arena_free')
  assert(pending==1 and w.execute_request_list[1].local_result=='uncertain')
 end
end)
case('exact sidecar routes next manual free execution into read-only legacy reconciliation and audits result',function()
 freshTraining();role={rid=5317,srv_id='yinghe_3360'};now=1791695000
 local old_day=TimeTool.getDayAnyHourTime;TimeTool.getDayAnyHourTime=function() return 1791666000 end
 local key='dldl_training_v1:yinghe_3360:5317:1791666000:arena_free'
 ud:setIntegerForKey(key..':pending',1)
 local old_fu=cc.FileUtils;local old_open=io.open;local old_remove=os.remove;local removed=false;local output={}
 cc.FileUtils={getInstance=function() return {getWritablePath=function() return '/mock/' end} end}
 io.open=function(path,mode)
  if mode=='r' then return {read=function() return 'v4_rejected|yinghe_3360:5317|1791666000|1791693165|9|1|47|code0\\n' end,close=function() end} end
  return {write=function(self,...) for _,v in ipairs({...}) do output[#output+1]=tostring(v) end end,close=function() end}
 end
 os.remove=function(path) assert(path=='/mock/dldl_arena_v4_reconcile.request');removed=true end
 local n=#sent;local w=trainingTask('arena_free');w:requestTask();assert(sent[#sent].id==29400 and ext.training.active.phase=='legacy_scope')
 local data=arenaBase(9,1);data.start_time=1791000000;data.end_time=1792000000
 receive(29400,data);receive(29400,data);now=now+3;ext.training:tick();receive(29400,data)
 assert(w.execute_request_list[1].local_reason=='action_rejected_unchanged' and removed and ud:getIntegerForKey(key..':pending',1)==0)
 assert(table.concat(output):find('action_rejected_unchanged',1,true))
 for i=n+1,#sent do assert(sent[i].id==29400 or sent[i].id==29401 or sent[i].id==31604) end
 io.open=old_open;cc.FileUtils=old_fu;os.remove=old_remove;TimeTool.getDayAnyHourTime=old_day
end)
case('real async refresh reply then old is_match one list waits for final is_match zero before choosing',function()
 freshTraining();startArena(0,8,2)
 local old={};local final={};for i=1,5 do old[i]={rid=100+i,srv_id='other',order_id=i};final[i]={rid=200+i,srv_id='other',order_id=i} end
 receive(29401,{code=1,is_match=0,match_cd_time=0,match_list=old});assert(sent[#sent].id==29402)
 receive(29402,{code=1});assert(sent[#sent].id==29401);local n=#sent
 receive(29401,{code=1,is_match=1,match_cd_time=now+3,match_list=old})
 assert(#sent==n and ext.training.active.phase=='matching' and not ext.training.active.action.opponent)
 local _,pending=ext.training.env.journal('arena_free');assert(pending==0)
 receive(29401,{code=1,is_match=0,match_cd_time=now+3,match_list=final})
 assert(sent[#sent].id==29446 and sent[#sent].data.choose_id==5 and ext.training.active.action.opponent.rid==205)
 receive(29446,{code=1,choose_id=5});assert(sent[#sent].id==29403)
 ext.training:cancel()
end)
case('matching polls read-only after transition and bounded timeout never selects challenges or writes pending',function()
 freshTraining();local w=startArena(0,8,2);receive(29401,{code=0});receive(29402,{code=1})
 local n=#sent;receive(29401,{code=1,is_match=1,match_list={{rid=5,srv_id='other'}}})
 now=now+3;ext.training:tick();assert(sent[#sent].id==29401)
 receive(29401,{code=1,is_match=1,match_list={{rid=6,srv_id='other'}}});now=now+13;ext.training:tick()
 assert(w.execute_request_list[1].local_reason=='matching_timeout')
 local _,pending=ext.training.env.journal('arena_free');assert(pending==0)
 for i=n+1,#sent do assert(sent[i].id==29401 or sent[i].id==31604) end
 freshTraining();w=startArena(0,8,2);receive(29401,{code=0});receive(29402,{code=1})
 receive(29401,{code=1,match_list={{rid=5,srv_id='other'}}})
 assert(w.execute_request_list[1].local_reason=='invalid_match_state')
end)
case('later transition after selection cannot pass the final resource guard',function()
 freshTraining();local w=startArena(0,8,2);opponents(5)
 receive(29401,{code=1,is_match=1,match_list=em.enemy_data.match_list,choose_id=5})
 local n=#sent;receive(29446,{code=1,choose_id=5})
 assert(w.execute_request_list[1].local_reason=='opponents_not_ready')
 local _,pending=ext.training.env.journal('arena_free');assert(pending==0)
 for i=n+1,#sent do assert(sent[i].id~=29403) end
end)
ext.uninstall()
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls',
        'real_code':'original controllers, protocol dispatch, configuration, helper UI; rendering and mutable inventories mocked'}
(ROOT/'evidence'/f'{os.environ["DLDL_TEST_PHASE"]}_training_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
