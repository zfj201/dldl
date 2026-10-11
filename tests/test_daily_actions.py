#!/usr/bin/env python3
"""Offline integration: real recovered senders, models, protocol dispatch and helper UI settings."""
import runpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ns=runpy.run_path(str(ROOT/'tests/test_daily_gifts.py'))
lua=ns['lua'];original=ns['original']
lua.execute("cc.p=function(x,y) return {x=x,y=y} end;PlayerAction=setmetatable({}, {__index=function(t,k) return k end})")
for path in ['config/dungeon_stone_data.luac','config/recruit_data.luac',
             'game/dungeonstone/dungeonstone_const.luac','game/dungeonstone/dungeonstone_event.luac',
             'game/dungeonstone/dungeonstone_model.luac','game/dungeonstone/dungeonstone_controller.luac',
             'game/pantheon/pantheon_model.luac','game/pantheon/pantheon_event.luac','game/pantheon/pantheon_controller.luac',
             'game/souldomain/souldomain_const.luac','game/souldomain/souldomain_event.luac',
             'game/souldomain/souldomain_model.luac','game/souldomain/souldomain_controller.luac',
             'game/partnersummon/partnersummon_const.luac','game/partnersummon/partnersummon_controller.luac']:
    original(path)
for name,path in [('Actions','daily_actions.lua'),('GameActions','daily_actions_game.lua')]:
    lua.globals()[name]=lua.execute((ROOT/'modules'/path).read_text())
lua.execute('''
local integers={}
function ud:getIntegerForKey(k,d) if integers[k]==nil then return d end return integers[k] end
function ud:setIntegerForKey(k,v) integers[k]=v end
local dm=setmetatable({}, {__index=DungeonstoneModel});dm:config()
ds=setmetatable({model=dm,SendProtocal=capture},{__index=DungeonstoneController})
function DungeonstoneController:getInstance() return ds end
pm=setmetatable({dispather=bus},{__index=PantheonModel})
pc=setmetatable({model=pm,SendProtocal=capture},{__index=PantheonController})
function PantheonController:getInstance() return pc end
sm=setmetatable({}, {__index=SoulDomainModel});sm:init()
sc=setmetatable({model=sm,SendProtocal=capture},{__index=SoulDomainController})
function SoulDomainController:getInstance() return sc end
su=setmetatable({model={setSummonData=function() end},SendProtocal=capture},{__index=PartnersummonController})
function PartnersummonController:getInstance() return su end
Queue_View_Type={PantheonBuff=1,SummonGain=2};QueueViewMgr={getInstance=function() return {addShowData=function() end} end}
RenderMgr={getInstance=function() return {doNextFrame=function(self,fn) fn() end} end}
TimesummonController={getInstance=function() return {getModel=function() return {getBidByGroupId=function() end} end} end}
PartnersummonEvent={Summon_Success_Evnet=1}
RedManager.RED_ID_LIST={};opens=true
SysController={getInstance=function() return {checkIsOpenByKey=function() return opens end} end}
contracts=20;capacity=100;hero_count=0
BackpackController={getInstance=function() return {getModel=function() return {getItemNumByBid=function(self,id) assert(id==10023);return contracts end} end} end}
HeroController={getInstance=function() return {getModel=function() return {getHeroMaxCount=function() return capacity,hero_count end} end} end}
TimeTool.getDayAnyHourTime=function(t,h) return math.floor(t/86400)*86400+h*3600 end
for _,d in ipairs({{ds,13030,'handle13030'},{ds,13032,'handle13032'},{pc,13250,'handle13250'},
 {pc,13251,'handle13251'},{sc,21800,'on21800'},{sc,21809,'on21809'},{su,23200,'handle23200'},{su,23201,'handle23201'}}) do
 ProtoMgr:RegisterCmdCallback(d[2],d[3],d[1])
end
function receive(id,data) ProtoMgr:cmd_callback(id,data) end
function resetRole()
 role={rid=role.rid+1,srv_id='srv'};contracts=20;su.req_flag=false;now=now+20;capacity=100;hero_count=0;opens=true
end
function task(pos,count)
 return window({{type=1,pos=pos,args={{args_key=9020,args_val=count or 10}}}})
end
function response() receive(23201,{group_id=200,times=10,code=1,func_type=0}) end
local before=#sent
ext=Extension.install(Gifts,Actions,GameActions)
case('all eight rows register without sends; six new rows default off',function()
 assert(#ext.specs==8 and #sent==before)
 for i=3,8 do
  assert(OneKeyBurdenMainWindow:getPosExecuteData(1,ext.specs[i].row).is_open==0)
 end
end)
case('summon count 10/20 persists locally and never reaches native save',function()
 local cfg=ext.specs[8].row
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,cfg).args[1].args_val==10)
 oc:sender31601({{type=1,type_list={{pos=cfg.id,is_open=1,args={{args_key=9020,args_val=20}}},{pos=1,is_open=0,args={}}}}})
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,cfg).args[1].args_val==20)
 assert(sent[#sent].id==31601 and #sent[#sent].data.list[1].type_list==1)
end)
case('weekly and monthly claims use actual free configuration only',function()
 for _,kind in ipairs({2,3}) do
  resetRole();local w=task(kind==2 and -2101800 or -2101799);w:requestTask()
  local data={gift_loop_list={{gift_type=kind,ref_time=123,gift_list={{charge_id=9990+kind,limit_count=1,buy_count=0}}}}}
  receive(21017,data);assert(sent[#sent].id==21018 and sent[#sent].data.charge_id==9990+kind)
  receive(21018,{code=1});data.gift_loop_list[1].gift_list[1].buy_count=1;receive(21017,data)
  assert(w.execute_request_list[1].local_result=='confirmed')
 end
end)
case('both worship tasks confirm refreshed state and skip already claimed',function()
 resetRole();local w=task(-2101797);w:requestTask()
 receive(13250,{worship_status=1,buff_id=0});assert(sent[#sent].id==13251)
 receive(13251,{code=1,buff_id=2});assert(sent[#sent].id==13250)
 receive(13250,{worship_status=0,buff_id=2});assert(w.execute_request_list[1].local_result=='confirmed')
 w=task(-2101797);w:requestTask();receive(13250,{worship_status=0});assert(w.execute_request_list[1].local_result=='skipped')
 w=task(-2101796);w:requestTask()
 local d={last_domain_id=1,is_daily_reward=0,open_list={},unit_list={}}
 receive(21800,d);assert(sent[#sent].id==21809)
 receive(21809,{code=1});d.is_daily_reward=1;receive(21800,d)
 assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('sweep uses highest passed dungeon and only free remaining count; no purchase',function()
 resetRole();local w=task(-2101798);w:requestTask()
 local ids=dm:getDungeonList(6);local total=dm:getFreeCount(6)
 local d={list={{type=6,day_free_num=total-1,day_buy_num=0}},pass_list={{id=ids[1]},{id=ids[2]}},reward_list={}}
 local start=#sent;receive(13030,d)
 assert(sent[#sent].id==13032 and sent[#sent].data.id==ids[2] and sent[#sent].data.times==1)
 receive(13032,{id=ids[2],code=1});d.list[1].day_free_num=total;receive(13030,d);receive(13030,d)
 assert(w.execute_request_list[1].local_result=='confirmed')
 for i=start+1,#sent do assert(sent[i].id~=13034 and sent[i].id~=13031) end
end)
case('10-contract summon validates matching reply and daily persistence',function()
 resetRole();contracts=10;local w=task(-2101795,10);w:requestTask();receive(23200,{})
 assert(sent[#sent].id==23201 and sent[#sent].data.recruit_type==4 and sent[#sent].data.times==10)
 receive(23201,{group_id=100,times=10,code=1,func_type=0});assert(not w.execute_request_list[1].local_result)
 response();assert(w.execute_request_list[1].local_result=='confirmed')
 local n=#sent;w=task(-2101795,10);w:requestTask()
 assert(w.execute_request_list[1].local_reason=='daily_target_done')
 for i=n+1,#sent do assert(sent[i].id~=23201) end
end)
case('20-contract summon waits for inventory update between two item-only tens',function()
 resetRole();local w=task(-2101795,20);w:requestTask();receive(23200,{});response()
 local n=#sent;ext.actions:tick();assert(#sent==n)
 contracts=10;ext.actions:tick();assert(sent[#sent].id==23201 and sent[#sent].data.recruit_type==4)
 response();assert(w.execute_request_list[1].local_result=='confirmed')
end)
case('insufficient total contracts and bag capacity block before any summon',function()
 for _,mode in ipairs({'contracts','capacity'}) do
  resetRole();if mode=='contracts' then contracts=19 else capacity=19 end
  local n=#sent;local w=task(-2101795,20);w:requestTask()
  assert(w.execute_request_list[1].local_reason==(mode=='contracts' and 'insufficient_contracts' or 'hero_bag_full'))
  for i=n+1,#sent do assert(sent[i].id~=23201) end
 end
end)
case('contract depletion and config change before sending never select diamonds',function()
 resetRole();local w=task(-2101795,20);w:requestTask();contracts=0;receive(23200,{})
 assert(w.execute_request_list[1].local_reason=='insufficient_contracts')
 resetRole();local cfg=RecruitData.data_partnersummon_data[200];cfg.item_five[1][1]=3
 w=task(-2101795,10);w:requestTask();assert(w.execute_request_list[1].local_reason=='contract_config_mismatch');cfg.item_five[1][1]=10023
end)
case('lost or rejected summon response never retries, including reinstallation',function()
 resetRole();local w=task(-2101795,10);w:requestTask();receive(23200,{})
 now=now+13;ext.actions:tick();assert(w.execute_request_list[1].local_result=='uncertain')
 ext.uninstall();ext=Extension.install(Gifts,Actions,GameActions)
 w=task(-2101795,10);w:requestTask();assert(w.execute_request_list[1].local_reason=='previous_request_unresolved')
 resetRole();w=task(-2101795,10);w:requestTask();receive(23200,{});receive(23201,{group_id=200,times=10,code=0})
 assert(w.execute_request_list[1].local_result=='uncertain')
end)
case('manual requests cannot collide; role/day changes and cancel stop further batches',function()
 resetRole();local w=task(-2101795,20);w:requestTask();receive(23200,{})
 local n=#sent;su:send23201(200,10,3);assert(#sent==n)
 response();contracts=10;role={rid=999,srv_id='srv'};ext.actions:tick()
 assert(w.execute_request_list[1].local_result=='cancelled')
 resetRole();w=task(-2101795,20);w:requestTask();receive(23200,{});response();now=now+86400;ext.actions:tick()
 assert(w.execute_request_list[1].local_result=='cancelled')
 resetRole();w=task(-2101795,20);w:requestTask();receive(23200,{});ext.actions:cancel()
 assert(w.execute_request_list[1].local_result=='cancelled')
end)
case('all summon requests in integration suite use contracts and exactly ten',function()
 for _,send in ipairs(sent) do if send.id==23201 then
  assert(send.data.group_id==200 and send.data.times==10 and send.data.recruit_type==4)
 end end
end)
ext.uninstall()
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls'}
(ROOT/'evidence/phase7_daily_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
