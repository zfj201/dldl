#!/usr/bin/env python3
"""Daily limited shops and reward collection, real recovered protocol contracts."""
import contextlib,io,json,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()):ns=runpy.run_path(str(ROOT/'tests/test_daily_recast.py'))
lua=ns['lua'];original=ns['original']
runpy.run_path(str(ROOT/'tests/fixtures_supplies.py'))['setup'](lua,original)
for v,n in [('Supplies','daily_supplies'),('GameSupplies','daily_supplies_game')]:lua.globals()[v]=lua.execute((ROOT/'modules'/(n+'.lua')).read_text())
lua.execute('''
function installSupplies() return Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras,Recast,GameRecast,Supplies,GameSupplies) end
freshSupplies();local n=#sent;ext=installSupplies()
case('21 daily entries plus reward category preserve settings and run rewards last',function()
 assert(#ext.specs==22 and #sent==n)
 local t=ext.reward_type;local rows=OneKeyBurdenConst.SimplifyTypeList[1]
 for _,r in ipairs(rows) do assert(r.id~=-2101775) end
 assert(SimplifyData.data_list[t].name=='奖励领取' and #OneKeyBurdenConst.SimplifyTypeList[t]==1)
 assert(SimplifyData.data_list[t].sort_id==SimplifyData.data_list[16].sort_id+0.75)
 for i=19,22 do assert(OneKeyBurdenMainWindow:getPosExecuteData(ext.specs[i].type or 1,ext.specs[i].row).is_open==0) end
 local w=setmetatable({select_index=1,task_list={{id=1},{id=t}},operate_list={[1]={},[t]={}}},{__index=OneKeyBurdenMainWindow})
 for _,typ in ipairs({1,t}) do for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[typ]) do local d=w:getPosExecuteData(typ,r);d.is_open=1;w.operate_list[typ][r.id]=d end end
 local q=w:saveOperateRequest(true);assert(q[#q].pos==-2101775 and q[#q].type==t)
 local pref=w:getPosExecuteData(1,ext.specs[21].row);assert(pref.args[1].args_val==0)
 w.operate_list[1][-2101776].args[1].args_val=1;w:saveOperateRequest(true)
 assert(w:getPosExecuteData(1,ext.specs[21].row).args[1].args_val==1)
 -- Existing daily-tab settings use the same key after the move.
 oc:sender31601({{type=1,type_list={{pos=-2101775,is_open=1,args={}}}}})
 assert(w:getPosExecuteData(t,ext.specs[22].row).is_open==1)
 w.select_index=2;q=w:saveOperateRequest(false);assert(#q==1 and q[1].type==t)
 local before=#sent;oc:sender31609(1,t)
 for _,op in ipairs({0,1,2}) do oc:sender31604(t,op) end
 assert(not oc:getModel():getTipsTypeRed(1,t) and #sent==before)
 for _,s in ipairs(sent) do if s.id==31601 then for _,g in ipairs(s.data.list) do assert(g.type>0);for _,r in ipairs(g.type_list) do assert(r.pos>0) end end end end
end)
case('tree buys only five weekly products to remaining limits and repeat is read-only',function()
 freshSupplies();counts[27005]={[2]=1};local w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop')
 local n=#sent-1;assert(ext.supplies.active.pending.id==27005 and sent[#sent].data.num==1)
 while ext.supplies.active do supplyAccept() end
 assert(w.execute_index==2 and #w.execute_request_list[1].local_entries==5)
 local allowed={[27005]=true,[27006]=true,[27013]=true,[27021]=true,[27012]=true};local buys=0
 for i=n+1,#sent do if sent[i].id==13402 then assert(allowed[sent[i].data.eid]);buys=buys+1 end end;assert(buys==5)
 n=#sent;w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop');assert(#sent==n+1)
end)
case('guild chooses monthly and weekly products, excludes lifetime lookalikes',function()
 freshSupplies();local w=supplyTask('guild_shop');w:requestTask();supplyQuery('guild_shop')
 local bought={}
 while ext.supplies.active do local p=ext.supplies.active.pending;bought[p.id]=p.period;supplyAccept() end
 assert(bought[35134]==3 and bought[35141]==3 and bought[35123]==2 and bought[35110]==2)
 assert(not bought[35102] and not bought[35101] and not bought[35132])
 assert(w.execute_request_list[1].local_reason=='shop_product_missing') -- Two newer goods absent in static snapshot.
end)
case('new guild goods match weekly allowlist; changed config never spends',function()
 freshSupplies()
 local configs=ExchangeData.data_shop_exchage_guild
 local added={}
 for _,v in ipairs({{35142,93851,'神赐羽翎',1,60000},{35143,94108,'1级随机灵晶',5,10000}}) do
  local base;for _,v in pairs(configs) do if v.id==35141 then base=v end end;local c=deepCopy(base);c.id=v[1];c.item_bid=v[2];c.item_name=v[3];c.limit_month=0;c.limit_week=v[4];c.price=v[5];c.discount=0;c.buy_condit={}
  configs[c.id]=c;added[#added+1]=c.id
 end
 local w=supplyTask('guild_shop');w:requestTask();supplyQuery('guild_shop');local bought={}
 while ext.supplies.active do local p=ext.supplies.active.pending;bought[p.id]=p.num;supplyAccept() end
 assert(bought[35142]==1 and bought[35143]==5 and w.execute_request_list[1].local_reason=='supply_complete')
 for _,id in ipairs(added) do configs[id]=nil end
 freshSupplies();local c;for _,v in pairs(ExchangeData.data_shop_fishing) do if v.id==78001 then c=v end end;local old=c.pay_type;c.pay_type='gold'
 w=supplyTask('fishing_shop');w:requestTask();receive(13401,shopData(78));local n=#sent
 local ok=pcall(function() ext.supplies:tick() end);assert(not ok)
 for i=n+1,#sent do assert(sent[i].id~=13402) end;c.pay_type=old;ext.supplies:cancel()
end)
case('period rollover reconciles stale pending; missing identity prevents queries',function()
 freshSupplies();local w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop');local p=ext.supplies.active.pending
 ext.supplies:cancel();now=p.ref+1;w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop')
 assert(ext.supplies.active.pending.ref>p.ref and ext.supplies.active.pending.before==0);ext.supplies:cancel()
 freshSupplies();local old=ext.supplies.env.identity;ext.supplies.env.identity=function() return nil end
 local n=#sent;local ok,why=ext.supplies:start('tree_shop',function() end);assert(not ok and why=='no_role' and #sent==n);ext.supplies.env.identity=old
end)
case('fish refresh option buys only limited score voucher, never diamond voucher',function()
 for _,option in ipairs({0,1}) do
  freshSupplies();local w=supplyTask('fishing_shop',option);w:requestTask();supplyQuery('fishing_shop')
  local bought={};while ext.supplies.active do local p=ext.supplies.active.pending;bought[p.id]=p.num;supplyAccept() end
  assert(bought[78001]==10 and bought[78000]==4 and not bought[78003])
  assert((bought[78002] or 0)==(option==1 and 10 or 0))
 end
end)
case('partial balance buys affordable count; locked items and exhausted balance skip',function()
 freshSupplies();stocks[ItemData.data_assets_label2id.divine_fruit]=24000
 local w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop');assert(ext.supplies.active.pending.num==1)
 stocks[ItemData.data_assets_label2id.divine_fruit]=0;supplyAccept()
 assert(w.execute_request_list[1].local_reason=='shop_funds_short')
 freshSupplies();shopUnlocked=false;w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop')
 assert(w.execute_request_list[1].local_reason=='shop_locked')
end)
case('lost purchase ack is reconciled by exact count, never blindly resent',function()
 freshSupplies();local w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop')
 local p=ext.supplies.active.pending;now=now+21;ext.supplies:tick();local n=#sent
 w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop');assert(#sent==n+1 and w.execute_request_list[1].local_result=='uncertain')
 counts[p.id]={[p.period]=p.before+p.num};w=supplyTask('tree_shop');w:requestTask();supplyQuery('tree_shop')
 assert(ext.supplies.active.pending.id~=p.id and #ext.supplies.active.entries==1);ext.supplies:cancel()
end)
case('wrong shop ack ignored; fresh count required; day and guild changes cancel',function()
 freshSupplies();local w=supplyTask('guild_shop');w:requestTask();supplyQuery('guild_shop');local p=ext.supplies.active.pending
 receive(13402,{type=78,eid=p.id,code=1,msg=''});assert(ext.supplies.active.phase=='reply')
 receive(13402,{type=5,eid=p.id,code=1,msg=''});supplyQuery('guild_shop')
 assert(w.execute_request_list[1].local_result=='uncertain')
 freshSupplies();w=supplyTask('guild_shop');w:requestTask();supplyQuery('guild_shop');role.gid=10
 local n=#sent;ext.supplies:tick();assert(not ext.supplies.active);for i=n+1,#sent do assert(sent[i].id~=13402) end
 freshSupplies();w=supplyTask('tree_shop');w:requestTask();now=now+86400;ext.supplies:tick();assert(not ext.supplies.active)
end)
case('daily claims chain into newly unlocked daily reward then activity boxes only',function()
 freshSupplies();questStates={[90001]=1,[90018]=0,[90019]=2};boxStates={[20]=true}
 local w=supplyTask('daily_rewards');w:requestTask();supplyQuery('daily_rewards')
 assert(sent[#sent].id==10406 and sent[#sent].data.id==90001 and sent[#sent].data.type==3)
 questStates[90018]=1;supplyAccept();assert(sent[#sent].id==10406 and sent[#sent].data.id==90018)
 supplyAccept();assert(sent[#sent].id==20301 and sent[#sent].data.activity==0)
 supplyAccept();assert(w.execute_index==2 and #w.execute_request_list[1].local_entries==3)
 local n=#sent;w=supplyTask('daily_rewards');w:requestTask();supplyQuery('daily_rewards');assert(#sent==n+2)
end)
case('unconfirmed daily rewards stay pending and missing ready rewards do not claim',function()
 freshSupplies();questStates={[90018]=1};local w=supplyTask('daily_rewards');w:requestTask();supplyQuery('daily_rewards')
 receive(10406,{type=3,nodes={{id=90018}},flag=1,msg=''});supplyQuery('daily_rewards')
 assert(w.execute_request_list[1].local_result=='uncertain')
 freshSupplies();role.activity=0;w=supplyTask('daily_rewards');w:requestTask();local n=#sent;supplyQuery('daily_rewards');assert(#sent==n)
end)
case('manual request conflict, query timeout, disconnect, disk failure and uninstall are bounded',function()
 freshSupplies();mall:sender13402(1,1);local w=supplyTask('tree_shop');local n=#sent;w:requestTask();assert(#sent==n)
 now=now+21;w=supplyTask('tree_shop');w:requestTask();now=now+21;ext.supplies:tick();assert(w.execute_index==2)
 freshSupplies();connected=false;w=supplyTask('tree_shop');n=#sent;w:requestTask();assert(#sent==n)
 freshSupplies();w=supplyTask('tree_shop');w:requestTask();receive(13401,shopData(27))
 local old=ext.supplies.env.save;ext.supplies.env.save=function() error('disk full') end;n=#sent
 for t in pairs(clock.timers) do t.fn() end;assert(#sent==n);ext.supplies.env.save=old
 ext.uninstall();assert(not SimplifyData.data_list[-2101774] and not OneKeyBurdenConst.SimplifyTypeList[-2101774]);assert(OneKeyBurdenConst.SimplifyTypeList[1][#OneKeyBurdenConst.SimplifyTypeList[1]].id~=-2101775)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'passed':len(names),'new_cases':names[-12:],'network':'offline; recovered mall/task controllers, config, helper queue'}
(ROOT/'evidence/phase23_supplies_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
