#!/usr/bin/env python3
"""Build an auditable game_start extension from the exact recovered baseline."""
import hashlib,json,pathlib
from lupa.lua51 import LuaRuntime
root=pathlib.Path(__file__).resolve().parents[1]
base=root/'recovered/phase2/hotupdate/lua/game_start.luac'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='3b8c0a56adcc9731f54dfca0c0943aa9911669e9537126e5447239ce49c2cb59'
parts=[base.read_text(),'\n-- DLDL free-gift extension: local tasks, default off.\ndo\nlocal ok, result = pcall(function()\n']
for var,name in [('Gifts','daily_gifts.lua'),('Actions','daily_actions.lua'),('GameActions','daily_actions_game.lua'),('Extension','xiangxiang_gifts_extension.lua')]:
    parts+=['local '+var+' = (function()\n',(root/'modules'/name).read_text(),'\nend)()\n']
parts+=['''
    local installed = Extension.install(Gifts, Actions, GameActions)
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
out=root/'recovered/phase7/game_start.luac';out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
record={'output':str(out),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'lua51_syntax_pass':ok,
 'inputs':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [base,root/'modules/daily_gifts.lua',root/'modules/xiangxiang_gifts_extension.lua',root/'modules/daily_actions.lua',root/'modules/daily_actions_game.lua']}}
(root/'evidence/phase7_gifts_bundle.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
