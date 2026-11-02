-- Explicit product + period allowlist. Use official mall/task controllers.
local M={}
local function uint(n) return type(n)=='number' and n>=0 and n%1==0 end
local shops={
 tree_shop={type=27,config='data_shop_recovery',currency='divine_fruit',items={{10055,2},{10056,2},{10702,2},{52026,2},{10701,2}}},
 guild_shop={type=5,config='data_shop_exchage_guild',currency='guild_seal',items={{14021,3},{93419,3},{29905,2},{13001,2},{10074,2},{10011,2},{10012,2},{93851,2},{94108,2},{10002,2}}},
 fishing_shop={type=78,config='data_shop_fishing',currency='fish_score',items={{126,2},{127,1},{11010,1}}}}
local limits={'limit_day','limit_week','limit_month'}
local refs={'day_ref_time','week_ref_time','month_ref_time'}
function M.bind(Supplies,ctx)
 local mall=MallController:getInstance();local task=TaskController:getInstance()
 local bag=BackpackController:getInstance():getModel();local ud=cc.UserDefault:getInstance()
 local runner,internal,manual_until=nil,false,0
 local snapshot,quests,activity=nil,nil,nil
 local function day() return math.floor((ctx.now()+3*3600)/86400) end
 local function role() return RoleController:getInstance():getRoleVo() end
 local function scope(k)
  local s=assert(ctx.roleKey())
  if k=='guild_shop' then s=s..':'..tostring(role().gsrv_id)..':'..tostring(role().gid) end
  return s
 end
 local function key(k) return 'dldl_supplies_v1:'..scope(k)..':'..k end
 local function load(k)
  local s=ud:getStringForKey(key(k),'');if s=='' then return end
  local p=json.decode(s);assert(type(p)=='table' and p.kind==k,'invalid supply journal');return p
 end
 local function clear(k) ud:setStringForKey(key(k),'');ud:flush() end
 local function guard(k)
  if not ctx.connected() then return 'connection_unavailable' end
  if ctx.now()<manual_until or mall.mall_buy_win then return 'manual_claim_pending' end
  if k=='guild_shop' and (not uint(role().gid) or role().gid==0) then return 'no_guild' end
  if runner and runner.active and runner.active.pending and runner.active.pending.scope~=scope(k) then return 'guild_changed' end
 end
 local function allowed(c,s,period)
  if c.type~=s.type or c.pay_type~=s.currency or not uint(c.id) or not uint(c.item_num) or c.item_num==0
   or not uint(c.price) or c.price==0 or not uint(c.discount or 0) then return false end
  if not uint(c[limits[period]]) or c[limits[period]]==0 then return false end
  for i,f in ipairs(limits) do if i~=period and (c[f] or 0)~=0 then return false end end
  for _,f in ipairs({'role_limit_count','limit_count','gnw_limit_count'}) do if (c[f] or 0)~=0 then return false end end
  if c.change_price and next(c.change_price) then return false end
  return true
 end
 local function unlocked(c)
  if (c.limit_vip or 0)>(role().vip_lev or 0) then return false end
  if c.glev then
   local g=GuildController:getInstance():getModel():getMyGuildInfo()
   if not g or not uint(g.lev) or g.lev<c.glev then return false end
  end
  if c.buy_condit and next(c.buy_condit) then return MainuiController:getInstance():checkIsOpenByActivate(c.buy_condit)==true end
  return true
 end
 local function count(d,id,period)
  local found
  for _,v in ipairs(d.item_list) do
   if v.item_id==id then
    assert(not found,'duplicate shop product');found=v
   end
  end
  if not found then return 0 end -- Official full list omits products never bought.
  local value
  for _,e in ipairs(found.ext or {}) do
   if e.key==period then assert(value==nil and uint(e.val),'invalid purchase count');value=e.val end
  end
  assert(value~=nil,'missing period purchase count');return value
 end
 local function product(k,p)
  local s=shops[k];for _,c in pairs(ExchangeData[s.config] or {}) do if c.id==p.id then return c end end
 end
 local function price(c) return (c.discount or 0)>0 and c.discount or c.price end
 local function balance(s)
  local bid=ItemData.data_assets_label2id[s.currency];assert(bid,'missing shop currency')
  local n=bag:getItemNumByBid(bid);assert(uint(n),'invalid shop balance');return n
 end
 local function state(k,id)
  local list=k=='quest' and quests.quest_list or activity.activity_box
  for _,v in ipairs(list) do if (k=='quest' and v.id or v.activity)==id then return k=='quest' and v.finish or true end end
 end
 runner=Supplies.new({identity=function() local id,r=ctx.identity(),role();if not id or not r then return end;return tostring(id)..':'..tostring(r.gid)..':'..tostring(r.gsrv_id) end,day=day,now=ctx.now,guard=guard,load=load,clear=clear,
  report=function(k,result)
   ud:setStringForKey(key(k)..':last',json.encode(result));ud:flush()
  end,
  query=function(k)
   snapshot=nil;quests=nil;activity=nil
   if shops[k] then mall:sender13401(shops[k].type)
   else task:sender10400(3);task:requestActivityInfo() end
  end,
  receive=function(k,id,d,phase)
   if phase~='query' and phase~='verify' then return end
   if shops[k] and id==13401 and d.type==shops[k].type then
    assert(d.code==1 and type(d.item_list)=='table','shop query rejected')
    assert(d.is_half==0,'unsupported temporary discount')
    snapshot=deepCopy(d)
   elseif k=='daily_rewards' then
    if id==10400 and d.type==3 then assert(type(d.quest_list)=='table','invalid daily quests');quests=deepCopy(d)
    elseif id==20300 then assert(type(d.activity_box)=='table','invalid activity boxes');activity=deepCopy(d) end
   end
  end,
  ready=function(k) return shops[k] and snapshot~=nil or k=='daily_rewards' and quests~=nil and activity~=nil end,
  select=function(k,option)
   if shops[k] then
    local s=shops[k];local shortage,locked,missing=false,false,false
    for _,wanted in ipairs(s.items) do
     if k~='fishing_shop' or wanted[1]~=11010 or option==1 then
      local matched=false
      local configs={};for _,c in pairs(ExchangeData[s.config] or {}) do configs[#configs+1]=c end
      table.sort(configs,function(a,b) return a.id<b.id end)
      for _,c in ipairs(configs) do
       if c.item_bid==wanted[1] and (c[limits[wanted[2]]] or 0)>0 then
        matched=true;assert(allowed(c,s,wanted[2]),'shop configuration changed')
        local ref=snapshot[refs[wanted[2]]];assert(uint(ref) and ref>ctx.now(),'invalid shop refresh time')
        local used=count(snapshot,c.id,wanted[2]);local remain=c[limits[wanted[2]]]-used
        assert(remain>=0,'purchase count exceeds limit')
        if remain>0 then
         if not unlocked(c) then locked=true
         else
          local unit=price(c);local n=math.min(remain,math.floor(balance(s)/unit),999)
          if n>0 then return {kind=k,scope=scope(k),id=c.id,bid=c.item_bid,name=c.item_name,shop=s.type,
           period=wanted[2],ref=ref,before=used,num=n,amount=n*c.item_num,price=unit,limit=c[limits[wanted[2]]],day=day()}
          else shortage=true end
         end
        end
       end
      end
      if not matched then missing=true end
     end
    end
    return nil,shortage and 'shop_funds_short' or locked and 'shop_locked' or missing and 'shop_product_missing' or 'supply_complete'
   end
   -- Claim ready daily quests first: they award activity and can unlock the daily reward.
   local ids={};for _,q in ipairs(quests.quest_list) do
    assert(uint(q.id) and uint(q.finish) and q.finish<=2,'invalid daily quest')
    if q.finish==1 and QuestData.data_get_day[q.id] then ids[#ids+1]=q.id end
   end;table.sort(ids)
   if #ids>0 then local id=ids[1];return {kind=k,scope=scope(k),action='quest',id=id,name=QuestData.data_get_day[id].name,day=day()} end
   assert(uint(role().activity),'invalid activity')
   local ids={};for _,c in pairs(ActivityData.data_get) do
    if c.activity<=role().activity and not state('activity',c.activity) then ids[#ids+1]=c.activity end
   end;table.sort(ids)
   if #ids>0 then return {kind=k,scope=scope(k),action='activity',ids=ids,name='每日活跃度奖励',amount=#ids,day=day()} end
   return nil,'rewards_complete'
  end,
  save=function(k,p) ud:setStringForKey(key(k),json.encode(p));ud:flush() end,
  act=function(p)
   internal=true;local ok,e=pcall(function()
    if p.shop then
     local c=product(p.kind,p);assert(c and allowed(c,shops[p.kind],p.period) and unlocked(c) and price(c)==p.price
      and c.item_bid==p.bid and c[limits[p.period]]==p.limit and balance(shops[p.kind])>=p.num*p.price,'purchase changed before send')
     mall:sender13402(p.id,p.num)
    elseif p.action=='quest' then task:requestSubmitTask(p.id,TaskConst.type.quest)
    else task:requestGetActivityAwards(0) end
   end);internal=false;if not ok then error(e) end
  end,
  reply=function(p,id,d)
   if p.shop and id==13402 and d.type==p.shop and d.eid==p.id then return d.code==1
   elseif p.action=='quest' and id==10406 and d.type==3 then
    for _,n in ipairs(d.nodes or {}) do if n.id==p.id then return d.flag==1 end end
    if d.flag~=1 then return false end
   elseif p.action=='activity' and id==20301 and d.activity==0 then return d.code==1 end
  end,
  verify=function(p)
   if p.scope~=scope(p.kind) then return false,'guild_changed' end
   if p.shop then
    local ref=snapshot[refs[p.period]]
    if ref~=p.ref then
     if uint(ref) and ref>p.ref and ctx.now()>=p.ref then return false,'new_period' end
     return false,'shop_period_changed'
    end
    if count(snapshot,p.id,p.period)==p.before+p.num then return true end
   else
    if day()>p.day then return false,'new_period' end
    if p.action=='quest' then if state('quest',p.id)==2 then return true end
    else for _,id in ipairs(p.ids) do if not state('activity',id) then return false end end;return true end
   end
   return false,'previous_request_unresolved'
  end})
 for _,v in ipairs({{mall,'sender13402'},{task,'requestSubmitTask'},{task,'requestGetActivityAwards'}}) do
  ctx.patch(v[1],v[2],function(old) return function(self,...)
   if not internal then
    if runner.active then message('小助手正在购买或领奖，请稍后操作');return end
    manual_until=ctx.now()+20
   end
   return old(self,...)
  end end)
 end
 for _,v in ipairs({{mall,13401,'handle13401'},{mall,13402,'handle13402'},{task,10400,'on10400'},
  {task,10406,'on10406'},{task,20300,'on20300'},{task,20301,'on20301'}}) do
  local id=v[2];ctx.patch(v[1],v[3],function(old) return function(self,d)
   old(self,d);if runner.active then ctx.safe(function() runner:onPacket(id,d) end) end
  end end)
 end
 runner.load=load;runner.shops=shops
 return runner,function() return ctx.now()<manual_until or mall.mall_buy_win~=nil end
end
return M
