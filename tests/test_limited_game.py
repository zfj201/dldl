#!/usr/bin/env python3
"""Recovered native senders plus local category, settings, queue and ownership."""
import contextlib,io,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()): ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for f in ['daily_extras','voyage','limited']:
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+f+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Voyage','voyage_automation'),('GameVoyage','voyage_automation_game'),('Limited','limited_automation'),('GameLimited','limited_automation_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute(r'''
freshQuest();role.lev=200
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
GameVoyage.bind(Voyage,ext);local n=#sent;GameLimited.bind(Limited,ext)
local t,p=ext.limited.type,ext.limited.pos
local key='dldl_sanpao_v1:'..role.srv_id..':'..role.rid
assert(#sent==n and OneKeyBurdenMainWindow:getPosExecuteData(t,ext.limited.row).is_open==0)
local w=setmetatable({select_index=1,task_list={SimplifyData.data_list[t]},operate_list={[t]={}}},{__index=OneKeyBurdenMainWindow})
local d=w:getPosExecuteData(t,ext.limited.row);d.is_open=1;w.operate_list[t][p]=d
local q=w:saveOperateRequest(true);assert(#q==1 and q[1].type==t and q[1].pos==p)
assert(w:getPosExecuteData(t,ext.limited.row).is_open==1)
assert(not pcall(function() oc:sender31602(t,p) end))
n=#sent;oc:sender31609(1,t);oc:sender31604(t,1);assert(#sent==n and not oc:getModel():getTipsTypeRed(1,t))
local function task() local w=window({{type=t,pos=p,args={}},{type=1,pos=999,args={}}});w.removeOneTimeTicket=function() end;return w end
local function base()
 return {camp_id=100935,open_day=1,num=10,status=0,all_score=0,reward_list={},chapter_list={
 {chapter_id=1,status=1,is_pass=0,score=0},{chapter_id=2,status=0,is_pass=0,score=0},{chapter_id=3,status=0,is_pass=0,score=0},
 {chapter_id=4,status=0,is_pass=0,score=0},{chapter_id=5,status=0,is_pass=0,score=0}}}
end
local w=task();w:requestTask();assert(sent[#sent].id==16413)
receive(16413,base());assert(sent[#sent].id==16414)
n=#sent;limitedc:sender16415(1,1,20,3);assert(#sent==n,'manual settlement interfered with owned request')
receive(16414,{code=1});assert(sent[#sent].id==16413)
local b=base();b.status=1;b.num=9;receive(16413,b)
assert(sent[#sent].id==16415 and sent[#sent].data.chapter_id==1 and sent[#sent].data.is_pass==1 and sent[#sent].data.all_score==20 and sent[#sent].data.round==3)
receive(16415,{code=1,chapter_id=1,all_score=20,round=3,is_pass=1})
assert(not limitedc.result_shown,'automation opened native result overlay')
b.status=0;b.chapter_list[1].is_pass=1;b.chapter_list[1].score=20;b.all_score=20;receive(16413,b)
assert(sent[#sent].id==16416);receive(16416,{code=1});b.reward_list={{reward_id=1}};receive(16413,b)
assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='available_complete')
assert(w.execute_request_list[1].limited.claimed==1 and w.other_progress>0)
limitedc:openActionJfczResultWindow(true,{});assert(limitedc.result_shown,'manual result overlay suppressed')
limitedc.result_shown=nil
local w=task();w:requestTask();n=#sent;receive(16413,b)
assert(w.execute_index==2 and #sent==n,'repeat run spent another attempt')
-- Cancellation retains pending and does not dispatch a settlement.
w=task();w:requestTask();receive(16413,base());w:close_callback()
n=#sent;receive(16414,{code=1});assert(#sent==n and not ext.limited.runner.active)
assert(json.decode(ud:getStringForKey(key..':last','')).pending.kind=='start')
-- Preferences are per role/server; detach restores rows and wrappers.
local before=role.rid;role.rid=before+1
assert(OneKeyBurdenMainWindow:getPosExecuteData(t,ext.limited.row).is_open==0);role.rid=before
ext.detach();assert(not SimplifyData.data_list[t] and not OneKeyBurdenConst.SimplifyTypeList[t])
print('limited game: local settings, category isolation, queue advance, real senders, result ownership, repeat, cancellation, detach passed')
''')
