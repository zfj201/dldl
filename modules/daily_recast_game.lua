-- Only backpack 13001/13002; no saving/replacing, equipment moves or purchases.
local M={}
local function uint(n) return type(n)=='number' and n>=0 and n%1==0 end
local function fields(list,k,v)
 if type(list)~='table' then return end
 local out={};for _,x in ipairs(list) do if not uint(x[k]) or not uint(x[v]) then return end;out[#out+1]=x[k]..'='..x[v] end
 table.sort(out);return table.concat(out,',')
end
local function signature(d,draft)
 local a=fields(draft and d.extra_attr or d.attr,'attr_id','attr_val');if not a then return end
 local skills={}
 for _,v in ipairs(d.extra or {}) do
  if (draft and (v.extra_k==3 or v.extra_k==4 or v.extra_k==9)) or (not draft and (v.extra_k==1 or v.extra_k==2 or v.extra_k==8)) then skills[#skills+1]=v end
 end
 local s=fields(skills,'extra_k','extra_v');if not s then return end
 return a..'|'..s
end
function M.bind(Recast,ctx)
 local h=HeroController:getInstance();local b=BackpackController:getInstance();local bag=b:getModel()
 local ud=cc.UserDefault:getInstance();local storage=BackPackConst.Bag_Code.BACKPACK
 local runner,internal,manual_until=nil,false,0
 local wanted,details,quota,verify_detail={},{},nil,nil
 local function key() return 'dldl_recast_v1:'..assert(ctx.roleKey()) end
 local function load()
  local text=ud:getStringForKey(key(),'');if text=='' then return {} end
  local d=json.decode(text);assert(type(d)=='table','invalid recast journal');return d
 end
 local function write(d) ud:setStringForKey(key(),json.encode(d));ud:flush() end
 local function day() return math.floor((ctx.now()+3*3600)/86400) end
 local function guard()
  if not ctx.connected() then return 'connection_unavailable' end
  if ctx.now()<manual_until or h.artifact_recast_win or h.artifact_select_skill_window then return 'manual_claim_pending' end
 end
 local function cost(bid)
  local cfg=PartnerArtifactData.data_artifact_data[bid]
  local expected=bid==13001 and {500,50000} or bid==13002 and {2500,100000}
  if not expected or not cfg or type(cfg.ref_expend)~='table' or #cfg.ref_expend~=2 then return end
  local values={};for _,v in ipairs(cfg.ref_expend) do if values[v[1]] then return end;values[v[1]]=v[2] end
  if values[10004]~=expected[1] or values[1]~=expected[2] then return end
  return expected
 end
 local function current(id) return bag:getBagItemById(storage,id) end
 local function eligible(d)
  if not d or (d.base_id~=13001 and d.base_id~=13002) or d.quantity~=1 or d.is_lock~=0
   or d.expire_type~=0 or not uint(d.id) or d.id==0 then return false end
  local cfg=ItemData.data_get_data(d.base_id)
  if not cfg or cfg.quality~=(d.base_id==13001 and 3 or 4) then return false end
  if type(d.extra)~='table' or type(d.extra_attr)~='table' or not signature(d,false) or #d.attr==0 then return false end
  -- Existing unsaved results may be overwritten, as explicitly requested.
  local q=quota and quota[d.base_id]
  if not q then return false end
  if d.base_id==13002 and q.current>0 and q.current>=q.limit then return false end
  return true
 end
 runner=Recast.new({identity=ctx.identity,day=day,now=ctx.now,guard=guard,load=load,
  query=function()
   wanted={};details={};quota=nil;verify_detail=nil
   local ids={}
   for _,v in pairs(bag:getBagItemList(storage) or {}) do
    local bid=v.base_id or (v.config and v.config.id)
    if (bid==13001 or bid==13002) and uint(v.id) and v.id>0 then wanted[v.id]=bid;ids[#ids+1]={id=v.id} end
   end
   if #ids>0 then b:send10506(storage,ids) end
   h:sender11048()
  end,
  receive=function(id,d)
   if id==11048 then
    if type(d.artifact_ref_count)~='table' then error('invalid recast counts') end
    local q={};for _,v in ipairs(d.artifact_ref_count) do
     assert(uint(v.base_id) and uint(v.current) and uint(v.limit) and not q[v.base_id],'invalid recast count')
     q[v.base_id]={current=v.current,limit=v.limit}
    end;quota=q
   elseif id==10506 and d.storage==storage then
    for _,v in ipairs(d.list or {}) do
     if wanted[v.id]==v.base_id then details[v.id]=deepCopy(v) end
     if runner.active and runner.active.phase=='verify' and runner.active.target.id==v.id then verify_detail=deepCopy(v) end
    end
   end
  end,
  select=function()
   if not quota then return nil,'awaiting_details' end
   for id in pairs(wanted) do if not details[id] then return nil,'awaiting_details' end end
   local all={};local short=false
   for id,d in pairs(details) do
    if eligible(d) then
     local c=cost(d.base_id)
     if not c then return nil,'recast_config_changed' end
     local essence,coin=bag:getItemNumByBid(10004),bag:getItemNumByBid(1)
     if uint(essence) and uint(coin) and essence>=c[1] and coin>=c[2] then
      all[#all+1]={id=id,bid=d.base_id,name=d.base_id==13001 and '紫品·八蛛矛' or '金品·八蛛矛',
       before=signature(d,false),draft=signature(d,true),essence=essence,coin=coin,cost_essence=c[1],cost_coin=c[2]}
     else short=true end
    end
   end
   if #all==0 then return nil,short and 'insufficient_recast_materials' or 'no_recast_target' end
   return all[math.random(#all)]
  end,
  recheck=function(t)
   local v=current(t.id);local c=cost(t.bid)
   if not v or (v.base_id or (v.config and v.config.id))~=t.bid or v.is_lock~=0 or v.quantity~=1
    or signature(v,false)~=t.before or signature(v,true)~=t.draft then return 'recast_target_changed' end
   if not c or c[1]~=t.cost_essence or c[2]~=t.cost_coin then return 'recast_config_changed' end
   if bag:getItemNumByBid(10004)~=t.essence or bag:getItemNumByBid(1)~=t.coin then return 'recast_resources_changed' end
  end,
  savePending=function(a) local d=load();d.pending={day=a.day,target=a.target};write(d) end,
  act=function(t)
   internal=true;local ok,e=pcall(function() h:sender11033(0,t.id,{},{}) end);internal=false;if not ok then error(e) end
  end,
  detail=function(id) verify_detail=nil;b:send10506(storage,{{id=id}}) end,
  verify=function(t)
   if not verify_detail then return end
   local d=verify_detail
   if d.base_id~=t.bid or d.quantity~=1 or not current(t.id) or signature(d,false)~=t.before then return false,'recast_target_changed' end
   if type(d.extra_attr)~='table' or #d.extra_attr==0 or not signature(d,true) then return false,'recast_result_missing' end
   local essence,coin=bag:getItemNumByBid(10004),bag:getItemNumByBid(1)
   if essence<t.essence-t.cost_essence or coin<t.coin-t.cost_coin then return false,'unexpected_recast_cost' end
   if essence==t.essence-t.cost_essence and coin==t.coin-t.cost_coin then return true end
  end,
  saveCompleted=function(a)
   local d=load();d.completed_day=a.day;d.target=a.target;d.pending=nil
   write(d)
  end})
 for _,name in ipairs({'sender11033','sender11034','sender11030','sender11035','sender11036'}) do
  ctx.patch(h,name,function(old) return function(self,...)
   if not internal and (runner.active or ctx.busy()) then message('小助手正在核实重铸，请稍后操作');return end
   if not internal then manual_until=ctx.now()+20 end
   return old(self,...)
  end end)
 end
 for _,p in ipairs({{h,11033},{h,11048},{b,10506}}) do
  local id=p[2];ctx.patch(p[1],'handle'..id,function(old) return function(self,d)
   old(self,d);if runner.active then ctx.safe(function() runner:onPacket(id,d) end) end
  end end)
 end
 runner.load=load
 return runner,function() return guard()=='manual_claim_pending' end
end
return M
