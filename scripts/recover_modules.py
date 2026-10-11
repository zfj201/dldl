#!/usr/bin/env python3
"""Recover selected indexed Lua resources; retain provenance and decode results."""
import argparse,hashlib,json,pathlib,re,subprocess,sys,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('pattern');a=p.parse_args()
rows=json.loads((root/'evidence/phase2_file_map.json').read_text())
out=root/'recovered/phase2/lua';out.mkdir(parents=True,exist_ok=True)
manifest_path=root/'evidence/phase2_modules.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else []
known={x['logical'] for x in manifest if x.get('status')=='decoded'}
with zipfile.ZipFile(json.loads((root/'input/sample.json').read_text())['source']) as z:
 for row in rows:
  logical=row['logical']
  if not logical.endswith(('.lua','.luac')) or not re.search(a.pattern,logical) or logical in known:continue
  work=root/'recovered/phase2/module_runs'/logical
  run=subprocess.run([sys.executable,str(root/'scripts/emulate_preprocess.py'),'--offline','--resource',row['asset'],'--out',str(work)],capture_output=True,text=True)
  work.mkdir(parents=True,exist_ok=True);(work/'process.log').write_text(run.stdout+run.stderr)
  entry=dict(row,encrypted_sha256=hashlib.sha256(z.read(row['asset'])).hexdigest(),status='failed')
  if run.returncode==0 and (work/'result.json').exists():
   result=json.loads((work/'result.json').read_text())
   if result.get('completed') and result.get('xxtea_length_valid'):
    data=(work/'decoded.bin').read_bytes();dest=out/logical;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    entry.update(status='decoded',size=len(data),sha256=hashlib.sha256(data).hexdigest(),path=str(dest.relative_to(root)),head_hex=data[:16].hex())
  manifest=[x for x in manifest if x['logical']!=logical]+[entry]
  manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
  print(entry['status'],logical,entry.get('size'),flush=True)
  if entry['status']=='failed':print(run.stdout+run.stderr,flush=True)
