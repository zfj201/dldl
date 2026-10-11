#!/usr/bin/env python3
"""Offline pointer/PLT/call-site triage. Candidates are not executed-path proof."""
import hashlib
import json
import pathlib
import struct

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAP = ROOT / 'recovered/runtime'
meta = json.loads((SNAP / 'manifest.json').read_text())
maps = (SNAP / 'maps.txt').read_text().splitlines()
libc_base = min(int(x.split()[0].split('-')[0], 16) - int(x.split()[2], 16)
                for x in maps if x.endswith('/libc.so'))
names = {'exit', '_exit', 'kill', 'tgkill', 'abort', 'ptrace', 'syscall',
         'pthread_create', 'open', 'openat', 'fopen', 'prctl'}
with (ROOT / 'extracted/runtime_libc.so').open('rb') as f:
    elf = ELFFile(f)
    symbols = {s.name: s['st_value'] for s in elf.get_section_by_name('.dynsym').iter_symbols()
               if s.name in names}
cs = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
cs.skipdata = True
result = {'snapshot_pid': meta['pid'], 'libc_base': hex(libc_base), 'modules': []}
listing = []
for name in ('libcocos2dlua.so', 'libFairGuard.so'):
    segments = [s for s in meta['segments'] if s['name'] == name]
    base = next(s['start'] for s in segments if s['file_offset'] == 0)
    data = bytearray(max(s['end'] for s in segments) - base)
    for seg in segments:
        raw = (SNAP / seg['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == seg['sha256']
        data[seg['start'] - base:seg['end'] - base] = raw
    def dis(lo, hi):
        return '\n'.join(f'{i.address:#x}: {i.mnemonic} {i.op_str}'
                         for i in cs.disasm(bytes(data[lo:hi]), lo))
    slots = {}
    for symbol, rva in symbols.items():
        needle = struct.pack('<Q', libc_base + rva)
        start = 0
        while True:
            pos = data.find(needle, start)
            if pos < 0:
                break
            slots[pos] = symbol
            start = pos + 1
    refs = []
    stubs = {}
    syscalls = []
    exit_group_wrappers = []
    branches = {}
    for off in range(0, len(data) - 16, 4):
        ins = struct.unpack_from('<I', data, off)[0]
        if ins & 0x7c000000 == 0x14000000:
            imm = ins & 0x3ffffff
            if imm & 0x2000000:
                imm -= 0x4000000
            branches.setdefault(off + imm * 4, []).append(off)
        if ins == 0xd4000001:
            syscalls.append(hex(off))
            listing.append(f'\n{name} SVC candidate {off:#x}\n{dis(max(0, off-32), off+16)}')
            # AArch64 Linux __NR_exit_group = 94 (MOVZ X8, #94; SVC #0).
            if off >= 4 and struct.unpack_from('<I', data, off-4)[0] == 0xd2800bc8:
                exit_group_wrappers.append(off-4)
        if ins & 0x9f000000 != 0x90000000:
            continue
        reg = ins & 31
        imm = ((ins >> 29) & 3) | (((ins >> 5) & 0x7ffff) << 2)
        if imm & 0x100000:
            imm -= 0x200000
        page = (off & ~4095) + (imm << 12)
        for delta in (4, 8, 12):
            nxt = struct.unpack_from('<I', data, off + delta)[0]
            if nxt & 0xffc00000 == 0xf9400000 and (nxt >> 5) & 31 == reg:
                slot = page + ((nxt >> 10) & 4095) * 8
                if slot in slots:
                    refs.append({'adrp': hex(off), 'load': hex(off+delta),
                                 'slot': hex(slot), 'symbol': slots[slot]})
                    # Standard AArch64 PLT starts ADRP x16; LDR x17; ADD; BR x17.
                    if reg == 16 and delta == 4 and data[off+12:off+16] == bytes.fromhex('20021fd6'):
                        stubs[off] = slots[slot]
                    listing.append(f'\n{name} {slots[slot]} pointer reference\n{dis(off, off+24)}')
    calls = []
    exit_group_calls = []
    for stub in exit_group_wrappers:
        for site in branches.get(stub, []):
            exit_group_calls.append({'wrapper': hex(stub), 'site': hex(site)})
            listing.append(f'\n{name} direct exit_group caller\n{dis(max(0,site-128),site+24)}')
    for stub, symbol in stubs.items():
        for site in branches.get(stub, []):
            calls.append({'symbol': symbol, 'stub': hex(stub), 'site': hex(site)})
            if symbol in {'exit', '_exit', 'kill', 'ptrace', 'syscall'}:
                listing.append(f'\n{name} {symbol} caller\n{dis(max(0, site-48), site+24)}')
    result['modules'].append({'name': name, 'pointer_slots': {hex(k): v for k,v in slots.items()},
                              'pointer_refs': refs, 'plt_calls': calls, 'svc_candidates': syscalls,
                              'exit_group_wrappers': [hex(x) for x in exit_group_wrappers],
                              'exit_group_calls': exit_group_calls})
(ROOT/'evidence/phase5_exit_scan.json').write_text(json.dumps(result, indent=2))
(ROOT/'evidence/phase5_exit_scan.asm.txt').write_text('\n'.join(listing))
for module in result['modules']:
    print(module['name'], 'slots', len(module['pointer_slots']), 'refs', len(module['pointer_refs']),
          'calls', len(module['plt_calls']), 'svc candidates', len(module['svc_candidates']))
    print([c for c in module['plt_calls'] if c['symbol'] in {'exit','kill','syscall','ptrace'}])
