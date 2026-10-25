#!/usr/bin/env python3
"""Real payload lifecycle against recovered game classes; no device/network calls."""
import contextlib,io,json,pathlib,runpy,tempfile,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
os.environ['DLDL_TEST_PHASE']='phase13'
with contextlib.redirect_stdout(io.StringIO()):
    ns=runpy.run_path(str(ROOT/'tests/test_daily_recovery.py'))
lua=ns['lua']
runpy.run_path(str(ROOT/'tests/fixtures_daily_extras.py'))['setup'](lua,ns['ns']['original'])
runpy.run_path(str(ROOT/'tests/fixtures_voyage.py'))['setup'](lua,ns['ns']['original'])
runpy.run_path(str(ROOT/'tests/fixtures_mine.py'))['setup'](lua,ns['ns']['original'])
build=runpy.run_path(str(ROOT/'lsposed-module/scripts/build-payload.py'))
with contextlib.redirect_stdout(io.StringIO()):build['build']()
asset=ROOT/'lsposed-module/app/src/main/assets/extension'
for p in asset.glob('*.lua'):
    ok,error=lua.eval('function(s) local f,e=loadstring(s);return f~=nil,e end')(p.read_text());assert ok,error
lua.globals().factory=lua.execute((asset/'payload.lua').read_text())
lua.execute('''
freshQuest()
original_rows=#OneKeyBurdenConst.SimplifyTypeList[1]
oc.model.getTypeOperateList=function() return {} end
oc.model.type_func_list={}
local n=#sent
local before=VipController:getInstance().sender21018
local original=VipController:getInstance().handle21018
VipController:getInstance().handle21018=false
local ok,err=pcall(factory)
assert(not ok and tostring(err):find('handle21018'),tostring(err))
assert(VipController:getInstance().sender21018==before,'partial installation not rolled back')
assert(#OneKeyBurdenConst.SimplifyTypeList[1]==original_rows,'failed install added rows')
assert(#sent==n,'installation sent a game request')
VipController:getInstance().handle21018=original
''')
with tempfile.TemporaryDirectory(prefix='dldl-loader-') as temp:
    base=pathlib.Path(temp);bundle=base/'bundle';bundle.mkdir();(base/'automation').mkdir()
    for name in ('bootstrap.lua','payload.lua'):(bundle/name).write_bytes((asset/name).read_bytes())
    lua.globals().boot=str(bundle/'bootstrap.lua');lua.globals().disabled_path=str(base/'disabled')
    lua.execute('''
GAME_INITED=false;package.loaded.game_start=nil;DLDL_DAILY_GIFTS=nil;DLDL_EXTENSION_LOADER=nil
assert(dofile(boot)==1)
GAME_INITED=true;package.loaded.game_start=true
local n=#sent
assert(dofile(boot)==0)
local a=DLDL_DAILY_GIFTS
assert(#a.specs==17 and #OneKeyBurdenConst.SimplifyTypeList[1]==original_rows+17 and #sent==n)
assert(a.voyage and SimplifyData.data_list[a.voyage.type].name=='其他自动化')
assert(a.mine and #OneKeyBurdenConst.SimplifyTypeList[a.voyage.type]==3)
for i=1,20 do assert(dofile(boot)==0) end
assert(DLDL_DAILY_GIFTS==a and DLDL_EXTENSION_LOADER.generation==1)
local key='loader_test_pending';ud:setIntegerForKey(key,1)
local f=assert(io.open(disabled_path,'w'));f:close()
assert(dofile(boot)==2)
assert(#OneKeyBurdenConst.SimplifyTypeList[1]==original_rows and DLDL_DAILY_GIFTS==nil and ud:getIntegerForKey(key,0)==1)
assert(not SimplifyData.data_list[-2101803] and not OneKeyBurdenConst.SimplifyTypeList[-2101803])
os.remove(disabled_path)
assert(dofile(boot)==0 and DLDL_EXTENSION_LOADER.generation==2)
local old=DLDL_DAILY_GIFTS
beginGame=function() end
assert(dofile(boot)==0 and DLDL_EXTENSION_LOADER.generation==3)
assert(DLDL_DAILY_GIFTS~=old and #OneKeyBurdenConst.SimplifyTypeList[1]==original_rows+17)
assert(#sent==n and ud:getIntegerForKey(key,0)==1)
-- The release bundle preserves pending isolation and skips contract shortage.
ext=DLDL_DAILY_GIFTS
freshQuest();contracts=0
local w=window({{type=1,pos=-2101795,args={{args_key=9020,args_val=10}}},{type=1,pos=-2101790,args={}}})
w:requestTask();receive(23200,{recruit_list={{recruit_type=4}}});ext.actions:tick()
assert(w.execute_index==2 and w.execute_request_list[1].local_reason=='insufficient_contracts')
w:requestTask();assert(sent[#sent].id==13518);ext.quests:cancel()
freshQuest();local k=heroKey();ud:setIntegerForKey(k..':pending',1)
local hero=trainingTask('hero');local requests=#sent;hero:requestTask()
assert(hero.execute_request_list[1].local_reason=='previous_request_unresolved')
noUpgradeSince(requests);assert(ud:getIntegerForKey(k..':pending',0)==1)
-- Mounting never clears the pending record, including after a generation change.
beginGame=function() end;assert(dofile(boot)==0)
assert(ud:getIntegerForKey(k..':pending',0)==1)
n=#sent
-- A later wrapper is owned by another party and must not be overwritten.
local foreign=function() end
VipController:getInstance().sender21018=foreign
DLDL_DAILY_GIFTS.detach()
assert(VipController:getInstance().sender21018==foreign)
assert(#OneKeyBurdenConst.SimplifyTypeList[1]==original_rows and #sent==n)
''')
print(json.dumps({'existing_regression_cases':len(lua.globals().passed),'payload_lua51':True,'lifecycle':['partial installation rollback','17 entries without requests','20 repeated callbacks idempotent','disable restores rows and preserves journal','reenable','generation remount','foreign wrapper preserved','release contract shortage continues to guild task','release unknown hero pending retained across remount'],'network':'none'},ensure_ascii=False,indent=2))
