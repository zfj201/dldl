#!/usr/bin/env python3
"""Limited event state machine: synthetic server replies, no live account data."""
import pathlib
from lupa.lua51 import LuaRuntime
ROOT=pathlib.Path(__file__).resolve().parents[1]
lua=LuaRuntime(unpack_returned_tuples=True)
lua.globals().Limited=lua.execute((ROOT/'modules/limited_automation.lua').read_text())
lua.execute(r'''
local passed=0
local function case(name,fn) fn();passed=passed+1;print('PASS '..name) end
local function clone(t) if type(t)~='table' then return t end;local c={};for k,v in pairs(t) do c[k]=clone(v) end;return c end
local cfg={data_open={[10]={}},data_customs={[10]={}},data_reward={[10]={{reward_id=1,score=20},{reward_id=2,score=60}}}}
for i=1,5 do
 cfg.data_open[10][i]={chapter_id=i,chapter_score=i*20,conds={{'lev',18},{'holiday_day',i}}}
 if i>1 then table.insert(cfg.data_open[10][i].conds,{'chapter_id',i-1}) end
 cfg.data_customs[10][i]={{dun_id=1,all_score=i*20,score=i,arrow_num=20}}
end
local function base(day)
 local b={camp_id=10,open_day=day or 2,num=10,status=0,all_score=0,reward_list={},chapter_list={}}
 for i=1,5 do b.chapter_list[i]={chapter_id=i,status=i==1 and 1 or 0,is_pass=0,score=0} end;return b
end
local r,actions,result,saved,now,identity,day,guard,queryCount
local function setup(old)
 actions={};result=nil;saved=old;now=100;identity='a';day=1;guard=nil;queryCount=0
 r=Limited.new({identity=function() return identity end,day=function() return day end,now=function() return now end,
 guard=function() return guard end,config=function() return cfg end,level=function() return 200 end,
 load=function() return saved end,save=function(a) saved={pending=clone(a.pending)} end,query=function() queryCount=queryCount+1 end,
 act=function(kind,p) assert(saved.pending);actions[#actions+1]={kind=kind,p=clone(p)} end})
 r:start(function(a) result=a end)
end
case('server flag, day, level and predecessor gate stages',function()
 local b=base(1);assert(Limited.plan(b,cfg,200).chapter==1)
 b.chapter_list[1].is_pass=1;b.chapter_list[2].status=1
 assert(Limited.plan(b,cfg,200).chapter==nil)
 b.open_day=2;assert(Limited.plan(b,cfg,200).chapter==2)
 assert(Limited.plan(b,cfg,17).chapter==nil)
 b.chapter_list[2].status=0;assert(Limited.plan(b,cfg,200).chapter==nil)
end)
case('target uses actual round totals and rejects changed scoring',function()
 local score,round=Limited.target(cfg,10,2);assert(score==40 and round==1)
 local c=clone(cfg);c.data_customs[10][2][1].all_score=100;assert(not Limited.target(c,10,2))
 c=clone(cfg);c.data_open[10][2].chapter_score=99;assert(not Limited.target(c,10,2))
end)
case('normal start, settle, requery, claim, verify and next stage',function()
 setup();local b=base();r:onInfo(b);assert(actions[1].kind=='start' and saved.pending.chapter==1)
 r:onReply('start',{code=1});b.status=1;b.num=9;r:onInfo(b)
 assert(actions[2].kind=='settle' and actions[2].p.score==20 and actions[2].p.round==1)
 r:onReply('settle',{all_score=20});b.status=0;b.all_score=20;b.chapter_list[1].is_pass=1;b.chapter_list[1].score=20;b.chapter_list[2].status=1;r:onInfo(b)
 assert(actions[3].kind=='claim');r:onReply('claim',{code=1});b.reward_list={{reward_id=1}};r:onInfo(b)
 assert(actions[4].kind=='start' and actions[4].p.chapter==2 and r.active.claimed==1)
 r:onReply('start',{});b.status=1;b.num=8;r:onInfo(b);assert(actions[5].kind=='settle')
 r:onReply('settle',{});b.status=0;b.all_score=60;b.chapter_list[2].is_pass=1;b.chapter_list[2].score=40;r:onInfo(b)
 assert(actions[6].kind=='claim');r:onReply('claim',{code=1});b.reward_list={{reward_id=1},{reward_id=2}};r:onInfo(b)
 assert(result.reason=='available_complete' and #result.entries==2 and result.claimed==2 and result.score==60 and not saved.pending)
end)
case('completed stage is never repeated',function()
 setup();local b=base(1);b.chapter_list[1].is_pass=1;b.chapter_list[1].score=20;b.all_score=20;b.reward_list={{reward_id=1}};r:onInfo(b)
 assert(#actions==0 and result.reason=='available_complete')
end)
case('claim available rewards before checking empty attempts',function()
 setup();local b=base();b.num=0;b.all_score=20;r:onInfo(b);assert(actions[1].kind=='claim')
end)
case('manual unfinished game is left untouched',function()
 setup();local b=base();b.status=1;r:onInfo(b);assert(#actions==0 and result.reason=='manual_game_pending')
end)
case('no attempts prevents start',function() setup();local b=base();b.num=0;r:onInfo(b);assert(#actions==0 and result.reason=='no_attempts') end)
case('missing and duplicate server stages are rejected',function()
 setup();local b=base();b.chapter_list[2]=nil;r:onInfo(b);assert(#actions==0)
 setup();b=base();b.chapter_list[2]=clone(b.chapter_list[1]);r:onInfo(b);assert(result.reason=='invalid_state')
end)
case('unknown activity is skipped without writes',function() setup();local b=base();b.camp_id=11;r:onInfo(b);assert(#actions==0 and result.reason=='unknown_config') end)
case('reply rejection preserves pending without retry',function() setup();r:onInfo(base());r:onReply('start',{code=0});assert(result.reason=='action_rejected' and saved.pending and #actions==1) end)
case('settlement must be confirmed by server stage score',function()
 setup({pending={kind='settle',camp=10,chapter=1,score=20,round=1}});r:onInfo(base());assert(result.reason=='request_unresolved' and #actions==0)
end)
case('interrupted accepted settlement recovers without resubmitting',function()
 setup({pending={kind='settle',camp=10,chapter=1,score=20,round=1}});local b=base(1);b.chapter_list[1].is_pass=1;b.chapter_list[1].score=20;b.all_score=20;b.reward_list={{reward_id=1}};r:onInfo(b)
 assert(result.reason=='available_complete' and #actions==0 and not saved.pending)
end)
case('owned accepted start resumes settlement only',function()
 setup({pending={kind='start',camp=10,chapter=1,score=20,round=1}});local b=base();b.status=1;r:onInfo(b);assert(#actions==1 and actions[1].kind=='settle')
end)
case('unconfirmed reward does not blindly claim twice',function()
 setup({pending={kind='claim',camp=10,ids={1}}});r:onInfo(base());assert(result.reason=='reward_unconfirmed' and #actions==0)
end)
case('old activity journal cannot settle into a new activity',function()
 setup({pending={kind='settle',camp=9,chapter=1,score=20,round=1}});r:onInfo(base());assert(actions[1].kind=='start' and saved.pending.camp==10)
end)
case('timeout, role, day, disconnect and cancellation stop writes',function()
 for _,which in ipairs({'time','role','day','guard','cancel'}) do
  setup();r:onInfo(base());if which=='time' then now=120 elseif which=='role' then identity='b' elseif which=='day' then day=2 elseif which=='guard' then guard='connection_unavailable' end
  if which=='cancel' then r:cancel() else r:tick() end
  assert(result and #actions==1 and saved.pending)
 end
end)
print(passed..' limited automation cases passed')
''')
