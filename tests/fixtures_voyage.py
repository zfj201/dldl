"""Real voyage controller/model/config contracts; mock transport, storage location and UI."""
import json,tempfile
from lupa.lua51 import lua_type

def setup(lua, original):
    for p in ['config/item_data1.luac','config/item_data.luac','config/shipping_data.luac','game/voyage/voyage_const.luac','game/voyage/voyage_event.luac',
              'game/voyage/voyage_order_vo.luac','game/voyage/voyage_model.luac','game/voyage/voyage_controller.luac',
              'game/onekeyburden/onekeyburden_model.luac']:
        original(p)
    def convert(v):
        if lua_type(v)!='table':return v
        keys=list(v.keys())
        if keys and set(keys)==set(range(1,len(keys)+1)):return [convert(v[i]) for i in range(1,len(keys)+1)]
        return {str(k):convert(v[k]) for k in keys}
    def table(v):
        if isinstance(v,dict):return lua.table_from({k:table(x) for k,x in v.items()})
        if isinstance(v,list):return lua.table_from([table(x) for x in v])
        return v
    lua.globals().voyage_json_encode=lambda v:json.dumps(convert(v),ensure_ascii=False)
    lua.globals().voyage_json_decode=lambda v:table(json.loads(v))
    lua.globals().voyage_test_directory=tempfile.mkdtemp(prefix='dldl-voyage-')+'/'
    lua.execute('''
json={encode=function(t) return voyage_json_encode(t) end,decode=function(s) return voyage_json_decode(s) end}
cc.FileUtils={getInstance=function() return {getWritablePath=function() return voyage_test_directory end} end}
function VoyageOrderVo.New()
 local o=setmetatable({Fire=function() end},{__index=VoyageOrderVo});o:__init();return o
end
vm=setmetatable({},{__index=VoyageModel});vm:config()
vo=setmetatable({model=vm,SendProtocal=BaseController.SendProtocal},{__index=VoyageController})
function VoyageController:getInstance() return vo end
function vo:openVoyageDispatchWindow() end
for _,id in ipairs({23800,23801,23802,23804,23805}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,vo) end
oc.model.getTipsTypeRed=OneKeyBurdenModel.getTipsTypeRed
function freshVoyage()
 freshExtra();role.energy=6000;role.energy_cache=0;stocks[7]=6000;stocks[10014]=2;stocks[3]=1000;vm:config()
end
function voyageInfo(orders,free,coin)
 return {order_list=orders or {},free_times=free or 0,coin_times=coin or 0,lev=2,up_list={}}
end
function order(id,bid,status)
 return {order_id=id,order_bid=bid or 29301,status=status or 1,end_time=status==2 and now+20000 or 0,assign_ids={}}
end
function startVoyage(orders,free,coin)
 local w=window({{type=-2101803,pos=-2101783,args={}},{type=1,pos=999,args={}}})
 w:requestTask();receive(23805,{flag=0});receive(23800,voyageInfo(orders,free,coin));ext.voyage.runner:tick();return w
end
''')
