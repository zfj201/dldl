#!/usr/bin/env python3
"""Regression for explicit battle entry and expired daily journals in release code."""
import contextlib,io,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()): ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua']
build=runpy.run_path(str(ROOT/'lsposed-module/scripts/build-payload.py'))
for var,name in [('Quests','daily_quests.lua'),('GameQuests','daily_quests_game.lua')]:
    lua.globals()[var]=lua.execute(build['release_source'](name,(ROOT/'modules'/name).read_text()))
lua.execute(r'''
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests)
local ncase=0
local function test(name,fn) fn();ncase=ncase+1;print('PASS '..name) end
local function reset()
 if ext.quests.active then ext.quests:cancel() end
 freshQuest();now=2000000000;autoQuestEnter=false
end
local function key() return 'dldl_quests_v1:'..role.srv_id..':'..role.rid..':ruins' end
local function pending(field,value) ud:setIntegerForKey(key()..':'..field,value) end
local function markOld()
 local d=ext.quests.env.day()-86400
 pending('pending',1);pending('day',d);pending('sent_at',d+100);pending('before_end_time',now-100)
end
local function current(quota,extra) local d=rbase(quota or 0,{status=0});for k,v in pairs(extra or {}) do d[k]=v end;return d end
local function countSince(n,id) local c=0;for i=n+1,#sent do if sent[i].id==id then c=c+1 end end;return c end
local function prepared()
 local w=startQ('ruins');receive(13100,current(2));assert(ext.quests.active.phase=='enter');return w
end
test('challenge requires own successful entry and a fresh base response',function()
 reset();local w=prepared();local n=#sent
 assert(MainuiController:getUIFightType()==77 and sent[n].id==20060 and not ext.quests.env.pending('ruins'))
 receive(20060,{combat_type=82,type=0});assert(#sent==n and ext.quests.active.phase=='enter')
 receive(20060,{combat_type=77,type=0});assert(sent[#sent].id==13100 and not ext.quests.env.pending('ruins'))
 receive(13100,current(1));assert(sent[#sent].id==13105 and ext.quests.env.pending('ruins'))
 local last=#sent;ext.quests:cancel();assert(MainuiController:getUIFightType()==1 and sent[last+1].id==20060 and sent[last+1].data.combat_type==0)
end)
test('busy entry never challenges and restores previous UI',function()
 reset();local w=prepared();local n=#sent;receive(20060,{combat_type=77,type=1})
 assert(w.execute_request_list[1].local_reason=='battle_busy' and countSince(n,13105)==0 and MainuiController:getUIFightType()==1)
end)
test('entry timeout is retryable and leaves no consumption journal',function()
 reset();local w=prepared();local n=#sent;now=now+21;ext.quests:tick()
 assert(w.execute_request_list[1].local_reason=='enter_timeout' and not ext.quests.env.pending('ruins') and countSince(n,13105)==0)
end)
test('foreign view change stops without overwriting the new view',function()
 reset();local w=prepared();MainuiController:setUIFightType(82);local n=#sent;ext.quests:tick()
 assert(w.execute_request_list[1].local_reason=='battle_view_changed' and countSince(n,20060)==0 and MainuiController:getUIFightType()==82)
end)
test('empty quota stops before battle entry',function()
 reset();local w=startQ('ruins');local n=#sent;receive(13100,current(0))
 assert(w.execute_request_list[1].local_reason=='daily_target_done' and countSince(n,20060)==0 and countSince(n,13105)==0)
end)
test('expired prior-day record needs two separate stable read rounds',function()
 reset();markOld();local w=qtask('ruins');local n=#sent;w:requestTask();assert(sent[#sent].id==13100)
 local b=current(0);receive(13100,b);receive(13100,b);assert(ext.quests.env.pending('ruins'))
 now=now+2;ext.quests:tick();assert(countSince(n,13100)==2);receive(13100,b)
 assert(not ext.quests.env.pending('ruins') and w.execute_request_list[1].local_reason=='daily_target_done')
 assert(countSince(n,13105)==0 and countSince(n,20060)==0)
end)
test('expired record with quota resumes normal formation and guarded entry',function()
 reset();markOld();local w=qtask('ruins');w:requestTask();local b=current(2);receive(13100,b);now=now+2;ext.quests:tick();receive(13100,b)
 assert(sent[#sent].id==11211 and not ext.quests.env.pending('ruins'))
 receive(11211,{type=92,formation_type=1,pos_info={{pos=1,id=2}}});receive(13100,b);assert(sent[#sent].id==20060)
end)
test('same-day, invalid, future and unexpired journals remain protected',function()
 for _,mode in ipairs({'same_day','future','missing','unexpired','bad_sent'}) do
  reset();markOld()
  if mode=='same_day' then pending('day',ext.quests.env.day());pending('sent_at',now-1000)
  elseif mode=='future' then pending('day',ext.quests.env.day()+86400)
  elseif mode=='missing' then pending('sent_at',-1)
  elseif mode=='unexpired' then pending('before_end_time',now+1)
  else pending('sent_at',ext.quests.env.day()+1) end
  local w=qtask('ruins');local n=#sent;w:requestTask()
  assert(w.execute_request_list[1].local_reason=='previous_request_unresolved' and ext.quests.env.pending('ruins') and countSince(n,13100)==0 and countSince(n,13105)==0,mode)
 end
end)
test('current fight or server active battle prevents stale recovery',function()
 reset();markOld();fight=true;fight_type=77;local w=qtask('ruins');w:requestTask();assert(ext.quests.env.pending('ruins') and w.execute_request_list[1].local_reason=='battle_busy')
 reset();markOld();w=qtask('ruins');w:requestTask();receive(13100,current(0,{status=1}));assert(ext.quests.env.pending('ruins') and w.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
test('changed, missing and timed out reconciliation never clears pending',function()
 for _,mode in ipairs({'changed','missing_status','timeout'}) do
  reset();markOld();local w=qtask('ruins');w:requestTask();local b=current(2)
  if mode=='missing_status' then b.status=nil;receive(13100,b)
  else receive(13100,b);now=now+2;ext.quests:tick()
   if mode=='changed' then b.fight_time=b.fight_time+1;receive(13100,b) else now=now+21;ext.quests:tick() end
  end
  assert(ext.quests.env.pending('ruins') and w.execute_request_list[1].local_result=='uncertain',mode)
 end
end)
test('recovery disconnect and role changes retain original journal',function()
 for _,mode in ipairs({'disconnect','role'}) do
  reset();markOld();local oldKey=key();local w=qtask('ruins');w:requestTask();receive(13100,current(0))
  if mode=='disconnect' then connected=false else role.rid=role.rid+1 end
  ext.quests:tick();assert(ud:getIntegerForKey(oldKey..':pending',0)==1 and not ext.quests.active)
 end
end)
test('guild journal never uses ruins rollover recovery',function()
 reset();markOld();ud:setIntegerForKey('dldl_quests_v1:'..role.srv_id..':'..role.rid..':guild_wish:pending',1)
 local w=qtask('guild_wish');local n=#sent;w:requestTask();assert(w.execute_request_list[1].local_reason=='previous_request_unresolved' and countSince(n,13518)==0)
end)
print(ncase..' release ruins regressions passed')
''')
