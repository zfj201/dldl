#!/usr/bin/env python3
"""Run a reviewed local Lua file once on the target Cocos scheduler thread.
No automatic restart, file writes to phone, or repeat execution on timeout.
"""
import argparse,json,pathlib,threading,frida
p=argparse.ArgumentParser();p.add_argument('file');p.add_argument('--pid',required=True,type=int)
p.add_argument('--serial',default='4XQ4U4Z94T85TGAY');p.add_argument('--out',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
b=(root/'recovered/libcocos2dlua.so.memory.so').read_bytes()
expected={str(x):b[x:x+16].hex() for x in [0x6c9564,0x6c9578,0x6ca238,0x6c9f2c,0x6c97a8,0x6ca96c,0x6c9ba8,0xa24b94]}
source=(root/'scripts/run_lua_once.js').read_text().replace('__EXPECTED__',json.dumps(expected)).replace('__SOURCE__',json.dumps(pathlib.Path(a.file).read_text()))
rows=[];done=threading.Event()
def callback(msg,data):
 rows.append(msg);print(json.dumps(msg,ensure_ascii=False),flush=True)
 if msg.get('type')=='error' or msg.get('payload',{}).get('kind') in ['lua_result','failure']:done.set()
session=frida.get_device(a.serial,timeout=10).attach(a.pid)
try:
 script=session.create_script(source);script.on('message',callback);script.load()
 if not done.wait(20):rows.append({'timeout':True});print('Timed out; no retry',flush=True)
finally:
 session.detach();pathlib.Path(a.out).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
if not any(r.get('payload',{}).get('kind')=='lua_result' and r['payload']['status']==0 for r in rows):raise SystemExit(1)
