#!/usr/bin/env python3
"""Bounded, timestamped Frida attachment experiment; no suppression or retries."""
import argparse,datetime,json,pathlib,threading,time,frida
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--seconds',type=int,default=45);p.add_argument('--script');p.add_argument('--out',required=True);a=p.parse_args()
rows=[];ended=threading.Event();out=pathlib.Path(a.out)
def record(kind,**kw):
 row={'time':datetime.datetime.now().isoformat(),'kind':kind,**kw};rows.append(row);out.write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(json.dumps(row,ensure_ascii=False),flush=True)
session=None
try:
 record('attach_begin',pid=a.pid)
 session=frida.get_device('4XQ4U4Z94T85TGAY',timeout=10).attach(a.pid)
 session.on('detached',lambda reason,crash:(record('detached',reason=reason,crash=str(crash)),ended.set()))
 record('attached')
 source=pathlib.Path(a.script).read_text() if a.script else "send({kind:'passive_ready',pid:Process.id});"
 script=session.create_script(source);script.on('message',lambda msg,data:record('message',message=msg));script.load()
 ended.wait(a.seconds)
 if not ended.is_set():record('hold_completed',seconds=a.seconds)
except Exception as error:
 record('exception',error_type=type(error).__name__,error=str(error))
 raise
finally:
 if session and not ended.is_set():session.detach()
 record('experiment_finished')
