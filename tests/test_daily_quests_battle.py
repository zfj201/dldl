#!/usr/bin/env python3
"""Pure phase11v3 ruins battle and settlement state-machine tests."""
import json
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
lua=LuaRuntime(unpack_returned_tuples=True)
lua.globals()['Quests']=lua.execute((ROOT/'modules/daily_quests.lua').read_text())
lua.execute(r'''
passed={}
function case(n,f) f();passed[#passed+1]=n end
function fixture()
 local e={t=100,id='srv:1',sent={},pending=false,base={kill_time=2,boss_id=7,hp_per=0,fight_time=0,end_time=9999}}
 e.env={identity=function() return e.id end,day=function() return 1 end,now=function() return e.t end,log=function() end,
  pending=function() return e.pending end,openGuard=function() end,battleReady=function() return true end,
  guildScope=function() return true end,diamonds=function() return 500 end,ruinsBoss=function() return true end,
  checkForm=function() end,savePending=function(k,p,a) e.pending=p end,
  query=function(k) e.sent[#e.sent+1]='query:'..k end,guard=function() end,
  nativeSkip=function(a) if not a.skip_sent then e.skips=(e.skips or 0)+1;a.skip_sent=true end end,
  act=function(a) e.sent[#e.sent+1]=a end}
 e.r=Quests.new(e.env);e.r:start('ruins',function(x) e.result=x end)
 e.r:onPacket(11211,{type=92,formation_type=1,pos_info={{pos=1,id=1}}})
 e.r:onPacket(13100,e.base)
 return e
end
case('battle start before acknowledgement preserves exact own challenge confirmation',function()
 local e=fixture();e.r:onBattleStart({combat_type=77,current_wave=1,total_wave=1});e.r:tick();e.r:tick();assert(e.skips==1 and e.pending)
 e.r:onPacket(13105,{code=1,id=0});assert(e.r.active.accepted and e.r.active.phase=='battle')
 e.r:onBattleEnd({combat_type=77,result=1,show_panel_type=1});assert(e.r.active.phase=='battle_result')
 e.r:onPacket(13106,{result=1,is_self=1,combat_type=77,hp_per=10000});assert(e.r.active.phase=='verify' and e.pending)
 e.r:onPacket(13100,{kill_time=1,boss_id=7,hp_per=0,fight_time=1,end_time=9999});assert(e.r.active.phase=='cleanup' and not e.pending)
end)
case('settlement before acknowledgement cannot clear pending until exact callback and state agree',function()
 local e=fixture();e.r:onBattleStart({combat_type=77});e.r:onBattleEnd({combat_type=77,result=1})
 e.r:onPacket(13106,{result=1,is_self=1,combat_type=77,hp_per=10000});assert(e.r.active.phase=='battle_result' and e.pending)
 e.r:onPacket(13100,{kill_time=1,boss_id=7,hp_per=0,fight_time=1,end_time=9999});assert(e.pending)
 e.r:onPacket(13105,{code=1,id=0});assert(e.r.active.phase=='verify' and e.pending)
 e.r:onPacket(13100,{kill_time=1,boss_id=7,hp_per=0,fight_time=1,end_time=9999});assert(not e.pending)
end)
case('reconnect resets ruins skip and unrelated combat notifications leave phase unchanged',function()
 local e=fixture();e.r:onPacket(13105,{code=1,id=0});local deadline=e.r.active.deadline
 e.r:onBattleStart({combat_type=55});e.r:onBattleEnd({combat_type=55,result=1});assert(e.r.active.phase=='battle' and e.r.active.deadline==deadline and not e.r.active.battle_started)
 e.r:onBattleStart({combat_type=77});e.r:tick();assert(e.skips==1)
 e.r:onBattleStart({combat_type=77});assert(not e.r.active.skip_sent);e.r:tick();assert(e.skips==2)
end)
case('confirmed loss preserves rewards and stops its own task without a second challenge',function()
 local e=fixture();e.r:onPacket(13105,{code=1,id=0});e.r:onPacket(13106,{result=2,is_self=1,combat_type=77,hp_per=8000})
 e.r:onPacket(13100,{kill_time=2,boss_id=7,hp_per=8000,fight_time=1,end_time=9999});assert(not e.pending)
 local n=#e.sent;e.r:tick();assert(e.result.status=='skipped' and e.result.reason=='ruins_defeat' and #e.sent==n)
end)
case('missing final settlement retains journal and no remaining-count push can retry it',function()
 local e=fixture();e.r:onPacket(13105,{code=1,id=0});e.r:onBattleStart({combat_type=77});e.r:onBattleEnd({combat_type=77,result=1})
 local n=#e.sent;e.r:onPacket(13100,{kill_time=1,boss_id=7,hp_per=0,fight_time=1,end_time=9999});e.t=e.r.active.deadline;e.r:tick()
 assert(e.result.status=='uncertain' and e.pending and #e.sent==n)
 e.r:start('ruins',function(x) e.result=x end);assert(e.result.reason=='previous_request_unresolved' and e.pending and #e.sent==n)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
record={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls'}
(ROOT/'evidence/phase11v3_battle_tests.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps(record,ensure_ascii=False,indent=2))
