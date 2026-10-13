#!/usr/bin/env python3
"""Offline Lua 5.1 tests with recovered hot-update protocol/controller code."""
import json,os
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
lua=LuaRuntime(unpack_returned_tuples=True)
lua.globals().Gifts=lua.execute((ROOT/'modules/daily_gifts.lua').read_text())
lua.execute('''
passed={}
function case(name,f) f();passed[#passed+1]=name end
function fixture()
 local f={now=0,identity='role1',queries={},claims={},results={},free=true}
 f.runner=Gifts.new({timeout=10,now=function() return f.now end,identity=function() return f.identity end,
  refresh=function(k) f.queries[#f.queries+1]=k end,claim=function(id) f.claims[#f.claims+1]=id end,
  freeId=function(k) return k==1 and 9991 or 9995 end,isFree=function() return f.free end})
 function f:start(k) return self.runner:start(k or 1,function(r) self.results[#self.results+1]=r end) end
 function f:info(k,count,period)
  return {gift_type=k,ref_time=period or 100,gift_list={{charge_id=k==1 and 9991 or 9995,buy_count=count,limit_count=1}}}
 end
 return f
end
case('each correct free gift claims once and requires post-reply verification',function()
 for _,kind in ipairs({1,6}) do
  local f=fixture();assert(f:start(kind));assert(not f:start(kind))
  f.runner:onInfo(f:info(kind==1 and 6 or 1,0));assert(#f.claims==0)
  f.runner:onInfo(f:info(kind,0));f.runner:onInfo(f:info(kind,0))
  assert(#f.claims==1 and f.claims[1]==(kind==1 and 9991 or 9995))
  f.runner:onInfo(f:info(kind,1));assert(#f.results==0)
  f.runner:onReply({code=1});assert(#f.queries==2 and #f.results==0)
  f.runner:onInfo(f:info(kind,1));assert(f.results[1].status=='confirmed')
 end
end)
case('already claimed and missing gifts never claim',function()
 local f=fixture();f:start();f.runner:onInfo(f:info(1,1));assert(#f.claims==0)
 f=fixture();f:start();f.runner:onInfo({gift_type=1,ref_time=100,gift_list={}})
 assert(#f.claims==0 and f.results[1].status=='skipped')
end)
case('paid or mismatched config cannot claim',function()
 local f=fixture();f.free=false;f:start();f.runner:onInfo(f:info(1,0))
 assert(#f.claims==0 and f.results[1].reason=='free_config_mismatch')
end)
case('failure code and unchanged count are not success',function()
 local f=fixture();f:start();f.runner:onInfo(f:info(1,0));f.runner:onReply({code=0})
 f.runner:onInfo(f:info(1,0));assert(f.results[1].status=='uncertain' and #f.claims==1)
 f:start();f.runner:onInfo(f:info(1,0));assert(#f.claims==1)
end)
case('lost response queries and verifies without resending',function()
 local f=fixture();f:start();f.runner:onInfo(f:info(1,0));f.now=11;f.runner:tick()
 assert(#f.claims==1 and #f.queries==2);f.runner:onInfo(f:info(1,1))
 assert(f.results[1].status=='confirmed')
end)
case('query timeout and verification timeout terminate',function()
 local f=fixture();f:start();f.now=11;f.runner:tick();assert(#f.claims==0 and f.results[1].reason=='query_timeout')
 f=fixture();f:start();f.runner:onInfo(f:info(1,0));f.now=11;f.runner:tick();f.now=22;f.runner:tick()
 assert(f.results[1].reason=='verification_timeout' and #f.claims==1)
end)
case('period rollover and identity changes never confirm old claim',function()
 local f=fixture();f:start();f.runner:onInfo(f:info(1,0));f.runner:onReply({code=1})
 f.runner:onInfo(f:info(1,1,200));assert(f.results[1].reason=='period_changed')
 f=fixture();f:start();f.identity='role2';f.runner:onInfo(f:info(1,0));assert(#f.claims==0)
end)
case('cancelled claim remains protected on repeat',function()
 local f=fixture();f:start();f.runner:onInfo(f:info(1,0));f.runner:cancel()
 f:start();f.runner:onInfo(f:info(1,0));assert(#f.claims==1 and f.results[2].status=='uncertain')
end)
case('invalid or duplicated counts rejected',function()
 local f=fixture();f:start();local d=f:info(1,0);d.gift_list[1].buy_count=-1;f.runner:onInfo(d)
 assert(#f.claims==0 and f.results[1].status=='error')
 f=fixture();f:start();d=f:info(1,0);d.gift_list[2]=d.gift_list[1];f.runner:onInfo(d);assert(#f.claims==0)
end)
TRUE=1;FALSE=0
function TI18N(s) return s end
function BaseClass() return {} end
function class() return {} end
function message() end
function deepCopy(t) if type(t)~='table' then return t end local c={} for k,v in pairs(t) do c[k]=deepCopy(v) end return c end
RedManager={RedOrder={reward=1},getInstance=function() return {doRedPointDelay=function() end} end}
BackPackConst={quality={white=1,green=2,blue=3,purple=4,orange=5,red=6}}
MainuiConst={icon={seven_login=1}}
display={LEFT_CENTER=1,CENTER=2,CENTER_TOP=3}
local pref={};ud={getBoolForKey=function(self,k,default) if pref[k]==nil then return default end return pref[k] end,
 setBoolForKey=function(self,k,v) pref[k]=v end,flush=function() end}
cc={rect=function(...) return {...} end,UserDefault={getInstance=function() return ud end}}
sent={};function capture(self,id,data) sent[#sent+1]={id=id,data=data} end
bus={Fire=function() end};GlobalEvent={getInstance=function() return bus end}
clock={timers={}};function clock:add(fn) local t={fn=fn};self.timers[t]=true;return t end
function clock:remove(t) self.timers[t]=nil end
GlobalTimeTicket={getInstance=function() return clock end}
now=0;connected=true;GameNet={getInstance=function() return {getTime=function() return now end,IsServerConnect=function() return connected end} end}
role={rid=11,srv_id='srv'};RoleController={getInstance=function() return {getRoleVo=function() return role end} end}
SortTools={KeyLowerSorter=function(k) return function(a,b) return a[k]<b[k] end end,
 tableLowerSorter=function(keys) return function(a,b) for _,k in ipairs(keys) do if a[k]~=b[k] then return a[k]<b[k] end end return false end end}
TimeTool={checkServerOpenTime=function() return true end}
WelfareController={getInstance=function() return {setWelfareStatus=function() end} end}
WelfareIcon={every_day_gift=10006}
''')
def original(path):
    p=ROOT/'recovered/phase2/hotupdate/lua'/path
    if not p.exists():p=ROOT/'recovered/phase2/lua'/path
    lua.execute(p.read_text())
for path in ['config/charge_loop_data.luac','game/vip/vip_event.luac','game/vip/vip_const.luac',
             'game/vip/vip_model.luac','game/vip/vip_controller.luac','game/onekeyburden/onekeyburden_const.luac',
             'game/onekeyburden/onekeyburden_event.luac','game/onekeyburden/onekeyburden_controller.luac','config/simplify_data.luac',
             'sys/net/proto_mgr.luac']:
    original(path)
lua.execute('''
vc=setmetatable({model=setmetatable({month_week_data={},month_week_red_list={}}, {__index=VipModel}),dispather=bus,SendProtocal=capture},{__index=VipController})
function VipController:getInstance() return vc end
oc=setmetatable({model={getTypeOperateData=function() return nil end},SendProtocal=capture},{__index=OneKeyBurdenController})
function OneKeyBurdenController:getInstance() return oc end
ProtoMgr.is_init=true;ProtoMgr.cmd_callback_table={};ProtoMgr.queue_cmd_table={}
ProtoMgr:RegisterCmdCallback(21017,'handle21017',vc)
ProtoMgr:RegisterCmdCallback(21018,'handle21018',vc)
function window(rows)
 return setmetatable({execute_request_list=rows,execute_index=1,operate_type=1,
 stop_btn_lb={setString=function() end},updateLoopList=function() end,onCountDownTicket=function() end},{__index=OneKeyBurdenAutoWindow})
end
function info(kind,count,period)
 return {gift_loop_list={{gift_type=kind,ref_time=period or 100,gift_list={{charge_id=kind==1 and 9991 or 9995,limit_count=1,buy_count=count}}}}}
end
''')
for path in ['game/onekeyburden/view/onekeyburden_main_window.luac','game/onekeyburden/view/onekeyburden_auto_window.luac']:
    original(path)
lua.globals().Extension=lua.execute((ROOT/'modules/xiangxiang_gifts_extension.lua').read_text())
lua.execute('''
local original_save=oc.sender31601;local original_query=vc.handle21017
local before=#sent;ext=Extension.install(Gifts)
case('installation is idempotent, registers two visible default-off rows, sends nothing',function()
 assert(#sent==before and Extension.install(Gifts)==ext)
 local rows=OneKeyBurdenConst.SimplifyTypeList[1]
 assert(rows[1].title=='斗罗集市·每日礼包领取' and rows[2].title=='学院活动·每日特惠领取')
 for i=1,2 do assert(OneKeyBurdenMainWindow:getPosExecuteData(1,rows[i]).is_open==FALSE) end
end)
case('original helper queue keeps both tasks but native save strips both IDs',function()
 local main=setmetatable({task_list={{id=1}},select_index=1,operate_list={[1]={
 [-2101802]={pos=-2101802,is_open=TRUE,args={}},[-2101801]={pos=-2101801,is_open=TRUE,args={}},
 [1]={pos=1,is_open=TRUE,args={}}}}},{__index=OneKeyBurdenMainWindow})
 local queue=main:saveOperateRequest(false);assert(#queue==3 and queue[1].pos==-2101802 and queue[2].pos==-2101801)
 local save=sent[#sent];assert(save.id==31601 and #save.data.list[1].type_list==1 and save.data.list[1].type_list[1].pos==1)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(1,OneKeyBurdenConst.SimplifyTypeList[1][1]).is_open==TRUE)
 assert(not pcall(function() oc:sender31602(1,-2101802) end))
end)
case('registered real protocol callbacks run both gifts serially and resume native task',function()
 local w=window({{type=1,pos=-2101802},{type=1,pos=-2101801},{type=1,pos=1}})
 w:requestTask();assert(sent[#sent].id==21017 and sent[#sent].data.gift_type==1)
 ProtoMgr:cmd_callback(21017,info(1,0));assert(sent[#sent].id==21018 and sent[#sent].data.charge_id==9991)
 local n=#sent;vc:sender21018(9995);assert(#sent==n)
 w:updateDataList({type=1,pos=1,args={}});assert(w.execute_index==1)
 ProtoMgr:cmd_callback(21018,{code=1});assert(w.execute_index==1 and sent[#sent].id==21017)
 ProtoMgr:cmd_callback(21017,info(1,1));assert(w.execute_index==2 and w.execute_request_list[1].local_result=='confirmed')
 w:requestTask();assert(sent[#sent].data.gift_type==6)
 ProtoMgr:cmd_callback(21017,info(6,0));assert(sent[#sent].data.charge_id==9995)
 ProtoMgr:cmd_callback(21018,{code=1});ProtoMgr:cmd_callback(21017,info(6,1));assert(w.execute_index==3)
 assert(next(clock.timers)==nil);w:requestTask();assert(sent[#sent].id==31602 and sent[#sent].data.pos==1)
end)
case('manual in-flight claim prevents custom send and stops local queue',function()
 vc:sender21018(9991);local n=#sent
 local w=window({{type=1,pos=-2101802}});w:requestTask()
 assert(w.is_execute_finish and w.execute_request_list[1].local_reason=='manual_claim_pending')
 for i=n+1,#sent do assert(sent[i].id~=21017 and sent[i].id~=21018) end
 ProtoMgr:cmd_callback(21018,{code=1})
end)
case('uninstall restores functions and leaves no custom rows or timers',function()
 ext.uninstall();assert(oc.sender31601==original_save and vc.handle21017==original_query)
 for _,row in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do assert(row.id~=-2101802 and row.id~=-2101801) end
 assert(next(clock.timers)==nil)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'runtime':lua.eval('_VERSION'),'passed':len(names),'cases':names,'network':'mocked; no device calls'}
(ROOT/'evidence'/f'{os.environ.get("DLDL_TEST_PHASE","phase6")}_gifts_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
