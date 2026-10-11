#!/usr/bin/env python3
"""Phase11v2 guild/ruins integration, real recovered senders/handlers with mock server and rendering."""
import os,runpy,json
from pathlib import Path
os.environ['DLDL_TEST_PHASE']='phase11v3'
ROOT=Path(__file__).resolve().parents[1]
ns=runpy.run_path(str(ROOT/'tests/test_daily_training.py'))
lua=ns['lua'];original=ns['original']
for p in ['config/temple_boss_data.luac','config/combat_type_data.luac',
          'base/basecontroller.luac','game/guild/guild_controller.luac','game/godruins/god_ruins_controller.luac']:
    original(p)
lua.execute("bc.getModel=function() return {} end;tolua={isnull=function() return false end}")
original('game/battle/new_view/battle_ui_panel.luac')
for var,p in [('Quests','daily_quests.lua'),('GameQuests','daily_quests_game.lua')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/p).read_text())
lua.execute('''
Send=function(id,data) capture(nil,id,data) end
function ProtoMgr:getInstance() return self end
qcapture=BaseController.SendProtocal
TwoGodsBattleController={isTwogodsBattleType=function() return false end}
local gm={updateMyGuildInfo=function(self,d) self.my_guild_info=d end,updateRedStatus=function() end}
gc=setmetatable({model=gm,SendProtocal=qcapture},{__index=GuildController})
function GuildController:getInstance() return gc end
function gc:checkGuildDunRed() end
function gc:checkGuildWarRed() end
function gc:checkGuildShopRed() end
GuildConst={post_type={member=1}}
GuildEvent=setmetatable({}, {__index=function(t,k) return k end})
gc.registerGuildInfoEvent=function() end
-- Unrelated guild event registration is stubbed; senders/handler stay original.
GodRuinsModel={updateBaseData=function(self,d) self.baseData=d end,setBattleData=function(self,id) self.battle_id=id end}
rc=setmetatable({SendProtocal=qcapture,checkRed=function() end},{__index=GodRuinsController})
function GodRuinsController:getInstance() return rc end
GlobalEvent.Fire=function() end
BattleConst.Fight_Type.GodRuins=77
HolyPillarTrialController={};SoulController={}
for _,p in ipairs({{gc,13518},{rc,13100},{rc,13106}}) do
 ProtoMgr:RegisterCmdCallback(p[2],'handle'..p[2],p[1])
end
bc.getWatchReplayStatus=function() return replay or false end
bc.getIsSameBattleType=function(self,t) return fight_type==t end
bc.getFightTypeInfo=function(self,t) return fight and fight_type==t end
bc.send20062=function(self) capture(self,20062,{}) end
bc.getBattleUIPanel=function() return panel end
bc.scInitFightStart=function(self,data) end
bc.scReBattleFight=function(self,data) end
bc.scFightEnd=function(self,data) end
bc.openFinishView=function(self,open,t,data)
 if open then
  local v={isOpen=function() return true end,root_wnd={},item_scroll={},fight_type=t}
  if data.result==1 then function v:onCloseBtn() fight=false;bc.finish_result_view_list[t]=nil end;bc.finish_result_view_list[t]=v
  else function v:close() fight=false;bc.finish_fail_view_list[t]=nil end;bc.finish_fail_view_list[t]=v end
 end
end
function freshQuest()
 freshTraining();role.gid=10;role.gsrv_id='guild';role.vip_lev=3;stocks[3]=1000
 ProtoMgr.cmd_callback_table[13548]=nil;ProtoMgr.cmd_callback_table[13105]=nil;fight=false;fight_type=nil;replay=false;panel=nil
end
function qtask(kind)
 local positions={guild_wish=-2101790,ruins=-2101787}
 return window({{type=1,pos=positions[kind],args={}}})
end
function rbase(n,extra)
 local id;for k in pairs(TempleBossData.data_get_boss) do id=k;break end
 local d={kill_time=n,boss_id=id,hp_per=0,fight_time=0,end_time=now+1000}
 for k,v in pairs(extra or {}) do d[k]=v end;return d
end
function startQ(k,n)
 local w=qtask(k);w:requestTask()
 if k=='guild_wish' then assert(sent[#sent].id==13518);return w end
 assert(k=='ruins' and sent[#sent].id==11211 and sent[#sent].data.type==92)
 receive(11211,{type=92,formation_type=1,pos_info={{pos=1,id=2}}})
 if n~=nil then receive(13100,rbase(n)) end
 return w
end
DanmatchController={getInstance=function() error('removed controller must not be used') end}
local original_multiform_sender=hc.send11253
local install_sent=#sent
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests)
case('fourteen optional rows preserve original twelve and only guild ruins remain',function()
 assert(#ext.specs==14 and ext.version=='daily_quests_v2' and #sent==install_sent)
 local old_ids={-2101802,-2101801,-2101800,-2101799,-2101798,-2101797,-2101796,-2101795,-2101794,-2101791,-2101793,-2101792}
 for i,id in ipairs(old_ids) do assert(ext.specs[i].pos==id) end
 for i=13,14 do assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[i].row).is_open==0) end
 assert(ext.specs[13].kind=='guild_wish' and ext.specs[14].kind=='ruins' and hc.send11253==original_multiform_sender)
 for _,row in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do assert(row.id~=-2101789 and row.id~=-2101788) end
end)
case('historical tournament preferences and pending are never read written or barriers for fourteen rows',function()
 local original_get=ud.getIntegerForKey;local original_set=ud.setIntegerForKey
 local original_bool_get=ud.getBoolForKey;local original_bool_set=ud.setBoolForKey
 local function retired(k) return k:find(':danmatch:',1,true) or k:find(':-2101789',1,true) or k:find(':-2101788',1,true) end
 ud.getIntegerForKey=function(self,k,d) assert(not retired(k),'historical integer read');return original_get(self,k,d) end
 ud.setIntegerForKey=function(self,k,v) assert(not retired(k),'historical integer write');return original_set(self,k,v) end
 ud.getBoolForKey=function(self,k,d) assert(not retired(k),'historical boolean read');return original_bool_get(self,k,d) end
 ud.setBoolForKey=function(self,k,v) assert(not retired(k),'historical boolean write');return original_bool_set(self,k,v) end
 for _,spec in ipairs(ext.specs) do
  freshQuest();local key='dldl_quests_v1:'..role.srv_id..':'..role.rid..':danmatch:pending'
  original_set(ud,key,1)
  local pref='dldl_gifts_v1:'..role.srv_id..':'..role.rid
  original_bool_set(ud,pref..':-2101789',true);original_bool_set(ud,pref..':-2101788',true)
  local setting=OneKeyBurdenMainWindow:getPosExecuteData(1,spec.row)
  local w=window({{type=1,pos=spec.pos,args=setting.args}});local n=#sent;w:requestTask()
  assert(w.execute_request_list[1].local_reason~='manual_claim_pending')
  local selected=spec.quest and ext.quests or spec.training and ext.training or type(spec.kind)=='number' and ext.runner or ext.actions
  selected:cancel()
  assert(original_get(ud,key,0)==1 and original_bool_get(ud,pref..':-2101789',false) and original_bool_get(ud,pref..':-2101788',false))
  for i=n+1,#sent do assert(sent[i].id<30100 or sent[i].id>30105) end
 end
 ud.getIntegerForKey=original_get;ud.setIntegerForKey=original_set;ud.getBoolForKey=original_bool_get;ud.setBoolForKey=original_bool_set
end)
case('retired task IDs in stale queues are skipped without native sends then guild runs',function()
 freshQuest();local n=#sent
 local w=window({{type=1,pos=-2101789,args={}},{type=1,pos=-2101788,args={}},{type=1,pos=-2101790,args={}}})
 w:requestTask();w:requestTask();assert(w.execute_index==3)
 for i=1,2 do assert(w.execute_request_list[i].local_result=='skipped' and w.execute_request_list[i].local_reason=='task_removed') end
 oc:sender31602(1,-2101789);oc:sender31602(1,-2101788)
 assert(#sent==n);w:requestTask();assert(sent[#sent].id==13518)
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=2});assert(w.is_execute_finish)
end)
case('retired settings are filtered from real saved queues and native settings payloads',function()
 for _,is_all in ipairs({false,true}) do
  freshQuest();local data={}
  for _,cfg in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do data[cfg.id]=OneKeyBurdenMainWindow:getPosExecuteData(1,cfg);data[cfg.id].is_open=0 end
  data[-2101790].is_open=1
  data[-2101789]={type=1,pos=-2101789,is_open=1,args={}}
  data[-2101788]={type=1,pos=-2101788,is_open=1,args={}}
  local main=setmetatable({task_list={{id=1}},select_index=1,operate_list={[1]=data}},{__index=OneKeyBurdenMainWindow})
  local queue=main:saveOperateRequest(is_all);assert(#queue==1 and queue[1].pos==-2101790)
  for _,g in ipairs(sent[#sent].data.list) do for _,row in ipairs(g.type_list) do assert(row.pos~=-2101789 and row.pos~=-2101788) end end
 end
end)
case('removed runner kinds cannot start query purchase or restore historical journals',function()
 freshQuest();local n=#sent
 for _,k in ipairs({'danmatch','danmatch_buy3'}) do
  local ok,why=ext.quests:start(k,function() error('unexpected completion') end)
  assert(not ok and why=='unknown_task' and not ext.quests.active and not ext.quests.env.pending(k))
 end
 assert(#sent==n)
end)
case('guild error advances to the next row without sending a second guild action',function()
 freshQuest();local w=window({{type=1,pos=-2101790,args={}},{type=1,pos=-2101787,args={}}})
 w:requestTask();local n=#sent;receive(13518,{gid=999,gsrv_id='foreign',wish_gift_type=0})
 assert(w.execute_index==2 and w.execute_request_list[1].local_result=='error')
 for i=n+1,#sent do assert(sent[i].id~=13548) end
 w:requestTask();assert(sent[#sent].id==11211 and w.execute_index==2)
 ext.quests:cancel()
end)
case('guild wish uses callback-only13548 type2 and postquery exact guild confirmation',function()
 freshQuest();local w=startQ('guild_wish')
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=0})
 assert(sent[#sent].id==13548 and sent[#sent].data.wish_gift_type==2)
 receive(13548,{code=1,wish_gift_type=2});assert(sent[#sent].id==13518)
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=2});assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('guild alreadyclaimed branch1 and no guild never attempt alternate reward',function()
 freshQuest();local w=startQ('guild_wish');local n=#sent
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=1});assert(w.execute_request_list[1].local_result=='skipped');for i=n+1,#sent do assert(sent[i].id~=13548) end
 freshQuest();role.gid=0;w=qtask('guild_wish');w:requestTask();assert(w.execute_request_list[1].local_reason=='no_guild')
end)
case('missing wish response retains journal across restart and nextday',function()
 freshQuest();local w=startQ('guild_wish');receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=0})
 now=now+21;ext.quests:tick();assert(w.execute_request_list[1].local_result=='uncertain')
 now=now+86400;w=qtask('guild_wish');local n=#sent;w:requestTask();assert(w.execute_request_list[1].local_reason=='previous_request_unresolved' and sent[#sent].id==31604)
 for i=n+1,#sent do assert(sent[i].id~=13548) end
end)
case('contracts insufficient skips only mirror task then guild executes in real queue',function()
 freshQuest();contracts=19
 local w=window({{type=1,pos=-2101795,args={{args_key=9020,args_val=20}}},{type=1,pos=-2101790,args={}}})
 local n=#sent;w:requestTask();w:requestTask();assert(w.execute_request_list[1].local_result=='skipped' and w.execute_index==2 and sent[#sent].id==13518)
 for i=n+1,#sent do assert(sent[i].id~=23201) end
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=2});assert(w.is_execute_finish)
end)
case('ruins own challenge callback and success verify actual remaining rewards',function()
 freshQuest();local w=startQ('ruins',1);assert(sent[#sent].id==13105 and sent[#sent].data.id==0)
 receive(13105,{code=1,id=0});fight=true;fight_type=77
 local b=ext.quests.active.base;receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
 receive(13100,rbase(0,{end_time=b.end_time,fight_time=1}));ext.quests:tick();ext.quests:tick();receive(13100,rbase(0))
 assert(w.execute_request_list[1].local_result=='confirmed' and not ext.quests.env.pending('ruins'))
end)
case('ruins confirmed defeat stops own retry and advances to later guild task',function()
 freshQuest();local w=window({{type=1,pos=-2101787,args={}},{type=1,pos=-2101790,args={}}});w:requestTask()
 receive(11211,{type=92,formation_type=1,pos_info={{pos=1,id=2}}});receive(13100,rbase(2))
 receive(13105,{code=1,id=0});local b=ext.quests.active.base;fight=true;fight_type=77
 receive(13106,{result=2,is_self=1,combat_type=77,hp_per=8000})
 receive(13100,rbase(2,{boss_id=b.boss_id,hp_per=8000,end_time=b.end_time,fight_time=1}))
 ext.quests:tick();ext.quests:tick();w:requestTask();assert(w.execute_request_list[1].local_reason=='ruins_defeat' and w.execute_index==2 and sent[#sent].id==13518)
 receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=2});assert(w.is_execute_finish)
end)
case('foreign ruins settlement leaves pending without another challenge',function()
 freshQuest();local w=startQ('ruins',1);receive(13105,{code=1,id=0});receive(13106,{result=1,is_self=0,combat_type=77,hp_per=0})
 assert(w.execute_request_list[1].local_result=='uncertain' and ext.quests.env.pending('ruins'))
end)
case('partial20 summon depletion skips remaining contract batch and continues queue',function()
 freshQuest();local w=window({{type=1,pos=-2101795,args={{args_key=9020,args_val=20}}},{type=1,pos=-2101790,args={}}})
 w:requestTask();receive(23200,{});local n=#sent;contracts=0;response();ext.actions:tick()
 assert(w.execute_request_list[1].local_result=='skipped' and w.execute_request_list[1].local_reason=='insufficient_contracts')
 for i=n+1,#sent do assert(sent[i].id~=23201) end
 w:requestTask();receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=2});assert(w.is_execute_finish)
end)
case('mirror pending remains uncertain and later guild row is skipped without retry',function()
 freshQuest();local w=window({{type=1,pos=-2101795,args={{args_key=9020,args_val=10}}},{type=1,pos=-2101790,args={}}})
 w:requestTask();receive(23200,{});now=now+20;ext.actions:tick();assert(w.execute_index==2 and not w.is_execute_finish)
 local n=#sent;w:requestTask()
 assert(w.execute_request_list[1].local_result=='uncertain' and w.execute_request_list[2].local_result=='error'
   and w.execute_request_list[2].local_reason=='manual_claim_pending' and w.execute_index==2 and w.is_execute_finish)
 for i=n+1,#sent do assert(sent[i].id~=13548 and sent[i].id~=23201) end
end)
case('role/day change cannot apply late owned callback or clear old journal',function()
 freshQuest();local w=startQ('guild_wish');receive(13518,{gid=10,gsrv_id='guild',wish_gift_type=0})
 local previous=role;role={rid=previous.rid+1,srv_id=previous.srv_id,gid=10,gsrv_id='guild',vip_lev=3}
 receive(13548,{code=1,wish_gift_type=2});assert(w.execute_request_list[1].local_result=='cancelled')
 role=previous;assert(ext.quests.env.pending('guild_wish'))
 freshQuest();w=startQ('ruins',1);now=now+86400;ext.quests:tick();assert(w.execute_request_list[1].local_result=='cancelled' and ext.quests.env.pending('ruins'))
end)
case('ruins native skip77 and reordered settlement callback retain own battle state',function()
 freshQuest();local w=startQ('ruins',1);local b=ext.quests.active.base;fight=true;fight_type=77;bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1})
 panel=setmetatable({root_wnd={},battle_type=77,skip_btn={isVisible=function() return true end}}, {__index=BattleUIPanel})
 receive(13105,{code=1,id=0});ext.quests:tick();assert(sent[#sent].id==20062)
 assert(ext.quests.active and ext.quests.active.phase=='battle',tostring(ext.quests.active and ext.quests.active.phase));ext.quests:cancel();assert(w.execute_request_list[1].local_result=='cancelled')
 freshQuest();w=startQ('ruins',1);b=ext.quests.active.base;bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1})
 ext.quests:cancel();assert(w.execute_request_list[1].local_result=='cancelled')
end)
case('guild pending still blocks ruins and own ruins pending still blocks a restart',function()
 freshQuest();local key='dldl_quests_v1:'..role.srv_id..':'..role.rid
 ud:setIntegerForKey(key..':guild_wish:pending',1)
 local n=#sent;local w=qtask('ruins');w:requestTask()
 assert(w.execute_request_list[1].local_reason=='manual_claim_pending')
 for i=n+1,#sent do assert(sent[i].id~=11211 and sent[i].id~=13105) end
 freshQuest();w=startQ('ruins',1);local own='dldl_quests_v1:'..role.srv_id..':'..role.rid..':ruins:pending'
 receive(13105,{code=1,id=0});now=now+91;ext.quests:tick();assert(ext.quests.env.pending('ruins'))
 n=#sent;w=qtask('ruins');w:requestTask()
 assert(w.execute_request_list[1].local_result=='uncertain' and w.execute_request_list[1].local_reason=='previous_request_unresolved' and ud:getIntegerForKey(own,0)==1)
 for i=n+1,#sent do assert(sent[i].id~=11211 and sent[i].id~=13100 and sent[i].id~=13105) end
end)
case('unknown ruins result advances queue while its pending skips later guild without retry',function()
 freshQuest();local w=window({{type=1,pos=-2101787,args={}},{type=1,pos=-2101790,args={}}})
 w:requestTask();receive(11211,{type=92,formation_type=1,pos_info={{pos=1,id=2}}});receive(13100,rbase(2))
 receive(13106,{result=2,is_self=1,combat_type=77,hp_per=8000});now=now+21;ext.quests:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].local_result=='uncertain' and ext.quests.env.pending('ruins'))
 local n=#sent;w:requestTask();assert(w.is_execute_finish and w.execute_request_list[2].local_reason=='manual_claim_pending')
 for i=n+1,#sent do assert(sent[i].id~=13105 and sent[i].id~=13518 and sent[i].id~=13548) end
end)
case('ruins runs all remaining rewards using only own id zero challenge with fresh verification',function()
 freshQuest();local w=startQ('ruins',2);local n=#sent-1
 for remaining=2,1,-1 do
  local b=ext.quests.active.base;receive(13105,{code=1,id=0});fight=true;fight_type=77
  bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1})
  receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
  receive(13100,rbase(remaining-1,{end_time=b.end_time,fight_time=b.fight_time+1}))
  ext.quests:tick();ext.quests:tick()
  receive(13100,rbase(remaining-1,{end_time=b.end_time,fight_time=b.fight_time+1}))
 end
 assert(w.execute_request_list[1].local_result=='confirmed' and not ext.quests.env.pending('ruins'))
 local count=0;for i=n+1,#sent do if sent[i].id==13105 then count=count+1;assert(sent[i].data.id==0) end;assert(sent[i].id~=13103 and sent[i].id~=11212) end
 assert(count==2)
end)
case('ruins empty invalid duplicate or missing owned formation never writes or challenges',function()
 for _,mode in ipairs({'empty','invalid','duplicate','foreign'}) do
  freshQuest();local w=qtask('ruins');w:requestTask();local n=#sent
  local d={type=92,formation_type=1,pos_info={{pos=1,id=2}}}
  if mode=='empty' then d.pos_info={} elseif mode=='invalid' then d.formation_type=0 elseif mode=='duplicate' then d.pos_info[2]={pos=1,id=2} else d.pos_info[1].id=999 end
  receive(11211,d);assert(w.execute_request_list[1].local_result=='error' and not ext.quests.env.pending('ruins'))
  for i=n+1,#sent do assert(sent[i].id~=13105 and sent[i].id~=11212) end
 end
end)
case('ruins native skip requires own visible panel correct combat type and no replay',function()
 freshQuest();local w=startQ('ruins',1);receive(13105,{code=1,id=0});fight=true;fight_type=77
 bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1})
 local visible=true;panel=setmetatable({root_wnd={},battle_type=77,skip_btn={isVisible=function() return visible end}},{__index=BattleUIPanel})
 local n=#sent;replay=true;ext.quests:tick();assert(#sent==n);replay=false;visible=false;ext.quests:tick();assert(#sent==n)
 visible=true;panel.battle_type=55;ext.quests:tick();assert(#sent==n);panel.battle_type=77
 fight_type=55;ext.quests:tick();assert(#sent==n);fight_type=77;ext.quests:tick();assert(sent[#sent].id==20062)
 n=#sent;ext.quests:tick();assert(#sent==n);ext.quests:cancel()
end)
case('ruins start and settlement before callback still require exact accepted id zero',function()
 for _,reverse in ipairs({false,true}) do
  freshQuest();local w=startQ('ruins',1);local b=ext.quests.active.base;fight=true;fight_type=77
  bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1})
  if reverse then receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000});assert(ext.quests.active.phase=='battle');receive(13105,{code=1,id=0})
  else receive(13105,{code=1,id=0});bc:scFightEnd({combat_type=77,result=1,show_panel_type=1});receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000}) end
  assert(ext.quests.active.phase=='verify' and ext.quests.env.pending('ruins'))
  receive(13100,rbase(0,{end_time=b.end_time,fight_time=1}));ext.quests:tick();ext.quests:tick();receive(13100,rbase(0,{end_time=b.end_time,fight_time=1}))
  assert(w.execute_request_list[1].local_result=='confirmed' and not ext.quests.env.pending('ruins'))
 end
end)
case('ruins mismatched callback after battle start never confirms or retries',function()
 for _,reply in ipairs({{code=1,id=1},{code=0,id=0}}) do
  freshQuest();local w=startQ('ruins',1);bc:scInitFightStart({combat_type=77,current_wave=1,total_wave=1});local n=#sent
  receive(13105,reply);assert(w.execute_request_list[1].local_result=='uncertain' and ext.quests.env.pending('ruins'))
  for i=n+1,#sent do assert(sent[i].id~=13105) end
 end
end)
case('ruins combat55 and late battle notifications cannot alter owned verification',function()
 freshQuest();local w=startQ('ruins',1);local b=ext.quests.active.base
 local phase=ext.quests.active.phase;local deadline=ext.quests.active.deadline
 bc:scInitFightStart({combat_type=55});bc:scReBattleFight({combat_type=55});bc:scFightEnd({combat_type=55,result=1,show_panel_type=1})
 assert(ext.quests.active.phase==phase and ext.quests.active.deadline==deadline and not ext.quests.active.battle_started)
 receive(13105,{code=1,id=0});receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
 assert(ext.quests.active.phase=='verify');bc:scInitFightStart({combat_type=77});bc:scFightEnd({combat_type=77,result=1,show_panel_type=1})
 assert(ext.quests.active.phase=='verify');ext.quests:cancel()
end)
case('ruins remaining rewards alone cannot clear unknown settlement counters period or diamonds',function()
 for _,mode in ipairs({'remaining','period','diamonds','loss_hp'}) do
  freshQuest();local w=startQ('ruins',2);local b=ext.quests.active.base;receive(13105,{code=1,id=0})
  receive(13106,{result=mode=='loss_hp' and 2 or 1,is_self=1,combat_type=77,hp_per=8000})
  local d=rbase(mode=='remaining' and 2 or mode=='loss_hp' and 2 or 1,{end_time=b.end_time,boss_id=b.boss_id,hp_per=mode=='loss_hp' and 9000 or 10000})
  if mode=='period' then d.end_time=b.end_time+1 elseif mode=='diamonds' then stocks[3]=999 end
  local n=#sent;receive(13100,d);assert(ext.quests.active.phase=='verify' and ext.quests.env.pending('ruins'))
  now=now+21;ext.quests:tick();assert(w.execute_request_list[1].local_result=='uncertain' and ext.quests.env.pending('ruins'))
  for i=n+1,#sent do assert(sent[i].id~=13105) end
 end
end)
case('ruins zero quota closed feature expired boss and manual battle skip without consumption',function()
 freshQuest();local w=startQ('ruins',0);assert(w.execute_request_list[1].local_reason=='daily_target_done')
 freshQuest();opens=false;w=qtask('ruins');local n=#sent;w:requestTask();assert(w.execute_request_list[1].local_reason=='not_open')
 for i=n+1,#sent do assert(sent[i].id~=13105 and sent[i].id~=11211) end
 freshQuest();w=startQ('ruins');receive(13100,rbase(2,{end_time=now}));assert(w.execute_request_list[1].local_reason=='invalid_ruins_state' and not ext.quests.env.pending('ruins'))
 freshQuest();fight=true;fight_type=23;w=qtask('ruins');n=#sent;w:requestTask();assert(w.execute_request_list[1].local_reason=='battle_busy')
 for i=n+1,#sent do assert(sent[i].id~=13105) end
end)
case('real untouched ruins boss with hp_per zero and remaining rewards is challenged',function()
 freshQuest();now=1791714000;local w=startQ('ruins');local n=#sent
 receive(13100,{boss_id=11315,kill_time=2,hp_per=0,fight_time=0,end_time=1791789774})
 assert(sent[#sent].id==13105 and sent[#sent].data.id==0 and not w.execute_request_list[1].local_result and ext.quests.env.pending('ruins'))
 assert(#sent==n+1);ext.quests:cancel()
end)
case('fully depleted ruins boss at hp_per10000 skips while damaged bosses below10000 can challenge',function()
 for _,hp in ipairs({10000,8000,9999}) do
  freshQuest();local w=startQ('ruins');local n=#sent;receive(13100,rbase(2,{hp_per=hp}))
  if hp==10000 then
   assert(w.execute_request_list[1].local_result=='skipped' and w.execute_request_list[1].local_reason=='ruins_boss_defeated' and not ext.quests.env.pending('ruins'))
   for i=n+1,#sent do assert(sent[i].id~=13105) end
  else assert(sent[#sent].id==13105 and ext.quests.env.pending('ruins'));ext.quests:cancel() end
 end
end)
case('owned ruins queue blocks manual challenge refresh rewards formation and native skip',function()
 freshQuest();startQ('ruins',1);local n=#sent
 rc:reqChallenge(0);rc:reqRefreshBoss();rc:reqShareBoss();rc:reqDailyReward(1,1);rc:reqStarReward(1);hc:sender11212(92,{},0);bc:send20062();gc:send13548(1)
 assert(#sent==n);ext.quests:cancel()
end)

case('server background victory rotates boss and expiry then continues remaining reward once',function()
 freshQuest();now=1791715275;stocks[3]=94178
 local w=startQ('ruins');receive(13100,{boss_id=11315,kill_time=2,hp_per=0,fight_time=0,end_time=1791789774})
 receive(13105,{code=1,id=0});now=now+2
 receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
 receive(13100,{boss_id=11201,kill_time=1,hp_per=0,fight_time=1,end_time=1791801676})
 assert(not ext.quests.env.pending('ruins') and ext.quests.active.phase=='cleanup')
 ext.quests:tick();ext.quests:tick();local n=#sent
 receive(13100,{boss_id=11201,kill_time=1,hp_per=0,fight_time=1,end_time=1791801676})
 assert(#sent==n+1 and sent[#sent].id==13105 and ext.quests.env.pending('ruins'))
 receive(13105,{code=1,id=0});now=now+2;receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
 receive(13100,{boss_id=11315,kill_time=0,hp_per=0,fight_time=2,end_time=1791802676})
 ext.quests:tick();ext.quests:tick();receive(13100,{boss_id=11315,kill_time=0,hp_per=0,fight_time=2,end_time=1791802676})
 assert(w.execute_request_list[1].local_result=='confirmed' and not ext.quests.env.pending('ruins'))
end)
case('random replacement may redraw the same boss with updated valid expiry',function()
 freshQuest();local w=startQ('ruins',1);local b=ext.quests.active.base
 receive(13105,{code=1,id=0});receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
 receive(13100,{boss_id=b.boss_id,kill_time=0,hp_per=0,fight_time=1,end_time=b.end_time+1000})
 assert(not ext.quests.env.pending('ruins') and ext.quests.active.phase=='cleanup');ext.quests:cancel()
end)
case('rotated victory requires exact fight reward inventory and valid full-health replacement',function()
 for _,mode in ipairs({'fight','kill','hp','boss','diamond','expired'}) do
  freshQuest();now=1791715275;stocks[3]=94178;local w=startQ('ruins')
  receive(13100,{boss_id=11315,kill_time=2,hp_per=0,fight_time=0,end_time=1791789774})
  receive(13105,{code=1,id=0});receive(13106,{result=1,is_self=1,combat_type=77,hp_per=10000})
  local d={boss_id=11201,kill_time=1,hp_per=0,fight_time=1,end_time=1791801676}
  if mode=='fight' then d.fight_time=2 elseif mode=='kill' then d.kill_time=0 elseif mode=='hp' then d.hp_per=1
  elseif mode=='boss' then d.boss_id=0 elseif mode=='diamond' then stocks[3]=94177
  elseif mode=='expired' then d.end_time=now end
  local n=#sent;receive(13100,d);assert(ext.quests.env.pending('ruins'))
  if ext.quests.active then now=now+21;ext.quests:tick() end
  assert(w.execute_request_list[1].local_result=='uncertain')
  for i=n+1,#sent do assert(sent[i].id~=13105) end
 end
end)
local recovery_token='phase11v2-win|yinghe_3356:5005|1791666000|1791715275|7789ef7f68b74ad86e950d09ce36b9a3649e82f36872d948f2743c3346d66dcb|13105:1:0|13106:1791715277:1:1:77|before:11315:2:1791789774:0:94178|after:11201:1:1791801676:1:0:94178'
function recoveryFixture(mode,action)
 freshQuest();role={rid=5005,srv_id='yinghe_3356',gid=10,gsrv_id='guild'};now=1791715400;stocks[3]=94178
 local old_day=TimeTool.getDayAnyHourTime;TimeTool.getDayAnyHourTime=function() return 1791666000 end
 local original_key='dldl_quests_v1:yinghe_3356:5005:ruins'
 local vals={pending=1,day=1791666000,sent_at=1791715275,before_boss_id=11315,before_kill_time=2,
  before_end_time=1791789774,before_fight_time=0,before_diamonds=94178}
 for k,v in pairs(vals) do ud:setIntegerForKey(original_key..':'..k,v) end
 local old_fu,old_open,old_remove=cc.FileUtils,io.open,os.remove
 local token=mode=='token' and 'wrong' or recovery_token;local removed=false;local output={}
 cc.FileUtils={getInstance=function() return {getWritablePath=function() return '/mock/' end} end}
 io.open=function(path,access)
  if access=='r' then assert(path=='/mock/dldl_ruins_v2_reconcile.request');if removed then return nil end;return {read=function() return token end,close=function() end} end
  return {write=function(self,...) for _,v in ipairs({...}) do output[#output+1]=tostring(v) end end,close=function() end}
 end
 os.remove=function(path) assert(path=='/mock/dldl_ruins_v2_reconcile.request');removed=true end
 if mode=='role' then role.rid=5006;for k,v in pairs(vals) do ud:setIntegerForKey('dldl_quests_v1:yinghe_3356:5006:ruins:'..k,v) end
 elseif mode=='day' then TimeTool.getDayAnyHourTime=function() return 1791579600 end
 elseif vals[mode]~=nil then ud:setIntegerForKey(original_key..':'..mode,vals[mode]+1)
 elseif mode=='guild' then ud:setIntegerForKey('dldl_quests_v1:yinghe_3356:5005:guild_wish:pending',1)
 elseif mode=='battle' then fight=true;fight_type=23 elseif mode=='replay' then replay=true end
 local n=#sent;local w=qtask('ruins');w:requestTask()
 local data={boss_id=11201,kill_time=1,hp_per=0,fight_time=1,end_time=1791801676}
 if action then action(w,data,n) end
 local pending=ud:getIntegerForKey(original_key..':pending',0)
 for i=n+1,#sent do assert(sent[i].id==13100 or sent[i].id==31604,'recovery must only read13100') end
 local confirmed=w.execute_request_list[1].local_reason=='ruins_v2_rotation_reconciled'
 assert(confirmed==removed and pending==(confirmed and 0 or mode=='pending' and 2 or 1))
 if ext.quests.active then ext.quests:cancel() end
 io.open=old_open;cc.FileUtils=old_fu;os.remove=old_remove;TimeTool.getDayAnyHourTime=old_day
 return w,table.concat(output)
end
case('exact audited pending recovers only after two separate read-only rounds and stops immediately',function()
 local w,audit=recoveryFixture('valid',function(w,d,n)
  assert(sent[#sent].id==13100 and ext.quests.active.phase=='recovery_verify')
  receive(13100,d);receive(13100,d);assert(ext.quests.env.pending('ruins'))
  now=now+1;ext.quests:tick();receive(13100,d);assert(ext.quests.env.pending('ruins'))
  now=now+1;receive(13100,d);assert(ext.quests.env.pending('ruins'))
  ext.quests:tick();assert(sent[#sent].id==13100);receive(13100,d)
  assert(w.is_execute_finish and w.execute_request_list[1].local_result=='confirmed' and not ext.quests.active)
 end)
 assert(audit:find('ruins_v2_rotation_reconciled',1,true))
end)
case('recovery token role day every saved baseline other pending and busy battle are exact barriers',function()
 for _,mode in ipairs({'token','role','day','pending','sent_at','before_boss_id','before_kill_time','before_end_time','before_fight_time','before_diamonds','guild','battle','replay'}) do
  recoveryFixture(mode,function(w,d,n)
   assert(not ext.quests.active and w.execute_request_list[1].local_result~='confirmed')
   for i=n+1,#sent do assert(sent[i].id~=13100) end
  end)
 end
end)
case('recovery mismatched second state inventory or absent second response preserves pending',function()
 for _,mode in ipairs({'boss_id','kill_time','hp_per','fight_time','end_time','diamond','timeout','latepacket','rolechange','daychange'}) do
  recoveryFixture('valid',function(w,d,n)
   receive(13100,d);now=now+2;ext.quests:tick()
   if mode=='timeout' then now=now+21;ext.quests:tick()
   elseif mode=='latepacket' then now=now+21;receive(13100,d)
   elseif mode=='diamond' then stocks[3]=94177;receive(13100,d)
   elseif mode=='rolechange' then role.rid=5006;receive(13100,d)
   elseif mode=='daychange' then TimeTool.getDayAnyHourTime=function() return 1791752400 end;ext.quests:tick()
   else d[mode]=d[mode]+1;receive(13100,d) end
   assert(not ext.quests.active and w.execute_request_list[1].local_result~='confirmed')
  end)
 end
end)
ext.uninstall()
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
record={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls','real_code':'original ruins/hero/guild senders and handlers; protocol dispatch and recovered configs; rendering/inventories mocked'}
(ROOT/'evidence/phase11v3_quests_tests.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(record,ensure_ascii=False,indent=2))
