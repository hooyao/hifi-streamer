#!/usr/bin/env python3
"""Apply an operator-supplied immutable release for one optional module."""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import logging
import logging.handlers
import fcntl
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'modules/audio-agent'))
from hifi.config import atomic_json
from hifi.maintenance import transaction
from hifi.websocket import Client

CONFIG = Path.home()/'.config/hifi-streamer'


def output_idle():
    for path in Path('/proc/asound').glob('card*/stream0'):
        if 'Status: Running' in path.read_text():
            return False
    return True


def healthy(component):
    if component == 'web':
        import urllib.request
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return opener.open('http://127.0.0.1:8080/',timeout=2).status == 200
        except Exception:
            return False
    try:
        client = Client()
        client.send({'type':'command','command':'get_auth_state'})
        response = client.receive()
        client.close()
        return response.get('type') == 'auth_state'
    except Exception:
        return False


def main():
    state_dir = CONFIG/'state'
    state_dir.mkdir(parents=True,exist_ok=True)
    logger = logging.getLogger('update')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.handlers.RotatingFileHandler(state_dir/'update-apply.log',maxBytes=262144,backupCount=1))
    update_lock = (CONFIG/'update.lock').open('a')
    try:
        fcntl.flock(update_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('another update is already running')
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest',type=Path)
    args = parser.parse_args()
    candidate = json.loads(args.manifest.read_text())
    component = candidate['component']
    if component not in ('soloist','web'):
        raise ValueError('DLNA compatibility pair upgrades require a dedicated maintenance release')
    registry_ref = re.fullmatch(r'[a-z0-9._:/-]+@sha256:[a-f0-9]{64}',candidate['image'])
    local_ref = re.fullmatch(r'sha256:[a-f0-9]{64}',candidate['image'])
    if not (registry_ref or local_ref):
        raise ValueError('release requires immutable registry digest or verified local image ID')
    from hifi.maintenance import validate_candidate
    validate_candidate(candidate)
    refs = json.loads((CONFIG/'images.json').read_text())
    original_refs = dict(refs)
    history_path = CONFIG/f'{component}-release.json'
    current = json.loads(history_path.read_text()) if history_path.exists() else None
    if current is None:
        raise ValueError('record verified current release metadata before enabling updates')
    validate_candidate(current)
    if current.get('component') != component or current.get('image') != refs[component]:
        raise ValueError('current release metadata differs from configured image')
    if not output_idle():
        raise ValueError('update requires idle output')
    free = shutil.disk_usage(CONFIG).free
    if free < candidate['size']*2+256*1048576:
        raise ValueError('insufficient disk space')
    if registry_ref:
        subprocess.run(['podman','pull',candidate['image']],check=True,timeout=300)
    actual_size = int(subprocess.check_output(['podman','image','inspect',candidate['image'],'--format','{{.Size}}']))
    if actual_size != candidate['size']:
        raise ValueError('manifest size differs from downloaded image')
    actual_id = subprocess.check_output(['podman','image','inspect',candidate['image'],'--format','{{.Id}}'],text=True).strip().removeprefix('sha256:')
    if local_ref and candidate['image'] != 'sha256:'+actual_id:
        raise ValueError('local image ID differs')
    spec = importlib.util.spec_from_file_location('manage',REPO/'deploy/manage.py')
    manage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manage)
    # Rebuild only the affected unit; preserve DLNA services and their network identity.
    original = (manage.UNITS/f'hifi-{component}.service').read_text()
    def activate(release):
        if release is candidate and not output_idle():
            raise ValueError('playback started during update')
        if release is current:
            text = original
        else:
            if refs[component] not in original:
                raise ValueError('service image differs from recorded release')
            text = original.replace(refs[component],release['image'])
        (manage.UNITS/f'hifi-{component}.service').write_text(text)
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['systemctl','--user','restart',f'hifi-{component}'],check=True)
    def check():
        for _ in range(20):
            if healthy(component):
                return True
            time.sleep(1)
        return False
    def commit(new, old):
        refs[component] = new['image']
        atomic_json(CONFIG/'images.json',refs)
        atomic_json(history_path,new)
        atomic_json(CONFIG/f'{component}-previous.json',old)
    # Web has no DAC access: its update must preserve ongoing DLNA playback.
    stop_agent = component == 'soloist'
    if stop_agent:
        subprocess.run(['systemctl','--user','stop','hifi-agent'],check=True)
    try:
        logger.info('updating %s',component)
        transaction(current,candidate,output_idle(),free,activate,check,commit)
        logger.info('committed %s',component)
    except Exception as error:
        atomic_json(CONFIG/'images.json',original_refs)
        atomic_json(history_path,current)
        logger.warning('update failed for %s: %s',component,type(error).__name__)
        raise
    finally:
        if stop_agent:
            subprocess.run(['systemctl','--user','start','hifi-agent'],check=True)


if __name__ == '__main__':
    main()
