"""Reversible application bootstrap acceptance on a dedicated renderer account."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'modules/audio-agent'))
from hifi.config import Config, atomic_json
from hifi.devices import discover


def run(*args, check=True):
    return subprocess.run(args, check=check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replace-app-state', action='store_true', required=True,
                        help='Temporarily replace private app state and generated units; restore in finally')
    parser.add_argument('--dsd', action='store_true', help='Include device-qualified DoP')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise RuntimeError('run as the dedicated service account')
    home = Path.home()
    config_path = home/'.config/hifi-streamer'
    data_path = home/'.local/share/hifi-streamer'
    unit_path = home/'.config/systemd/user'
    original = Config(config_path)
    device = next((d for d in discover() if d['id'] == original.data['dac']), None)
    if device is None or not (config_path/'images.json').is_file():
        raise RuntimeError('requires a configured connected DAC and immutable images')
    backup = home/'.local/share/hifi-install-tests'/str(time.time_ns())
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup.parent, 0o700)
    (backup/'units').mkdir(mode=0o700)
    units = ['hifi-agent','hifi-web','hifi-mpd','hifi-upmpdcli','hifi-soloist','hifi-update-check.timer']
    enabled = [unit for unit in units if run('systemctl','--user','is-enabled',unit, check=False).returncode == 0]
    moved = []
    report = {'status':'running','checks':[], 'backup':str(backup)}
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = 'http://127.0.0.1:8080'
    headers = {'Content-Type':'application/json','Origin':base}

    def request(path, body=None, timeout=100):
        response = http.open(urllib.request.Request(base+'/api/'+path,
                            json.dumps(body).encode() if body is not None else None, headers), timeout=timeout)
        if response.headers.get('Set-Cookie'):
            headers['Cookie'] = response.headers['Set-Cookie'].split(';')[0]
        value = json.load(response)
        if value.get('csrf'):
            headers['X-CSRF-Token'] = value['csrf']
        return value

    def wait(reason=None):
        for _ in range(150):
            try:
                state = request('status')['output']
                if state['recovery']['reason'] == reason and (reason or state['health'] == 'ready'):
                    return state
            except (OSError, urllib.error.HTTPError):
                pass
            time.sleep(1)
        raise AssertionError('control plane did not reach expected output state')

    def checked(name):
        report['checks'].append(name)
        print(name+' passed', flush=True)

    try:
        # Stop the observer first so it cannot restart units during backup.
        run('systemctl','--user','stop','hifi-agent')
        run('systemctl','--user','disable','--now',*units, check=False)
        run('systemctl','--user','reset-failed',*units, check=False)
        for path in sorted(unit_path.glob('hifi-*')):
            if path.is_file() and not path.is_symlink():
                shutil.move(str(path), backup/'units'/path.name)
        for path, name in ((config_path,'config'), (data_path,'data')):
            if path.exists():
                shutil.move(str(path), backup/name)
                moved.append((path, name))
        run('systemctl','--user','daemon-reload')
        run('sh',str(REPO/'deploy/install.sh'))
        config = Config(config_path)
        shutil.copy2(backup/'config/images.json', config_path/'images.json')
        run(sys.executable,str(REPO/'deploy/manage.py'),'apply')
        for _ in range(30):
            try:
                request('status')
                break
            except OSError:
                time.sleep(1)
        else:
            raise AssertionError('fresh web status unavailable')
        state = request('status')
        assert state['config']['dac'] is None and not state['config']['spotify_key_set']
        assert state['sources']['spotify']['health'] == 'unconfigured'
        wait('dac_unconfigured')
        for unit in ('hifi-mpd','hifi-upmpdcli','hifi-soloist'):
            assert run('systemctl','--user','is-active',unit, check=False).returncode != 0
        assert not (config_path/'admin.json').exists()
        checked('empty-state password-free web and optional Spotify disabled')
        before_config = config.path.read_bytes()
        run('sh',str(REPO/'deploy/install.sh'))
        assert config.path.read_bytes() == before_config
        checked('idempotent account install preserves configuration')
        config.data['dac'] = 'absent-install-fixture'
        atomic_json(config.path, config.data)
        assert wait('dac_missing')['owner'] is None
        checked('selected missing DAC status')
        web_pid = subprocess.check_output(['podman','inspect','hifi-web','--format','{{.State.Pid}}'], text=True).strip()
        request('config', {'dac':device['id']})
        assert wait()['owner'] is None
        assert subprocess.check_output(['podman','inspect','hifi-web','--format','{{.State.Pid}}'], text=True).strip() == web_pid
        checked('first API DAC selection and fresh audio-unit startup without web restart')
        command = [sys.executable,str(REPO/'tests/dlna_smoke.py'),'--card',str(device['card']),
                   '--report',str(args.report.with_suffix('.formats.json'))]
        if args.dsd:
            command.append('--dsd')
        subprocess.run(command, check=True, timeout=180)
        checked('fresh DLNA formats and controls')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=type(error).__name__+': '+str(error))
        raise
    finally:
        run('systemctl','--user','stop','hifi-agent', check=False)
        run('systemctl','--user','disable','--now',*units, check=False)
        for path, name in reversed(moved):
            if path.exists():
                shutil.move(str(path), backup/('tested-'+name))
            shutil.move(str(backup/name), path)
        for path in (backup/'units').iterdir():
            shutil.move(str(path), unit_path/path.name)
        run('systemctl','--user','daemon-reload')
        run('systemctl','--user','reset-failed',*units, check=False)
        try:
            run('systemctl','--user','enable','--now',*enabled)
            run(sys.executable,str(REPO/'deploy/manage.py'),'apply')
            report['private_state_restored'] = True
        except Exception as error:
            report.update(private_state_restored=False, restore_error=type(error).__name__)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(args.report, report)
        if not report.get('private_state_restored'):
            raise RuntimeError('private-state restore failed; use the retained backup before playback')


if __name__ == '__main__':
    main()
