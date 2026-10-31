"""Original artifact senders/handlers/config; inventory and transport are simulated."""
def setup(lua, original):
    original('config/partner_artifact_data.luac')
    lua.execute('''
local strings={}
if not ud.getStringForKey then
 function ud:getStringForKey(k,d) return strings[k] or d end
 function ud:setStringForKey(k,v) strings[k]=v end
end
if not ud.flush then function ud:flush() end end
BackPackConst.Bag_Code.BACKPACK=1
ItemData=ItemData or {};local oldItem=ItemData.data_get_data
ItemData.data_get_data=function(id)
 if id==13001 or id==13002 then return {id=id,quality=id==13001 and 3 or 4} end
 return oldItem(id)
end
for _,id in ipairs({11033,11048}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,hc) end
function freshRecast()
 freshExtra();stocks[10004]=10000;stocks[1]=1000000;stocks[3]=1000
 hc.artifact_recast_win=nil;hc.artifact_select_skill_window=nil
end
function artifact(id,bid,draft)
 return {id=id,base_id=bid or 13001,quantity=1,expire_type=0,expire_time=0,is_lock=0,
  attr={{attr_id=1,attr_val=100}},extra_attr=draft and {{attr_id=1,attr_val=200}} or {},
  extra={{extra_k=1,extra_v=501}},main_attr={}}
end
function recastTask() return window({{type=1,pos=-2101779,args={}},{type=1,pos=999,args={}}}) end
function recastQuota(current)
 return {artifact_ref_count={{base_id=13001,current=0,limit=0},{base_id=13002,current=current or 0,limit=10}}}
end
function recastDetails()
 local list={};for _,v in pairs(bones) do list[#list+1]=deepCopy(v) end
 receive(10506,{storage=1,list=list})
end
function startRecast(current)
 local w=recastTask();w:requestTask();receive(11048,recastQuota(current));recastDetails();ext.recast:tick();return w
end
function finishRecast()
 local t=ext.recast.active.target
 stocks[10004]=stocks[10004]-t.cost_essence;stocks[1]=stocks[1]-t.cost_coin
 bones[t.id].extra_attr={{attr_id=1,attr_val=250}}
 receive(11033,{result=1,msg=''});recastDetails();ext.recast:tick()
end
''')
