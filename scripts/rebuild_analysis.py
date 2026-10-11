#!/usr/bin/env python3
"""Merge readable PT_LOAD bytes, preserving unmapped original ELF metadata.

Outputs are analysis artifacts, NOT standalone reloadable unpacked libraries.
The artificial text window and disabled shell dynsym only facilitate objdump.
"""
import hashlib, json, pathlib, struct
root=pathlib.Path(__file__).resolve().parents[1]
m=json.loads((root/'recovered/runtime/manifest.json').read_text())
report=[]
for name in ('libcocos2dlua.so','libFairGuard.so'):
    original=(root/'extracted/lib/arm64-v8a'/name).read_bytes()
    b=bytearray(original)
    phoff=struct.unpack_from('<Q',b,32)[0]
    phsize,phnum=struct.unpack_from('<HH',b,54)
    loads=[]
    for i in range(phnum):
        typ,flags,off,va,pa,fs,ms,align=struct.unpack_from('<IIQQQQQQ',b,phoff+i*phsize)
        if typ==1: loads.append((off,off+fs))
    ranges=[]
    for segment in m['segments']:
        if segment['name']!=name:continue
        data=(root/'recovered/runtime'/segment['file']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=segment['sha256']:raise ValueError('Dump hash mismatch')
        off=segment['file_offset']
        for low,high in loads:
            start=max(low,off);end=min(high,off+len(data))
            if end>start:
                b[start:end]=data[start-off:end-off];ranges.append([start,end])
    (root/'recovered'/f'{name}.memory.so').write_bytes(b)
    report.append({'name':name,'original_sha256':hashlib.sha256(original).hexdigest(),
        'memory_sha256':hashlib.sha256(b).hexdigest(),'merged_file_ranges':ranges,
        'changed_bytes':sum(x!=y for x,y in zip(original,b)),
        'warning':'Runtime pointers, zeroed metadata, and external trampolines remain. Not reloadable.'})
    if name=='libcocos2dlua.so':
        shoff=struct.unpack_from('<Q',b,40)[0]
        shsize,shnum,stridx=struct.unpack_from('<HHH',b,58)
        stroff,strsize=struct.unpack_from('<QQ',b,shoff+stridx*shsize+24)
        names=b[stroff:stroff+strsize]
        for i in range(shnum):
            off=shoff+i*shsize
            ni,typ=struct.unpack_from('<II',b,off)
            section=names[ni:].split(b'\0')[0]
            if section==b'.text':
                struct.pack_into('<QQQ',b,off+16,0x200000,0x200000,0xbf0000-0x200000)
            if typ in (2,11):struct.pack_into('<I',b,off+4,1)
        (root/'recovered'/f'{name}.analysis.so').write_bytes(b)
(root/'evidence/memory_reconstruction.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
