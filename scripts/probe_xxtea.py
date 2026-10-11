#!/usr/bin/env python3
"""Validate XXTEA against observed resource keys; no key brute force."""
import json, pathlib, struct, zipfile
MASK=(1<<32)-1
def decrypt(data, key):
    if len(data)%4 or len(data)<8: return None
    v=list(struct.unpack('<%dI'%(len(data)//4),data))
    k=struct.unpack('<4I',key[:16].ljust(16,b'\0'))
    n=len(v); total=((6+52//n)*0x9e3779b9)&MASK; y=v[0]
    while total:
        e=(total>>2)&3
        for p in range(n-1,-1,-1):
            z=v[p-1] if p else v[-1]
            mx=(((z>>5 ^ y<<2)+(y>>3 ^ z<<4)) ^ ((total^y)+(k[(p&3)^e]^z)))&MASK
            v[p]=(v[p]-mx)&MASK; y=v[p]
        total=(total-0x9e3779b9)&MASK
    raw=struct.pack('<%dI'%n,*v)
    size=v[-1]
    if (n-1)*4-3 <= size <= (n-1)*4:return raw[:size]
    return None

if __name__=='__main__':
    state=json.load(open('evidence/resource_state.json'))
    keys=[bytes.fromhex(state['key_hex'])]+[bytes.fromhex(v['hex']) for v in state['derived_fields']]
    heads=json.load(open('evidence/asset_headers.json'))
    samples=sorted([v for v in heads if v['head_hex'].startswith('6563393333363037')],key=lambda v:v['size'])[:8]
    with zipfile.ZipFile(json.load(open('input/sample.json'))['source']) as z:
        for s in samples:
            data=z.read(s['name'])
            for key in keys:
                out=decrypt(data[16:],key)
                if out is not None: print(s['name'],len(data),key,repr(out[:120]))
