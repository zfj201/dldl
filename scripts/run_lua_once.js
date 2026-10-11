'use strict';
// Sample-specific, executes once at a Cocos scheduler boundary on its own thread.
const mod = Process.getModuleByName('libcocos2dlua.so');
const expected = __EXPECTED__;
for (const [rva, hex] of Object.entries(expected)) {
  const bytes = new Uint8Array(mod.base.add(Number(rva)).readByteArray(hex.length / 2));
  const got = Array.from(bytes, x => x.toString(16).padStart(2,'0')).join('');
  if (got !== hex) throw new Error('Code mismatch at '+rva);
}
const fn = (rva,ret,args) => new NativeFunction(mod.base.add(rva),ret,args);
const getTop=fn(0x6c9564,'int',['pointer']);
const setTop=fn(0x6c9578,'void',['pointer','int']);
const getField=fn(0x6ca238,'void',['pointer','int','pointer']);
const pushString=fn(0x6c9f2c,'void',['pointer','pointer']);
const luaType=fn(0x6c97a8,'int',['pointer','int']);
const pcall=fn(0x6ca96c,'int',['pointer','int','int','int']);
const tostring=fn(0x6c9ba8,'pointer',['pointer','int','pointer']);
const source=Memory.allocUtf8String(__SOURCE__);
const loader=Memory.allocUtf8String('loadstring');
let finished=false;
function stackString(L) {
  const p=tostring(L,-1,ptr(0));return p.isNull() ? null : p.readUtf8String();
}
const hook=Interceptor.attach(mod.base.add(0xa24b94),{
  onEnter() {
    if (finished) return;
    const slot=mod.base.add(0xf19990).readPointer();
    const L=slot.readPointer();
    if (L.isNull()) return;
    finished=true;
    let top=null;
    try {
      top=getTop(L);
      if (top<0 || top>10000) throw new Error('Invalid Lua stack');
      getField(L,-10002,loader);
      if (luaType(L,-1)!==6) throw new Error('loadstring unavailable');
      pushString(L,source);
      const compile=pcall(L,1,1,0);
      if (compile!==0 || luaType(L,-1)!==6) throw new Error('Compile failed: '+stackString(L));
      const status=pcall(L,0,1,0);
      send({kind:'lua_result',status,result:stackString(L),thread:Process.getCurrentThreadId()});
    } catch(e) {send({kind:'failure',error:String(e)});}
    finally {if(top!==null)setTop(L,top);}
  }
});
send({kind:'ready',base:mod.base.toString()});
