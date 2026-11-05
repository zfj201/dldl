"""Recovered forest senders/model/config; synthetic defenders and hero IDs only."""
def setup(lua, original):
    for path in ['config/wood_data.luac','game/partner/partner_const.luac',
                 'game/giantwoodforest/giantwoodforest_const.luac','game/giantwoodforest/giantwoodforest_event.luac',
                 'game/giantwoodforest/giantwoodforest_model.luac','game/giantwoodforest/giantwoodforest_controller.luac']:
        original(path)
    lua.execute('''
local fm=setmetatable({},{__index=GiantWoodForestModel});fm:init()
forestc=setmetatable({model=fm,SendProtocal=BaseController.SendProtocal},{__index=GiantWoodForestController});fm.ctrl=forestc
GiantWoodForestController.getInstance=function() return forestc end
RedManager.doRedPointDelay=function() end
ProtoMgr.hasReg=function(self,id) return self.cmd_callback_table[id]~=nil end
MainuiController=MainuiController or {}
MainuiController.getInstance=function() return MainuiController end
MainuiController.getUIFightType=function(self) return self.forest_ui or 0 end
MainuiController.setUIFightType=function(self,v) self.forest_ui=v end
BattleConst.getUIFightByFightType=function(t) return t end
bc.send20060=function(self,t) capture(self,20060,{combat_type=t}) end
bc.getCurFightType=function(self) return 0 end

for _,id in ipairs({31900,31901,31903}) do ProtoMgr:RegisterCmdCallback(id,'on'..id,forestc) end
ProtoMgr:RegisterCmdCallback(11212,'handle11212',hc)
function forestKey() return 'dldl_forest_v1:'..role.srv_id..':'..role.rid end
function freshForest()
 freshOther();MainuiController.forest_ui=0;hc.form_go_fight_panel=nil;forestc.giantwoodforest_main_window=nil
 forestc.giantwoodforest_levup_window=nil;ud:setStringForKey(forestKey()..':last','')
 hc:getModel().hero_list={}
 for i=1,25 do hc:getModel().hero_list[i]={partner_id=i,bid=100+i,power=10000-i} end
end
function forestBase(state) return {state=state or 2,start_time=1,end_time=now+10000} end
function forestInfo(level,bids) return {level=level or 10,partner_bids=bids or {},fight_time=0,reward_list={}} end
function forestList(stars,used)
 local d={wood_defender_base={},use_partner_list=used or {}}
 for i=1,3 do d.wood_defender_base[i]={defender_id=i,rid=100+i,srv_id='synthetic',now_star=stars and stars[i] or 0} end
 return d
end
function forestForm(id,partial)
 return {type=106+id,formation_type=1,pos_info=partial or {{pos=1,id=1},{pos=2,id=2},{pos=3,id=3},{pos=4,id=4},{pos=5,id=5},{pos=6,id=6}},
 hallows_id=3,domain_id=1,hidden_id={{pos=1,id=21}},fusion_skill={{pos=1,id=31,skill_lev=1}},
 god_palace_skill={{pos=1,id=41,skill_lev=2}},war_souls_skill={{pos=1,id=51,quality=5,star=3}},common_list={{common_type=4,common_skill={}}}}
end
function forestTask(star)
 local w=window({{type=1,pos=-2101771,args={{args_key=9024,args_val=star or 5}}},{type=1,pos=999,args={}}});w.removeOneTimeTicket=function() end;return w
end
function forestTick() ext.forest.runner:tick() end
function forestQuery(stars,info,used)
 receive(31900,forestBase());forestTick();receive(31901,info or forestInfo());receive(31903,forestList(stars,used));forestTick()
end
''')
