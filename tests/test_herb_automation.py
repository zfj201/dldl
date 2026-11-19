from pathlib import Path

from lupa.lua51 import LuaRuntime


root = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().Herb = lua.execute((root / 'modules/herb_automation.lua').read_text())
lua.execute('''
local tiers = {{reward_id=1,day_limit=6}, {reward_id=2,day_limit=12}}
local function info(ids, ends)
    local list = {}
    for _, id in ipairs(ids) do list[#list+1] = {day_id=id} end
    return {camp_id=10, end_time=ends or 5000, status=0, day_list=list}
end

local function setup(count, eggs)
    local t, calls, result = 1000, {}, nil
    local function record(name) return function() calls[#calls+1]=name end end
    local runner = Herb.new({now=function() return t end, guard=function() end,
        isSelf=function(r) return r.rid==7 end, load=function() return eggs end,
        daily=function(_, d) return Herb.daily(d, tiers, count) end, matchClosed=function() return false end,
        query=record('query'), claim=record('claim'), match=record('match'), ready=record('ready'),
        field=function() return 5 end, select=record('select'), closeResult=record('close'), cancelMatch=record('cancel')})
    runner:start({camp=10}, function(a) result=a end, function() end)
    return runner, calls, function(s) t=t+s end, function() return result end
end

assert(Herb.rewardKind({{item_bid=3,item_num=500}})==nil)
assert(Herb.rewardKind({{item_bid=63566,item_num=1}})=='zero')
assert(Herb.rewardKind({{item_bid=63567,item_num=1}})=='full')
assert(Herb.MAX_MATCHES==11)

-- Reaching the threshold does not finish daily rewards until the server confirms each claim.
local r, calls, step, result = setup(12,{zero=true,full=true})
r:onInfo(info({1})); r:tick(); assert(calls[#calls]=='claim')
step(15); r:tick(); assert(calls[#calls]=='query')
r:onInfo(info({1,2})); r:tick(); assert(result().status=='done')

r,calls,step,result = setup(12,{zero=true,full=true})
r:onInfo(info({1})); r:tick(); r:onReply('claim',1); r:tick()
r:onInfo(info({1})); r:tick(); assert(result().reason=='claim_unconfirmed')

-- Daily complete is not overall complete without both eggs. Duplicate rounds and results are ignored.
r,calls,step,result = setup(12,{zero=true})
for i=1,Herb.MAX_MATCHES do
    r:onInfo(info({1,2})); r:tick(); assert(calls[#calls]=='match')
    r:onReady({end_time=2000,match_list={{rid=7,is_ready=0}}}); r:tick(); assert(calls[#calls]=='ready')
    r:onRound({round=1,end_time=2000}); r:tick(); assert(calls[#calls]=='select')
    local n=#calls; r:onRound({round=1,end_time=2000}); r:tick(); assert(#calls==n)
    r:onResult({list={{rid=7,num=12}}}); r:onResult({list={{rid=7,num=12}}})
    step(1); r:tick(); assert(calls[#calls]=='query')
end
r:onInfo(info({1,2})); r:tick()
assert(result().status=='partial' and result().reason=='run_limit' and result().matches==Herb.MAX_MATCHES)

r,calls,step,result = setup(12,{})
r:onInfo(info({1,2})); r:onInfo(info({1,2},5100)); r:tick()
assert(result().reason=='scope_changed' and #calls==1)
''')
print('仙草大作战：领奖回读、彩蛋识别、运行上限、跨期隔离通过')
