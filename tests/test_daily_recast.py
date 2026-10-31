#!/usr/bin/env python3
"""Gold/purple daily recast integration against recovered controllers and helper queue."""
import contextlib,io,json,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for f in ('daily_extras','voyage','recast'):
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+f+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Recast','daily_recast'),('GameRecast','daily_recast_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute('''
function installRecast() return Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras,Recast,GameRecast) end
freshRecast();local n=#sent;ext=installRecast()
case('18 daily rows install without requests and new task defaults off',function()
 assert(#ext.specs==18 and #sent==n)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[18].row).is_open==0)
end)
case('enabled setting enters full queue and never sends synthetic ID to server',function()
 local p=-2101779
 oc.model.getTypeOperateList=function() return {} end;oc.model.type_func_list={}
 local w=setmetatable({select_index=1,task_list={{id=1}},operate_list={[1]={}}},{__index=OneKeyBurdenMainWindow})
 for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do w.operate_list[1][r.id]={pos=r.id,is_open=r.id==p and 1 or 0,args={}} end
 local q=w:saveOperateRequest(true);local found=0
 for _,r in ipairs(q) do if r.pos==p then found=found+1 end end
 assert(found==1 and OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[18].row).is_open==1)
 for _,s in ipairs(sent) do if s.id==31601 then for _,t in ipairs(s.data.list) do for _,r in ipairs(t.type_list) do assert(r.pos~=p) end end end end
end)
case('both random choices reforge exactly once preserving attributes with exact material cost',function()
 local random=math.random;local seen={}
 for _,pick in ipairs({1,2}) do
  freshRecast();bones={[11]=artifact(11,13001,true),[12]=artifact(12,13002,true)}
  math.random=function(n) assert(n==2);return pick end
  local n=#sent;local w=startRecast();local t=ext.recast.active.target;seen[t.bid]=true
  assert(sent[#sent].id==11033)
  local d=sent[#sent].data;assert(d.partner_id==0 and d.artifact_id==t.id and #d.skills==0 and #d.select_skills==0)
  assert(ext.recast.load().pending)
  finishRecast();assert(w.execute_index==2 and w.execute_request_list[1].local_result=='confirmed')
  assert(w.execute_request_list[1].local_target.name==t.name and bones[t.id].attr[1].attr_val==100 and stocks[3]==1000)
  local count=0;for i=n+1,#sent do
   assert(sent[i].id==10506 or sent[i].id==11048 or sent[i].id==11033)
   if sent[i].id==11033 then count=count+1 end
  end;assert(count==1 and not ext.recast.load().pending)
  n=#sent;w=recastTask();w:requestTask();assert(#sent==n and w.execute_request_list[1].local_reason=='daily_target_done')
 end
 math.random=random;assert(seen[13001] and seen[13002])
end)
case('manual unsaved results remain eligible, locked items and gold lucky recasts are skipped',function()
 freshRecast();bones={[1]=artifact(1,13001,true),[2]=artifact(2,13001,true),[3]=artifact(3,13002,true)}
 bones[1].is_lock=1
 local random=math.random;math.random=function(n) assert(n==1);return 1 end
 local w=startRecast(10);assert(ext.recast.active.target.id==2);finishRecast();math.random=random
 freshRecast();bones={[2]=artifact(2,13002,true)};w=startRecast(10)
 assert(w.execute_request_list[1].local_reason=='no_recast_target')
end)
case('no candidates or materials and missing quota never spend',function()
 for _,mode in ipairs({'empty','quality','essence','coin','quota'}) do
  freshRecast();bones={[1]=artifact(1)}
  if mode=='empty' then bones={} elseif mode=='quality' then bones[1].base_id=13003
  elseif mode=='essence' then stocks[10004]=499 elseif mode=='coin' then stocks[1]=49999 end
  local n=#sent;local w=recastTask();w:requestTask()
  receive(11048,mode=='quota' and {artifact_ref_count={}} or recastQuota());recastDetails();ext.recast:tick()
  assert(w.execute_index==2 and not ext.recast.load().pending)
  for i=n+1,#sent do assert(sent[i].id~=11033) end
 end
end)
case('ack requires fresh item details and exact cost before completion',function()
 freshRecast();bones={[1]=artifact(1,13001,true)};local w=startRecast()
 receive(11033,{result=1,msg=''});ext.recast:tick();assert(w.execute_index==1)
 recastDetails();ext.recast:tick();assert(w.execute_index==1)
 stocks[10004]=stocks[10004]-500;stocks[1]=stocks[1]-50000;ext.recast:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].local_result=='confirmed')
end)
case('timeout and reinstall retain pending and never spend again even next day',function()
 freshRecast();bones={[1]=artifact(1)};local w=startRecast();now=now+21;ext.recast:tick()
 assert(w.execute_request_list[1].local_result=='uncertain');ext.uninstall();ext=installRecast()
 now=now+86400;local n=#sent;w=recastTask();w:requestTask()
 assert(#sent==n and w.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('next game day can overwrite a changed manual unsaved result',function()
 freshRecast();bones={[1]=artifact(1)};startRecast();finishRecast();now=now+86400
 bones[1].extra_attr={{attr_id=1,attr_val=999}};local w=startRecast();finishRecast()
 assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('role day and connection changes stop before sending',function()
 for _,mode in ipairs({'role','day','connection'}) do
  freshRecast();bones={[1]=artifact(1)};local w=recastTask();w:requestTask();receive(11048,recastQuota());recastDetails()
  if mode=='role' then role.rid=role.rid+1 elseif mode=='day' then now=now+86400 else connected=false end
  local n=#sent;ext.recast:tick();assert(not ext.recast.active)
  for i=n+1,#sent do assert(sent[i].id~=11033) end
 end
end)
case('manual UI and concurrent sender guarded; pending disk failure sends nothing',function()
 freshRecast();bones={[1]=artifact(1)};hc.artifact_select_skill_window={}
 local n=#sent;local w=recastTask();w:requestTask();assert(#sent==n)
 hc.artifact_select_skill_window=nil;w=startRecast();n=#sent;hc:sender11033(0,1,{},{});hc:sender11034(0,1,1);assert(#sent==n);ext.recast:cancel()
 freshRecast();bones={[1]=artifact(1)};w=recastTask();w:requestTask();receive(11048,recastQuota());recastDetails()
 local old=ext.recast.env.savePending;ext.recast.env.savePending=function() error('disk full') end
 n=#sent;for t in pairs(clock.timers) do t.fn() end
 assert(#sent==n and w.execute_index==2);ext.recast.env.savePending=old
end)
case('rejection and incorrect resource decrease remain uncertain',function()
 for _,mode in ipairs({'rejected','cost'}) do
  freshRecast();bones={[1]=artifact(1)};local w=startRecast()
  if mode=='rejected' then receive(11033,{result=0,msg=''})
  else stocks[1]=stocks[1]-50001;receive(11033,{result=1,msg=''});bones[1].extra_attr={{attr_id=1,attr_val=200}};recastDetails();ext.recast:tick() end
  assert(w.execute_request_list[1].local_result=='uncertain' and ext.recast.load().pending)
 end
end)
case('uninstall removes recast and restores original sender',function()
 ext.uninstall();local n=#sent;hc:sender11033(0,1,{},{})
 assert(#sent==n+1)
 for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do assert(r.id~=-2101779) end
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'passed':len(names),'cases':names,'network':'offline recovered controllers, protocol dispatch, config, helper UI; mocked inventory and rendering'}
(ROOT/'evidence/phase22_recast_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
