#!/usr/bin/env python3
"""Decode selected APK resources through existing target's memory-only transform."""
import argparse,hashlib,json,pathlib,zipfile
import frida
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True)
p.add_argument('--device',required=True);p.add_argument('--bootstrap',action='store_true')
p.add_argument('--out',default='recovered/phase2/native_probe');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
state=json.loads((root/'evidence/resource_state.json').read_text())
key=state['derived_fields'][0]['hex'];sign=bytes.fromhex(state['derived_fields'][1]['hex'])
headers=json.loads((root/'evidence/asset_headers.json').read_text())
samples=sorted([x for x in headers if x['head_hex'].startswith(sign.hex())],key=lambda x:x['size'])[:8]
if a.bootstrap:samples += [x for x in headers if x['name'].endswith('obk364w4z0k0oj248804e895vf968526wa845824b')]
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
device=frida.get_device(a.device,timeout=10);session=device.attach(a.pid)
records=[]
try:
    script=session.create_script(pathlib.Path(__file__).with_suffix('.js').read_text())
    script.on('message',lambda msg,data:print('FRIDA',json.dumps(msg),flush=True));script.load()
    print(json.dumps(script.exports_sync.info()),flush=True)
    source=json.loads((root/'input/sample.json').read_text())['source']
    with zipfile.ZipFile(source) as z:
        for item in samples:
            data=z.read(item['name']);record={'input':item['name'],'input_size':len(data)}
            try:
                decoded=script.exports_sync.decrypt(data[len(sign):].hex(),key)
                digest=hashlib.sha256(decoded).hexdigest();(out/(digest+'.bin')).write_bytes(decoded)
                record.update(output_sha256=digest,output_size=len(decoded),head_hex=decoded[:64].hex(),status='decoded')
            except Exception as e:record.update(status='error',error=str(e))
            records.append(record);print(json.dumps(record),flush=True)
            (out/'manifest.json').write_text(json.dumps(records,indent=2))
finally:session.detach()
