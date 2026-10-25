-- Serial dispatch/refresh controller. Only confirmed server changes advance progress.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.select(c)
 if type(c)~='table' or not uint(c.quality) or type(c.award)~='table' then return nil end
 for _,v in ipairs(c.award) do
  if type(v)~='table' or not uint(v[1]) or v[1]==0 or not uint(v[2]) or v[2]==0 then return nil end
 end
 if c.quality>3 then return true end
 if c.quality<1 then return false end
 for _,v in ipairs(c.award) do
  if (v[1]==3 or v[1]==10019) and type(v[2])=='number' and v[2]>0 then return true end
 end
 return false
end
function M.new(env)
 local self={env=env,progress=0}
 function self:publish()
  local a=self.active or self.last
  if a then env.save(a);if a.changed then a.changed(a) end end
 end
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  a.status=status;a.reason=reason;self.last=a;self.active=nil
  if a.identity==env.identity() then self:publish() end;if a.done then a.done(a) end
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or (a.check_day or a.day)~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard();if why then self:finish(a.pending and 'uncertain' or 'error',why);return false end
  return true
 end
 function self:query(phase)
  local a=self.active;a.phase=phase or 'query';a.info=nil;a.activity=nil;a.deadline=env.now()+20
  env.query()
 end
 function self:start(done,changed)
  if self.active then return false,'busy' end
  local id=env.identity();if not id then return false,'no_role' end
  local previous=env.load()
  if previous and previous.pending then
   self.active=previous;previous.identity=id;previous.done=done;previous.changed=changed;previous.recovery=true;previous.check_day=env.day()
   previous.status='running';previous.reason=nil
  else
   self.active={id=env.runId(),identity=id,day=env.day(),entries={},refresh={free=0,ticket=0,diamond=0,tickets=0,diamonds=0},
    progress=0,status='running',done=done,changed=changed}
  end
  if not self:valid() then return true end
  self:publish();self:query();return true
 end
 function self:balance()
  local b=env.balance()
  if type(b)~='table' or not uint(b.energy) or not uint(b.cache) or not uint(b.tickets) or not uint(b.diamonds) then return nil end
  return b
 end
 function self:cost(c,activity)
  if type(c.expend)~='table' or #c.expend~=1 or c.expend[1][1]~=7 or not uint(c.expend[1][2]) or c.expend[1][2]==0 then return nil end
  local value=c.expend[1][2]
  if activity==1 then
   local d=env.discount();if not uint(d) or d==0 or d>1000 then return nil end
   value=value*d/1000
  end
  if not uint(value) or value==0 then return nil end
  return value
 end
 function self:orders(info)
  if type(info.order_list)~='table' or not uint(info.free_times) or not uint(info.coin_times) or not uint(info.lev) then return nil end
  local rows,seen={},{}
  for _,o in ipairs(info.order_list) do
   if not uint(o.order_id) or o.order_id==0 or seen[o.order_id] or not uint(o.order_bid)
    or (o.status~=1 and o.status~=2 and o.status~=3) then return nil end
   seen[o.order_id]=true
   local c=env.config(o.order_bid)
   if type(c)~='table' or type(c.name)~='string' or M.select(c)==nil then return nil end
   rows[#rows+1]={order=o,config=c}
  end
  return rows
 end
 function self:mutate(kind,order,cost,assign,pay)
  if not self:valid() then return end
  local a=self.active;local b=self:balance();if not b then self:finish('error','invalid_assets');return end
  local p={kind=kind,at=env.now(),before=b,free=a.info.free_times,coin=a.info.coin_times,pay=pay}
  if kind=='dispatch' then
   if b.energy<cost then self:query();return end
   p.order_id=order.order_id;p.order_bid=order.order_bid;p.cost=cost
   local c=env.config(order.order_bid)
   p.name=c.name;p.quality=c.quality;p.award=c.award
  end
  a.rechecked=nil;a.pending=p;a.phase='reply';a.deadline=env.now()+20;a.info=nil
  self:publish() -- durable pending must precede the normal sender
  env.act(kind,p,assign)
 end
 function self:confirmed()
  local a=self.active;local p=a.pending;local b=self:balance()
  if not b or not a.info then return false end
  if b.manual_epoch~=p.before.manual_epoch then return false end
  local rows=self:orders(a.info);if not rows then self:finish('uncertain','invalid_order_state');return true end
  if p.kind=='dispatch' then
   local target
   for _,r in ipairs(rows) do local o=r.order
    if o.order_id==p.order_id and o.order_bid==p.order_bid and o.status~=1 and uint(o.end_time) and o.end_time>=p.at then target=o;break end
   end
   if not target then return false end
   -- A server state change also recovers a lost acknowledgement. Wait for asset
   -- delivery before allowing another mutation, including cache refills.
   if b.energy+b.cache>p.before.energy+p.before.cache-p.cost then return false end
   a.entries[#a.entries+1]={sequence=#a.entries+1,order_id=p.order_id,order_bid=p.order_bid,name=p.name,
    quality=p.quality,award=p.award,cost=p.cost,end_time=target.end_time,status='dispatched'}
  else
   local pay=p.pay;local r=a.refresh
   if pay.kind=='free' then if a.info.free_times~=p.free+1 then return false end
   elseif pay.kind=='ticket' then if b.tickets~=p.before.tickets-pay.num then return false end
   elseif pay.kind=='diamond' then
    if a.info.coin_times~=p.coin+1 or b.diamonds~=p.before.diamonds-pay.num then return false end
   else self:finish('uncertain','invalid_refresh_config');return true end
   r[pay.kind]=r[pay.kind]+1
   if pay.kind=='ticket' then r.tickets=r.tickets+pay.num end
   if pay.kind=='diamond' then r.diamonds=r.diamonds+pay.num end
  end
  a.pending=nil;a.progress=(a.progress or 0)+1;self.progress=self.progress+1
  a.remaining=b.energy+b.cache;self:publish()
  if a.recovery then self:finish('confirmed','previous_request_recovered')
  else a.phase='pause';a.next_at=env.now()+1;a.deadline=env.now()+20 end
  return true
 end
 function self:decide()
  local a=self.active;local rows=self:orders(a.info);local b=self:balance()
  if not rows then self:finish('error','invalid_order_state');return end
  if not b then self:finish('error','invalid_assets');return end
  a.remaining=b.energy+b.cache
  local floor=env.costFloor(a.activity)
  if not uint(floor) or floor==0 then self:finish('error','invalid_cost_config');return end
  if b.energy<floor then
   if b.cache>0 then
    a.cache_wait=a.cache_wait or env.now()
    if env.now()-a.cache_wait<10 then a.phase='cache_wait';a.next_at=env.now()+2;return end
    self:finish('confirmed','energy_cache_unavailable')
   else self:finish('confirmed','insufficient_intelligence') end
   return
  end
  a.cache_wait=nil
  local candidates,unget={},0
  for _,r in ipairs(rows) do
   if r.order.status==1 then
    unget=unget+1
    if M.select(r.config) then candidates[#candidates+1]=r end
   end
  end
  table.sort(candidates,function(x,y)
   if x.config.quality~=y.config.quality then return x.config.quality>y.config.quality end
   return x.order.order_id<y.order.order_id
  end)
  if #candidates>0 then
   local r=candidates[1];local cost=self:cost(r.config,a.activity)
   if not cost then self:finish('error','invalid_cost_config');return end
   if b.energy<cost then self:finish('confirmed','insufficient_intelligence');return end
   local assign,why=env.assign(a.info.lev,r.config)
   if not assign then self:finish('error',why or 'dispatch_conditions_unmet');return end
   self:mutate('dispatch',r.order,cost,assign);return
  end
  if unget==0 then self:finish('confirmed','no_refreshable_orders');return end
  local pay,why=env.payment(a.info,b)
  if not pay then self:finish('confirmed',why or 'refresh_unavailable');return end
  self:mutate('refresh',nil,nil,nil,pay)
 end
 function self:onPacket(id,data)
  if not self:valid() or type(data)~='table' then return end
  local a=self.active
  if id==23800 then a.info=data
  elseif id==23805 and (data.flag==0 or data.flag==1) then a.activity=data.flag
  elseif a.pending and ((a.pending.kind=='dispatch' and id==23802) or (a.pending.kind=='refresh' and id==23804)) then
   if data.flag==0 then
    a.pending=nil;self:finish('error','action_rejected');return
   elseif data.flag==1 then self:query('verify');return end
  elseif id==23801 and a.pending then
   -- Query the entire list; this update may precede the acknowledgement.
   a.phase='verify';a.next_query=env.now()+1
  end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if a.pending then
   if a.info and self:confirmed() then return end
   if not self.active then return end
   if env.now()>=a.deadline then
    if not a.rechecked then a.rechecked=true;self:query('verify')
    else self:finish('uncertain','request_unresolved') end
   elseif a.phase=='verify' and env.now()>=(a.next_query or 0) then a.next_query=env.now()+2;env.query() end
   return
  end
  if a.phase=='pause' or a.phase=='cache_wait' then
   if env.now()>=a.next_at then self:query() end
  elseif a.info and a.activity~=nil then self:decide()
  elseif env.now()>=a.deadline then self:finish('error','query_timeout') end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 function self:fail() self:finish(self.active and self.active.pending and 'uncertain' or 'error','runtime_error') end
 return self
end
return M
