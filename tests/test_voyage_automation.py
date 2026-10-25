#!/usr/bin/env python3
"""Voyage integration: real configs/senders/handlers plus asynchronous server simulation."""
import contextlib,io,json,os,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
os.environ['DLDL_TEST_PHASE']='phase18'
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
runpy.run_path(str(ROOT/'tests/fixtures_daily_extras.py'))['setup'](lua,original)
runpy.run_path(str(ROOT/'tests/fixtures_voyage.py'))['setup'](lua,original)
for var,name in [('Extras','daily_extras.lua'),('GameExtras','daily_extras_game.lua'),('Voyage','voyage_automation.lua'),('GameVoyage','voyage_automation_game.lua')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/name).read_text())
lua.execute('''
freshVoyage()
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
local before=#sent
GameVoyage.bind(Voyage,ext)
case('new sibling category is below shop; default off and no install requests',function()
 local v=ext.voyage
 assert(v.category.sort_id>SimplifyData.data_list[16].sort_id and #ext.specs==17)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(v.type,v.setting).is_open==0 and #sent==before)
end)
case('all real task variants obey quality and exact target item rules',function()
 local total,selected=0,0
 for _,c in pairs(ShippingData.data_order) do
  total=total+1;if Voyage.select(c) then selected=selected+1 end
 end
 assert(total==2020 and selected==975)
 assert(not Voyage.select(ShippingData.data_order[29309]))
end)
case('local preferences persist, native dispatch is filtered and original task 13 excluded',function()
 local t,p=ext.voyage.type,ext.voyage.pos
 oc:sender31601({{type=t,type_list={{pos=p,is_open=1,args={}}}},{type=3,type_list={{pos=13,is_open=1,args={}}}}})
 assert(OneKeyBurdenMainWindow:getPosExecuteData(t,ext.voyage.setting).is_open==1)
 assert(#sent[#sent].data.list==1 and sent[#sent].data.list[1].type==3)
 local n=#sent;oc:sender31609(1,t);assert(#sent==n and not oc.model:getTipsTypeRed(1,t))
 for _,op in ipairs({0,1,2}) do oc:sender31604(t,op) end
 assert(#sent==n,'local category lifecycle must never enter uint8 native protocol')
 oc:sender31604(3,1);assert(#sent==n+1 and sent[#sent].id==31604)
 local w=setmetatable({task_list={SimplifyData.data_list[3],ext.voyage.category},operate_list={
  [3]={[12]={pos=12,is_open=1,args={}},[13]={pos=13,is_open=1,args={}}},
  [t]={[p]={pos=p,is_open=1,args={}},[-2101782]={pos=-2101782,is_open=0,args={}}}}},{__index=OneKeyBurdenMainWindow})
 local q=w:saveOperateRequest(true);assert(#q==2)
 for _,r in ipairs(q) do assert(r.pos~=13) end
 assert(w.operate_list[3][13].is_open==1,'must not rewrite official preference')
end)
case('dispatch serially prioritizes red/orange; confirms list and asset delivery before next mutation',function()
 freshVoyage();local w=startVoyage({order(1,29301),order(2,29501),order(3,29404),order(4,29309)})
 assert(sent[#sent].id==23802 and sent[#sent].data.order_id==2 and #sent[#sent].data.assign_ids==0)
 local n=#sent;vo:requestRefreshOrder();vo:requestReceiveOrder(1,{});oc:sender31602(3,13);assert(#sent==n)
 receive(23802,{flag=1,msg='ok'});receive(23800,voyageInfo({order(1,29301),order(2,29501,2),order(3,29404),order(4,29309)}))
 ext.voyage.runner:tick();assert(#w.execute_request_list[1].voyage.entries==0,'wait for asset delivery')
 role.energy=4000;ext.voyage.runner:tick();assert(#w.execute_request_list[1].voyage.entries==1)
 now=now+1;ext.voyage.runner:tick();receive(23805,{flag=0});receive(23800,voyageInfo({order(1,29301),order(2,29501,2),order(3,29404),order(4,29309)}));ext.voyage.runner:tick()
 assert(sent[#sent].id==23802 and sent[#sent].data.order_id==3)
 receive(23802,{flag=1,msg='ok'});role.energy=2000
 receive(23800,voyageInfo({order(1,29301),order(2,29501,2),order(3,29404,2),order(4,29309)}));ext.voyage.runner:tick()
 now=now+1;ext.voyage.runner:tick();receive(23805,{flag=0});receive(23800,voyageInfo({order(1,29301),order(2,29501,2),order(3,29404,2),order(4,29309)}));ext.voyage.runner:tick()
 assert(sent[#sent].data.order_id==1)
 receive(23802,{flag=1,msg='ok'});role.energy=0
 receive(23800,voyageInfo({order(1,29301,2),order(2,29501,2),order(3,29404,2),order(4,29309)}));ext.voyage.runner:tick()
 now=now+1;ext.voyage.runner:tick();receive(23805,{flag=0});receive(23800,voyageInfo({order(1,29301,2),order(2,29501,2),order(3,29404,2),order(4,29309)}))
 ext.voyage.runner:tick();assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='insufficient_intelligence')
 assert(#w.execute_request_list[1].voyage.entries==3 and #ext.voyage.display(w)==5)
 local d=ext.voyage.load();assert(#d.entries==3 and not d.pending)
end)
case('refresh uses free then ticket then diamonds; identical offers still count confirmed consumption',function()
 freshVoyage();local offers={order(9,29309)};local w=startVoyage(offers)
 local function refresh(f,c,balance)
  assert(sent[#sent].id==23804)
  local n=#sent;ext.voyage.runner:tick();assert(#sent==n)
  receive(23804,{flag=1,msg='ok'});if balance then balance() end
  receive(23800,voyageInfo(offers,f,c));ext.voyage.runner:tick()
  now=now+1;ext.voyage.runner:tick();receive(23805,{flag=0});receive(23800,voyageInfo(offers,f,c));ext.voyage.runner:tick()
 end
 refresh(1,0);refresh(1,0,function() stocks[10014]=1 end);refresh(1,0,function() stocks[10014]=0 end)
 refresh(1,1,function() stocks[3]=970 end)
 local a=ext.voyage.runner.active
 assert(a.refresh.free==1 and a.refresh.ticket==2 and a.refresh.diamond==1 and a.refresh.diamonds==30 and a.refresh.tickets==2)
 ext.voyage.runner:cancel();assert(ext.voyage.load().pending,'in-flight fifth refresh retained on cancel')
end)
case('insufficient intelligence, including discount threshold, never refreshes',function()
 freshVoyage();role.energy=1999;local n=#sent;local w=startVoyage({order(9,29309)})
 for i=n+1,#sent do assert(sent[i].id~=23804 and sent[i].id~=23802) end
 assert(w.execute_request_list[1].local_reason=='insufficient_intelligence')
 freshVoyage();role.energy=1800
 w=window({{type=-2101803,pos=-2101783,args={}},{type=1,pos=999,args={}}});w:requestTask()
 receive(23800,voyageInfo({order(1,29301)}));receive(23805,{flag=1});ext.voyage.runner:tick();assert(sent[#sent].id==23802)
 receive(23802,{flag=1,msg='ok'});role.energy=0;receive(23800,voyageInfo({order(1,29301,2)}));ext.voyage.runner:tick()
 assert(w.execute_request_list[1].voyage.entries[1].cost==1800);ext.voyage.runner:cancel()
end)
case('cache wait, no open slot and insufficient diamonds stop without paid retry',function()
 freshVoyage();role.energy=1000;role.energy_cache=5000
 local w=startVoyage({order(9,29309)});local n=#sent
 for i=1,6 do now=now+2;ext.voyage.runner:tick();receive(23805,{flag=0});receive(23800,voyageInfo({order(9,29309)}));ext.voyage.runner:tick() end
 assert(w.execute_request_list[1].local_reason=='energy_cache_unavailable')
 for i=n+1,#sent do assert(sent[i].id~=23804 and sent[i].id~=23802) end
 freshVoyage();stocks[10014]=0;stocks[3]=29;w=startVoyage({order(9,29309)},1,8)
 assert(w.execute_request_list[1].local_reason=='insufficient_diamonds')
 freshVoyage();w=startVoyage({order(9,29301,2)})
 assert(w.execute_request_list[1].local_reason=='no_refreshable_orders')
end)
case('lost dispatch acknowledgement recovers from exact task state; restart never resends unresolved request',function()
 freshVoyage();local w=startVoyage({order(1,29301)});role.energy=4000
 receive(23801,order(1,29301,2));receive(23800,voyageInfo({order(1,29301,2)}));ext.voyage.runner:tick()
 assert(#w.execute_request_list[1].voyage.entries==1);ext.voyage.runner:cancel()
 freshVoyage();w=startVoyage({order(1,29301)})
 now=now+21;ext.voyage.runner:tick();now=now+21;ext.voyage.runner:tick()
 assert(w.execute_request_list[1].local_result=='uncertain')
 local n=#sent;w=startVoyage({order(1,29301)})
 ext.voyage.runner:tick();assert(ext.voyage.runner.active.recovery)
 for i=n+1,#sent do assert(sent[i].id~=23802 and sent[i].id~=23804) end
 role.energy=4000;receive(23800,voyageInfo({order(1,29301,2)}));ext.voyage.runner:tick()
 assert(w.execute_request_list[1].local_reason=='previous_request_recovered' and #w.execute_request_list[1].voyage.entries==1)
end)
case('explicit rejection, disconnect, role switch and unknown configuration do not continue spending',function()
 freshVoyage();local w=startVoyage({order(1,29301)});receive(23802,{flag=0,msg='no'})
 assert(w.execute_request_list[1].local_result=='error' and not ext.voyage.load().pending)
 freshVoyage();w=startVoyage({order(1,29301)});connected=false;ext.voyage.runner:tick();assert(ext.voyage.load().pending);connected=true
 freshVoyage();w=startVoyage({order(1,29301)});role={rid=role.rid+1,srv_id='srv'};ext.voyage.runner:tick()
 assert(w.execute_request_list[1].local_result=='cancelled')
 freshVoyage();w=startVoyage({order(1,999999)});assert(w.execute_request_list[1].local_result=='error')
end)
case('long result lists preserve duplicate tasks and never insert executable fake rows',function()
 freshVoyage();local w=window({{type=-2101803,pos=-2101783,is_execute=true,voyage={entries={}}}})
 for i=1,120 do w.execute_request_list[1].voyage.entries[i]={sequence=i,name='同名',order_id=1,order_bid=29301} end
 local list=ext.voyage.display(w);assert(#list==121 and #w.execute_request_list==1 and list[121].data.voyage_entry.sequence==120)
end)
case('low-level normal dispatch chooses eligible unoccupied heroes and blocks when impossible',function()
 freshVoyage();HeroCalculate.checkIsSpecialHero=function() return false end
 local model=hc:getModel()
 model.hero_list={[11]={partner_id=11,star=4,lev=20,camp_type=1},[12]={partner_id=12,star=3,lev=20,camp_type=2}}
 local ids=ext.voyage.runner.env.assign(1,ShippingData.data_order[29301]);assert(ids and #ids==2)
 vm:setOrderList({{order_id=99,order_bid=29301,status=2,assign_ids={{partner_id=11}}}})
 local no,why=ext.voyage.runner.env.assign(1,ShippingData.data_order[29301]);assert(not no and why=='dispatch_conditions_unmet')
end)
case('unknown journal or persistence failure advances safely without sending consumption',function()
 freshVoyage();local env=ext.voyage.runner.env;local oldload=env.load;env.load=function() error('corrupt journal') end
 local n=#sent;local w=startVoyage({order(1,29301)});assert(w.execute_request_list[1].local_result=='error')
 for i=n+1,#sent do assert(sent[i].id~=23802 and sent[i].id~=23804) end
 env.load=oldload;freshVoyage();local oldsave=env.save;local calls=0
 env.save=function(a) calls=calls+1;if calls>1 then error('disk full') end;return oldsave(a) end
 n=#sent;w=window({{type=-2101803,pos=-2101783,args={}},{type=1,pos=999,args={}}});w:requestTask()
 receive(23805,{flag=0});receive(23800,voyageInfo({order(1,29301)}))
 for t in pairs(clock.timers) do t.fn() end
 assert(w.execute_request_list[1].local_result=='uncertain')
 for i=n+1,#sent do assert(sent[i].id~=23802 and sent[i].id~=23804) end
 env.save=oldsave
end)
case('manual interference prevents attribution of an unresolved old request',function()
 freshVoyage();local w=startVoyage({order(1,29301)});ext.voyage.runner:cancel()
 now=now+21;vo:requestRefreshOrder();now=now+21
 local n=#sent;w=startVoyage({order(1,29301,2)});role.energy=4000
 receive(23800,voyageInfo({order(1,29301,2)}));ext.voyage.runner:tick()
 assert(ext.voyage.runner.active and #ext.voyage.runner.active.entries==0)
 for i=n+1,#sent do assert(sent[i].id~=23802 and sent[i].id~=23804) end
 ext.voyage.runner:cancel()
end)
case('history opens only saved results; scrolling cell reuse clears custom presentation',function()
 freshVoyage();local w=startVoyage({order(1,29301)});receive(23802,{flag=1,msg='ok'});role.energy=4000
 receive(23800,voyageInfo({order(1,29301,2)}));ext.voyage.runner:tick();ext.voyage.runner:cancel()
 local oldopen=oc.openOnekeyburdenAutoWindow;local historyWindow
 oc.openOnekeyburdenAutoWindow=function(self,open,list,op)
  historyWindow=window(list);historyWindow:openRootWnd(list,op)
 end
 local n=#sent;ext.voyage.showHistory();assert(#sent==n and historyWindow.is_execute_finish and historyWindow.voyage_history)
 historyWindow:requestTask();assert(#sent==n and #ext.voyage.display(historyWindow)==2)
 oc.openOnekeyburdenAutoWindow=oldopen
 local function node()
  return {visible=true,setVisible=function(self,b) self.visible=b end,setString=function(self,s) self.text=s end,
   getString=function(self) return self.text end,setFontSize=function(self,n) self.font=n end,addTo=function(self) return self end}
 end
 local rich=createRichLabel;createRichLabel=function() return node() end
 local cell=setmetatable({title_lb=node(),un_finish_node=node(),un_finish_lb=node(),item_scrollview=node(),root_wnd={}}, {__index=OneKeyBurdenAutoItem})
 local d=ext.voyage.display(historyWindow)[2].data;cell:setData(d,1)
 assert(cell.voyage_label.visible and cell.voyage_label.text:find('预计') and cell.title_lb.font==24)
 cell:setData({type=1,pos=1,is_execute=true,args={}},1)
 assert(not cell.voyage_label.visible and cell.title_lb.font==30)
 createRichLabel=rich
end)
case('uninstall restores category, sender wrappers and existing daily extension',function()
 ext.uninstall();assert(not SimplifyData.data_list[-2101803] and not OneKeyBurdenConst.SimplifyTypeList[-2101803])
 assert(not OneKeyBurdenMainWindow.createVoyageHistoryItem)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'passed':len(names),'cases':names,'network':'offline simulated responses; recovered voyage contracts used'}
(ROOT/'evidence/phase18_voyage_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
