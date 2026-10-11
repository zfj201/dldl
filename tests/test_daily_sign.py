#!/usr/bin/env python3
"""Lua 5.1 tests; all sends are captured locally, with recovered game methods."""
from pathlib import Path
import json, argparse
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--hotupdate',action='store_true');args=parser.parse_args()
lua=LuaRuntime(unpack_returned_tuples=True)
load=lua.eval('loadstring')
for file in (ROOT/'modules').glob('*.lua'):
    compiled=load(file.read_text(), '@'+str(file))
    if isinstance(compiled,tuple): raise AssertionError(compiled)
lua.globals().Sign=lua.execute((ROOT/'modules/daily_sign.lua').read_text())
lua.execute('''
passed = {}
function case(name, fn) fn(); table.insert(passed, name) end
function fixture()
  local f = {now=0, identity='server:role:session', queries=0, claims=0, results={}}
  f.runner=Sign.new({timeout=10,now=function() return f.now end,
    identity=function() return f.identity end,
    refresh=function() f.queries=f.queries+1 end,
    claim=function() f.claims=f.claims+1 end})
  function f:start() return self.runner:start(function(r) table.insert(self.results,r) end) end
  function f:state(status, day) return {month=10, day=day or 10, endTime=100000, status=status} end
  return f
end
case('fresh query, single claim, confirmed success',function()
  local f=fixture();assert(f:start());assert(f.queries==1 and f.claims==0)
  assert(not f:start());f.runner:onInfo(f:state(0));f.runner:onInfo(f:state(0));assert(f.claims==1)
  f.runner:onSuccess(9,f:state(1,9));assert(#f.results==0)
  f.runner:onSuccess(10,f:state(1));assert(f.results[1].status=='success')
  f.runner:onSuccess(10,f:state(1));assert(#f.results==1)
end)
case('ordinary and VIP already claimed; no supplemental claim',function()
  for _,status in ipairs({1,2,3,4}) do
    local f=fixture();f:start();f.runner:onInfo(f:state(status))
    assert(f.claims==0 and f.results[1].status=='skipped')
  end
end)
case('lost reply verified by state without resubmission',function()
  local f=fixture();f:start();f.runner:onInfo(f:state(0));f.now=11;f.runner:tick()
  assert(f.queries==2 and f.claims==1);f.runner:onInfo(f:state(1))
  assert(f.results[1].status=='confirmed')
end)
case('uncertain claim blocks same-period retry',function()
  local f=fixture();f:start();f.runner:onInfo(f:state(0));f.now=11;f.runner:tick()
  f.runner:onInfo(f:state(0));assert(f.results[1].status=='uncertain')
  f:start();f.runner:onInfo(f:state(0));assert(f.claims==1 and f.results[2].status=='uncertain')
  f:start();f.runner:onInfo(f:state(0,11));assert(f.claims==2)
end)
case('query timeout sends nothing',function()
  local f=fixture();f:start();f.now=11;f.runner:tick()
  assert(f.claims==0 and f.results[1].reason=='query_timeout')
end)
case('verification timeout leaves uncertainty',function()
  local f=fixture();f:start();f.runner:onInfo(f:state(0));f.now=11;f.runner:tick()
  f.now=22;f.runner:tick();assert(f.results[1].reason=='verification_timeout' and f.claims==1)
end)
case('role switch cancels before claiming',function()
  local f=fixture();f:start();f.identity='other';f.runner:onInfo(f:state(0))
  assert(f.claims==0 and f.results[1].reason=='role_changed')
end)
case('cancelled submitted request remains guarded',function()
  local f=fixture();f:start();f.runner:onInfo(f:state(0));f.runner:cancel()
  f:start();f.runner:onInfo(f:state(0));assert(f.claims==1 and f.results[2].status=='uncertain')
end)
case('period rollover does not confirm old request',function()
  local f=fixture();f:start();f.runner:onInfo(f:state(0));f.now=11;f.runner:tick()
  f.runner:onInfo(f:state(1,11));assert(f.results[1].reason=='period_changed')
end)
case('malformed state rejected',function()
  local f=fixture();f:start();f.runner:onInfo({status=0});assert(f.claims==0 and f.results[1].status=='error')
end)
-- Minimal engine shell; original game methods below supply network payloads and queue construction.
TRUE=1;FALSE=0
RedManager={RedOrder={reward=1}}
BackPackConst={quality={white=1,green=2,blue=3,purple=4,orange=5,red=6}}
MainuiConst={icon={seven_login=1}}
cc={rect=function(...) return {...} end}
function TI18N(s) return s end
function BaseClass() return {} end
function class() return {} end
function message() end
function deepCopy(t) if type(t)~='table' then return t end local c={} for k,v in pairs(t) do c[k]=deepCopy(v) end return c end
sent={}
function capture(self,id,data) table.insert(sent,{id=id,data=data}) end
bus={handlers={}}
function bus:Bind(event,fn) local token={event=event,fn=fn};self.handlers[token]=true;return token end
function bus:UnBind(token) self.handlers[token]=nil end
function bus:Fire(event,...) local copy={};for t in pairs(self.handlers) do table.insert(copy,t) end
  for _,t in ipairs(copy) do if self.handlers[t] and t.event==event then t.fn(...) end end end
GlobalEvent={getInstance=function() return bus end}
clock={timers={}}
function clock:add(fn) local token={fn=fn};self.timers[token]=true;return token end
function clock:remove(token) self.timers[token]=nil end
GlobalTimeTicket={getInstance=function() return clock end}
now=0;GameNet={getInstance=function() return {getTime=function() return now end} end}
role={rid=11,srv_id='srv'};RoleController={getInstance=function() return {getRoleVo=function() return role end} end}
SortTools={KeyLowerSorter=function(k) return function(a,b) return a[k]<b[k] end end,
  tableLowerSorter=function(keys) return function(a,b) for _,k in ipairs(keys) do
    if a[k]~=b[k] then return a[k]<b[k] end end return false end end}
''')
def original(path):
    source=ROOT/'recovered/phase2/lua'/path
    hot=ROOT/'recovered/phase2/hotupdate/lua'/path
    if args.hotupdate and hot.exists():source=hot
    lua.execute(source.read_text())
for path in ['game/welfare/welfare_event.luac','game/welfare/welfare_constants.luac','game/welfare/welfare_model.luac','game/welfare/welfare_controller.luac','game/onekeyburden/onekeyburden_const.luac','game/onekeyburden/onekeyburden_event.luac','game/onekeyburden/onekeyburden_controller.luac','config/simplify_data.luac','config/checkin_data.luac']:
    original(path)
lua.execute('''
wc=setmetatable({model=setmetatable({}, {__index=WelfareModel}),dispather=bus,SendProtocal=capture}, {__index=WelfareController})
function wc:setWelfareStatus() end
function WelfareController:getInstance() return wc end
oc=setmetatable({model={getTypeOperateData=function() return nil end},SendProtocal=capture}, {__index=OneKeyBurdenController})
function OneKeyBurdenController:getInstance() return oc end
''')
for path in ['game/onekeyburden/view/onekeyburden_main_window.luac','game/onekeyburden/view/onekeyburden_auto_window.luac']:
    original(path)
lua.globals().Extension=lua.execute((ROOT/'modules/xiangxiang_sign_extension.lua').read_text())
lua.execute('''
original_save=oc.sender31601;original_request=OneKeyBurdenAutoWindow.requestTask
original_update=OneKeyBurdenAutoWindow.updateDataList
ext=Extension.install(Sign)
case('local task opt-in default and duplicate install rejected',function()
  local cfg=OneKeyBurdenConst.SimplifyTypeList[1]
  assert(OneKeyBurdenMainWindow:getPosExecuteData(1,cfg[#cfg]).is_open==FALSE)
  assert(not pcall(function() Extension.install(Sign) end))
end)
case('actual game save builds local queue but strips custom server task',function()
  local main=setmetatable({task_list={{id=1}},select_index=1,operate_list={[1]={
    [-14101]={pos=-14101,is_open=TRUE,args={}},[1]={pos=1,is_open=TRUE,args={}}
  }}},{__index=OneKeyBurdenMainWindow})
  local queue=main:saveOperateRequest(false)
  assert(#queue==2 and queue[1].pos==-14101)
  local save=sent[#sent];assert(save.id==31601 and #save.data.list[1].type_list==1)
  assert(save.data.list[1].type_list[1].pos==1)
end)
function window(rows)
  return setmetatable({execute_request_list=rows,execute_index=1,stop_btn_lb={setString=function() end},
    updateLoopList=function() end,onCountDownTicket=function() end}, {__index=OneKeyBurdenAutoWindow})
end
case('real welfare controller reply completes local task and resumes native queue',function()
  local w=window({{type=1,pos=-14101},{type=1,pos=1}})
  local before=#sent;w:requestTask();assert(sent[#sent].id==14100)
  wc:handle14100({status=0,day=10,month=10,endTime=100000,reward_list={},progress_list={},signDay=0,targetValue=10})
  assert(sent[#sent].id==14101 and next(sent[#sent].data)==nil)
  w:updateDataList({type=1,pos=1,args={}});assert(w.execute_index==1)
  wc:handle14101({code=1,msg='',status=1,day=10,progress=0,reward_list={}})
  assert(w.execute_index==2 and w.execute_request_list[1].local_result=='success')
  assert(next(bus.handlers)==nil and next(clock.timers)==nil)
  w:requestTask();assert(sent[#sent].id==31602 and sent[#sent].data.pos==1)
  w:updateDataList({type=1,pos=999,args={}});assert(not w.is_execute_finish)
  w:updateDataList({type=1,pos=1,args={}});assert(w.is_execute_finish)
  for i=before+1,#sent do assert(not (sent[i].id==31602 and sent[i].data.pos==-14101)) end
end)
case('real failure reply does not advance or resubmit',function()
  local w=window({{type=1,pos=-14101}});w:requestTask()
  wc:handle14100({status=0,day=11,month=10,endTime=100000,reward_list={},progress_list={},targetValue=10})
  wc:handle14101({code=0,msg='failure'});assert(not w.is_execute_finish)
  now=11;for t in pairs(clock.timers) do t.fn() end
  assert(sent[#sent].id==14100)
  wc:handle14100({status=0,day=11,month=10,endTime=100000,reward_list={},progress_list={},targetValue=10})
  assert(w.is_execute_finish and w.execute_request_list[1].local_result=='uncertain')
end)
case('uninstall restores original functions and registration',function()
  ext.uninstall();assert(oc.sender31601==original_save and OneKeyBurdenAutoWindow.requestTask==original_request)
  assert(OneKeyBurdenAutoWindow.updateDataList==original_update)
  for _,v in ipairs(OneKeyBurdenConst.SimplifyTypeList[1]) do assert(v.id~=-14101) end
  assert(next(bus.handlers)==nil and next(clock.timers)==nil)
end)
''')
results=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
print(json.dumps({'runtime':lua.eval('_VERSION'),'passed':len(results),'cases':results},ensure_ascii=False,indent=2))
