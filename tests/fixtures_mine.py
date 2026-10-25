"""Recovered mine model/controller/config, with transport and rendering mocked."""
def setup(lua, original):
    for p in ['config/arena_mine_data.luac','game/mine/mine_event.luac','game/mine/mine_model.luac','game/mine/mine_controller.luac']:
        original(p)
    lua.execute('''
local strings={}
function ud:getStringForKey(k,d) local v=strings[k];if v==nil then return d end;return v end
function ud:setStringForKey(k,v) strings[k]=v end
RedManager.RED_ID_LIST=RedManager.RED_ID_LIST or {}
BattleConst.Fight_Type.Mine=57
local mm=setmetatable({},{__index=MineModel});mm:config()
mc=setmetatable({model=mm,dispather=bus,SendProtocal=BaseController.SendProtocal},{__index=MineController})
function MineController:getInstance() return mc end
detailWindows=0
function mc:openMineDefendInfoWindow(open) if open then detailWindows=detailWindows+1 end end
for _,id in ipairs({30300,30301,30302,30307}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,mc) end
ProtoMgr:RegisterCmdCallback(11251,'handle11251',hc)
function freshMine()
 freshVoyage();now=math.max(now+25,100000);replay=false;fight=false;detailWindows=0
 ud:setStringForKey('dldl_mine_v1:'..role.srv_id..':'..role.rid..':last','')
end
function mineBase()
 return {status=1,max_floor=50,mine_floor_id=50,mine_area_id=1,mine_id=4,trim_end_time=0,next_plunder_time=0,
 start_time=0,end_time=now+86400,mine_end_time=now+2000,plunder_times=2,plundered_times=0,left_hook_time=0,worship_times=0}
end
function mineForm()
 hc:getModel().hero_list={}
 local d={type=59,formations={}}
 for i=1,3 do
  hc:getModel().hero_list[i]={partner_id=i}
  d.formations[i]={order=i,formation_type=1,pos_info={{pos=1,id=i}}}
 end
 return d
end
function mineTarget(id,rid,start,combat)
 return {mine_id=id or 5,rid=rid or 0,srv_id='other',start_time=start or 0,end_time=now+5000,combat_state=combat or 0}
end
function mineArea(list) return {floor_id=50,area_id=1,area_num=1,mine_list=list or {mineTarget(5)}} end
function mineDetail(id)
 local d=mineTarget(id);d.floor_id=50;d.area_id=1;d.can_plunder_times=2;d.formations={};return d
end
function mineTask()
 local w=window({{type=-2101803,pos=-2101781,args={}},{type=1,pos=999,args={}}})
 w.removeOneTimeTicket=function() end
 return w
end
function startMine(list)
 local w=mineTask();w:requestTask();receive(30300,mineBase());receive(11251,mineForm());receive(30301,mineArea(list));return w
end
''')
