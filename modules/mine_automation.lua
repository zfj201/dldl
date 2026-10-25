-- One accepted challenge per game day, always on floor 50 / area 1.
local M={}
local function uint(v) return type(v)=='number' and v>=0 and v%1==0 end
function M.new(env)
 local self={env=env}
 function self:finish(status,reason)
  local a=self.active;if not a then return end
  self.active=nil;a.status=status;a.reason=reason;self.last=a
  if a.identity==env.identity() then env.save(a) end
  if a.done then a.done(a) end
 end
 function self:valid()
  local a=self.active;if not a then return false end
  if a.identity~=env.identity() or a.day~=env.day() then self:finish('cancelled','role_or_day_changed');return false end
  local why=env.guard(a);if why then self:finish(a.pending and 'uncertain' or 'error',why);return false end
  return true
 end
 function self:query(phase,id)
  local a=self.active;a.phase=phase;a.deadline=env.now()+20;env.query(phase,id)
 end
 function self:start(done)
  if self.active then return false,'busy' end
  if not env.identity() then return false,'no_role' end
  local last=env.load()
  local a={identity=env.identity(),day=env.day(),status='running',floor_id=50,area_id=1,done=done,excluded={}}
  self.active=a
  if last and last.day==a.day then
   a.mine_id=last.mine_id
   if last.completed or last.status=='confirmed' then a.completed=true;self:finish('skipped','daily_target_done');return true end
   if last.pending then a.pending=last.pending;a.mine_id=last.mine_id;self:finish('uncertain','previous_request_unresolved');return true end
  end
  if not self:valid() then return true end
  self:query('base');return true
 end
 function self:nextTarget()
  local a=self.active;local target=table.remove(a.targets,1)
  if not target then self:finish('skipped','no_challengeable_mine');return end
  a.mine_id=target.mine_id;self:query('detail',a.mine_id)
 end
 function self:base(d)
  local a=self.active
  for _,k in ipairs({'status','max_floor','trim_end_time','next_plunder_time','mine_floor_id','mine_area_id','mine_id','start_time','end_time'}) do
   if not uint(d[k]) then self:finish('error','invalid_mine_state');return end
  end
  if d.status~=1 or d.start_time>env.now() or d.end_time<=env.now() then self:finish('skipped','not_open');return end
  if d.max_floor<50 then self:finish('skipped','floor_50_locked');return end
  if d.trim_end_time>env.now() or d.next_plunder_time>env.now() then self:finish('skipped','mine_cooldown');return end
  a.base=d;self:query('form')
 end
 function self:area(d)
  if d.floor_id~=50 or d.area_id~=1 then return end
  if not uint(d.area_num) or d.area_num<1 or type(d.mine_list)~='table' then self:finish('error','invalid_mine_state');return end
  local a=self.active;local seen={};a.targets={}
  for _,t in ipairs(d.mine_list) do
   if not uint(t.mine_id) or t.mine_id<1 or t.mine_id>env.mineCount() or seen[t.mine_id]
    or not uint(t.rid) or type(t.srv_id)~='string' or not uint(t.start_time) or not uint(t.end_time)
    or (t.combat_state~=0 and t.combat_state~=1) then self:finish('error','invalid_mine_state');return end
   seen[t.mine_id]=true
   if not a.excluded[t.mine_id] and env.target(t,a.base) then a.targets[#a.targets+1]=t end
  end
  table.sort(a.targets,function(x,y)
   if (x.rid==0)~=(y.rid==0) then return x.rid==0 end
   return x.mine_id<y.mine_id
  end)
  self:nextTarget()
 end
 function self:onPacket(id,d)
  if not self:valid() or type(d)~='table' then return end
  local a=self.active
  if a.phase=='base' and id==30300 then self:base(d)
  elseif a.phase=='form' and id==11251 and d.type==env.formType() then
   local why=env.checkForm(d);if why then self:finish('error',why);return end
   self:query('area')
  elseif a.phase=='area' and id==30301 then self:area(d)
  elseif a.phase=='detail' and id==30302 and d.floor_id==50 and d.area_id==1 and d.mine_id==a.mine_id then
   if not uint(d.rid) or type(d.srv_id)~='string' or not uint(d.start_time) or not uint(d.end_time)
    or not uint(d.can_plunder_times) or (d.combat_state~=0 and d.combat_state~=1) then self:finish('error','invalid_mine_state');return end
   if not env.target(d,a.base) then self:nextTarget();return end
   if not self:valid() then return end
   a.pending=true;a.phase='reply';a.deadline=env.now()+20
   env.save(a) -- durable, before the only battle request
   env.act(a.mine_id)
  elseif a.phase=='reply' and id==30307 and d.floor_id==50 and d.area_id==1 and d.mine_id==a.mine_id then
   if d.code==1 then a.pending=nil;a.completed=true;self:finish('confirmed','challenge_started')
   elseif d.code==0 then
    a.pending=nil;env.save(a)
    if env.conflict() and not a.retried then
     a.retried=true;a.phase='deferred';a.deadline=env.now()+150
    else
     a.excluded[a.mine_id]=true;self:query('base')
    end
   end
  end
 end
 function self:tick()
  if not self:valid() then return end
  local a=self.active
  if env.now()>=a.deadline then self:finish(a.pending and 'uncertain' or 'error',a.phase..'_timeout');return end
  if a.phase=='deferred' and not env.conflict() then self:query('base') end
 end
 function self:cancel() self:finish('cancelled','cancelled') end
 function self:fail() self:finish(self.active and self.active.pending and 'uncertain' or 'error','runtime_error') end
 return self
end
return M
