#!/usr/bin/env python3
"""Sample-specific read-only ResourcesDecode singleton inspection (arm64)."""
import json, pathlib, shlex, struct, subprocess
root = pathlib.Path(__file__).resolve().parents[1]
m = json.loads((root/'recovered/runtime/manifest.json').read_text())
pid, serial = m['pid'], m['serial']
adb = ['adb', '-s', serial]
live = subprocess.check_output(adb+['shell','pidof',m['package']],text=True).strip()
if live != str(pid): raise SystemExit('PID changed; dump modules again')
base = next(s['start'] for s in m['segments'] if s['name']=='libcocos2dlua.so' and s['file_offset']==0)
def read(addr, size):
    addr &= 0x00ffffffffffffff  # Android ARM64 tagged heap pointers (TBI).
    if not 0 < size <= 4096: raise ValueError(size)
    page=addr & ~4095
    count=(addr-page+size+4095)//4096
    cmd=f'dd if=/proc/{pid}/mem bs=4096 skip={page//4096} count={count} 2>/dev/null'
    data=subprocess.check_output(adb+['exec-out','su -c '+shlex.quote(cmd)])
    data=data[addr-page:addr-page+size]
    if len(data)!=size: raise ValueError('Short read')
    return data
u64=lambda b:struct.unpack('<Q',b)[0]
global_addr=u64(read(base+0xf13708,8))
obj_addr=u64(read(global_addr,8))
print('singleton pointers', hex(global_addr), hex(obj_addr), flush=True)
obj=read(obj_addr,0x70)
key_addr=u64(obj[0x40:0x48]); key_len=struct.unpack_from('<I',obj,0x48)[0]
sign_addr=u64(obj[0x50:0x58]); sign_len=struct.unpack_from('<I',obj,0x58)[0]
if key_len>256 or sign_len>256: raise ValueError('Unexpected layout')
result={'pid':pid,'base':hex(base),'got_rva':'0xf13708',
        'global_address':hex(global_addr),'object_address':hex(obj_addr),
        'object_hex':obj.hex(),'key_hex':read(key_addr,key_len).hex(),
        'sign_hex':read(sign_addr,sign_len).hex(),'key_length':key_len,'sign_length':sign_len}
result['derived_fields'] = []
for offset in (0, 16, 32, 48):
    ptr = u64(obj[offset:offset+8])
    length = struct.unpack_from('<I', obj, offset+8)[0]
    if not 0 < length <= 256: raise ValueError('Unexpected derived field length')
    data = read(ptr, length)
    result['derived_fields'].append({'offset':hex(offset), 'length':length, 'hex':data.hex(),
                                     'text':data.decode('ascii',errors='replace')})
(root/'evidence/resource_state.json').write_text(json.dumps(result,indent=2))
wrapper = read(base+0x4c3fc8, 16)
if wrapper[:8] == bytes.fromhex('5100005820021fd6'):
    target = u64(wrapper[8:])
    (root/'recovered/runtime/xxtea_trampoline.bin').write_bytes(read(target,4096))
    (root/'evidence/xxtea_trampoline.json').write_text(json.dumps({'address':hex(target),'wrapper_rva':'0x4c3fc8'},indent=2))
    slot = u64(read(base+0xf97e88,8))
    owner = u64(read(slot,8))
    manager = u64(read(owner+0x18,8))
    vtable = u64(read(manager,8))
    method = u64(read(vtable+8,8))
    if method != base+0xf73868: raise ValueError('Different hook manager implementation')
    state_addr = u64(read(manager+0x10,8))
    original = u64(read(state_addr+0x158,8))
    preprocess = u64(read(state_addr+0x160,8))
    (root/'recovered/runtime/resource_preprocess.bin').write_bytes(read(preprocess,4096))
    fairguard_base = next(s['start'] for s in m['segments'] if s['name']=='libFairGuard.so' and s['file_offset']==0)
    (root/'evidence/resource_preprocess.json').write_text(json.dumps({'preprocess':hex(preprocess), 'original':hex(original), 'manager':hex(manager), 'state':hex(state_addr), 'fairguard_rva':hex(preprocess-fairguard_base)},indent=2))
print(json.dumps(result,indent=2))
