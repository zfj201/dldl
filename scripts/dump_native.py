#!/usr/bin/env python3
"""Read only target APK's native mappings through adb + existing root."""
import argparse
import hashlib
import json
import pathlib
import shlex
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--serial', required=True)
p.add_argument('--package', default='com.hnzh.dldlwhjx.huawei')
p.add_argument('--out', default='recovered/runtime')
a = p.parse_args()
adb = ['adb', '-s', a.serial]
pid_text = subprocess.check_output(adb + ['shell', 'pidof', a.package], text=True).strip()
if not pid_text.isdigit():
    raise SystemExit('Expected exactly one running target PID')
pid = int(pid_text)
def root(command):
    return subprocess.check_output(adb + ['exec-out', 'su -c ' + shlex.quote(command)])
maps = root(f'cat /proc/{pid}/maps').decode()
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)
(out/'maps.txt').write_text(maps)
manifest = {'pid': pid, 'package': a.package, 'serial': a.serial, 'segments': []}
for line in maps.splitlines():
    parts = line.split()
    if len(parts) < 6 or a.package not in parts[-1]:
        continue
    name = pathlib.PurePosixPath(parts[-1]).name
    if name not in ('libcocos2dlua.so', 'libFairGuard.so'):
        continue
    start, end = (int(x, 16) for x in parts[0].split('-'))
    if 'r' not in parts[1] or start % 4096 or end % 4096:
        raise ValueError(line)
    data = root(f'dd if=/proc/{pid}/mem bs=4096 skip={start//4096} count={(end-start)//4096} 2>/dev/null')
    if len(data) != end-start:
        raise ValueError(f'Short read: {line}: {len(data)}')
    filename = f'{name}.{start:x}-{end:x}.bin'
    (out/filename).write_bytes(data)
    manifest['segments'].append({'name': name, 'start': start, 'end': end,
        'file_offset': int(parts[2], 16), 'permissions': parts[1], 'file': filename,
        'sha256': hashlib.sha256(data).hexdigest()})
    print(filename, len(data), flush=True)
(out/'manifest.json').write_text(json.dumps(manifest, indent=2))
