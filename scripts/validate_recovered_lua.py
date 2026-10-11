#!/usr/bin/env python3
"""Hash and parse recovered Lua without executing the recovered programs."""
import hashlib,json,pathlib
from lupa.lua51 import LuaRuntime
root=pathlib.Path(__file__).resolve().parents[1]
lua=LuaRuntime(unpack_returned_tuples=True)
check=lua.eval('function(s,n) local f,e=loadstring(s,n);return f~=nil,e end')
result={};logical=set()
for label,name in [('apk','phase2_modules.json'),('hotupdate','phase2_hotupdate_modules.json')]:
 rows=json.loads((root/'evidence'/name).read_text());valid=[];errors=[]
 for row in rows:
  if row['status']!='decoded':continue
  data=(root/row['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256']
  ok,error=check(data.decode('utf-8'),'@'+row['logical'])
  (valid if ok else errors).append(row['logical'] if ok else {'path':row['logical'],'error':error})
  logical.add(row['logical'])
 result[label]={'decoded_files':len(valid)+len(errors),'decoded_bytes':sum(r.get('size',0) for r in rows),
  'lua51_parse_pass':len(valid),'parse_errors':errors,'decode_failures':[r['logical'] for r in rows if r['status']!='decoded']}
result['distinct_logical_paths']=len(logical)
result['note']='APK and hot-update are separate versions; parse checks do not execute game scripts.'
(root/'evidence/phase2_lua_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
assert all(not result[x]['parse_errors'] and not result[x]['decode_failures'] for x in ['apk','hotupdate'])
