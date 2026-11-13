-- Sanpao orchestration through native start/settle/reward protocols.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.plan(b,cfg,level)
 if type(b)~='table' or not uint(b.open_day) or not uint(b.num) or not uint(b.all_score) or not uint(b.camp_id)
  or (b.status~=0 and b.status~=1) or type(b.chapter_list)~='table' or type(b.reward_list)~='table' then return nil,'invalid_state' end
 local opens=cfg.data_open[b.camp_id];local rounds=cfg.data_customs[b.camp_id];local rewards=cfg.data_reward[b.camp_id]
 if not opens or not rounds or not rewards then return nil,'unknown_config' end
 local chapters,claimed,pass={},{},0
 for _,v in ipairs(b.chapter_list) do
  if not uint(v.chapter_id) or chapters[v.chapter_id] or (v.is_pass~=0 and v.is_pass~=1) or (v.status~=0 and v.status~=1) or not uint(v.score) then return nil,'invalid_state' end
  chapters[v.chapter_id]=v;if v.is_pass==1 then pass=math.max(pass,v.chapter_id) end
 end
 for _,v in ipairs(b.reward_list) do if not uint(v.reward_id) then return nil,'invalid_state' end;claimed[v.reward_id]=true end
 local p={rewards={},chapter=nil,score=b.all_score}
 for _,v in ipairs(rewards) do if b.all_score>=v.score and not claimed[v.reward_id] then p.rewards[#p.rewards+1]=v.reward_id end end
 local ids={};for id in pairs(opens) do ids[#ids+1]=id end;table.sort(ids)
 for _,id in ipairs(ids) do
  local c=opens[id];local v=chapters[id];if not v or not rounds[id] then return nil,'unknown_config' end
  local allowed=v.status==1 and v.is_pass==0
  for _,cond in ipairs(c.conds) do
   if cond[1]=='lev' then allowed=allowed and level>=cond[2]
   elseif cond[1]=='holiday_day' then allowed=allowed and b.open_day>=cond[2]
   elseif cond[1]=='chapter_id' then allowed=allowed and pass>=cond[2]
   else return nil,'unknown_config' end
  end
  if allowed and not p.chapter then p.chapter=id end
 end
 return p
end
function M.target(cfg,camp,id)
 local rounds=cfg.data_customs[camp] and cfg.data_customs[camp][id]
 local open=cfg.data_open[camp] and cfg.data_open[camp][id]
 if not rounds or not open or #rounds==0 then return end
 local score=0
 for i,v in ipairs(rounds) do
  if v.dun_id~=i or not uint(v.all_score) or not uint(v.score) or v.score==0 or not uint(v.arrow_num)
   or v.all_score~=v.score*v.arrow_num then return end
  score=score+v.all_score
 end
 if score~=open.chapter_score then return end
 return score,#rounds
end
function M.new(env)
 local self={}
 function self:finish(status,reason)
  local a=self.active;if not a then return end;self.active=nil;a.status=status;a.reason=reason
  if a.changed then a.changed(a) end;if a.done then a.done(a) end
 end
 function self:query() local a=self.active;a.phase='query';a.deadline=env.now()+15;env.query() end
 function self:start(done,changed)
  if self.active then return false,'busy' end
  self.active={identity=env.identity(),day=env.day(),entries={},claimed=0,done=done,changed=changed}
  local why=env.guard();if why then self:finish('skipped',why);return true end
  local old=env.load();self.active.pending=old and old.pending
  self:query();return true
 end
 function self:save() env.save(self.active) end
 function self:send(kind)
  local a=self.active;a.phase=kind;a.deadline=env.now()+15;self:save();env.act(kind,a.pending)
 end
 function self:onInfo(b)
  local a=self.active;if not a or a.phase~='query' then return end
  if a.camp and a.camp~=b.camp_id then self:finish('uncertain','activity_changed');return end;a.camp=b.camp_id
  local p,why=M.plan(b,env.config(),env.level());if not p then self:finish('uncertain',why);return end
  local pending=a.pending
  if pending then
   if pending.camp~=b.camp_id then a.pending=nil;self:save()
   elseif pending.kind=='claim' then
    local got={};for _,v in ipairs(b.reward_list) do got[v.reward_id]=true end
    for _,id in ipairs(pending.ids) do if not got[id] then self:finish('uncertain','reward_unconfirmed');return end end
    a.claimed=a.claimed+#pending.ids;a.pending=nil;self:save()
   else
    local v;for _,c in ipairs(b.chapter_list) do if c.chapter_id==pending.chapter then v=c end end
    if v and v.is_pass==1 and v.score==pending.score then
     a.entries[#a.entries+1]={chapter=v.chapter_id,score=v.score};a.pending=nil;self:save()
    elseif pending.kind=='start' and b.status==1 then
     local score,round=M.target(env.config(),b.camp_id,pending.chapter)
     if not v or v.status~=1 or score~=pending.score or round~=pending.round then self:finish('uncertain','invalid_state');return end
     pending.kind='settle';self:send('settle');return
    else self:finish('uncertain','request_unresolved');return end
   end
  end
  a.score=p.score;if a.changed then a.changed(a) end
  if #p.rewards>0 then a.pending={kind='claim',camp=b.camp_id,ids=p.rewards};self:send('claim');return end
  if not p.chapter then self:finish('done','available_complete');return end
  if b.status==1 then self:finish('uncertain','manual_game_pending');return end
  if b.num==0 then self:finish('partial','no_attempts');return end
  local score,round=M.target(env.config(),b.camp_id,p.chapter)
  if not score then self:finish('uncertain','unknown_config');return end
  a.pending={kind='start',camp=b.camp_id,chapter=p.chapter,score=score,round=round};self:send('start')
 end
 function self:onReply(kind,d)
  local a=self.active;if not a or a.phase~=kind then return end
  if d.code~=nil and d.code~=1 then self:finish('partial','action_rejected');return end
  self:query()
 end
 function self:tick()
  local a=self.active;if not a then return end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('uncertain','role_or_day_changed');return end
  local why=env.guard();if why then self:finish('uncertain',why);return end
  if env.now()>a.deadline then self:finish('uncertain','response_timeout') end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 return self
end
return M
