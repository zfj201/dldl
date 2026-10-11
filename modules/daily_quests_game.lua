-- Scoped original protocol senders, saved formations and native battle skip.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
local function supported(k) return k=='guild_wish' or k=='ruins' end
function M.bind(Quests,ctx)
 local gc=GuildController:getInstance();local rc=GodRuinsController:getInstance()
 local hc=HeroController:getInstance();local hm=hc:getModel();local bc=BattleController:getInstance();local ud=cc.UserDefault:getInstance()
 local runner,internal,manual_until,result_views=nil,false,0,nil
 local function role() return RoleController:getInstance():getRoleVo() end
 local function day() local t=ctx.now();local d=TimeTool.getDayAnyHourTime(t,5);return d>t and d-86400 or d end
 local function key(kind) assert(supported(kind),'unknown quest');return 'dldl_quests_v1:'..assert(ctx.roleKey())..':'..kind end
 local function diamonds() return BackpackController:getInstance():getModel():getItemNumByBid(3) end
 -- One audited v2 win only; this token cannot recover arbitrary pending records.
 local recovery_token='phase11v2-win|yinghe_3356:5005|1791666000|1791715275|7789ef7f68b74ad86e950d09ce36b9a3649e82f36872d948f2743c3346d66dcb|13105:1:0|13106:1791715277:1:1:77|before:11315:2:1791789774:0:94178|after:11201:1:1791801676:1:0:94178'
 local function recoveryFile(suffix) return cc.FileUtils:getInstance():getWritablePath()..'dldl_ruins_v2_reconcile.'..suffix end
 local function recoveryRequest()
  local ok,token=pcall(function() local f=io.open(recoveryFile('request'),'r');if not f then return nil end;local s=f:read('*a');f:close();return s:match('^%s*(.-)%s*$') end)
  return ok and token==recovery_token
 end
 local function recoveryBaseline()
  if not recoveryRequest() or ctx.roleKey()~='yinghe_3356:5005' or day()~=1791666000 then return nil,'recovery_evidence_mismatch' end
  local k=key('ruins')
  local fields={pending=1,day=1791666000,sent_at=1791715275,before_boss_id=11315,before_kill_time=2,
   before_end_time=1791789774,before_fight_time=0,before_diamonds=94178}
  for f,v in pairs(fields) do if ud:getIntegerForKey(k..':'..f,-1)~=v then return nil,'recovery_journal_mismatch' end end
  if ud:getIntegerForKey(key('guild_wish')..':pending',0)~=0 then return nil,'recovery_other_pending' end
  return {boss_id=11201,kill_time=1,end_time=1791801676,fight_time=1,hp_per=0,diamonds=94178}
 end
 local function log(e,d)
  pcall(function() if not runner or not runner.active then return end
   local f=assert(io.open(cc.FileUtils:getInstance():getWritablePath()..'dldl_quests_trace.log','a'));f:write(tostring(ctx.now()),'|',e,'|',tostring(d),'\n');f:close()
  end)
 end
 local function checkForm(data)
  if type(data)~='table' or type(data.pos_info)~='table' or #data.pos_info==0 then return 'empty_quest_formation' end
  local cfg=FormationData.data_form_data[data.formation_type]
  if not cfg then return 'invalid_quest_formation' end
  local allowed,positions,ids={},{},{};for _,p in ipairs(cfg.pos or {}) do allowed[p[1]]=true end
  for _,v in ipairs(data.pos_info) do
   if not uint(v.pos) or not allowed[v.pos] or positions[v.pos] or not uint(v.id) or v.id==0 or ids[v.id] or not hm:getHeroById(v.id) then return 'invalid_quest_formation' end
   positions[v.pos]=true;ids[v.id]=true
  end
 end
 local function battleReady()
  if bc.getWatchReplayStatus and bc:getWatchReplayStatus() then return false end
  local a=runner and runner.active;local own=a and a.kind=='ruins' and a.phase=='cleanup'
  local won=bc.finish_result_view_list and bc.finish_result_view_list[77];local lost=bc.finish_fail_view_list and bc.finish_fail_view_list[77]
  if won or lost then
   if not own or not result_views or (won and won~=result_views.won) or (lost and lost~=result_views.lost) then return false end
   if won and won.fight_type==77 and won.isOpen and won:isOpen() and won.root_wnd and won.onCloseBtn then log('close_result','won');won:onCloseBtn();return false end
   if lost and lost.fight_type==77 and lost.isOpen and lost:isOpen() and lost.root_wnd and lost.item_scroll then log('close_result','lost');lost:close();return false end
   return false
  end
  if bc:getFightTypeInfo(77) then return false end
  return not bc:isInFight()
 end
 local function openGuard(k)
  local r=role()
  if k=='guild_wish' then if not uint(r.gid) or r.gid==0 then return 'no_guild' end
  elseif not SysController:getInstance():checkIsOpenByKey('temple_boss_open') then return 'not_open' end
 end
 local function guildScope(d) local r=role();return d.gid==r.gid and d.gid>0 and d.gsrv_id==r.gsrv_id end
 runner=Quests.new({identity=ctx.identity,day=day,now=ctx.now,log=log,diamonds=diamonds,checkForm=checkForm,
  recoveryRequest=recoveryRequest,recoveryBaseline=recoveryBaseline,
  reportRecovery=function(status,reason)
   pcall(function()
    local f=assert(io.open(recoveryFile('result'),'a'))
    f:write(tostring(ctx.now()),'|',tostring(ctx.roleKey()),'|',tostring(day()),'|',status,'|',tostring(reason),'|sent_at=1791715275|before=11315/2/1791789774/0/94178|after=11201/1/1791801676/1/0/94178\n');f:close()
    if status=='confirmed' and reason=='ruins_v2_rotation_reconciled' then os.remove(recoveryFile('request')) end
   end)
  end,
  guildScope=guildScope,openGuard=openGuard,ruinsBoss=function(id) return TempleBossData.data_get_boss[id]~=nil end,
  pending=function(k) return supported(k) and ud:getIntegerForKey(key(k)..':pending',0)~=0 end,
  savePending=function(k,pending,a)
   local base=key(k);ud:setIntegerForKey(base..':pending',pending and 1 or 0)
   if a then
    ud:setIntegerForKey(base..':day',a.day);ud:setIntegerForKey(base..':sent_at',ctx.now())
    local b=a.base or {};for _,f in ipairs({'kill_time','boss_id','end_time','fight_time'}) do ud:setIntegerForKey(base..':before_'..f,b[f] or -1) end
    ud:setIntegerForKey(base..':before_diamonds',a.diamonds or -1)
   end
   ud:flush()
  end,
  query=function(k)
   local r=role();log('query',k..'|role='..tostring(ctx.roleKey())..'|vip='..tostring(r.vip_lev)..'|gid='..tostring(r.gid)..'|gsrv='..tostring(r.gsrv_id)..'|gold='..tostring(r.gold)..'|red_gold='..tostring(r.red_gold)..'|diamonds='..tostring(diamonds()))
   if k=='guild_wish' then gc:SendProtocal(13518,{})
   elseif k=='ruins_form' then hc:sender11211(92)
   elseif k=='ruins' then rc:reqBaseData() end
  end,
  guard=function(k,a,action)
   local why=openGuard(k);if why then return why end
   if action=='wish' then if not guildScope(a.base) then return 'guild_changed' end;return end
   if checkForm(a.form) then return 'invalid_quest_formation' end
   if not battleReady() then return 'battle_busy' end
   if not uint(diamonds()) then return 'invalid_inventory' end
   if a.base.end_time<=ctx.now() then return 'ruins_expired' end
   if action=='ruins_challenge' and diamonds()~=a.diamonds then return 'inventory_changed' end
  end,
  battleReady=battleReady,
  nativeSkip=function(a)
   if a.skip_sent or not bc:isInFight() or bc:getWatchReplayStatus() then return end
   local t=77
   if not bc:getIsSameBattleType(t) then return end
   local p=bc:getBattleUIPanel()
   if not p or not p.root_wnd or p.battle_type~=t or not p.skip_btn or not p.skip_btn:isVisible() or not p.onClickSkipBtn then return end
   local c=CombatTypeData.data_fight_list[t];if not c or c.is_skip~='true' then return end
   internal=true;a.skip_sent=true;log('native_skip',t)
   local ok,err=pcall(function() p:onClickSkipBtn() end);internal=false;if not ok then error(err) end
  end,
  act=function(action)
   internal=true;log('act',action)
   local ok,err=pcall(function()
    if action=='wish' then gc:send13548(2)
    elseif action=='ruins_challenge' then rc:reqChallenge(0) end
   end)
   internal=false;if not ok then error(err) end
  end})
 -- Block manual mutations for every queue owner, preserving the exact originals.
 for _,p in ipairs({{rc,'reqChallenge'},
  {rc,'reqRefreshBoss'},{rc,'reqShareBoss'},{rc,'reqDailyReward'},{rc,'reqStarReward'},{gc,'send13548'},{bc,'send20062'}}) do
  ctx.patch(p[1],p[2],function(old) return function(obj,...)
   if not internal and ctx.busy() then message(TI18N('小助手正在核实任务，请稍后操作'));return end
   if not internal then manual_until=ctx.now()+15 end
   return old(obj,...)
  end end)
 end
 -- Capture callback-only replies without replacing existing callbacks.
 for _,p in ipairs({{gc,13548},{rc,13105}}) do local id=p[2]
  ctx.patch(p[1],'SendProtocal',function(old) return function(obj,n,data,cb,...)
   if n~=id or not internal or not runner.active then return old(obj,n,data,cb,...) end
   local owned=runner.active
   return old(obj,n,data,function(reply)
    if cb then cb(reply) end
    if runner.active==owned then ctx.safe(function() runner:onPacket(n,reply) end) end
   end,...)
  end end)
 end
 -- Only the owned ruins battle is observed; original handlers still run.
 ctx.patch(bc,'scInitFightStart',function(old) return function(obj,data)
  old(obj,data)
  if runner.active and runner.active.kind=='ruins' and data and data.combat_type==77 then
   ctx.safe(function() runner:onBattleStart(data) end)
  end
 end end)
 ctx.patch(bc,'scReBattleFight',function(old) return function(obj,data)
  old(obj,data)
  if runner.active and runner.active.kind=='ruins' and data and data.combat_type==77 then
   ctx.safe(function() runner:onBattleStart(data) end)
  end
 end end)
 ctx.patch(bc,'scFightEnd',function(old) return function(obj,data)
  if runner.active and runner.active.kind=='ruins' and data and data.combat_type==77 then
   ctx.safe(function() runner:onBattleEnd(data) end)
  end
  return old(obj,data)
 end end)
 for _,p in ipairs({{gc,13518},{rc,13100},{rc,13106},{hc,11211}}) do local id=p[2]
  ctx.patch(p[1],'handle'..id,function(old) return function(obj,data)
   old(obj,data)
   ctx.safe(function()
    local a=runner.active
    if a and id==13106 and a.kind=='ruins' and (a.phase=='ruins_challenge' or a.phase=='battle' or a.phase=='battle_result') then
     local t=77
     result_views={won=bc.finish_result_view_list and bc.finish_result_view_list[t],lost=bc.finish_fail_view_list and bc.finish_fail_view_list[t]}
    end
    if id==13100 or id==13518 then
     local fields={};for _,k in ipairs({'gid','gsrv_id','wish_gift_type','boss_id','kill_time','hp_per','fight_time','end_time'}) do if data[k]~=nil then fields[#fields+1]=k..'='..tostring(data[k]) end end
     log('baseline',id..'|'..table.concat(fields,'|'))
    elseif id==11211 then log('formation','type='..tostring(data.type)..'|saved_positions='..tostring(data.pos_info and #data.pos_info)) end
    runner:onPacket(id,data)
   end)
  end end)
 end
 return runner,function(current)
  if ctx.now()<manual_until then return true end
  for _,k in ipairs({'guild_wish','ruins'}) do
   if k~=current and ud:getIntegerForKey(key(k)..':pending',0)~=0 then return true end
  end
  return false
 end
end
return M
