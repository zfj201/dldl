"""Recovered controller contracts; only rendering, transport and inventories are mocked."""
def setup(lua, original):
    lua.execute('''
ActionRankCommonType={moon_cake=1,hero_match=2}
ActionConstants={GiftBuyType={FREE=1}}
ActionConstants.GiftBuyLimitType={NORMAL=0}
GlobalEvent.DelayFire=function() end
bus.DelayFire=function() end
''')
    for p in ['config/common_gift_data.luac','config/guild_new_boss_data.luac','config/desisive_battle_data.luac',
              'game/guildboss/guildboss_controller.luac','game/jialingpass/jialingpass_controller.luac',
              'game/jialingpass/jialingpass_model.luac','game/common_gift_shop/common_gift_shop_const.luac',
              'game/common_gift_shop/common_gift_shop_item_vo.luac','game/common_gift_shop/common_gift_shop_model.luac',
              'game/common_gift_shop/common_gift_shop_controller.luac']:
        original(p)
    lua.execute('''
function CommonGiftShopItemVo.New()
 local v=setmetatable({},{__index=CommonGiftShopItemVo});v:__init();return v
end
GuildbossEvent={};JiaLingPassEvent={};CommonGiftShopEvent={}
local gm={setNewBossHuntData=function(self,d) self.base=d end}
gb=setmetatable({model=gm,SendProtocal=BaseController.SendProtocal},{__index=GuildbossController})
function GuildbossController:getInstance() return gb end
local tm=setmetatable({first_reward_list={}},{__index=JiaLingPassModel})
tc=setmetatable({model=tm,dispather=bus,SendProtocal=BaseController.SendProtocal},{__index=JiaLingPassController})
function JiaLingPassController:getInstance() return tc end
RedManager.getInstance=function() return {doRedPointDelay=function() end} end
local sm=setmetatable({},{__index=CommonGiftShopModel});sm:config()
sg=setmetatable({model=sm,SendProtocal=BaseController.SendProtocal},{__index=CommonGiftShopController})
function CommonGiftShopController:getInstance() return sg end
for _,p in ipairs({{gb,29720},{gb,29721},{tc,28700},{tc,28703},{sg,10572},{sg,10573}}) do
 ProtoMgr:RegisterCmdCallback(p[2],'handle'..p[2],p[1])
end
function freshExtra()
 freshQuest();background={}
 ProtoMgr.cmd_callback_table[28702]=nil
end
-- Preserve existing fixtures' fight semantics and model concurrent background types.
local old_fight=bc.getFightTypeInfo
function bc:getFightTypeInfo(t) return (background and background[t]) or old_fight(self,t) end
function extraTask(k)
 local ids={guild_trial=-2101786,temple_duel=-2101785,workshop_gift=-2101784}
 local w=window({{type=1,pos=ids[k],args={}},{type=1,pos=999,args={}}})
 w.removeOneTimeTicket=function() end
 return w
end
function guildBase(used)
 local id=next(GuildNewBossData.data_boss_get)
 return {boss_id=id,used_time=used or 0,buy_time=0,day_combat_time=0,is_last_boss=1}
end
function shopBase(n)
 return {type=2,bid=0,id=23,gift_list={{gift_id=2301,buy_num=n or 0}},ext_list={},remain_sec=600,is_red=1}
end
function startExtra(k)
 local w=extraTask(k);w:requestTask()
 if ext.extras.active and k~='workshop_gift' then
  receive(11211,{type=k=='guild_trial' and 65 or 122,formation_type=1,pos_info={{pos=1,id=2}}})
 end
 return w
end
function templeBase(n)
 receive(28703,{day_num=n or 2,first_reward={},step_reward=0})
 receive(28700,{status=1})
end
''')
