#!/usr/bin/env python3
"""Build a pure extension; no official startup resource or fixed game hash."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'lsposed-module/app/src/main/assets/extension'
# 业务源码在 modules/；生成的 payload.lua 只是打包结果，修改功能应改这些源文件。
# 每组状态机负责流程，带 _game 的适配层负责调用游戏控制器和接收协议回复。
PAIRS=[('Gifts','daily_gifts.lua'),('Actions','daily_actions.lua'),('GameActions','daily_actions_game.lua'),('Training','daily_training.lua'),('GameTraining','daily_training_game.lua'),('Quests','daily_quests.lua'),('GameQuests','daily_quests_game.lua'),('Extension','xiangxiang_gifts_extension.lua')]
def cut(s,start,end,replacement=''):
    assert s.count(start)==1,(start,s.count(start))
    a=s.index(start);b=s.index(end,a)
    return s[:a]+replacement+s[b:]
def release_source(name,s):
    # Keep historical recovery tooling in the analysis sources, exclude it from
    # the signed module payload. Generic pending protection remains intact.
    if name=='daily_training_game.lua':
        s=cut(s,"    local recovery_token=","    local function sorted")
        s=cut(s,'            -- Exact migration for the audited disconnected Phase11v3 request;','        end,\n        heroRecoveryLevel', '            return nil\n')
        s=s.replace("v.lev==6 or (a.legacy and v.lev==1)","v.lev==6")
        s=cut(s,'        legacyRequest=function()','        recoveryBaseline=function', '''        reportRecovery=function(status,reason) log('recovery_result',status..'|'..tostring(reason)) end,
''')
        s=cut(s,'            if a.sent_at<0 then','            for _,field in ipairs',"            if a.sent_at<0 then return nil,'missing_pending_baseline' end\n            if ud:getIntegerForKey(k..':explicit_rejected',0)~=1 then return nil,'explicit_rejection_required' end\n")
    if name=='daily_training.lua':
        s=cut(s,"            if kind=='arena_free' and env.legacyRequest", "            self:finish('uncertain','previous_request_unresolved')")
        s=cut(s,"        elseif id==29400 and a.phase=='legacy_scope'", "        elseif id==29400 and a.phase=='reject_verify'")
    if name=='daily_quests_game.lua':
        s=cut(s,' -- One audited v2 win only;', ' local function log')
        s=cut(s,'  recoveryRequest=recoveryRequest,', '  guildScope=guildScope,')
    if name=='daily_quests.lua':
        s=s.replace('  if a.recovery and env.reportRecovery then env.reportRecovery(status,reason) end\n','')
        s=cut(s,"   if kind=='ruins' and env.recoveryRequest", '   return true', "   self:finish('uncertain','previous_request_unresolved')\n")
        s=cut(s,"  if a.phase=='recovery_verify' then", "  if a.phase=='verify' then")
        s=s.replace(" or a.phase=='recovery_verify'",'')
        s=cut(s,"  if a.phase=='recovery_verify' and", "  elseif a.phase=='battle'")
        s=s.replace("  elseif a.phase=='battle' and a.battle_started", "  if a.phase=='battle' and a.battle_started")
    assert 'yinghe_' not in s and 'recovery_token' not in s and 'legacyRequest' not in s,name
    return s

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    parts=['-- Pure local extension factory. No task runs during installation.\nreturn function()\n']
    for var,name in PAIRS:
        parts += ['local '+var+'=(function()\n',release_source(name,(ROOT/'modules'/name).read_text()),'\nend)()\n']
    parts += ['return Extension.install(Gifts,Actions,GameActions,Training,GameTraining,Quests,GameQuests)\nend\n']
    (OUT/'payload.lua').write_text(''.join(parts))
    (OUT/'bootstrap.lua').write_bytes((ROOT/'lsposed-module/lua/bootstrap.lua').read_bytes())
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.lua'))}
    (OUT/'manifest.json').write_text(json.dumps({'version':'0.2.0','files':manifest},indent=2)+'\n')
    native=ROOT/'lsposed-module/app/src/main/jniLibs/arm64-v8a/libdldl_bridge.so'
    (OUT/'native.sha256').write_text(hashlib.sha256(native.read_bytes()).hexdigest()+'\n')
    print(json.dumps(manifest))
if __name__=='__main__':build()
