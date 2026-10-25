#!/usr/bin/env python3
"""Real saved formations, mine senders, replies, category and daily persistence."""
import contextlib,io,json,os,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for fixture in ['daily_extras','voyage','mine']:
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+fixture+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Voyage','voyage_automation'),('GameVoyage','voyage_automation_game'),('Mine','mine_automation'),('GameMine','mine_automation_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute('''
freshMine()
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
local n=#sent;GameVoyage.bind(Voyage,ext);GameMine.bind(Mine,ext)
case('mine installs below voyage in the local sibling category with no requests',function()
 local rows=OneKeyBurdenConst.SimplifyTypeList[ext.voyage.type]
 assert(#rows==3 and rows[1].id==ext.voyage.pos and rows[2].id==ext.mine.pos and rows[3].id==-2101782)
 assert(#ext.specs==17 and #sent==n)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(ext.voyage.type,ext.mine.row).is_open==0)
end)
case('both enabled settings enter all-category queue; native IDs stay filtered and original 13 excluded',function()
 local t=ext.voyage.type;local p=ext.voyage.pos;local m=ext.mine.pos
 local w=setmetatable({select_index=2,task_list={SimplifyData.data_list[3],ext.voyage.category},operate_list={
  [3]={[12]={pos=12,is_open=1,args={}},[13]={pos=13,is_open=1,args={}}},
  [t]={[p]={pos=p,is_open=1,args={}},[m]={pos=m,is_open=1,args={}},[-2101782]={pos=-2101782,is_open=0,args={}}}}},{__index=OneKeyBurdenMainWindow})
 local q=w:saveOperateRequest(true);assert(#q==3 and q[2].pos==p and q[3].pos==m)
 assert(#sent[#sent].data.list==1 and sent[#sent].data.list[1].type==3)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(t,ext.mine.row).is_open==1)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(t,ext.voyage.setting).is_open==1)
 local n=#sent;oc:sender31604(t,1);oc:sender31609(1,t);assert(#sent==n)
 assert(not pcall(function() oc:sender31602(t,m) end))
end)
case('accepted exact 50/1 target advances immediately while its battle remains running',function()
 freshMine();local n=#sent;local w=startMine()
 assert(sent[#sent].id==30302 and sent[#sent].data.floor_id==50 and sent[#sent].data.area_id==1)
 receive(30302,mineDetail(5));assert(detailWindows==0 and sent[#sent].id==30307)
 local req=sent[#sent].data;assert(req.floor_id==50 and req.area_id==1 and req.mine_id==5)
 assert(ext.mine.load().pending and w.execute_index==1)
 background[57]={};receive(30307,{code=1,floor_id=50,area_id=1,mine_id=5})
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='challenge_started' and background[57])
 assert(ext.mine.load().completed and not ext.mine.load().pending)
 local allowed={[30300]=true,[11251]=true,[30301]=true,[30302]=true,[30307]=true}
 for i=n+1,#sent do assert(allowed[sent[i].id],'no settlement, skip, occupy or formation save') end
 n=#sent
 for i=1,3 do local q=mineTask();q:requestTask();assert(q.execute_request_list[1].local_reason=='daily_target_done' and ext.mine.load().mine_id==5) end
 assert(#sent==n)
end)
case('wrong floor area mine and unrelated acknowledgements never complete',function()
 freshMine();local w=startMine();receive(30302,mineDetail(5));local n=#sent
 for _,d in ipairs({{code=1,floor_id=49,area_id=1,mine_id=5},{code=1,floor_id=50,area_id=2,mine_id=5},{code=1,floor_id=50,area_id=1,mine_id=3}}) do receive(30307,d) end
 assert(w.execute_index==1 and ext.mine.runner.active and #sent==n)
 receive(30307,{code=1,floor_id=50,area_id=1,mine_id=5});assert(w.execute_index==2)
end)
case('prefer eligible idle mine; exclude self protected busy and expired mines',function()
 freshMine();local list={mineTarget(4),mineTarget(3,22,now-10),mineTarget(2,33,0,1),mineTarget(1,44),mineTarget(5)}
 local w=startMine(list);assert(sent[#sent].id==30302 and sent[#sent].data.mine_id==5)
 local d=mineDetail(5);d.combat_state=1;receive(30302,d)
 assert(sent[#sent].id==30302 and sent[#sent].data.mine_id==1)
 receive(30302,mineDetail(1));receive(30307,{code=1,floor_id=50,area_id=1,mine_id=1})
 assert(w.execute_index==2)
 freshMine();w=startMine({mineTarget(4),mineTarget(3,22,now-10),mineTarget(2,33,0,1)})
 assert(w.execute_request_list[1].local_reason=='no_challengeable_mine' and not ext.mine.runner.active)
end)
case('explicit rejection tries another target once; never loops forever through rejected mines',function()
 freshMine();local list={mineTarget(1),mineTarget(2)};local w=startMine(list)
 for _,id in ipairs({1,2}) do
  assert(sent[#sent].data.mine_id==id);receive(30302,mineDetail(id));receive(30307,{code=0,floor_id=50,area_id=1,mine_id=id})
  assert(not ext.mine.load().pending)
  receive(30300,mineBase());receive(11251,mineForm());receive(30301,mineArea(list))
 end
 assert(w.execute_request_list[1].local_reason=='no_challengeable_mine')
end)
case('lost acknowledgement persists and remount never resends same-day uncertain challenge',function()
 freshMine();local w=startMine();receive(30302,mineDetail(5));now=now+21;ext.mine.runner:tick()
 assert(w.execute_request_list[1].local_result=='uncertain' and ext.mine.load().pending)
 ext.uninstall();ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
 GameVoyage.bind(Voyage,ext);GameMine.bind(Mine,ext)
 local n=#sent;w=mineTask();w:requestTask()
 assert(#sent==n and w.execute_request_list[1].local_reason=='previous_request_unresolved')
 now=now+86400;w=mineTask();w:requestTask();assert(sent[#sent].id==30300);ext.mine.runner:cancel()
end)
case('closed season locked floor rest cooldown replay and same battle cannot launch',function()
 for _,field in ipairs({'status','max_floor','trim_end_time','next_plunder_time'}) do
  freshMine();local w=mineTask();w:requestTask();local d=mineBase()
  d[field]=field=='status' and 2 or field=='max_floor' and 49 or now+1
  receive(30300,d);assert(w.execute_index==2 and sent[#sent].id~=30307)
 end
 for _,mode in ipairs({'replay','battle','closed','disconnect'}) do
  freshMine();if mode=='replay' then replay=true elseif mode=='battle' then background[57]={} elseif mode=='closed' then opens=false else connected=false end
  local n=#sent;local w=mineTask();w:requestTask();assert(w.execute_index==2 and #sent==n)
 end
end)
case('three saved teams validated; empty duplicate unknown heroes never challenge or rewrite formations',function()
 for _,mode in ipairs({'empty','duplicate','unknown','position','order','teams'}) do
  freshMine();local w=mineTask();w:requestTask();receive(30300,mineBase());local f=mineForm()
  if mode=='empty' then f.formations[2].pos_info={}
  elseif mode=='duplicate' then f.formations[2].pos_info[1].id=1
  elseif mode=='unknown' then f.formations[2].pos_info[1].id=999
  elseif mode=='position' then f.formations[2].pos_info[1].pos=99
  elseif mode=='order' then f.formations[2].order=1 else table.remove(f.formations) end
  receive(11251,f);assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='invalid_mine_formation')
  assert(sent[#sent].id~=30307)
 end
end)
case('late owned detail never opens popup; user cancel leaves pending and late success cannot repeat',function()
 freshMine();local w=startMine();ext.mine.runner:cancel();receive(30302,mineDetail(5));assert(detailWindows==0)
 freshMine();w=startMine();receive(30302,mineDetail(5));ext.mine.runner:cancel()
 receive(30307,{code=1,floor_id=50,area_id=1,mine_id=5});local n=#sent;w=mineTask();w:requestTask()
 assert(#sent==n and ext.mine.load().pending)
end)
case('role day disconnect manual interference and malformed state stop without challenge',function()
 for _,mode in ipairs({'role','day','disconnect','bad'}) do
  freshMine();local w=mineTask();w:requestTask();local n=#sent
  if mode=='role' then role.rid=role.rid+1 elseif mode=='day' then now=now+86400 elseif mode=='disconnect' then connected=false end
  local d=mineBase();if mode=='bad' then d.trim_end_time=-1 end;receive(30300,d)
  assert(w.execute_index==2 or w.is_execute_finish)
  for i=n+1,#sent do assert(sent[i].id==31604) end
 end
 freshMine();mc:sender30307(50,1,5);local n=#sent;local w=mineTask();w:requestTask();assert(#sent==n and w.execute_request_list[1].local_reason=='manual_operation_pending')
 now=now+21;w=startMine();local n=#sent;mc:sender30307(50,1,3);mc:sender30302(50,1,3);assert(#sent==n);ext.mine.runner:cancel()
end)
case('persistence failure prevents battle request and safely finishes queue',function()
 freshMine();local w=startMine();local save=ext.mine.runner.env.save
 ext.mine.runner.env.save=function() error('disk full') end
 local n=#sent;receive(30302,mineDetail(5));assert(#sent==n and w.execute_index==2 and w.execute_request_list[1].local_reason=='runtime_error')
 ext.mine.runner.env.save=save
end)
case('known concurrent automated combat rejection waits for that combat only then re-queries',function()
 freshMine();local conflict=ext.mine.runner.env.conflict;local busy=true;ext.mine.runner.env.conflict=function() return busy end
 local w=startMine();receive(30302,mineDetail(5));receive(30307,{code=0,floor_id=50,area_id=1,mine_id=5})
 local n=#sent;ext.mine.runner:tick();assert(#sent==n and ext.mine.runner.active.phase=='deferred')
 busy=false;ext.mine.runner:tick();assert(sent[#sent].id==30300)
 receive(30300,mineBase());receive(11251,mineForm());receive(30301,mineArea());receive(30302,mineDetail(5))
 receive(30307,{code=1,floor_id=50,area_id=1,mine_id=5});assert(w.execute_index==2)
 ext.mine.runner.env.conflict=conflict
end)
case('voyage advances into mine and mine advances onward in the same actual helper queue',function()
 freshMine();role.energy=1453
 local w=window({{type=-2101803,pos=-2101783,args={}},{type=-2101803,pos=-2101781,args={}},{type=1,pos=999,args={}}})
 w:requestTask();receive(23800,voyageInfo({order(1,29309)},1,1));receive(23805,{flag=0});ext.voyage.runner:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='insufficient_intelligence')
 w:requestTask();receive(30300,mineBase());receive(11251,mineForm());receive(30301,mineArea());receive(30302,mineDetail(5))
 receive(30307,{code=1,floor_id=50,area_id=1,mine_id=5})
 assert(w.execute_index==3 and w.execute_request_list[2].local_reason=='challenge_started')
end)
case('query timeout never creates battle pending or sends a challenge',function()
 freshMine();local w=mineTask();w:requestTask();local n=#sent;now=now+21;ext.mine.runner:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='base_timeout' and #sent==n)
 assert(not ext.mine.load().pending)
end)
case('mine result cells clear their content when reused for voyage and native tasks',function()
 freshMine()
 local function node() return {setVisible=function(self,v) self.visible=v end,setString=function(self,v) self.text=v end,
 setFontSize=function(self,v) self.font=v end,addTo=function(self) return self end} end
 local old=createRichLabel;createRichLabel=function() return node() end
 local cell=setmetatable({title_lb=node(),un_finish_node=node(),un_finish_lb=node(),item_scrollview=node(),root_wnd={}}, {__index=OneKeyBurdenAutoItem})
 cell:setData({type=-2101803,pos=-2101781,is_execute=true,mine={reason='challenge_started',mine_id=5}},1)
 assert(cell.mine_label.visible and cell.mine_label.text:find('50层1区'))
 cell:setData({type=-2101803,pos=-2101783,is_execute=true,voyage={entries={},refresh={}}},1)
 assert(not cell.mine_label.visible and cell.voyage_label.visible)
 cell:setData({type=1,pos=1,is_execute=true,args={}},1)
 assert(not cell.mine_label.visible and not cell.voyage_label.visible and cell.title_lb.font==30)
 createRichLabel=old
end)
case('uninstall removes both other-automation tasks and restores controller methods',function()
 ext.uninstall();assert(not SimplifyData.data_list[-2101803] and not OneKeyBurdenConst.SimplifyTypeList[-2101803])
 local n=#sent;mc:sender30307(50,1,5);assert(#sent==n+1)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'passed':len(names),'cases':names,'network':'offline; real mine controller/model/config and protocol callbacks'}
(ROOT/'evidence/phase19_mine_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
