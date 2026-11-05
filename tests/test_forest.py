#!/usr/bin/env python3
"""Forest battle/formation/queue regression with recovered classes and synthetic replies."""
import contextlib,io,json,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()): ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for f in ['daily_extras','voyage','mine','redbag','fishing_mail','forest']:
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+f+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Voyage','voyage_automation'),
                 ('GameVoyage','voyage_automation_game'),('Forest','forest_automation'),('GameForest','forest_automation_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute(r'''
freshForest()
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
GameVoyage.bind(Voyage,ext)
local before=#sent;GameForest.bind(Forest,ext);local firstCase=#passed
function prepareForest(stars,info,used,partial)
 local w=forestTask();w:requestTask();forestQuery(stars,info,used)
 if ext.forest.runner.active and ext.forest.runner.active.phase=='form' then
  receive(11211,forestForm(ext.forest.runner.active.id,partial));forestTick()
 end
 return w
end
function challengeForest()
 forestTick();assert(sent[#sent].id==20060 and sent[#sent].data.combat_type==82);receive(20060,{combat_type=82,type=0});forestTick();assert(sent[#sent].id==31906)
 fight=true;fight_type=82;bc:scInitFightStart({combat_type=82})
end
function settleForest(result,stars)
 bc:scFightEnd({combat_type=82,result=result});fight=false
 now=now+2;forestTick();assert(sent[#sent].id==31903)
 receive(31903,forestList(stars));forestTick();forestTick()
end
case('installation is passive; daily row defaults off and five stars',function()
 assert(#sent==before)
 local d=OneKeyBurdenMainWindow:getPosExecuteData(1,ext.forest.row)
 assert(d.is_open==0 and d.args[1].args_val==5)
end)
case('star selection is saved locally and included in execution queue',function()
 local w=setmetatable({select_index=1,task_list={SimplifyData.data_list[1]},operate_list={[1]={}}},{__index=OneKeyBurdenMainWindow})
 for _,cfg in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do local d=w:getPosExecuteData(1,cfg);d.is_open=cfg.id==ext.forest.pos and 1 or 0;w.operate_list[1][cfg.id]=d end
 w.operate_list[1][ext.forest.pos].args[1].args_val=4
 local q=w:saveOperateRequest(true);assert(#q==1 and q[1].args[1].args_val==4)
 local d=w:getPosExecuteData(1,ext.forest.row);assert(d.is_open==1 and d.args[1].args_val==4)
 assert(not pcall(function() oc:sender31602(1,ext.forest.pos) end))
end)
case('all nonbattle phases stop before querying heroes or challenging',function()
 for _,state in ipairs({0,1,3}) do
  freshForest();local w=forestTask();w:requestTask();local n=#sent;receive(31900,forestBase(state));forestTick()
  assert(w.execute_request_list[1].local_reason=='non_battle_period' and w.execute_index==2)
  for i=n+1,#sent do assert(sent[i].id~=11211 and sent[i].id~=31906 and sent[i].id~=11212) end
 end
end)
case('three opponents start independently at five; full formation is preserved',function()
 freshForest();local stars={0,0,0};local w=forestTask();w:requestTask()
 for i=1,3 do
  forestQuery(stars);receive(11211,forestForm(i));forestTick();assert(ext.forest.runner.active, tostring(w.execute_request_list[1].local_reason));assert(ext.forest.runner.active.phase=='ready')
  challengeForest();assert(sent[#sent].data.defender_id==i and sent[#sent].data.star==5)
  stars[i]=5;settleForest(1,stars)
 end
 forestQuery(stars);assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='forest_complete')
 assert(#w.execute_request_list[1].forest.attempts==3)
end)
case('confirmed defeat lowers stars and next defender resets to five',function()
 freshForest();local w=prepareForest();challengeForest();settleForest(2,{0,0,0})
 forestQuery();receive(11211,forestForm(1));forestTick();challengeForest();assert(sent[#sent].data.star==4)
 settleForest(0,{0,0,0});forestQuery();receive(11211,forestForm(1));forestTick();challengeForest();assert(sent[#sent].data.star==3)
 settleForest(1,{3,0,0});forestQuery({3,0,0});receive(11211,forestForm(2));forestTick();challengeForest();assert(sent[#sent].data.star==5 and sent[#sent].data.defender_id==2)
 ext.forest.runner:cancel();fight=false
end)
case('one star defeat is exhausted and never retried that day',function()
 freshForest();local w=forestTask(1);w:requestTask();forestQuery();receive(11211,forestForm(1));forestTick();challengeForest();settleForest(2,{0,0,0})
 forestQuery();assert(ext.forest.runner.active.id==2 and ext.forest.runner.active.current_star==1);ext.forest.runner:cancel()
end)
case('skip waits for visible native button and excludes other fights and replay',function()
 freshForest();prepareForest();challengeForest();local visible=false;local clicks=0
 panel={root_wnd={},battle_type=82,skip_btn={isVisible=function() return visible end},onClickSkipBtn=function() clicks=clicks+1 end}
 forestTick();assert(clicks==0);now=now+5;forestTick();assert(clicks==0)
 visible=true;replay=true;forestTick();assert(clicks==0);replay=false;panel.battle_type=77;forestTick();assert(clicks==0)
 panel.battle_type=82;forestTick();forestTick();assert(clicks==1)
 ext.forest.runner:cancel();fight=false;panel=nil
end)
case('fill replaces only unavailable members, descending power, preserving equipment',function()
 freshForest();local d=forestForm(1,{{pos=1,id=20},{pos=2,id=1},{pos=3,id=2}})
 local used={{defender_id=2,partner_list={{partner_id=2}}}};local info=forestInfo(11,{{bid=101}})
 local f=assert(GameForest.fill(d,info,forestList(nil,used),1,hc:getModel():getHeroList(),FormationData.data_form_data[1].pos,11))
 assert(f.pos_info[1].id==20 and f.pos_info[2].id==3 and f.pos_info[3].id==4 and f.pos_info[4].id==5)
 assert(f.hallows_id==d.hallows_id and f.hidden_id[1].id==21 and f.domain_id==1 and f.fusion_skill[1].id==31 and f.common_list[1].common_type==4)
 assert(d.pos_info[2].id==1,'input mutated')
 local low=assert(GameForest.fill(d,forestInfo(10,{{bid=101}}),forestList(),1,hc:getModel():getHeroList(),FormationData.data_form_data[1].pos,11))
 assert(low.pos_info[2].id==1,'bans applied below rank threshold')
end)
case('double camp, duplicate species, linked heroes and cross-defender use are excluded',function()
 freshForest();local hs=hc:getModel():getHeroList()
 hs[1].isDoubleCampHero=function() return true end;hs[1].main_camp_id=101;hs[1].sub_camp_id=999
 hs[2].bid=103;hs[4].getCanChangeBid=function() return 103 end;hs[5].getLinkPartnerId=function() return 2 end
 local f=assert(GameForest.fill(forestForm(1,{}),forestInfo(11,{{bid=999}}),forestList(nil,{{defender_id=2,partner_list={{partner_id=6}}}}),1,hs,FormationData.data_form_data[1].pos,11))
 local selected={};for _,p in ipairs(f.pos_info) do selected[p.id]=true end
 assert(not selected[1] and selected[2] and not selected[3] and not selected[4] and not selected[5] and not selected[6] and selected[7])
end)
case('formation save must be accepted and read back before challenge',function()
 freshForest();local w=prepareForest(nil,nil,nil,{{pos=1,id=20}})
 assert(sent[#sent].id==11212);local saved=deepCopy(sent[#sent].data);assert(#saved.pos_info==6)
 forestTick();assert(sent[#sent].id==11212)
 receive(11212,{type=107,code=1});assert(sent[#sent].id==11211)
 saved.pos_info={saved.pos_info[6],saved.pos_info[5],saved.pos_info[4],saved.pos_info[3],saved.pos_info[2],saved.pos_info[1]};receive(11211,saved);forestTick();challengeForest();assert(w.execute_index==1)
 ext.forest.runner:cancel();fight=false
end)
case('save mismatch and insufficient available heroes never challenge',function()
 freshForest();local w=prepareForest(nil,nil,nil,{{pos=1,id=20}});receive(11212,{type=107,code=1});receive(11211,forestForm(1));forestTick()
 assert(w.execute_request_list[1].local_reason=='formation_mismatch')
 freshForest();hc:getModel().hero_list={[1]={partner_id=1,bid=101,power=1}};w=prepareForest();assert(w.execute_request_list[1].local_reason=='formation_insufficient')
end)
case('skill ordering is immaterial but changed skills fail verification',function()
 local a=forestForm(1);a.fusion_skill={{pos=1,id=21,skill_lev=1},{pos=2,id=22,skill_lev=2}}
 local b=deepCopy(a);b.fusion_skill={b.fusion_skill[2],b.fusion_skill[1]};assert(GameForest.sameForm(a,b))
 b.fusion_skill[1].skill_lev=3;assert(not GameForest.sameForm(a,b))
end)
case('native battle context is confirmed before sending challenge; unrelated battle stops',function()
 freshForest();local w=prepareForest();forestTick();assert(sent[#sent].id==20060)
 local n=#sent;receive(20060,{combat_type=77,type=0});forestTick();assert(#sent==n)
 receive(20060,{combat_type=82,type=1});assert(w.execute_request_list[1].local_reason=='battle_busy' and MainuiController:getUIFightType()==0)
end)
case('negative challenge acknowledgement clears only the rejected request',function()
 freshForest();local w=prepareForest();forestTick();receive(20060,{combat_type=82,type=0});forestTick()
 receive(31906,{code=0});assert(w.execute_request_list[1].local_reason=='challenge_rejected')
 local d=json.decode(ud:getStringForKey(forestKey()..':last',''));assert(not d.pending)
end)
case('registration allows otherwise discarded acknowledgement and is detached cleanly',function()
 assert(ProtoMgr:hasReg(31906) and ProtoMgr.cmd_callback_table[31906].dldl_forest_reply)
end)
case('manual battle view change cancels pending without automatic replay',function()
 freshForest();local w=prepareForest();challengeForest();MainuiController.forest_ui=77;forestTick()
 assert(w.execute_request_list[1].local_reason=='battle_view_changed' and MainuiController:getUIFightType()==77);fight=false
end)
case('completed opponents skip even after reload; no bonus-star farming',function()
 freshForest();local w=prepareForest({5,4,1});assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='forest_complete')
end)
case('lost reply keeps pending; a fresh confirmed win reconciles without replaying',function()
 freshForest();local w=prepareForest();challengeForest();now=now+181;forestTick();fight=false
 assert(w.execute_request_list[1].local_result=='uncertain')
 w=forestTask();w:requestTask();forestQuery();assert(w.execute_request_list[1].local_reason=='request_unresolved')
 w=forestTask();w:requestTask();forestQuery({5,0,0});assert(ext.forest.runner.active.id==2);ext.forest.runner:cancel()
end)
case('result requires owned combat start and ignores replay and foreign battle',function()
 freshForest();prepareForest();forestTick();receive(20060,{combat_type=82,type=0});forestTick();local a=ext.forest.runner.active
 bc:scFightEnd({combat_type=1082,result=2});assert(a.phase=='battle')
 bc:scFightEnd({combat_type=77,result=2});assert(a.phase=='battle')
 bc:scFightEnd({combat_type=82,result=2});assert(a.phase=='battle')
 ext.forest.runner:cancel()
end)
case('stale win progress retries only reads then stops uncertain',function()
 freshForest();local w=prepareForest();challengeForest();bc:scFightEnd({combat_type=82,result=1});fight=false;local n=#sent
 for i=1,6 do now=now+3;forestTick();receive(31903,forestList());forestTick() end
 assert(w.execute_request_list[1].local_reason=='result_mismatch')
 for i=n+1,#sent do assert(sent[i].id~=31906) end
end)
case('disconnect and role/day changes retain unresolved fight and stop safely',function()
 for _,mode in ipairs({'disconnect','role','day'}) do
  freshForest();local w=prepareForest();challengeForest();local rid=role.rid
  if mode=='disconnect' then connected=false elseif mode=='role' then role.rid=rid+1 else now=now+86400 end
  forestTick();assert(not ext.forest.runner.active);role.rid=rid;connected=true;fight=false
 end
end)
case('external formation or opponent changes cannot overlap owned run',function()
 freshForest();prepareForest();local n=#sent
 hc:sender11212(107,1,{},0,{},0,{},{},{},{});forestc:send31906(2,5);forestc:send31909()
 assert(#sent==n);ext.forest.runner:cancel()
end)
case('owned result closes before next battle and progression remains observable',function()
 freshForest();local w=prepareForest();challengeForest();bc:scFightEnd({combat_type=82,result=1});bc:openFinishView(true,82,{result=1})
 now=now+2;forestTick();receive(31903,forestList({5,0,0}));forestTick();assert(ext.forest.runner.active.phase=='cleanup')
 forestTick();assert(not bc.finish_result_view_list[82]);forestTick();assert(ext.forest.runner.active.phase=='base' and w.other_progress>0)
 ext.forest.runner:cancel();fight=false
end)
case('closing queue detaches runner without advancing cancelled work',function()
 freshForest();local w=prepareForest();w:close_callback();assert(not ext.forest.runner.active and w.execute_index==1)
end)
forestCount=#passed-firstCase
ext.detach();assert(not ProtoMgr:hasReg(31906))

''')
print(json.dumps({'forest_cases':lua.globals().forestCount,'network':'none'},ensure_ascii=False))
