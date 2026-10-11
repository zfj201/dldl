'use strict';
// Prepared only; NOT executed in the initial investigation.
// SHA-256-specific arm64 sample. Attach to existing target, no spawn/restart.
if (Process.arch !== 'arm64') throw new Error('Requires arm64');
const mod = Process.getModuleByName('libcocos2dlua.so');
const entry = mod.base.add(0x4c3b60); // Core after FairGuard preprocessing.
if (entry.readU32() !== 0xd10143ff) throw new Error('Sample code mismatch');
if (mod.base.add(0xc6d520).readUtf8String(16) !== '0db5c76bad3972ad') {
  throw new Error('Sample constant mismatch');
}
let captured = 0;
let total = 0;
Interceptor.attach(entry, {
  onEnter(args) { this.outLength = args[3]; },
  onLeave(retval) {
    if (retval.isNull() || captured >= 256) return;
    try {
      const length = this.outLength.readU32();
      if (!length || length > 32 * 1024 * 1024 || total + length > 256 * 1024 * 1024) return;
      const data = retval.readByteArray(length);
      send({kind: 'xxtea_output', index: captured++, length}, data);
      total += length;
    } catch (e) { send({kind: 'read_error', error: String(e)}); }
  }
});
send({kind: 'ready', base: mod.base.toString(), core: entry.toString()});
