#!/usr/bin/env python3
"""Read-only guard-state snapshot through root /proc; never attaches or writes."""
import argparse, datetime, json, pathlib, shlex, struct, subprocess
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--out',required=True);a=p.parse_args()
adb=['adb','-s','4XQ4U4Z94T85TGAY']
def run(cmd):return subprocess.check_output(adb+['exec-out','su -c '+shlex.quote(cmd)],timeout=10)
live=subprocess.check_output(adb+['shell','pidof','com.hnzh.dldlwhjx.huawei'],text=True).strip()
if live!=str(a.pid):raise SystemExit('PID changed')
lines=run(f'cat /proc/{a.pid}/maps').decode().splitlines()
regions=[]
for line in lines:
 f=line.split();lo,hi=[int(v,16) for v in f[0].split('-')];regions.append((lo,hi,f[1],int(f[2],16),f[-1]))
def read(addr,size):
 addr &= 0x00ffffffffffffff
 assert any(lo<=addr and addr+size<=hi and 'r' in perms for lo,hi,perms,off,name in regions),'unmapped pointer'
 page=addr&~4095;count=(addr-page+size+4095)//4096
 d=run(f'dd if=/proc/{a.pid}/mem bs=4096 skip={page//4096} count={count} 2>/dev/null')
 d=d[addr-page:addr-page+size];assert len(d)==size;return d
def ptr(addr):return struct.unpack('<Q',read(addr,8))[0]&0x00ffffffffffffff
result={'time':datetime.datetime.now().isoformat(),'pid':a.pid,'modules':[]}
for name,slot_rva,entry in [('libcocos2dlua.so',0xf97e88,0xf67510),('libFairGuard.so',0x4dbe88,0x4ab510)]:
 base=min(lo-off for lo,hi,perms,off,n in regions if n.endswith('/'+name))
 row={'name':name,'base':hex(base),'entry_hex':read(base+entry,32).hex()}
 try:
  slot=ptr(base+slot_rva);context=ptr(slot);state=ptr(context+0x40)
  row.update(slot=hex(slot),context=hex(context),state=hex(state),status=hex(struct.unpack('<I',read(state+0x430,4))[0]),counter=struct.unpack('<H',read(state+0x42e,2))[0])
 except Exception as e:row['error']=str(e)
 result['modules'].append(row)
pathlib.Path(a.out).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
