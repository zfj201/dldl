#!/usr/bin/env python3
"""Startup events, timeouts and role guards, with no image coordinates/device/network."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
lua.globals().Startup=lua.execute((Path(__file__).resolve().parents[1]/'modules/startup_automation.lua').read_text())
lua.execute(r'''
function fixture(mode)
 local f={time=1000,s={},opens=0,closes=0,submits=0,reports={}}
 f.env={now=function() return f.time end,inspect=function() return f.s end,
  cancelled=function() return f.cancelled end,report=function(id,s,r) f.reports[#f.reports+1]={id,s,r} end,
  enter=function() f.opens=f.opens+1 end,closeNotice=function() f.closes=f.closes+1 end,
  submit=function() f.submits=f.submits+1 end,result=function() return f.result end}
 f.command='v1\trun-1\t11\tsrv\t1000\t1300\t'..(mode or 'run_all')..'\n'
 f.runner=Startup.new(f.env)
 function f:tick() self.runner:tick(self.command) end
 function f:city()
  self.s={role={rid=11,srv_id='srv'},ready=true};self:tick();self.time=self.time+3;self:tick()
 end
 return f
end
local f=fixture();f.runner:tick(nil);assert(#f.reports==0 and f.opens==0 and f.submits==0)
for _,text in ipairs({'','v1\t../../id\t11\tsrv\t1000\t1300\trun_all',
 'v1\tid\t11\tsrv\t1000\t1301\trun_all','v1\tid\t11\tsrv\t1000\t900\trun_all',
 'v1\tid\t11\tsrv\t999999999999999999999999999\t999999999999999999999999999999\tverify',
 'v1\tid\t11\tsrv\t1000\t1200\tpurchase'}) do
 assert(not Startup.parse(text,1000),text)
end
assert(not Startup.parse(f.command,1301));assert(not Startup.parse(f.command,994))
f.s={notice=true};f:tick();assert(f.closes==1 and f.opens==0)
f.s={login=true,server='srv',agreed=true,canEnter=true}
for i=1,20 do f:tick() end
assert(f.opens==1 and f.submits==0,'login must not repeat during slow connection')
f:city();assert(f.submits==1)
for i=1,20 do f:tick() end;assert(f.submits==1)
f.result={status='running',reason='executing'};f:tick();assert(f.runner.status=='running')
f.s.ready=false -- native helper takes over the main UI while executing.
f.result={status='completed',reason='queue_finished'};f:tick();assert(f.runner.done and f.runner.status=='completed')
f:tick();assert(f.submits==1)
f=fixture('verify');f:city();assert(f.runner.status=='verified' and f.submits==0)
for _,case in ipairs({'wrong_server','agreement','wrong_role','blocked_update','cancelled','timeout'}) do
 f=fixture();f.s={login=true,server='srv',agreed=true,canEnter=true}
 if case=='wrong_server' then f.s.server='other'
 elseif case=='agreement' then f.s.agreed=false
 elseif case=='wrong_role' then f.s={role={rid=12,srv_id='srv'},ready=true}
 elseif case=='blocked_update' then f.s={blocked='required_update'}
 elseif case=='cancelled' then f.cancelled=true
 else f.time=1301 end
 f:tick();assert(f.opens==0 and f.submits==0,case)
end
f=fixture();f.s={role={rid=11,srv_id='srv'},ready=true};f:tick();f.time=1002;f.s.ready=false;f:tick()
f.time=1003;f.s.ready=true;f:tick();f.time=1005;f:tick();assert(f.submits==0)
f.time=1006;f:tick();assert(f.submits==1)
f.s={};f:tick();assert(f.runner.status=='uncertain')
f=fixture();f:city();f.result={status='uncertain',reason='previous_run_unresolved'};f:tick()
assert(f.runner.done and f.runner.status=='uncertain')
-- A fresh explicit request can run in the same process after a diagnostic completes.
f=fixture('verify');f:city();f.command=f.command:gsub('run%-1','run-2'):gsub('verify','run_all')
f:tick();f.time=f.time+3;f:tick();assert(f.submits==1)
''')
print('startup: idle, strict commands, single login, city stability, verify isolation, role/server guards, cancellation, timeouts and results passed')
