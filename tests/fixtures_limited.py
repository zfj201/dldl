"""Recovered action controller methods; synthetic activity state and transport."""
def setup(lua,original):
    original('game/action/action_controller.luac')
    original('config/holiday_bit_data.luac')
    lua.execute('''
ud.limited_strings=ud.limited_strings or {}
ud.getStringForKey=ud.getStringForKey or function(self,k,default) return self.limited_strings[k] or default end
ud.setStringForKey=ud.setStringForKey or function(self,k,v) self.limited_strings[k]=v end
limitedc=setmetatable({SendProtocal=BaseController.SendProtocal,dispather={Fire=function() end}},{__index=ActionController})
ActionController.getInstance=function() return limitedc end
limitedc.getActionSubTabVo=function() return {end_time=now+10000,camp_id=100935} end
ActionEvent={GAP_NEEDLE_INFO_EVENT=1,GAP_NEEDLE_REWARD_EVENT=2}
RoleEnv={keys={gap_needle_dun='needle'},getInstance=function() return {set=function() end} end}
limitedc.openActionJfczResultWindow=function(self,shown) self.result_shown=shown end
for _,id in ipairs({16413,16414,16415,16416}) do ProtoMgr:RegisterCmdCallback(id,'handle'..id,limitedc) end
''')
