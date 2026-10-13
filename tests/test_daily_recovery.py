#!/usr/bin/env python3
"""Phase12 disconnected-session, isolated journals, server snapshots and UI regression."""
import os,runpy,json
from pathlib import Path
os.environ['DLDL_TEST_PHASE']='phase12'
ROOT=Path(__file__).resolve().parents[1]
ns=runpy.run_path(str(ROOT/'tests/test_daily_quests.py'))
lua=ns['lua']
lua.execute(r'''
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests)
function heroKey()
 local day=ext.training.env.day()
 return 'dldl_training_v1:'..role.srv_id..':'..role.rid..':'..day..':hero'
end
function baseHeroes(level)
 return {num=100,buy_num=0,partners={{partner_id=1,lev=level or 1,bid=21401,star=5,break_lev=0}}}
end
function noUpgradeSince(n)
 for i=n+1,#sent do assert(sent[i].id~=11003) end
end
case('disconnected full custom queue finishes without any query mutation or pending',function()
 freshQuest();connected=false;local rows={}
 for _,s in ipairs(ext.specs) do rows[#rows+1]={type=1,pos=s.pos,args={{args_key=s.kind=='arena_tickets' and 9021 or 9020,args_val=10}}} end
 local n=#sent;local w=window(rows)
 for i=1,#rows do w:requestTask() end
 assert(w.is_execute_finish)
 for _,r in ipairs(rows) do assert(r.local_reason=='connection_unavailable') end
 for i=n+1,#sent do assert(sent[i].id==31604) end
 assert(ud:getIntegerForKey(heroKey()..':pending',0)==0);connected=true
end)
case('cached level one cannot upgrade without current server base response',function()
 freshQuest();autoHeroDetails=false;local w=trainingTask('hero');local n=#sent;w:requestTask()
 assert(sent[#sent].id==11025 and ext.training.active.phase=='prepare')
 receive(11025,{num=100,buy_num=0,partners={{partner_id=2,lev=20,bid=21401,star=5,break_lev=0}}});ext.training:tick()
 assert(w.execute_request_list[1].local_reason=='no_eligible_target');noUpgradeSince(n)
 assert(ud:getIntegerForKey(heroKey()..':pending',0)==0)
end)
case('missing base response times out without pending and following gift still runs',function()
 freshQuest();autoHeroDetails=false
 local w=window({{type=1,pos=-2101793,args={}},{type=1,pos=-2101802,args={}}});local n=#sent;w:requestTask()
 now=now+16;ext.training:tick();assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='details_timeout')
 assert(ud:getIntegerForKey(heroKey()..':pending',0)==0);noUpgradeSince(n)
 w:requestTask();assert(sent[#sent].id==21017);receive(21017,info(1,1));assert(w.is_execute_finish)
end)
case('fresh level change and disconnection after base cannot write a mutation journal',function()
 for _,mode in ipairs({'level','disconnect'}) do
  freshQuest();autoHeroDetails=false;local w=trainingTask('hero');local n=#sent;w:requestTask()
  receive(11025,baseHeroes(mode=='level' and 6 or 1))
  if mode=='disconnect' then connected=false end
  ext.training:tick();noUpgradeSince(n)
  assert(w.execute_request_list[1].local_reason==(mode=='level' and 'no_eligible_target' or 'connection_unavailable'))
  assert(ud:getIntegerForKey(heroKey()..':pending',0)==0);connected=true
 end
end)
case('unresolved hero only protects itself and every unrelated module remains queryable',function()
 freshQuest();local key=heroKey();ud:setIntegerForKey(key..':pending',1)
 local ids={[-2101802]=21017,[-2101798]=13030,[-2101797]=13250,[-2101796]=21800,
  [-2101795]=23200,[-2101794]=11211,[-2101791]=11211,[-2101792]=10506,[-2101790]=13518,[-2101787]=11211}
 addBone()
 for _,s in ipairs(ext.specs) do
  if ids[s.pos] then
   local w=window({{type=1,pos=s.pos,args={{args_key=s.kind=='arena_tickets' and 9021 or 9020,args_val=10}}}})
   w:requestTask();assert(sent[#sent].id==ids[s.pos] and not w.execute_request_list[1].local_result)
   local runner=s.quest and ext.quests or s.training and ext.training or type(s.kind)=='number' and ext.runner or ext.actions
   runner:cancel()
  end
 end
 local n=#sent;local w=trainingTask('hero');w:requestTask()
 assert(w.execute_request_list[1].local_reason=='previous_request_unresolved');noUpgradeSince(n)
 assert(ud:getIntegerForKey(key..':pending',0)==1)
end)
case('new hero pending persists target and verifies completed level twice without resending',function()
 freshQuest();local w=trainingTask('hero');w:requestTask();local k=heroKey()
 assert(ud:getIntegerForKey(k..':before_partner_id',0)==1 and ud:getIntegerForKey(k..':before_level',0)==1)
 now=now+16;ext.training:tick();assert(w.execute_request_list[1].local_reason=='reply_timeout')
 local n=#sent;w=trainingTask('hero');w:requestTask();assert(ext.training.active.phase=='hero_recovery')
 receive(11025,baseHeroes(6));assert(ud:getIntegerForKey(k..':pending',0)==1)
 now=now+1;ext.training:tick();assert(ext.training.active.phase=='hero_recovery_wait')
 now=now+1;ext.training:tick();assert(sent[#sent].id==11025)
 receive(11025,baseHeroes(6));assert(w.execute_request_list[1].local_reason=='hero_recovered_completed')
 assert(ud:getIntegerForKey(k..':pending',1)==0 and ud:getIntegerForKey(k..':used',0)==1);noUpgradeSince(n)
end)
case('generic unknown level one missing target and conflicting snapshots retain own pending',function()
 for _,mode in ipairs({'one','missing','conflict','timeout','role'}) do
  freshQuest();local w=trainingTask('hero');w:requestTask();local k=heroKey();now=now+16;ext.training:tick()
  local n=#sent;w=trainingTask('hero');w:requestTask()
  if mode=='missing' then receive(11025,{num=100,buy_num=0,partners={}});now=now+16;ext.training:tick()
  elseif mode=='timeout' then now=now+16;ext.training:tick()
  elseif mode=='role' then role={rid=role.rid+1,srv_id=role.srv_id};ext.training:tick()
  else
   receive(11025,baseHeroes(mode=='one' and 1 or 6))
   if mode=='conflict' then now=now+2;ext.training:tick();receive(11025,baseHeroes(2)) end
  end
  assert(w.execute_request_list[1].local_result~='confirmed' and ud:getIntegerForKey(k..':pending',0)==1);noUpgradeSince(n)
 end
end)
case('audited old disconnected request requires exact sidecar and double unchanged snapshot',function()
 local old_open,old_fu,old_remove,old_day=io.open,cc.FileUtils,os.remove,TimeTool.getDayAnyHourTime
 local correct='phase11v3|bc73670fab9465e93957e6a11a9001c0ac2727f370d8a7e0b5e98685059eee32|yinghe_3356:5005|1791752400|1791779059|33794|1|reply_timeout'
 for _,mode in ipairs({'correct','wrong_token','wrong_role','changed','missing','daychange'}) do
  freshQuest();now=1791810000;role={rid=5005,srv_id='yinghe_3356',gid=10,gsrv_id='guild'}
  TimeTool.getDayAnyHourTime=function() return 1791752400 end
  heroList[33794]=deepCopy(heroList[1]);heroList[33794].partner_id=33794
  local k=heroKey();ud:setIntegerForKey(k..':pending',1);ud:setIntegerForKey(k..':used',0)
  for _,f in ipairs({'partner_id','bid','level','sent_at'}) do ud:setIntegerForKey(k..':before_'..f,0) end
  local removed=false
  cc.FileUtils={getInstance=function() return {getWritablePath=function() return '/mock/' end} end}
  io.open=function(path,access)
   if access=='r' then assert(path=='/mock/dldl_hero_reconcile.request');return {read=function() return mode=='wrong_token' and 'invalid' or correct end,close=function() end} end
   return {write=function() end,close=function() end}
  end
  os.remove=function(path) assert(path=='/mock/dldl_hero_reconcile.request');removed=true end
  if mode=='wrong_role' then role.rid=5006;ud:setIntegerForKey(heroKey()..':pending',1) end
  local n=#sent;local w=trainingTask('hero');w:requestTask()
  if mode~='wrong_token' and mode~='wrong_role' then
   local d={num=100,buy_num=0,partners={deepCopy(heroList[33794])}}
   if mode=='missing' then d.partners={} end
   receive(11025,d)
   if mode=='missing' then now=now+16;ext.training:tick()
   elseif mode=='daychange' then TimeTool.getDayAnyHourTime=function() return 1791838800 end;ext.training:tick()
   else now=now+2;ext.training:tick();if mode=='changed' then d.partners[1].lev=6 end;receive(11025,d) end
  end
  assert(removed==(mode=='correct'))
  assert(ud:getIntegerForKey(k..':pending',0)==(mode=='correct' and 0 or 1));noUpgradeSince(n)
  if mode=='correct' then assert(w.execute_request_list[1].local_reason=='hero_recovered_unchanged' and ud:getIntegerForKey(k..':used',1)==0) end
 end
 io.open,cc.FileUtils,os.remove,TimeTool.getDayAnyHourTime=old_open,old_fu,old_remove,old_day
end)
case('result rendering distinguishes pending disconnected timeout and already claimed',function()
 local strings={};doSetVisible=function() end
 local item=setmetatable({title_lb={setString=function() end},updateRewardList=function() end,
  un_finish_node={setVisible=function() end},un_finish_lb={setString=function(self,s) strings[#strings+1]=s end,setFontSize=function() end}}, {__index=OneKeyBurdenAutoItem})
 for reason,text in pairs({connection_unavailable='连接不可用',query_timeout='状态查询超时',previous_request_unresolved='上次结果待核实',already_claimed='礼包已领取'}) do
  item:setData({type=1,pos=-2101802,args={},local_result='error',local_reason=reason},1)
  assert(strings[#strings]:find(text,1,true) and strings[#strings]~='暂未执行')
 end
end)
ext.uninstall()
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
record={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls'}
(ROOT/'evidence/phase12_recovery_tests.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(record,ensure_ascii=False,indent=2))
