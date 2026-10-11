"""Exercise the real updater on the device with a bad immutable web candidate."""
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.config import atomic_json
from hifi.maintenance import transaction

repo=Path(__file__).resolve().parents[1]
config=Path.home()/'.config/hifi-streamer'
refs=json.loads((config/'images.json').read_text())
def image_info(ref):
    value=json.loads(subprocess.check_output(['podman','image','inspect',ref]))[0]
    return {'image':'sha256:'+value['Id'].removeprefix('sha256:'),'size':value['Size'],'data_version':1,'component':'web'}
current=image_info(refs['web'])
path=config/'web-release.json'
backup=path.read_bytes() if path.exists() else None
atomic_json(path,current)
bad=image_info('docker.io/library/alpine:3.22')
manifest=repo/'.local-build/bad-web-release.json'
atomic_json(manifest,bad)
unit=Path.home()/'.config/systemd/user/hifi-web.service'
before=unit.read_text()
dlna_before=subprocess.check_output(['systemctl','--user','show','hifi-upmpdcli','-p','ActiveEnterTimestamp'],text=True)
result={}
try:
    process=subprocess.run([sys.executable,str(repo/'deploy/update.py'),str(manifest)],capture_output=True,text=True,timeout=100)
    assert process.returncode!=0,'bad candidate unexpectedly committed'
    assert unit.read_text()==before,'original unit was not restored'
    assert json.loads((config/'images.json').read_text())==refs,'refs changed after failed update'
    assert subprocess.check_output(['systemctl','--user','is-active','hifi-web'],text=True).strip()=='active'
    import urllib.request
    http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    assert http.open('http://127.0.0.1:8080/',timeout=5).status==200
    assert 'candidate failed health check' in process.stderr,process.stderr[-1200:]
    result['bad_candidate_real_rollback']='passed'
    assert dlna_before==subprocess.check_output(['systemctl','--user','show','hifi-upmpdcli','-p','ActiveEnterTimestamp'],text=True)
    result['dlna_not_restarted']='passed'
    # Real immutable current-image success through the same CLI.
    atomic_json(manifest,current)
    subprocess.run([sys.executable,str(repo/'deploy/update.py'),str(manifest)],check=True,timeout=60)
    result['health_commit']='passed'
    for name,free,old,new in (
        ('disk_insufficient',0,current,current),
        ('candidate_expired',10**10,current,{**current,'expires_at':time.time()-1}),
        ('rollback_expired',10**10,{**current,'expires_at':time.time()-1},current),
    ):
        attempts=[]
        try:
            transaction(old,new,True,free,attempts.append,lambda:True,lambda *a:None)
            raise AssertionError(name+' not rejected')
        except ValueError:
            assert not attempts
            result[name]='passed'
    (repo/'.local-build/update-device-report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
finally:
    # Keep verified release metadata for subsequent actual releases.
    if unit.read_text()!=before:
        unit.write_text(before)
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['systemctl','--user','restart','hifi-web'],check=True)
