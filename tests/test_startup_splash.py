#!/usr/bin/env python3
"""Observe the exact splash node, including detached/hidden/faded/obsolete scene cases."""
from pathlib import Path
from lupa.lua51 import LuaRuntime

root = Path(__file__).resolve().parents[1]
lua = LuaRuntime()
lua.globals().source = (root / 'lsposed-module/lua/splash.lua').read_text()
lua.execute('''
function detect() return assert(loadstring(source))() end
assert(detect()==0) -- before cocos and FileUpdate exist
tolua={isnull=function(n) return n.dead or false end}
local function node(parent)
 return {parent=parent,visible=true,opacity=255,
 getParent=function(s) return s.parent end,isVisible=function(s) return s.visible end,getOpacity=function(s) return s.opacity end}
end
scene=node();cc={Director={getInstance=function() return {getRunningScene=function() return scene end} end}}
layer=node(scene);sprite=node(layer);FileUpdate_Instance={flash_png=sprite}
assert(detect()==1) -- no SDK loading dialog is required
sprite.visible=false;assert(detect()==0);sprite.visible=true
layer.visible=false;assert(detect()==0);layer.visible=true
sprite.opacity=0;assert(detect()==0);sprite.opacity=255
layer.opacity=0;assert(detect()==0);layer.opacity=255
sprite.parent=nil;assert(detect()==0);sprite.parent=layer
sprite.dead=true;assert(detect()==0);sprite.dead=false
local previous=scene;scene=node();assert(detect()==0);scene=previous
sprite.getOpacity=function() error('deleted native object') end;assert(detect()==0)
FileUpdate_Instance=nil;assert(detect()==0)
''')
print('Splash detection: exact current-scene node, visibility, opacity, detach, disposal and API failure passed')
