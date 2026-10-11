'use strict';
if (Process.arch !== 'arm64') throw new Error('Requires arm64');
const mod = Process.getModuleByName('libcocos2dlua.so');
if (mod.base.add(0x4c3b60).readU32() !== 0xd10143ff ||
    mod.base.add(0xc6d520).readUtf8String(16) !== '0db5c76bad3972ad') {
  throw new Error('Wrong sample');
}
// Invoke only the existing resource transform on separately allocated input.
// This does not invoke Lua, game actions, or the network.
const decode = new NativeFunction(mod.base.add(0x4c3fc8), 'pointer',
  ['pointer', 'uint', 'pointer', 'uint', 'pointer']);
const release = new NativeFunction(Process.getModuleByName('libc.so').getExportByName('free'), 'void', ['pointer']);
function unhex(value) {
  if (value.length % 2 || !/^[0-9a-f]*$/i.test(value)) throw new Error('Bad hex');
  const array = new Uint8Array(value.length / 2);
  for (let i = 0; i < array.length; i++) array[i] = parseInt(value.slice(i*2,i*2+2),16);
  return array;
}
rpc.exports = {
  info() { return {base: mod.base.toString(), wrapper: mod.base.add(0x4c3fc8).toString()}; },
  decrypt(dataHex, keyHex) {
    const bytes = unhex(dataHex), keyBytes = unhex(keyHex);
    if (!bytes.length || bytes.length > 16*1024*1024 || keyBytes.length !== 16) throw new Error('Invalid length');
    const input = Memory.alloc(bytes.length), key = Memory.alloc(16), length = Memory.alloc(4);
    input.writeByteArray(bytes.buffer); key.writeByteArray(keyBytes.buffer); length.writeU32(0);
    const result = decode(input, bytes.length, key, 16, length);
    if (result.isNull()) throw new Error('Native decoder returned NULL');
    try {
      const size = length.readU32();
      if (!size || size > 32*1024*1024) throw new Error('Invalid output length: '+size);
      return result.readByteArray(size);
    } finally { release(result); }
  }
};
