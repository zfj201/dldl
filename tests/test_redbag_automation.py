#!/usr/bin/env python3
"""Guild redbag collection against recovered real senders/model and helper queue."""
import contextlib,io,json,pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua'];original=ns['ns']['original']
for f in ['daily_extras','voyage','mine','redbag']:
    runpy.run_path(str(ROOT/'tests'/('fixtures_'+f+'.py')))['setup'](lua,original)
for var,name in [('Extras','daily_extras'),('GameExtras','daily_extras_game'),('Voyage','voyage_automation'),('GameVoyage','voyage_automation_game'),('Mine','mine_automation'),('GameMine','mine_automation_game'),('Redbag','redbag_automation'),('GameRedbag','redbag_automation_game')]:
    lua.globals()[var]=lua.execute((ROOT/'modules'/(name+'.lua')).read_text())
lua.execute('''
freshRedbag()
ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
GameVoyage.bind(Voyage,ext);GameMine.bind(Mine,ext)
local n=#sent;GameRedbag.bind(Redbag,ext)
case('redbag row follows mine and stays default off without sending requests',function()
 local rows=OneKeyBurdenConst.SimplifyTypeList[ext.voyage.type]
 assert(#rows==4 and rows[3].id==ext.redbag.pos and rows[4].id==ext.voyage.history.id)
 assert(#sent==n and OneKeyBurdenMainWindow:getPosExecuteData(ext.voyage.type,ext.redbag.row).is_open==0)
end)
case('setting enters the full helper queue and is filtered from native save',function()
 local t=ext.voyage.type;local p=ext.redbag.pos
 local w=setmetatable({select_index=1,task_list={ext.voyage.category},operate_list={
  [t]={[p]={pos=p,is_open=1,args={}}}}},{__index=OneKeyBurdenMainWindow})
 for _,r in ipairs(OneKeyBurdenConst.SimplifyTypeList[t]) do if not w.operate_list[t][r.id] then w.operate_list[t][r.id]={pos=r.id,is_open=0,args={}} end end
 local n=#sent;local q=w:saveOperateRequest(true)
 assert(#q==1 and q[1].pos==p and #sent==n)
 assert(OneKeyBurdenMainWindow:getPosExecuteData(t,ext.redbag.row).is_open==1)
 assert(not pcall(function() oc:sender31602(t,p) end))
end)
case('sequential claims prefer expiring bags, require exact ack and aggregate actual value',function()
 freshRedbag();local w=startRedbag({redbag(2,51,now+400),redbag(1,92,now+200)})
 assert(sent[#sent].id==13536 and sent[#sent].data.id==1 and ext.redbag.load().pending.id==1)
 receive(13536,redbagReply(99,92));assert(ext.redbag.runner.active.phase=='reply')
 receive(13536,redbagReply(1,92,18));assert(w.execute_index==1 and redbagWindows==1)
 -- Only the unrelated manual reply above opens its original UI.
 redbagNext({redbag(1,92,nil,1),redbag(2)},redbagQuota(1))
 assert(sent[#sent].data.id==2);receive(13536,redbagReply(2,51,7))
 redbagNext({redbag(1,92,nil,1),redbag(2,51,nil,1)},redbagQuota(2))
 local a=w.execute_request_list[1].redbag
 assert(w.execute_index==2 and a.status=='confirmed' and #a.entries==2 and a.entries[1].val==18 and a.entries[2].val==7)
 assert(not ext.redbag.load().pending and redbagWindows==1)
end)
case('claimed empty and expired bags are skipped; quota does not block member redbags',function()
 freshRedbag();local w=startRedbag({redbag(1,51,nil,1),redbag(2,51,now),redbag(3,51,nil,0,10),redbag(4,51),redbag(5,92)},redbagQuota(2))
 assert(sent[#sent].id==13536 and sent[#sent].data.id==5)
 receive(13536,redbagReply(5,92));redbagNext({redbag(4,51)},redbagQuota(2))
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='quota_reached')
end)
case('special per-type quota and limited special member redbag are enforced',function()
 freshRedbag();local q=redbagQuota(2,2,1,1);q.list[3].day_recv_num=1
 local w=startRedbag({redbag(1,40),redbag(2,91)},q)
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='quota_reached')
 freshRedbag();w=startRedbag({redbag(1,91)},redbagQuota(2,2,0,0))
 assert(sent[#sent].id==13536 and sent[#sent].data.id==1);ext.redbag.runner:cancel()
end)
case('incremental pushes alone cannot authorize a claim before a full list',function()
 freshRedbag();local w=redbagTask();w:requestTask();receive(13523,redbagQuota());receive(13534,redbagList({redbag(1)},1));ext.redbag.runner:tick()
 assert(sent[#sent].id==13534 and w.execute_index==1)
 receive(13534,redbagList({redbag(1)}));receive(13534,redbagList({redbag(1,51,nil,1)},1));ext.redbag.runner:tick()
 assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='no_claimable_redbag')
end)
case('explicit rejection is tried once then other bags continue',function()
 freshRedbag();local w=startRedbag({redbag(1),redbag(2)})
 receive(13536,redbagReply(1,51,0,0));redbagNext({redbag(1),redbag(2)})
 assert(sent[#sent].data.id==2);receive(13536,redbagReply(2));redbagNext({redbag(1),redbag(2,51,nil,1)})
 assert(w.execute_index==2 and w.execute_request_list[1].redbag.rejected==1 and #w.execute_request_list[1].redbag.entries==1)
end)
case('lost reply is never retried; later flag verifies the claim without inventing amount',function()
 freshRedbag();local w=startRedbag({redbag(1)})
 now=now+21;ext.redbag.runner:tick();assert(w.execute_index==2 and ext.redbag.load().pending)
 local n=#sent;w=startRedbag({redbag(1)})
 assert(w.execute_request_list[1].local_reason=='previous_request_unresolved' and #sent==n+2)
 w=startRedbag({redbag(1,51,nil,1),redbag(2)})
 assert(sent[#sent].data.id==2 and ext.redbag.runner.active.entries[1].recovered)
 receive(13536,redbagReply(2));redbagNext({})
 assert(w.execute_index==2 and #w.execute_request_list[1].redbag.entries==2)
end)
case('expired unresolved bag does not permanently block future new bags',function()
 freshRedbag();startRedbag({redbag(1,51,now+2)});ext.redbag.runner:cancel();now=now+5
 local w=startRedbag({redbag(2)})
 assert(sent[#sent].data.id==2 and ext.redbag.runner.active.unverified==1);ext.redbag.runner:cancel()
end)
case('repeated same-day runs collect newly arriving bags without a daily completion lock',function()
 freshRedbag();local w=startRedbag({});assert(w.execute_index==2)
 w=startRedbag({redbag(2,92)});assert(sent[#sent].data.id==2)
 receive(13536,redbagReply(2,92));redbagNext({});assert(w.execute_index==2)
 w=startRedbag({redbag(2,92,nil,1),redbag(3,92)});assert(sent[#sent].data.id==3);ext.redbag.runner:cancel()
end)
case('guild role and day changes, disconnect and closed feature stop before claiming',function()
 for _,mode in ipairs({'guild','role','day','disconnect','closed'}) do
  freshRedbag();local w=redbagTask();w:requestTask();local n=#sent
  if mode=='guild' then role.gid=9 elseif mode=='role' then role.rid=role.rid+1 elseif mode=='day' then now=now+86400 elseif mode=='disconnect' then connected=false else opens=false end
  receive(13523,redbagQuota());ext.redbag.runner:tick();assert(not ext.redbag.runner.active)
  for i=n+1,#sent do assert(sent[i].id~=13536) end
 end
 freshRedbag();role.gid=0;local n=#sent;local w=redbagTask();w:requestTask();assert(#sent==n and w.execute_request_list[1].local_reason=='no_guild')
end)
case('manual claim is preserved outside the runner and blocked during collection',function()
 freshRedbag();rbc:sender13536(10);local n=#sent;local w=redbagTask();w:requestTask()
 assert(#sent==n and w.execute_request_list[1].local_reason=='manual_operation_pending')
 now=now+21;w=startRedbag({redbag(1)});n=#sent;rbc:sender13536(2);assert(#sent==n)
 ext.redbag.runner:cancel();receive(13536,redbagReply(1));assert(redbagWindows==0)
 receive(13536,redbagReply(11));assert(redbagWindows==1)
end)
case('query and reply timeout advance queue; bad quotas config and disk errors never claim',function()
 freshRedbag();local w=redbagTask();w:requestTask();now=now+21;ext.redbag.runner:tick();assert(w.execute_request_list[1].local_reason=='query_timeout')
 freshRedbag();local q=redbagQuota();q.list[1].day_recv_num=-1;w=startRedbag({},q);assert(w.execute_request_list[1].local_reason=='invalid_quota')
 freshRedbag();local cfg=GuildData.data_guild_red_bag[51];GuildData.data_guild_red_bag[51]=nil
 -- Avoid calling official updateData with an invalid config; test runner validation directly.
 w=redbagTask();w:requestTask();ext.redbag.runner:onPacket(13523,redbagQuota());ext.redbag.runner:onPacket(13534,redbagList({redbag(1)}));ext.redbag.runner:tick()
 assert(w.execute_request_list[1].local_reason=='invalid_config');GuildData.data_guild_red_bag[51]=cfg
 freshRedbag();w=redbagTask();w:requestTask();receive(13523,redbagQuota());receive(13534,redbagList({redbag(1)}))
 local save=ext.redbag.runner.env.save;ext.redbag.runner.env.save=function() error('disk full') end
 local n=#sent;for t in pairs(clock.timers) do t.fn() end;assert(#sent==n and w.execute_index==2)
 ext.redbag.runner.env.save=save
end)
case('uninstall remount retains pending and cannot resend an uncertain claim',function()
 freshRedbag();startRedbag({redbag(1)});ext.redbag.runner:cancel();ext.uninstall()
 ext=Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests,Extras,GameExtras)
 GameVoyage.bind(Voyage,ext);GameMine.bind(Mine,ext);GameRedbag.bind(Redbag,ext)
 local n=#sent;local w=startRedbag({redbag(1)});assert(#sent==n+2 and w.execute_request_list[1].local_reason=='previous_request_unresolved')
end)
case('result cells show confirmed rewards then clear when reused',function()
 freshRedbag()
 local function node() return {setVisible=function(self,v) self.visible=v end,setString=function(self,v) self.text=v end,
 setFontSize=function(self,v) self.font=v end,addTo=function(self) return self end} end
 local old=createRichLabel;createRichLabel=function() return node() end
 local cell=setmetatable({title_lb=node(),un_finish_node=node(),un_finish_lb=node(),item_scrollview=node(),root_wnd={}}, {__index=OneKeyBurdenAutoItem})
 cell:setData({type=-2101803,pos=-2101780,is_execute=true,redbag={reason='no_claimable_redbag',entries={{asset='gold',val=25}}}},1)
 assert(cell.redbag_label.visible and cell.redbag_label.text:find('钻石 25'))
 cell:setData({type=-2101803,pos=-2101781,is_execute=true,mine={reason='challenge_started',mine_id=5}},1)
 assert(not cell.redbag_label.visible and cell.mine_label.visible)
 createRichLabel=old
end)
case('uninstall restores all task rows and native manual claim behavior',function()
 ext.uninstall();assert(not OneKeyBurdenConst.SimplifyTypeList[-2101803])
 local n=#sent;rbc:sender13536(90);assert(#sent==n+1)
 receive(13536,redbagReply(90));assert(redbagWindows==1)
end)
''')
names=[lua.globals().passed[i] for i in range(1,len(lua.globals().passed)+1)]
result={'passed':len(names),'cases':names,'network':'offline; recovered redbag controller/model/config and original helper queue'}
(ROOT/'evidence/phase20_redbag_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
