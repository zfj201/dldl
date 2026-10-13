#!/usr/bin/env python3
"""Build an auditable game_start extension from the exact recovered baseline."""
import argparse,hashlib,json,pathlib
from lupa.lua51 import LuaRuntime
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--phase',default='phase12');a=p.parse_args()
assert a.phase=='phase12','phase7/phase8/phase9/phase10/phase11/phase11v2/phase11v3 artifacts are immutable'
base=root/'recovered/phase2/hotupdate/lua/game_start.luac'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='3b8c0a56adcc9731f54dfca0c0943aa9911669e9537126e5447239ce49c2cb59'
parts=[base.read_text(),'\n-- DLDL free-gift extension: local tasks, default off.\ndo\nlocal ok, result = pcall(function()\n']
module_pairs=[('Gifts','daily_gifts.lua'),('Actions','daily_actions.lua'),('GameActions','daily_actions_game.lua'),
              ('Training','daily_training.lua'),('GameTraining','daily_training_game.lua'),('Quests','daily_quests.lua'),('GameQuests','daily_quests_game.lua'),('Extension','xiangxiang_gifts_extension.lua')]
for var,name in module_pairs:
    parts+=['local '+var+' = (function()\n',(root/'modules'/name).read_text(),'\nend)()\n']
parts+=['''
    local installed = Extension.install(Gifts, Actions, GameActions, Training, GameTraining, Quests, GameQuests)
    _G.DLDL_DAILY_GIFTS = installed
    return installed.version
end)
local fu = cc.FileUtils:getInstance()
pcall(function()
    local output = assert(io.open(fu:getWritablePath() .. "dldl_gifts_install.txt", "w"))
    output:write("installed=", tostring(ok), "\\n")
    output:write("result=", tostring(result), "\\n")
    output:write("loaded_at=", tostring(os.time()), "\\n")
    output:write("game_start=", tostring(fu:fullPathForFilename("game_start.luac")), "\\n")
    if ok then
        for _, spec in ipairs(DLDL_DAILY_GIFTS.specs) do
            output:write("task=", spec.title, "|", tostring(spec.pos), "\\n")
        end
    end
    output:close()
end)
if not ok then print("[dldl_gifts] " .. tostring(result)) end
end
''']
data=''.join(parts).encode()
check=LuaRuntime(unpack_returned_tuples=True).eval('function(s) local f,e=loadstring(s);return f~=nil,e end')
ok,err=check(data.decode());assert ok,err
out=root/'recovered'/a.phase/'game_start.luac';out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
record={'output':str(out),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'lua51_syntax_pass':ok,
 'inputs':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [base]+[root/'modules'/name for _,name in module_pairs]}}
(root/'evidence'/f'{a.phase}_gifts_bundle.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
