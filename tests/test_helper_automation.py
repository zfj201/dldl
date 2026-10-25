#!/usr/bin/env python3
"""Automation consumes real helper queue once; rejects stale/mismatched commands and ambiguous retries."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
lua.globals().Automation=lua.execute((Path(__file__).resolve().parents[1]/'modules/helper_automation.lua').read_text())
lua.execute(r'''
function fixture()
 local f={time=1000,role={rid=11,srv_id='srv'},day=20000,ready=true,busy=false,online=true,
   memory={},reports={},opens=0,starts=0,queues=0,cancels=0,rows={{type=1,pos=1},{type=2,pos=2}},opened=false}
 f.env={now=function() return f.time end,day=function() return f.day end,role=function() return f.role end,
  ready=function() return f.ready end,busy=function() return f.busy end,connected=function() return f.online end,
  recall=function(k) return f.memory[k] end,remember=function(k,v) f.memory[k]=v end,
  report=function(s) f.reports[#f.reports+1]=s end,open=function() f.opens=f.opens+1 end,
  opened=function() return f.opened end,queue=function() f.queues=f.queues+1;return f.rows end,
  start=function(rows) assert(next(f.memory),'must claim before start');f.starts=f.starts+1 end,
  cancel=function() f.cancels=f.cancels+1 end,snapshot=function() return f.snapshot end,
  results=function(rows) f.results=rows end}
 f.runner=Automation.new(f.env)
 f.command='v1\trun-1\t11\tsrv\t20000\t1000\t1200\trun_all\n'
 function f:start() self.runner:tick(self.command);self.opened=true;self.runner:tick(self.command) end
 return f
end
for _,change in ipairs({'malformed','expired','wrong_role','wrong_day','busy'}) do
 local f=fixture()
 if change=='malformed' then f.command='v1\t../../x\t11\tsrv\t20000\t1000\t1200\trun_all'
 elseif change=='expired' then f.time=1300 elseif change=='wrong_role' then f.role.rid=12
 elseif change=='wrong_day' then f.day=20001 else f.busy=true end
 f.runner:tick(f.command);assert(f.opens==0 and f.starts==0 and not next(f.memory),change)
end
local f=fixture();f.ready=false;f.runner:tick(f.command);assert(f.runner.status=='waiting' and not next(f.memory))
f.ready=true;f:start();assert(f.opens==1 and f.starts==1 and f.queues==1)
f.snapshot={index=1,total=2,finished=false};f.runner:tick(f.command)
f.snapshot={index=2,total=2,finished=true,all_executed=true,rows=f.rows};f.runner:tick(f.command)
assert(f.runner.status=='completed' and f.results==f.rows)
f.runner=Automation.new(f.env);f.runner:tick(f.command);assert(f.runner.status=='already_completed' and f.starts==1)
f.runner=Automation.new(f.env);f.runner:tick(f.command:gsub('run%-1','run-2'));assert(f.starts==1)
-- Even a crash before the window opens must never replay the full list.
f=fixture();f.runner:tick(f.command);f.runner=Automation.new(f.env);f.runner:tick(f.command)
assert(f.runner.status=='uncertain' and f.opens==1 and f.starts==0)
f=fixture();f:start();f.snapshot={index=1,total=2,finished=true,all_executed=false}
f.runner:tick(f.command);assert(f.runner.status=='uncertain')
f=fixture();f:start();f.snapshot={index=1,total=2,finished=false};f.runner:tick(f.command)
f.time=1181;f.runner:tick(f.command);assert(f.runner.status=='uncertain' and f.cancels==1)
f=fixture();f:start();f.role.rid=12;f.runner:tick(f.command);assert(f.runner.status=='uncertain' and f.cancels==1)
f=fixture();f:start();f.snapshot=nil;f.runner:tick(f.command);assert(f.runner.status=='uncertain')
f=fixture();f.rows={};f:start();assert(f.runner.status=='completed' and f.starts==0)
f=fixture();f.env.open=function() error('injected open failure') end
local ok=pcall(function() f.runner:tick(f.command) end);assert(not ok);f.runner:fail('open_failed')
f.runner=Automation.new(f.env);f.runner:tick(f.command);assert(f.runner.status=='uncertain')
''')
lua.execute(r'''
-- Confirmed subtask progress keeps a legitimate long refresh loop alive.
f=fixture();f:start();f.snapshot={index=1,total=2,finished=false,progress=0};f.runner:tick(f.command)
for i=1,25 do
 f.time=f.time+100;f.snapshot.progress=i;f.runner:tick(f.command)
 assert(f.runner.active and f.cancels==0)
end
f.time=f.time+181;f.runner:tick(f.command);assert(f.runner.status=='uncertain' and f.cancels==1)
''')
print('automation: validation, full queue, completion, daily deduplication, crash/stall/role isolation passed')
