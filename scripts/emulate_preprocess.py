#!/usr/bin/env python3
"""Offline ARM64 resource preprocessing using captured target mappings.

All writes and allocation occur inside Unicorn. Missing readable data pages are
fetched from the specified target PID and cached locally; no remote writes.
Unknown external calls and syscalls stop emulation instead of being executed.
"""
import argparse,hashlib,json,pathlib,shlex,struct,subprocess,time,zipfile
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_MEM_INVALID,UC_HOOK_CODE,UcError
from unicorn.arm64_const import *
from probe_xxtea import decrypt

p=argparse.ArgumentParser();p.add_argument('--snapshot',default='recovered/phase2/runtime')
p.add_argument('--resource',default='assets/res/4/8/obk364w4z0k0oj248804e895vf968526wa845824b')
p.add_argument('--resource-file',help='Use a locally captured encrypted resource instead of an APK entry')
p.add_argument('--offline',action='store_true',help='Stop if a required data page is not already cached')
p.add_argument('--out',default='recovered/phase2/emulated');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];snapshot=root/a.snapshot
meta=json.loads((snapshot/'manifest.json').read_text());out=root/a.out;out.mkdir(parents=True,exist_ok=True)
page_dir=snapshot/'pages';page_dir.mkdir(exist_ok=True)
adb=['adb','-s',meta['serial']]
maps=[]
for line in (snapshot/'maps.txt').read_text().splitlines():
    fields=line.split();lo,hi=[int(s,16) for s in fields[0].split('-')]
    maps.append((lo,hi,fields[1],int(fields[2],16),fields[-1] if len(fields)>5 else ''))
fair=next(s['start'] for s in meta['segments'] if s['name']=='libFairGuard.so' and s['file_offset']==0)
libc=min(lo-off for lo,hi,perm,off,name in maps if name.endswith('/libc.so'))
uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);mapped=set();remote_pages=[];calls={};instruction_count=0
failure=None
def put(addr,data):
    lo=addr&~4095;hi=(addr+len(data)+4095)&~4095
    run=None
    for page in range(lo,hi,4096):
        if page not in mapped:
            if run is None:run=page
        elif run is not None:
            uc.mem_map(run,page-run);mapped.update(range(run,page,4096));run=None
    if run is not None:
        uc.mem_map(run,hi-run);mapped.update(range(run,hi,4096))
    uc.mem_write(addr,bytes(data))
for segment in meta['segments']:
    data=(snapshot/segment['file']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=segment['sha256']:raise ValueError('Snapshot hash mismatch')
    put(segment['start'],data)

def fetch(page):
    remote=page&0x00ffffffffffffff
    if not any(lo<=remote and remote+4096<=hi and 'r' in perm for lo,hi,perm,off,name in maps):
        raise ValueError(f'Address outside readable snapshot maps: {page:x}')
    cache=page_dir/f'{remote:x}.bin'
    if cache.exists():
        data=cache.read_bytes()
        if len(data)!=4096:raise ValueError('Invalid cached page size')
        return data
    if a.offline:raise ValueError(f'Offline page not cached: {remote:x}')
    if len(remote_pages)>=512:raise ValueError('Lazy page limit reached')
    live=subprocess.check_output(adb+['shell','pidof',meta['package']],text=True).strip()
    if live!=str(meta['pid']):raise ValueError('Target PID changed')
    cmd=f'dd if=/proc/{meta["pid"]}/mem bs=4096 skip={remote//4096} count=1 2>/dev/null'
    data=subprocess.check_output(adb+['exec-out','su -c '+shlex.quote(cmd)])
    if len(data)!=4096:raise ValueError('Short remote page read')
    cache.write_bytes(data);remote_pages.append({'address':hex(remote),'sha256':hashlib.sha256(data).hexdigest()})
    return data
def ensure(addr,size):
    for page in range(addr&~4095,(addr+size+4095)&~4095,4096):
        if page not in mapped:put(page,fetch(page))
def read(addr,size):ensure(addr,size);return bytes(uc.mem_read(addr,size))
def invalid(uc,access,address,size,value,data):
    global failure
    try:ensure(address,max(1,size));return True
    except Exception as e:failure=str(e);return False
uc.hook_add(UC_HOOK_MEM_INVALID,invalid)
heap=0x1000000000;heap_end=heap+64*1024*1024;heap_next=heap
uc.mem_map(heap,heap_end-heap);mapped.update(range(heap,heap_end,4096))
allocations={}
def alloc(size):
    global heap_next
    if size>32*1024*1024:raise ValueError(f'Allocation too large {size}')
    result=heap_next;heap_next+=(max(size,1)+15)&~15
    if heap_next>=heap_end:raise ValueError('Emulated heap exhausted')
    allocations[result]=size;return result
def cstr(addr,limit=1024*1024):
    result=bytearray()
    while len(result)<limit:
        size=min(4096-(addr&4095),limit-len(result));b=read(addr,size)
        end=b.find(b'\0')
        if end>=0:return bytes(result+b[:end])
        result.extend(b);addr+=size
    raise ValueError('Unterminated string')
handlers={}
with (root/'extracted/runtime_libc.so').open('rb') as f:
    elf=ELFFile(f)
    for symbol in elf.get_section_by_name('.dynsym').iter_symbols():
        if symbol['st_value']:handlers[libc+symbol['st_value']]=symbol.name
registers=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5]
def external(name,args):
    x0,x1,x2,x3,x4,x5=args
    if name in ('malloc','_Znwm','_Znam'):return alloc(x0)
    if name=='calloc':result=alloc(x0*x1);return result
    if name=='realloc':
        result=alloc(x1)
        if x0:uc.mem_write(result,read(x0,min(x1,allocations.get(x0,x1))))
        return result
    if name in ('free','_ZdlPv','_ZdaPv'):return 0
    if name in ('memcpy','memmove','__memcpy_chk','__memmove_chk'):
        uc.mem_write(x0,read(x1,x2));return x0
    if name in ('memset','__memset_chk'):
        uc.mem_write(x0,bytes([x1&255])*x2);return x0
    if name in ('strlen','__strlen_chk'):return len(cstr(x0))
    if name=='memcmp':
        aa,bb=read(x0,x2),read(x1,x2);return next((i-j for i,j in zip(aa,bb) if i!=j),0)
    if name in ('strcmp','strncmp'):
        aa,bb=cstr(x0),cstr(x1)
        if name=='strncmp':aa,bb=aa[:x2],bb[:x2]
        return (aa>bb)-(aa<bb)
    if name=='memchr':
        pos=read(x0,x2).find(bytes([x1&255]));return 0 if pos<0 else x0+pos
    if name in ('pthread_mutex_lock','pthread_mutex_unlock'):return 0
    raise ValueError('Unsupported external '+name)
sentinel=0x3000000000;put(sentinel,b'\x00'*4096)
def code(uc,address,size,data):
    global instruction_count,failure
    instruction_count+=1
    if address==sentinel:uc.emu_stop();return
    try:
        if address in handlers:
            name=handlers[address];calls[name]=calls.get(name,0)+1
            value=external(name,[uc.reg_read(r) for r in registers])
            uc.reg_write(UC_ARM64_REG_X0,value&0xffffffffffffffff)
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
        ins=bytes(uc.mem_read(address,4))
        if struct.unpack('<I',ins)[0]&0xffe0001f==0xd4000001:raise ValueError('System call blocked in emulator')
        if not any(s['start']<=address<s['end'] for s in meta['segments']):
            raise ValueError(f'Unknown external PC {address:x}')
    except Exception as e:failure=str(e);uc.emu_stop()
uc.hook_add(UC_HOOK_CODE,code)
if a.resource_file:resource=(root/a.resource_file).read_bytes()
else:
    with zipfile.ZipFile(json.loads((root/'input/sample.json').read_text())['source']) as z:resource=z.read(a.resource)
state=json.loads((root/'evidence/resource_state.json').read_text());sign=bytes.fromhex(state['derived_fields'][1]['hex'])
assert resource.startswith(sign)
payload=resource[len(sign):];buffer=alloc(len(payload)+8192);uc.mem_write(buffer,payload)
stack=0x2000000000;put(stack,b'\0'*(2*1024*1024));uc.reg_write(UC_ARM64_REG_SP,stack+2*1024*1024-0x100)
uc.reg_write(UC_ARM64_REG_X0,buffer);uc.reg_write(UC_ARM64_REG_X1,len(payload));uc.reg_write(UC_ARM64_REG_LR,sentinel)
started=time.monotonic()
try:uc.emu_start(fair+0x341660,sentinel,timeout=60_000_000,count=5_000_000)
except UcError as e:failure=f'{failure or ""}; {e}'
pc=uc.reg_read(UC_ARM64_REG_PC)
result={'resource':a.resource_file or a.resource,'pid':meta['pid'],'fairguard_base':hex(fair),'instructions':instruction_count,
        'seconds':time.monotonic()-started,'pc':hex(pc),'pc_rva':hex(pc-fair),'failure':failure,
        'completed':pc==sentinel and failure is None,'calls':calls,'new_remote_pages':remote_pages}
if result['completed']:
    preprocessed=bytes(uc.mem_read(buffer,len(payload)))
    (out/'preprocessed.bin').write_bytes(preprocessed)
    result['changed_bytes']=sum(x!=y for x,y in zip(payload,preprocessed))
    decoded=decrypt(preprocessed,bytes.fromhex(state['derived_fields'][0]['hex']))
    result['xxtea_length_valid']=decoded is not None
    if decoded is not None:
        (out/'decoded.bin').write_bytes(decoded);result['decoded_size']=len(decoded);result['head_hex']=decoded[:64].hex()
result['registers']={f'x{i}':hex(uc.reg_read(r)) for i,r in enumerate(registers)}
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
