#!/usr/bin/env python3
"""Reproduce sample fingerprint, ZIP inventory, DEX validation and extraction."""
import argparse,collections,hashlib,json,pathlib,struct,zipfile,zlib
p=argparse.ArgumentParser();p.add_argument('apk');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];apk=pathlib.Path(a.apk).resolve()
for name in ('input','evidence','extracted','recovered/plaintext','logs'):(root/name).mkdir(parents=True,exist_ok=True)
def write(name,obj):(root/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
h=hashlib.sha256()
with apk.open('rb') as f:
    for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
write('input/sample.json',{'source':str(apk),'size':apk.stat().st_size,'sha256':h.hexdigest()})
headers=[];dex=[]
with zipfile.ZipFile(apk) as z:
    write('evidence/zip_inventory.json',[{'name':i.filename,'size':i.file_size,'compressed':i.compress_size,'crc':i.CRC} for i in z.infolist()])
    for i in z.infolist():
        n=i.filename;path=pathlib.PurePosixPath(n)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe ZIP path')
        if n.startswith('assets/res/'):
            with z.open(n) as f:head=f.read(64)
            headers.append({'name':n,'size':i.file_size,'head_hex':head.hex()})
            if head.startswith(b'return {'):
                out=root/'recovered/plaintext'/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(n))
        elif n.endswith('.dex') or n.startswith(('lib/','assets/')):
            z.extract(n,root/'extracted')
        if n.endswith('.dex'):
            b=z.read(n)
            dex.append({'file':n,'size':len(b),'magic':b[:8].hex(),'file_size_header':struct.unpack_from('<I',b,32)[0],
                'classes':struct.unpack_from('<I',b,96)[0],'methods':struct.unpack_from('<I',b,88)[0],
                'adler32_ok':struct.unpack_from('<I',b,8)[0]==zlib.adler32(b[12:]),'sha1_ok':b[12:32]==hashlib.sha1(b[32:]).digest()})
write('evidence/asset_headers.json',headers);write('evidence/dex_validation.json',dex)
print('SHA256',h.hexdigest(),'resource entries',len(headers),'DEX files',len(dex))
