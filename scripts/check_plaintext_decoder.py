#!/usr/bin/env python3
"""Replay the native resource decoder on synthetic plaintext, entirely offline.

This checks the two signature gates, not FileUtils resolution or phone loading.
Only captured decoder instructions may execute; any other call stops the run.
"""
import hashlib
import argparse
import json
import pathlib
import struct
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_LR, UC_ARM64_REG_SP

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAP = ROOT/'recovered/runtime'
meta = json.loads((SNAP/'manifest.json').read_text())
segments = [s for s in meta['segments'] if s['name'] == 'libcocos2dlua.so']
base = next(s['start'] for s in segments if s['file_offset'] == 0)
rows = []
parser = argparse.ArgumentParser()
parser.add_argument('--resource-file', type=pathlib.Path)
args = parser.parse_args()
cases = [('short', b'return 7'),
                      ('module', b'local M = {}\nfunction M.check() return "dldl_probe" end\nreturn M\n'),
                      ('long', b'-- harmless source\n' + b'local value = 1\n'*16 + b'return value\n')]
if args.resource_file:
    cases.append(('staged_resource',args.resource_file.read_bytes()))
for label, source in cases:
    assert len(source) <= 0x10000
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    for seg in segments:
        data = (SNAP/seg['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == seg['sha256']
        uc.mem_map(seg['start'], seg['end']-seg['start'])
        uc.mem_write(seg['start'], data)
    mem = 0x1000000000
    uc.mem_map(mem, 0x20000)
    obj, buf, output, canary, sign1, sign2 = [mem+x for x in (0x100,0x8000,0x2000,0x3000,0x4000,0x5000)]
    # Set a private canary cell in emulated memory; never edit the source snapshot.
    uc.mem_write(base+0xf1c990, struct.pack('<Q',canary))
    state = bytearray(0x40)
    struct.pack_into('<Q',state,0x10,sign1)
    struct.pack_into('<I',state,0x18,16)
    struct.pack_into('<Q',state,0x30,sign2)
    struct.pack_into('<I',state,0x38,16)
    state[0x3c] = 1  # Signature checking enabled, both stages.
    uc.mem_write(obj,bytes(state))
    uc.mem_write(sign1,b'8ad44aab87f92768')
    uc.mem_write(sign2,b'ec9336077f73f54c')
    uc.mem_write(buf,source)
    stop = mem+0x1f000
    uc.reg_write(UC_ARM64_REG_SP,mem+0x1e000)
    uc.reg_write(UC_ARM64_REG_LR,stop)
    for reg,val in [(UC_ARM64_REG_X0,obj),(UC_ARM64_REG_X1,buf),
                    (UC_ARM64_REG_X2,len(source)),(UC_ARM64_REG_X3,output)]:
        uc.reg_write(reg,val)
    trace = []
    def check(emu, address, size, unused):
        rva = address-base
        if not 0x73c808 <= rva < 0x73cb70:
            raise RuntimeError(f'Unexpected code target {address:#x}; no external calls allowed')
        trace.append(rva)
    uc.hook_add(UC_HOOK_CODE,check)
    uc.emu_start(base+0x73ca9c,stop,count=2000)
    pointer = uc.reg_read(UC_ARM64_REG_X0)
    length = struct.unpack('<Q',uc.mem_read(output,8))[0]
    unchanged = pointer == buf and length == len(source) and bytes(uc.mem_read(buf,len(source))) == source
    assert unchanged
    rows.append({'case':label,'bytes':len(source),'input_sha256':hashlib.sha256(source).hexdigest(),
                 'same_pointer_size_and_bytes':unchanged,'instructions':len(trace),
                 'decrypt_wrapper_called':0x4c3fc8 in trace})
result = {'decoder_rva':'0x73ca9c','signature_check_rva':'0x73c808',
          'scope':'Synthetic resource decoder only; does not establish Android require/FileUtils acceptance',
          'cases':rows}
(ROOT/'evidence/phase5_plaintext_decoder.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
