#!/usr/bin/env python3
"""Decode scoped resources from the read-only game src snapshot."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('pattern');a=p.parse_args()
base=root/'recovered/phase2/hotupdate'
rows=json.loads((root/'evidence/phase2_hotupdate_inventory.json').read_text())
manifest_path=root/'evidence/phase2_hotupdate_modules.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else []
known={x['logical'] for x in manifest if x.get('status')=='decoded'}
for row in rows:
 logical=row['logical']
 if not logical.endswith(('.lua','.luac')) or not re.search(a.pattern,logical) or logical in known:continue
 source=base/'raw'/logical
 assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
 work=base/'runs'/logical
 run=subprocess.run([sys.executable,str(root/'scripts/emulate_preprocess.py'),'--offline','--resource-file',str(source),'--out',str(work)],capture_output=True,text=True)
 work.mkdir(parents=True,exist_ok=True);(work/'process.log').write_text(run.stdout+run.stderr)
 entry={'logical':logical,'encrypted_sha256':row['sha256'],'status':'failed'}
 if run.returncode==0 and (work/'result.json').exists():
  result=json.loads((work/'result.json').read_text())
  if result.get('completed') and result.get('xxtea_length_valid'):
   data=(work/'decoded.bin').read_bytes();dest=base/'lua'/logical;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   entry.update(status='decoded',size=len(data),sha256=hashlib.sha256(data).hexdigest(),path=str(dest.relative_to(root)))
 manifest=[x for x in manifest if x['logical']!=logical]+[entry]
 manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print(entry['status'],logical,entry.get('size'),flush=True)
 if entry['status']=='failed':print(run.stdout+run.stderr,flush=True)
