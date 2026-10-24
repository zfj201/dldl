#!/usr/bin/env python3
"""Once-daily background challenges and the exact free workshop gift, offline integration."""
import contextlib,io,json,os,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('DLDL_TEST_PHASE','phase16')
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
runpy.run_path(str(ROOT/'tests/fixtures_daily_extras.py'))['setup'](lua,original)
for var,name in [('Extras','daily_extras.lua'),('GameExtras','daily_extras_game.lua'),
                 ('Automation','helper_automation.lua'),('GameAutomation','helper_automation_game.lua')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/name).read_text())
lua.execute('''
freshExtra()
local before=#sent
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
case('seventeen optional rows install without requests; three new defaults off',function()
 assert(#ext.specs==17 and #sent==before)
 for i=15,17 do assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[i].row).is_open==0) end
end)
case('two accepted challenges advance into free gift while both battles still run',function()
 freshExtra()
 local w=window({{type=1,pos=-2101786,args={}},{type=1,pos=-2101785,args={}},{type=1,pos=-2101784,args={}},{type=1,pos=999,args={}}})
 local first=#sent;w:requestTask()
 receive(11211,{type=65,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29720,guildBase());assert(sent[#sent].id==29721)
 background[38]={};receive(29721,{code=1})
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='challenge_started')
 w:requestTask();receive(11211,{type=122,formation_type=1,pos_info={{pos=1,id=2}}})
 templeBase();assert(sent[#sent].id==28702)
 background[86]={};receive(28702,{code=1})
 assert(w.execute_index==3 and w.execute_request_list[2].local_reason=='challenge_started')
 w:requestTask();receive(10572,shopBase());assert(sent[#sent].id==10573)
 local d=sent[#sent].data;assert(d.type==2 and d.bid==0 and d.gift_id==2301 and d.num==1)
 receive(10573,{code=1,type=2,bid=0,id=23,gift_id=2301,buy_num=1})
 assert(w.execute_index==3);receive(10572,shopBase(1));assert(w.execute_index==4,tostring(w.execute_index)..'|'..tostring(w.execute_request_list[3].local_reason)..'|'..tostring(ext.extras.active and ext.extras.active.phase))
 local mutations={[29721]=0,[28702]=0,[10573]=0}
 local allowed={[11211]=true,[29720]=true,[29721]=true,[28700]=true,[28701]=true,[28703]=true,[28702]=true,[10572]=true,[10573]=true}
 for i=first+1,#sent do assert(allowed[sent[i].id],'skip, paid or settlement request');if mutations[sent[i].id] then mutations[sent[i].id]=mutations[sent[i].id]+1 end end
 for _,n in pairs(mutations) do assert(n==1) end
 local n=#sent
 for _,k in ipairs({'guild_trial','temple_duel','workshop_gift'}) do local q=extraTask(k);q:requestTask();assert(q.execute_request_list[1].local_reason=='daily_target_done') end
 assert(#sent==n and background[38] and background[86])
end)
case('manual challenges already performed today do not launch again',function()
 freshExtra();local w=startExtra('guild_trial');local n=#sent;receive(29720,guildBase(1))
 assert(#sent==n and w.execute_request_list[1].local_reason=='daily_target_done')
 freshExtra();w=startExtra('temple_duel');templeBase(1)
 assert(w.execute_request_list[1].local_reason=='daily_target_done' and sent[#sent].id~=28702)
end)
case('no guild or closed event sends no mutation',function()
 freshExtra();role.gid=0;local n=#sent;local w=startExtra('guild_trial');assert(#sent==n and w.execute_request_list[1].local_reason=='no_guild')
 freshExtra();w=startExtra('temple_duel');receive(28703,{day_num=2,first_reward={}});receive(28700,{status=2})
 assert(w.execute_request_list[1].local_reason=='not_open')
end)
case('same combat type and replay block, other background type allowed',function()
 for _,k in ipairs({'guild_trial','temple_duel'}) do
  freshExtra();background[k=='guild_trial' and 38 or 86]={};local n=#sent
  local w=startExtra(k);assert(#sent==n and w.execute_request_list[1].local_reason=='battle_busy')
 end
 freshExtra();replay=true;local w=startExtra('temple_duel');assert(w.execute_request_list[1].local_reason=='battle_busy')
end)
case('empty or mismatched formation cannot launch either challenge',function()
 for _,k in ipairs({'guild_trial','temple_duel'}) do
  freshExtra();local w=extraTask(k);w:requestTask();local n=#sent
  receive(11211,{type=k=='guild_trial' and 122 or 65,formation_type=1,pos_info={{pos=1,id=2}}});assert(#sent==n)
  receive(11211,{type=k=='guild_trial' and 65 or 122,formation_type=1,pos_info={}})
  assert(w.execute_request_list[1].local_reason=='empty_quest_formation' and #sent==n)
 end
end)
case('lost challenge acceptance remains pending across repeats and remount',function()
 for _,k in ipairs({'guild_trial','temple_duel'}) do
  freshExtra();local w=startExtra(k)
  if k=='guild_trial' then receive(29720,guildBase()) else templeBase() end
  now=now+21;ext.extras:tick();assert(w.execute_request_list[1].local_result=='uncertain')
  ext.uninstall();ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
  local n=#sent;local q=startExtra(k);assert(#sent==n and q.execute_request_list[1].local_reason=='previous_request_unresolved')
 end
end)
case('rejected challenge does not count as completion or retry',function()
 for _,k in ipairs({'guild_trial','temple_duel'}) do
  freshExtra();local w=startExtra(k)
  if k=='guild_trial' then receive(29720,guildBase());receive(29721,{code=0}) else templeBase();receive(28702,{code=0}) end
  assert(w.execute_request_list[1].local_result=='uncertain')
  local n=#sent;w=startExtra(k);assert(#sent==n and w.execute_request_list[1].local_reason=='previous_request_unresolved')
 end
end)
case('invalid daily counts never fall back to paid or rewardless challenges',function()
 for _,v in ipairs({-1,3,0.5}) do
  freshExtra();local w=startExtra('temple_duel');templeBase(v)
  assert(w.execute_request_list[1].local_result=='error' and sent[#sent].id~=28702)
 end
 freshExtra();local w=startExtra('guild_trial');local d=guildBase();d.boss_id=0;receive(29720,d)
 assert(w.execute_request_list[1].local_result=='error' and sent[#sent].id~=29721)
end)
case('free gift already claimed never buys another gift',function()
 freshExtra();local w=startExtra('workshop_gift');local n=#sent;receive(10572,shopBase(1))
 assert(#sent==n and w.execute_request_list[1].local_reason=='already_claimed')
end)
case('connection loss between query and mutation sends no business request',function()
 freshExtra();local w=startExtra('workshop_gift');connected=false;local n=#sent
 receive(10572,shopBase());assert(sent[#sent].id~=10573 and #sent==n)
 assert(w.execute_request_list[1].local_reason=='connection_unavailable');connected=true
end)
case('free config exact rewards price type and daily limit are required',function()
 local c=CommonGiftData.data_shop[23][2301]
 for _,f in ipairs({'gift_type','charge_id','charge_acc','activity','limit_type','limit_times'}) do
  freshExtra();local old=c[f];c[f]=99;local n=#sent;local w=startExtra('workshop_gift')
  assert(#sent==n and w.execute_request_list[1].local_reason=='gift_config_changed');c[f]=old
 end
 for _,f in ipairs({'cost','reward','limit_cond'}) do
  freshExtra();local old=c[f];c[f]={{3,1}};local n=#sent;local w=startExtra('workshop_gift')
  assert(#sent==n and w.execute_request_list[1].local_reason=='gift_config_changed');c[f]=old
 end
end)
case('foreign shop replies and unverified gift state cannot complete or resend',function()
 freshExtra();local w=startExtra('workshop_gift');local d=shopBase();d.bid=123;local n=#sent
 receive(10572,d);assert(#sent==n)
 receive(10572,shopBase());receive(10573,{code=1,type=2,bid=0,id=23,gift_id=2301,buy_num=1})
 local after=#sent;receive(10572,shopBase());assert(w.execute_index==1 and #sent==after)
 now=now+21;ext.extras:tick();assert(w.execute_request_list[1].local_result=='uncertain')
 local q=startExtra('workshop_gift');assert(q.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('close while awaiting acceptance keeps pending and ignores late callback',function()
 freshExtra();local w=startExtra('temple_duel');templeBase();w:close_callback()
 receive(28702,{code=1});assert(not ext.extras.active)
 local n=#sent;local q=startExtra('temple_duel');assert(#sent==n and q.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('day rollover cancels old callback and retains unknown request',function()
 freshExtra();local w=startExtra('guild_trial');receive(29720,guildBase());now=now+86400
 receive(29721,{code=1});assert(w.execute_request_list[1].local_result=='cancelled')
 local n=#sent;local q=startExtra('guild_trial');assert(#sent==n and q.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('manual mutation during own queue is blocked and recent manual operation isolates task',function()
 freshExtra();local w=startExtra('workshop_gift');local n=#sent;sg:send10573(2,0,2301,1);assert(#sent==n)
 ext.extras:cancel();freshExtra();sg:send10573(2,0,2301,1);n=#sent
 w=startExtra('workshop_gift');assert(#sent==n and w.execute_request_list[1].local_reason=='manual_claim_pending')
 now=now+16
end)
function deferredQueue()
 freshExtra()
 local w=window({{type=1,pos=-2101786,args={}},{type=1,pos=-2101785,args={}},{type=1,pos=-2101784,args={}}})
 w.removeOneTimeTicket=function() end
 w:requestTask();receive(11211,{type=65,formation_type=1,pos_info={{pos=1,id=2}}})
 receive(29720,guildBase());background[38]={};receive(29721,{code=1})
 w:requestTask();receive(11211,{type=122,formation_type=1,pos_info={{pos=1,id=2}}});templeBase()
 receive(28702,{code=0})
 assert(w.execute_index==3 and w.execute_request_list[2].local_result=='deferred' and ext.extras:hasDeferred())
 return w
end
case('explicit busy rejection defers only own second battle, gift runs before retry',function()
 local w=deferredQueue();local n=#sent;ext.extras:pollDeferred();assert(#sent==n)
 w:requestTask();receive(10572,shopBase());receive(10573,{code=1,type=2,bid=0,id=23,gift_id=2301,buy_num=1});receive(10572,shopBase(1))
 assert(w.is_execute_finish and w.execute_request_list[3].local_result=='confirmed' and ext.extras:hasDeferred())
 DLDL_DAILY_GIFTS=ext;oc.onekeyburden_auto_window=w
 local automation=GameAutomation.bind(Automation)
 assert(not automation.env.snapshot().finished,'automatic close must wait for deferred initiation')
 background[38]=nil;ext.extras:pollDeferred();assert(sent[#sent].id==11211)
 receive(11211,{type=122,formation_type=1,pos_info={{pos=1,id=2}}});templeBase()
 assert(sent[#sent].id==28702);background[86]={};receive(28702,{code=1})
 assert(w.execute_index==3 and w.execute_request_list[2].local_reason=='challenge_started')
 assert(not ext.extras:hasDeferred() and automation.env.snapshot().finished and background[86])
 oc.onekeyburden_auto_window=nil;DLDL_DAILY_GIFTS=nil
end)
case('deferred retry verifies new quota and never launches if manually completed meanwhile',function()
 local w=deferredQueue();background[38]=nil;ext.extras:pollDeferred()
 receive(11211,{type=122,formation_type=1,pos_info={{pos=1,id=2}}});local n=#sent;templeBase(1)
 assert(sent[#sent].id~=28702 and w.execute_request_list[2].local_reason=='daily_target_done' and not ext.extras:hasDeferred())
 assert(not ext.extras.env.pending('temple_duel'))
end)
case('deferred close timeout and role change never issue a retry',function()
 for _,mode in ipairs({'close','timeout','role'}) do
  local w=deferredQueue();local n=#sent
  if mode=='close' then w:close_callback()
  elseif mode=='timeout' then now=now+181;ext.extras:pollDeferred()
  else role={rid=role.rid+1,srv_id=role.srv_id};ext.extras:pollDeferred() end
  assert(not ext.extras:hasDeferred())
  if mode~='close' then assert(#sent==n) end
 end
end)
case('deferred background query has a bounded timeout and failed retry is never retried twice',function()
 local w=deferredQueue();background[38]=nil;ext.extras:pollDeferred();now=now+21;ext.extras:pollDeferred()
 assert(not ext.extras:hasDeferred() and w.execute_request_list[2].local_result=='error')
 w=deferredQueue();background[38]=nil;ext.extras:pollDeferred()
 receive(11211,{type=122,formation_type=1,pos_info={{pos=1,id=2}}});templeBase();receive(28702,{code=0})
 local n=#sent;ext.extras:pollDeferred();assert(#sent==n and not ext.extras:hasDeferred())
 assert(w.execute_request_list[2].local_result=='uncertain')
end)
case('missing acceptance or unrelated manual combat never authorizes deferred retry',function()
 freshExtra();background[38]={};local w=startExtra('temple_duel');templeBase();receive(28702,{code=0})
 assert(not ext.extras:hasDeferred() and w.execute_request_list[1].local_result=='uncertain')
 freshExtra();local a=startExtra('guild_trial');receive(29720,guildBase());background[38]={};receive(29721,{code=1})
 w=startExtra('temple_duel');templeBase();now=now+21;ext.extras:tick()
 assert(not ext.extras:hasDeferred() and w.execute_request_list[1].local_result=='uncertain')
end)
ext.uninstall()
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
record={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls',
        'contracts':'Recovered challenge/shop senders, registered handlers, callback-only 28702 and exact gift configuration.'}
(ROOT/'evidence/phase16_extras_tests.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False,indent=2))
