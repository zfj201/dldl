#!/usr/bin/env python3
"""Fishing/mail workflows against recovered controllers and real dispatcher, without device calls."""
import contextlib,io,json,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for f in ['daily_extras','voyage','mine','redbag','fishing_mail']:
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+f+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Voyage','voyage_automation'),
                 ('GameVoyage','voyage_automation_game'),('Fishing','fishing_automation'),('Mail','mail_automation'),('GameOther','other_automation_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute(r'''
freshOther()
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
GameVoyage.bind(Voyage,ext)
local before=#sent;GameOther.bind(Fishing,Mail,ext)
local firstCase=#passed
case('new rows bind without requests; defaults select medium and aquatic orders',function()
 assert(#sent==before)
 local rows=OneKeyBurdenConst.SimplifyTypeList[ext.voyage.type]
 assert(rows[2]==ext.mail.row and rows[3]==ext.fishing.row and rows[4]==ext.voyage.history)
 local d=OneKeyBurdenMainWindow:getPosExecuteData(ext.voyage.type,ext.fishing.row)
 assert(d.is_open==0 and d.args[1].args_str=='3|1')
 local t=Fishing.types(nil);assert(t[1] and t[3] and not t[2] and not t[4])
 t=Fishing.types('4|3|2|1');assert(t[1] and t[2] and t[3] and t[4]);assert(not next(Fishing.types('')))
 assert(Fishing.category({type=1,condition=10001},function() return {type=1} end)==1)
end)
case('settings persist locally and both tasks enter the queue without native IDs',function()
 local t=ext.voyage.type;local w=setmetatable({select_index=1,task_list={ext.voyage.category},operate_list={[t]={}}},{__index=OneKeyBurdenMainWindow})
 for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[t]) do
  local d=w:getPosExecuteData(t,r);d.is_open=(r.id==ext.fishing.pos or r.id==ext.mail.pos) and 1 or 0
  if r.id==ext.fishing.pos then d.args[1].args_str='1|2|3|4' end;w.operate_list[t][r.id]=d
 end
 local n=#sent;local q=w:saveOperateRequest(true);assert(#q==2 and q[1].pos==ext.mail.pos and q[2].pos==ext.fishing.pos and #sent==n)
 assert(w:getPosExecuteData(t,ext.fishing.row).args[1].args_str=='1|2|3|4' and q[2].args[1].args_str=='1|2|3|4')
 assert(not pcall(function() oc:sender31602(t,ext.fishing.pos) end))
end)
case('all unmatched orders refresh before any casting; identical reroll is valid',function()
 freshOther();local b=fishBase({10004,10002,10003});local w=otherTask('fishing');w:requestTask();fishQuery(b)
 assert(sent[#sent].id==12026 and sent[#sent].data.id==1)
 receive(12026,{code=1,free_quest_times=0});fishNext(b)
 assert(sent[#sent].id==12026 and ext.fishing.runner.active.refreshes==1)
 b.quest_list[1].order_id=10001;receive(12026,{code=1,free_quest_times=0});fishNext(b)
 assert(sent[#sent].id==12026 and sent[#sent].data.id==2)
 b.quest_list[2].order_id=10003;receive(12026,{code=1,free_quest_times=0});fishNext(b)
 assert(sent[#sent].id==12004 and w.execute_index==1 and w.other_progress==3)
 ext.fishing.runner:cancel()
end)
case('caught chest is opened via hook delivery; final three orders are claimed without extra cast',function()
 freshOther();local b=fishBase();local w=otherTask('fishing');w:requestTask();fishQuery(b)
 assert(sent[#sent].id==12004)
 local chest;for id,c in pairs(FishData.data_fish_info) do if c.type==7 then chest=id;break end end;assert(chest)
 b.fish_id=123;b.fish_bid=chest
 receive(12009,{fish_id=123,fish_bid=chest});receive(12004,{code=9});fishNext(b)
 assert(sent[#sent].id==12013 and sent[#sent].data.type==2 and sent[#sent].data.fish_id==123)
 b.fish_id=0;b.fish_bid=0;for _,o in ipairs(b.quest_list) do o.finish=1;o.value=o.target_val end
 receive(12013,{code=1,type=2});fishNext(b)
 for i=1,3 do
  assert(sent[#sent].id==12015 and sent[#sent].data.id==i)
  b.quest_list[i].finish=2;receive(12015,{code=1});fishNext(b)
 end
 local a=w.execute_request_list[1].other
 assert(w.execute_index==2 and a.reason=='orders_complete' and a.casts==1 and a.chests==1 and a.claimed==3)
end)
case('normal catch, escaped fish and line break continue at native pacing',function()
 freshOther();local b=fishBase();local w=otherTask('fishing');w:requestTask();fishQuery(b)
 for _,code in ipairs({2,3}) do
  receive(12004,{code=code});local n=#sent;now=now+1;ext.fishing.runner:tick();assert(#sent==n)
  fishNext(b);assert(sent[#sent].id==12004)
 end
 b.fish_id=124;b.fish_bid=10001;receive(12004,{code=1});fishNext(b)
 assert(sent[#sent].id==12013 and sent[#sent].data.type==2)
 b.fish_id=0;receive(12013,{code=1,type=2});fishNext(b);assert(sent[#sent].id==12004)
 assert(ext.fishing.runner.active.deliveries==1 and ext.fishing.runner.active.chests==0);ext.fishing.runner:cancel()
end)
case('completed orders are not refreshed and already finished day consumes no resources',function()
 freshOther();local b=fishBase({10004,10002,10003},2);local w=otherTask('fishing');w:requestTask();local n=#sent;fishQuery(b)
 assert(#sent==n and w.execute_index==2 and w.execute_request_list[1].local_reason=='orders_complete')
end)
case('free refresh allowed at zero vouchers; shortages, empty filters and native delegation stop safely',function()
 freshOther();stocks[11010]=0;local b=fishBase({10004,10002,10003});local w=otherTask('fishing');w:requestTask();fishQuery(b)
 assert(w.execute_request_list[1].local_reason=='insufficient_refresh')
 freshOther();stocks[11010]=0;b.free_quest_times=1;w=otherTask('fishing');w:requestTask();fishQuery(b);assert(sent[#sent].id==12026);ext.fishing.runner:cancel()
 freshOther();stocks[127]=0;w=otherTask('fishing');w:requestTask();fishQuery(fishBase());assert(w.execute_request_list[1].local_reason=='insufficient_energy')
 freshOther();w=otherTask('fishing','');w:requestTask();assert(w.execute_request_list[1].local_reason=='no_selected_types')
 freshOther();fc.auto_fishing_ticket={};w=otherTask('fishing');w:requestTask();assert(w.execute_request_list[1].local_reason=='native_auto');fc.auto_fishing_ticket=nil
end)
case('unlocked order fishery and exhausted premium bait are verified before casting',function()
 freshOther();local b=fishBase();b.cur_fishery_id=1002;b.bait_id=102;stocks[FishData.data_bait[102].item_bid]=0
 local w=otherTask('fishing');w:requestTask();fishQuery(b);assert(sent[#sent].id==12022 and sent[#sent].data.bait_id==101)
 b.bait_id=101;receive(12022,{bait_id=101});fishNext(b);assert(sent[#sent].id==12002 and sent[#sent].data.fishery_id==1001)
 b.cur_fishery_id=1001;receive(12002,{code=1,cur_fishery_id=1001});fishNext(b);assert(sent[#sent].id==12004);ext.fishing.runner:cancel()
 freshOther();b=fishBase();b.fishery_id_list[1].is_unlock=1;w=otherTask('fishing');w:requestTask();fishQuery(b);assert(w.execute_request_list[1].local_reason=='fishery_locked')
end)
case('lost refresh acknowledgement never blindly spends another voucher and survives rerun',function()
 freshOther();local b=fishBase({10004,10002,10003});local w=otherTask('fishing');w:requestTask();fishQuery(b)
 now=now+26;ext.fishing.runner:tick();fishQuery(b)
 assert(w.execute_request_list[1].local_reason=='request_unresolved' and ext.fishing.load().pending)
 local n=#sent;w=otherTask('fishing');w:requestTask();fishQuery(b);assert(#sent==n+1 and w.execute_request_list[1].local_result=='uncertain')
 b.quest_list[1].order_id=10001;w=otherTask('fishing');w:requestTask();fishQuery(b)
 assert(sent[#sent].id==12026 and sent[#sent].data.id==2);ext.fishing.runner:cancel()
end)
case('unknown casts never replay, unchanged delivery is not success, rejected casts stop',function()
 freshOther();local b=fishBase();local w=otherTask('fishing');w:requestTask();fishQuery(b)
 now=now+26;ext.fishing.runner:tick();fishQuery(b)
 assert(w.execute_request_list[1].local_reason=='request_unresolved' and ext.fishing.load().pending.kind=='cast')
 freshOther();b=fishBase();b.fish_id=888;b.fish_bid=10001;w=otherTask('fishing');w:requestTask();fishQuery(b)
 receive(12013,{code=1,type=2});fishNext(b);assert(w.execute_request_list[1].local_reason=='request_unresolved')
 freshOther();w=otherTask('fishing');w:requestTask();fishQuery(fishBase());receive(12004,{code=0})
 assert(w.execute_request_list[1].local_reason=='action_rejected' and not ext.fishing.load().pending)
end)
case('malformed or incomplete daily orders cannot authorize refresh or cast',function()
 freshOther();local b=fishBase();table.remove(b.quest_list);local w=otherTask('fishing');w:requestTask();local n=#sent;fishQuery(b)
 assert(#sent==n and w.execute_request_list[1].local_reason=='invalid_state')
 freshOther();b=fishBase();b.quest_list[2].id=1;w=otherTask('fishing');w:requestTask();n=#sent;fishQuery(b)
 assert(#sent==n and w.execute_request_list[1].local_reason=='invalid_state')
end)
case('long successful fishing has no arbitrary cap and publishes real progress',function()
 freshOther();local w=otherTask('fishing');w:requestTask();fishQuery(fishBase())
 for i=1,55 do receive(12004,{code=2});fishNext(fishBase());assert(ext.fishing.runner.active and sent[#sent].id==12004) end
 assert(w.other_progress==55 and ext.fishing.runner.active.casts==55);ext.fishing.runner:cancel()
end)
case('manual requests, role/day changes, disconnect and cancellation cannot overlap pending casts',function()
 for _,mode in ipairs({'role','day','disconnect','cancel'}) do
  freshOther();local w=otherTask('fishing');w:requestTask();fishQuery(fishBase())
  local n=#sent;fc:reqFishing();assert(#sent==n)
  if mode=='role' then role.rid=role.rid+1 elseif mode=='day' then now=now+86400 elseif mode=='disconnect' then connected=false else ext.fishing.runner:cancel() end
  ext.fishing.runner:tick();assert(not ext.fishing.runner.active);for i=n+1,#sent do assert(sent[i].id==31604) end
 end
 freshOther();fc:reqFishing();local w=otherTask('fishing');w:requestTask();assert(w.execute_request_list[1].local_reason=='manual_operation_pending')
end)
case('mail claims one batch, verifies fresh status, never deletes and skips empty inbox',function()
 freshOther();local w=otherTask('mail');w:requestTask();receive(10800,{mail={mailEntry(1),mailEntry(2,1),mailEntry(3,2,0)}});ext.mail.runner:tick()
 assert(sent[#sent].id==10802)
 receive(10802,{ids={{id=1,srv_id='synthetic'},{id=2,srv_id='synthetic'}},msg='ok'})
 now=now+2;ext.mail.runner:tick();receive(10800,{mail={mailEntry(1,2,0),mailEntry(2,2,0),mailEntry(3,2,0)}});ext.mail.runner:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].other.count==2)
 w=otherTask('mail');w:requestTask();local n=#sent;receive(10800,{mail={}});ext.mail.runner:tick();assert(#sent==n and w.execute_request_list[1].local_reason=='mail_empty')
 for _,v in ipairs(sent) do assert(v.id~=10804) end
end)
case('mail missing reply is reconciled; partial batch can resume on a new explicit run',function()
 freshOther();local w=otherTask('mail');w:requestTask();receive(10800,{mail={mailEntry(1),mailEntry(2)}});ext.mail.runner:tick()
 now=now+21;ext.mail.runner:tick();receive(10800,{mail={mailEntry(1,2,0),mailEntry(2)}});ext.mail.runner:tick()
 assert(w.execute_request_list[1].local_reason=='mail_partial' and ext.mail.load().pending)
 local n=#sent;w=otherTask('mail');w:requestTask();receive(10800,{mail={mailEntry(1,2,0),mailEntry(2)}});ext.mail.runner:tick()
 assert(#sent==n+2 and sent[#sent].id==10802)
 receive(10802,{ids={{id=2,srv_id='synthetic'}},msg='ok'});now=now+2;ext.mail.runner:tick()
 receive(10800,{mail={mailEntry(1,2,0),mailEntry(2,2,0)}});ext.mail.runner:tick()
 assert(w.execute_request_list[1].other.count==1 and not ext.mail.load().pending)
end)
case('mail manual operation guards and disconnect stop before claiming',function()
 freshOther();local w=otherTask('mail');w:requestTask();receive(10800,{mail={mailEntry(1)}});ext.mail.runner:tick()
 local n=#sent;mailc:getAllGoods();assert(#sent==n);connected=false;ext.mail.runner:tick();assert(w.execute_request_list[1].local_result=='uncertain')
 freshOther();mailc:getAllGoods();w=otherTask('mail');w:requestTask();assert(w.execute_request_list[1].local_reason=='manual_operation_pending')
end)
newCases={};for i=firstCase+1,#passed do newCases[#newCases+1]=passed[i] end
ext.detach()
''')
names=[lua.globals().newCases[i] for i in range(1,len(lua.globals().newCases)+1)]
print(json.dumps({'passed':len(names),'cases':names,'network':'none'},ensure_ascii=False,indent=2))
