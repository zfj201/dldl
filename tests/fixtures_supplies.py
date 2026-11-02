"""Original shop/task senders and callbacks with transport and UI simulation."""
def setup(lua,original):
    lua.execute('cc.p=function(x,y) return {x=x,y=y} end')
    for p in ['config/exchange_data.luac','config/quest_data.luac','config/activity_data.luac',
              'game/mall/mall_const.luac','game/mall/mall_controller.luac','game/task/task_const.luac','game/task/task_controller.luac']:
        original(p)
    lua.execute('''
MallEvent={};showAssetsMsg=function() end
mall=setmetatable({SendProtocal=BaseController.SendProtocal},{__index=MallController})
MallController.getInstance=function() return mall end
local guild=GuildController:getInstance();guild.hasUnionSkillQuickUsePending=function() return false end
MainuiController={getInstance=function() return {checkIsOpenByActivate=function() return shopUnlocked end} end}
guild:getModel().getMyGuildInfo=function() return {lev=30} end
local model={setRecvWeekNodeReward=function() end,addTaskList=function() end,addQuestReward=function() end,
 setTaskCompleted=function() end,updateActivityData=function() end,initActivityBoxAward=function() end,updateSingleActivityData=function() end}
taskc=setmetatable({model=model,SendProtocal=BaseController.SendProtocal},{__index=TaskController})
TaskController.getInstance=function() return taskc end
for _,p in ipairs({{mall,13401,'handle13401'},{mall,13402,'handle13402'},{taskc,10400,'on10400'},
 {taskc,10406,'on10406'},{taskc,20300,'on20300'},{taskc,20301,'on20301'}}) do ProtoMgr:RegisterCmdCallback(p[2],p[3],p[1]) end
function freshSupplies()
 freshRecast();now=now+30;shopUnlocked=true;mall.mall_buy_win=nil;role.activity=100
 role.gid=9;role.gsrv_id='guild';role.vip_lev=20
 stocks[ItemData.data_assets_label2id.divine_fruit]=10000000
 stocks[ItemData.data_assets_label2id.guild_seal]=10000000
 stocks[ItemData.data_assets_label2id.fish_score]=10000000
 counts={};questStates={};boxStates={}
end
function supplyTask(k,opt)
 local ids={tree_shop=-2101778,guild_shop=-2101777,fishing_shop=-2101776,daily_rewards=-2101775}
 return window({{type=1,pos=ids[k],args={{args_key=9022,args_val=opt or 0}}},{type=1,pos=999,args={}}})
end
function shopData(typ)
 local items={};for id,c in pairs(counts) do local ext={};for k,n in pairs(c) do ext[#ext+1]={key=k,val=n} end;items[#items+1]={item_id=id,ext=ext} end
 local day=math.floor((now+10800)/86400)*86400-10800
 return {type=typ,code=1,is_half=0,item_list=items,day_ref_time=day+86400,week_ref_time=day+604800,month_ref_time=day+2678400,loss_list={}}
end
function supplyQuery(k)
 if k=='daily_rewards' then
  local q={};for id,state in pairs(questStates) do q[#q+1]={id=id,finish=state} end
  receive(10400,{type=3,quest_list=q,nodes={},exp_list={}})
  local b={};for id in pairs(boxStates) do b[#b+1]={activity=id} end
  receive(20300,{activity_box=b,box_rewards={}})
 else receive(13401,shopData(ext.supplies.shops[k].type)) end
 ext.supplies:tick()
end
function supplyAccept()
 local p=ext.supplies.active.pending
 if p.shop then
  counts[p.id]=counts[p.id] or {};counts[p.id][p.period]=p.before+p.num
  receive(13402,{type=p.shop,eid=p.id,code=1,msg='',ext={{key=p.period,val=p.before+p.num}}})
 elseif p.action=='quest' then questStates[p.id]=2;receive(10406,{type=3,nodes={{id=p.id}},flag=1,msg=''})
 else for _,id in ipairs(p.ids) do boxStates[id]=true end;receive(20301,{activity=0,code=1,msg=''}) end
 supplyQuery(p.kind)
end
''')
