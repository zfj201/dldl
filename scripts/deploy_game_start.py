#!/usr/bin/env python3
"""Hash-guarded atomic replacement of one game-owned script, with backup.

User-authorized experiment only. Does not modify APK, accounts, or other scripts.
The app is stopped before replacement and reopened afterwards.
"""
import argparse,datetime,hashlib,json,pathlib,shlex,subprocess
p=argparse.ArgumentParser();p.add_argument('file',type=pathlib.Path);p.add_argument('--expect',required=True);p.add_argument('--out',required=True);a=p.parse_args()
adb=['adb','-s','4XQ4U4Z94T85TGAY'];pkg='com.hnzh.dldlwhjx.huawei'
base='/data/user/0/'+pkg+'/files';target=base+'/assets/src/game_start.luac'
backup=base+'/dldl_backup_20261011/game_start.luac';stage=target+'.dldl-install'
scratch='/data/local/tmp/dldl_game_start.stage'
original_hash='033b45a3d279ef2302003ba6f7ec9a6e740f200d9d8c5b775336307d65c35d7f'
def root(cmd,data=None):
 return subprocess.check_output(adb+['exec-out','su -c '+shlex.quote(cmd)],input=data,timeout=30)
def digest(path):return root('sha256sum '+shlex.quote(path)).decode().split()[0]
data=a.file.read_bytes();new_hash=hashlib.sha256(data).hexdigest()
assert digest(target)==a.expect,'Live script changed; aborting without replacement'
attrs=root('stat -c '+shlex.quote('%u %g %a')+' '+shlex.quote(target)).decode().split()
assert attrs==['10303','10303','600'],attrs
context=root('ls -Z '+shlex.quote(target)).decode().split()[0]
assert context.startswith('u:object_r:app_data_file:'),context
subprocess.check_call(adb+['shell','am','force-stop',pkg])
assert digest(target)==a.expect,'Script changed while stopping'
root('mkdir -p '+shlex.quote(base+'/dldl_backup_20261011'))
exists=root('test -f '+shlex.quote(backup)+' && echo yes || echo no').decode().strip()
if exists=='no':
 assert a.expect==original_hash,'Original backup missing; refuse to back up modified file'
 root('cp -p '+shlex.quote(target)+' '+shlex.quote(backup))
assert digest(backup)==original_hash,'Backup hash mismatch'
subprocess.check_call(adb+['push',str(a.file),scratch])
assert digest(scratch)==new_hash,'Transfer mismatch'
root('cp '+shlex.quote(scratch)+' '+shlex.quote(stage))
assert digest(stage)==new_hash,'Transfer mismatch'
root('chown 10303:10303 '+shlex.quote(stage))
root('chmod 600 '+shlex.quote(stage))
root('chcon '+shlex.quote(context)+' '+shlex.quote(stage))
root('mv '+shlex.quote(stage)+' '+shlex.quote(target))
assert digest(target)==new_hash,'Installed hash mismatch'
record={'time':datetime.datetime.now().isoformat(),'local_source':str(a.file),'previous_sha256':a.expect,
 'installed_sha256':new_hash,'target':target,'backup':backup,'backup_sha256':original_hash,'uid':10303,'mode':'600','selinux':context}
pathlib.Path(a.out).write_text(json.dumps(record,indent=2))
subprocess.check_call(adb+['shell','am','start','-n',pkg+'/com.game.sdk.GameSdkActivity'])
print(json.dumps(record,indent=2))
