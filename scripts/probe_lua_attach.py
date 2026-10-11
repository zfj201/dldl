import frida,json,pathlib
print('connecting',flush=True)
d=frida.get_device('4XQ4U4Z94T85TGAY',timeout=10)
print('attaching',flush=True)
s=d.attach(8136)
try:
 sc=s.create_script('''const m=Process.getModuleByName('libcocos2dlua.so');send({kind:'native',base:m.base.toString(),exports:m.enumerateExports().filter(x=>/lua_|luaL_|LuaStack|LuaEngine|mainLoop/.test(x.name)),symbols:m.enumerateSymbols().filter(x=>/lua_pcall|lua_gettop|luaL_loadbuffer|lua_settop|lua_tolstring/.test(x.name))});''')
 def callback(m,b):
  pathlib.Path('evidence/phase4_attach.json').write_text(json.dumps(m,indent=2));print(json.dumps(m),flush=True)
 sc.on('message',callback);sc.load()
finally:s.detach()
