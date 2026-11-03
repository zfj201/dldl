"""Recovered fishing/mail senders, fishing model and protocol dispatch; synthetic state only."""
def setup(lua, original):
    lua.execute('color2C4b=function(c) return c end')
    for path in ['config/fish_data.luac','game/fishing/fishing_const.luac','game/fishing/fishing_model.luac',
                 'game/fishing/fishing_controller.luac','game/mail/mail_controller.luac']:
        original(path)
    lua.execute('''
GlobalEvent.Fire=function() end
FishingEvent={Auto_Fishing_Status_Event=1}
FishingModel.newCacheData=function(self) local i=#self.cache_data_list+1;self.cache_data_list[i]={set_expired=function() end};return i end
FishingModel.setAllCacheExpired=function() end
FishingModel:init()
fc=setmetatable({SendProtocal=BaseController.SendProtocal,updateRed=function() end,role_update_event=true},{__index=FishingController})
FishingController.getInstance=function() return fc end
FishingController.updateRed=function() end
for _,id in ipairs({12000,12009,12013,12014,12022}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,fc) end
mailModel={initMailList=function(self,d) self.list=d end,getAllMailGood=function() end}
mailc=setmetatable({model=mailModel,SendProtocal=BaseController.SendProtocal},{__index=MailController})
MailController.getInstance=function() return mailc end
ProtoMgr:RegisterCmdCallback(10800,'mailListHandler',mailc)
ProtoMgr:RegisterCmdCallback(10802,'getAllGoodsHandler',mailc)
function freshOther()
 freshRedbag();now=now+30;stocks[127]=100;stocks[11010]=50
 role.Bind=function() end;role.UnBind=function() end
 fc.FishingMainWindow=nil;fc.auto_fishing_ticket=nil;FishingModel.canChangeFishiery=true;opens=true
 for _,k in ipairs({'fishing','mail'}) do ud:setStringForKey('dldl_'..k..'_v1:'..role.srv_id..':'..role.rid..':last','') end
end
function fishBase(ids,finish)
 local q={};for i,id in ipairs(ids or {10001,10003,10003}) do q[i]={id=i,order_id=id,finish=finish or 0,target_val=5,value=0} end
 return {cur_fishery_id=1001,bait_id=101,fish_id=0,fish_bid=0,quest_list=q,free_quest_times=0,
  fishery_id_list={{fishery_id=1001,is_unlock=2}},attr={},attr_list={},fishery_gear_list={}}
end
function otherTask(kind,types)
 return window({{type=-2101803,pos=kind=='fishing' and -2101773 or -2101772,
 args={{args_key=9023,args_str=types or '3|1'}}},{type=1,pos=999,args={}}})
end
function fishQuery(b) receive(12000,deepCopy(b));ext.fishing.runner:tick() end
function fishNext(b) now=now+8;ext.fishing.runner:tick();fishQuery(b) end
function mailEntry(id,status,has) return {id=id,srv_id='synthetic',status=status or 0,has_items=has==nil and 1 or has,type=1} end
''')
