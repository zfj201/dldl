"""Recovered redbag controller/model/config; transport and UI mocked."""
def setup(lua, original):
    for p in ['config/guild_data.luac','game/redbag/redbag_coust.luac','game/redbag/redbag_model.luac','game/redbag/redbag_controller.luac']:
        original(p)
    lua.execute('''
RedbagEvent={Get_Data_Event=1,Can_Get_Red_Bag=2};ChatEvent={RED_BAG_UPDATE=3}
SortTools.tableCommonSorter=function() return function(a,b) return a.id<b.id end end
GuildConst.red_index={get_redbag=1}
GuildController:getInstance():getModel().updateGuildRedStatus=function() end
local rm=setmetatable({},{__index=RedbagModel});rm:config()
rbc=setmetatable({model=rm,SendProtocal=BaseController.SendProtocal},{__index=RedbagController});rm.ctrl=rbc
function RedbagController:getInstance() return rbc end
redbagWindows=0
function rbc:openRegBagWindow(open) if open then redbagWindows=redbagWindows+1 end end
for _,id in ipairs({13523,13534,13536}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,rbc) end
function freshRedbag()
 freshMine();role.gid=5;role.gsrv_id='guild_srv';rm:config();redbagWindows=0
 ud:setStringForKey('dldl_redbag_v1:'..role.srv_id..':'..role.rid..':'..role.gsrv_id..':'..role.gid..':last','')
end
function redbagQuota(used,max,specialUsed,specialMax)
 return {day_send_num=0,list={{type=0,day_recv_num=used or 0,day_recv_max_num=max or 2},
  {type=91,day_recv_num=specialUsed or 0,day_recv_max_num=specialMax or 0},
  {type=40,day_recv_num=0,day_recv_max_num=1}}}
end
function redbag(id,typ,expiry,flag,num)
 return {id=id,type=typ or 51,time=expiry or now+500,flag=flag or 0,num=num or 0,max_num=10,rid=1,srv_id='other',name='sender',post=3,max_val=100,msg_id=0}
end
function redbagList(list,typ) return {type=typ or 0,list=list or {}} end
function redbagTask()
 return window({{type=-2101803,pos=-2101780,args={}},{type=1,pos=999,args={}}})
end
function startRedbag(list,quota)
 local w=redbagTask();w:requestTask();receive(13523,quota or redbagQuota());receive(13534,redbagList(list));ext.redbag.runner:tick();return w
end
function redbagReply(id,typ,val,code)
 return {code=code or 1,id=id,type=typ or 51,val=val or 10,msg='',list=redbagQuota(1).list}
end
function redbagNext(list,quota)
 now=now+2;ext.redbag.runner:tick();receive(13523,quota or redbagQuota());receive(13534,redbagList(list));ext.redbag.runner:tick()
end
''')
