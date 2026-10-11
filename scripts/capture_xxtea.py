#!/usr/bin/env python3
"""Prepared, not live-tested. Requires frida and compatible existing server.
Writes only XXTEA return buffers. Does not restart target or change return values.
"""
import argparse,hashlib,json,pathlib,time
import frida
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True)
p.add_argument('--device',required=True,help='Frida device ID from frida-ls-devices')
p.add_argument('--seconds',type=int,default=30)
p.add_argument('--out',default='recovered/xxtea_capture');a=p.parse_args()
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
def message(msg,data):
    if data:
        digest=hashlib.sha256(data).hexdigest()
        (out/(digest+'.bin')).write_bytes(data)
        msg['sha256']=digest
    with (out/'events.jsonl').open('a') as f:f.write(json.dumps(msg,ensure_ascii=False)+'\n')
    print(json.dumps(msg,ensure_ascii=False),flush=True)
device=frida.get_device(a.device,timeout=10)
session=device.attach(a.pid)
try:
    source=pathlib.Path(__file__).with_suffix('.js').read_text()
    script=session.create_script(source);script.on('message',message);script.load()
    time.sleep(max(1,min(a.seconds,300)))
finally:session.detach()
