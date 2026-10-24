-- Original controller senders only. No battle skip, settlement wait or paid fallback.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.bind(Extras,ctx)
 local gc=GuildbossController:getInstance();local tc=JiaLingPassController:getInstance()
 local sc=CommonGiftShopController:getInstance();local hc=HeroController:getInstance()
 local bc=BattleController:getInstance();local ud=cc.UserDefault:getInstance()
 local runner,internal,manual_until=nil,false,0
 local owned_battles={}
 local function day() local t=ctx.now();local d=TimeTool.getDayAnyHourTime(t,5);return d>t and d-86400 or d end
 local function key(k) return 'dldl_extras_v1:'..assert(ctx.roleKey())..':'..k end
 local function log(e,d)
  pcall(function()
   local f=assert(io.open(cc.FileUtils:getInstance():getWritablePath()..'dldl_extras_trace.log','a'))
   f:write(tostring(ctx.now()),'|',e,'|',tostring(d),'\n');f:close()
  end)
 end
 local function formType(k) return k=='guild_trial' and PartnerConst.Fun_Form.GuildNewSingleBoss or PartnerConst.Fun_Form.JiaLingPass end
 local function freeGift()
  local c=CommonGiftData.data_shop[23] and CommonGiftData.data_shop[23][2301]
  if not c or c.type~=2 or c.id~=23 or c.gift_id~=2301 or c.gift_type~=1 or c.charge_id~=0
   or c.charge_acc~=0 or c.activity~=0 or c.limit_type~=1 or c.limit_times~=1
   or type(c.cost)~='table' or next(c.cost) or type(c.limit_cond)~='table' or next(c.limit_cond)
   or type(c.reward)~='table' or #c.reward~=2 then return false end
  local items={};for _,v in ipairs(c.reward) do if items[v[1]] then return false end;items[v[1]]=v[2] end
  return items[52026]==1 and items[52025]==100
 end
 local function guard(k)
  if not ctx.connected() then return 'connection_unavailable' end
  if ctx.now()<manual_until then return 'manual_claim_pending' end
  local r=RoleController:getInstance():getRoleVo()
  local open= k=='guild_trial' and 'guild_new_boss_limit' or k=='temple_duel' and 'arena_mine_open_new_limit' or 'soul_guider_open_cond'
  if not SysController:getInstance():checkIsOpenByKey(open,false) then return 'not_open' end
  if k=='guild_trial' and (not uint(r.gid) or r.gid==0) then return 'no_guild' end
  if k=='workshop_gift' then if not freeGift() then return 'gift_config_changed' end;return end
  -- Different background combat types may coexist; only this type/replay blocks.
  local t=k=='guild_trial' and 38 or 86
  if bc:getFightTypeInfo(t) or bc:getWatchReplayStatus() then return 'battle_busy' end
 end
 runner=Extras.new({identity=ctx.identity,now=ctx.now,day=day,log=log,guard=guard,freeGift=freeGift,formType=formType,
  queueBusy=ctx.busy,
  accepted=function(k) owned_battles[k]={identity=ctx.identity(),day=day()} end,
  conflict=function(k)
   local other=k=='guild_trial' and 'temple_duel' or 'guild_trial'
   local own=owned_battles[other]
   return own and own.identity==ctx.identity() and own.day==day()
    and bc:getFightTypeInfo(other=='guild_trial' and 38 or 86)~=nil
    and bc:getFightTypeInfo(other=='guild_trial' and 38 or 86)~=false
  end,
  checkForm=function(d)
   local c=FormationData.data_form_data[d.formation_type]
   if not c or type(d.pos_info)~='table' or #d.pos_info==0 then return 'empty_quest_formation' end
   local allowed,positions,heroes={},{},{};for _,v in ipairs(c.pos or {}) do allowed[v[1]]=true end
   for _,v in ipairs(d.pos_info) do
    if not uint(v.pos) or not allowed[v.pos] or positions[v.pos] or not uint(v.id) or v.id==0 or heroes[v.id] or not hc:getModel():getHeroById(v.id) then return 'invalid_quest_formation' end
    positions[v.pos]=true;heroes[v.id]=true
   end
  end,
  guildBoss=function(id) return GuildNewBossData.data_boss_get[id]~=nil end,
  guildAvailable=function(d)
   local c=GuildNewBossData.data_constant
   return uint(c.attr_free_times.val) and uint(c.day_kill_times.val) and d.used_time<c.attr_free_times.val
    and (d.is_last_boss==1 or d.day_combat_time<c.day_kill_times.val)
  end,
  templeDailyCount=function() return DesisiveBattleData.data_const.battle_day_gain_num.val end,
  pending=function(k) return ud:getIntegerForKey(key(k)..':pending',0)~=0 end,
  completed=function(k) return ud:getIntegerForKey(key(k)..':completed_day',-1)==day() end,
  save=function(k,state,a)
   local b=key(k)
   -- Persist completion first; an interrupted flush must remain conservative.
   if state=='completed' then ud:setIntegerForKey(b..':completed_day',a.day) end
   ud:setIntegerForKey(b..':pending',state=='pending' and 1 or 0)
   ud:setIntegerForKey(b..':sent_day',a.day);ud:flush()
  end,
  query=function(k,kind)
   log('query',k)
   if k=='form' then hc:sender11211(formType(kind))
   elseif k=='guild_trial' then gc:send29720()
   elseif k=='temple_duel' then tc:sender28700();tc:sender28703()
   elseif k=='workshop_gift' then sc:send10572(2,0) end
  end,
  act=function(k)
   internal=true;log('act',k)
   local ok,err=pcall(function()
    if k=='guild_trial' then gc:send29721()
    elseif k=='temple_duel' then tc:sender28702()
    elseif k=='workshop_gift' then sc:send10573(2,0,2301,1) end
   end)
   internal=false;if not ok then error(err) end
  end})
 for _,p in ipairs({{gc,'send29721'},{gc,'send29723'},{gc,'send29725'},{gc,'send29730'},
  {tc,'sender28702'},{sc,'send10573'}}) do
  ctx.patch(p[1],p[2],function(old) return function(obj,...)
   if not internal and (ctx.busy() or runner.active) then message(TI18N('小助手正在核实任务，请稍后操作'));return end
   if not internal then manual_until=ctx.now()+15 end
   return old(obj,...)
  end end)
 end
 -- 28702 is callback-only in the official controller. Keep any original callback.
 ctx.patch(tc,'SendProtocal',function(old) return function(obj,id,d,cb,...)
  if id~=28702 or not internal or not runner.active then return old(obj,id,d,cb,...) end
  local owned=runner.active
  return old(obj,id,d,function(reply)
   if cb then cb(reply) end
   log('challenge_reply',id..'|code='..tostring(type(reply)=='table' and reply.code))
   if runner.active==owned then ctx.safe(function() runner:onPacket(id,reply) end) end
  end,...)
 end end)
 for _,p in ipairs({{gc,29720},{gc,29721},{tc,28700},{tc,28703},{sc,10572},{sc,10573},{hc,11211}}) do
  local id=p[2]
  ctx.patch(p[1],'handle'..id,function(old) return function(obj,d)
   old(obj,d)
   if runner.active then ctx.safe(function()
    local fields={}
    for _,k in ipairs({'code','type','bid','id','gift_id','buy_num','boss_id','used_time','buy_time','day_combat_time','status','day_num'}) do
     if d[k]~=nil then fields[#fields+1]=k..'='..tostring(d[k]) end
    end
    if id==10572 then for _,v in ipairs(d.gift_list or {}) do if v.gift_id==2301 then fields[#fields+1]='free_buy_num='..tostring(v.buy_num) end end end
    log('packet',id..'|'..table.concat(fields,'|'));runner:onPacket(id,d)
   end) end
  end end)
 end
 return runner,function() return ctx.now()<manual_until end
end
return M
