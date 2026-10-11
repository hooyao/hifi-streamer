"""Inject service/route faults and verify automatic paused recovery on a host."""
import argparse
import http.client
import json
import socket
import subprocess
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.service_lock import maintenance_lock


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(f'/run/user/{__import__("os").getuid()}/hifi-streamer/agent.sock')


def attempt_history(path):
    """A healthy fresh installation has not persisted any recovery attempts."""
    path = Path(path)
    return json.loads(path.read_text()).get('attempts', []) if path.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--retry-only', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--fault', choices=['mpd', 'start-limit', 'route', 'player', 'session'], default='mpd')
    parser.add_argument('--automatic-only', action='store_true')
    parser.add_argument('--observe-usb', action='store_true')
    parser.add_argument('--wait-ready', action='store_true')
    args = parser.parse_args()
    cookie = ''
    csrf = ''

    def api(path, data=None):
        nonlocal cookie, csrf
        connection = UnixConnection('localhost')
        headers = {'Host':'localhost', 'Origin':'http://localhost', 'Cookie':cookie,
                   'X-CSRF-Token':csrf, 'Content-Type':'application/json'}
        connection.request('POST' if data is not None else 'GET', '/api/'+path,
                           json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        result = json.loads(response.read())
        if response.getheader('Set-Cookie'):
            cookie = response.getheader('Set-Cookie').split(';')[0]
        connection.close()
        if response.status >= 400:
            raise RuntimeError(f'API returned {response.status}')
        csrf = result.get('csrf', csrf)
        return result

    def wait_ready(after=None):
        started = time.monotonic()
        while time.monotonic()-started < 150:
            output = api('status')['output']
            history_path = Path.home()/'.config/hifi-streamer/state/recovery.json'
            attempts = attempt_history(history_path)
            if output['health'] == 'ready' and (after is None or any(t >= after for t in attempts)):
                if after is not None:
                    assert output['owner'] is None
                return output
            time.sleep(1)
        raise AssertionError('automatic recovery did not finish')

    password = json.loads((Path.home()/'.config/hifi-streamer/admin.json').read_text())['password']
    api('login', {'password':password})
    if args.observe_usb:
        rows = []
        missing = False
        started = time.monotonic()
        while time.monotonic()-started < 300:
            output = api('status')['output']
            state = (output['hardware']['availability'], output['recovery']['phase'],
                     output['recovery']['reason'], output['owner'])
            if not rows or rows[-1]['state'] != state:
                rows.append({'seconds':round(time.monotonic()-started), 'state':state})
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps({'passed':False,'transitions':rows},indent=2))
            if state[0] == 'missing':
                missing = True
                assert state[2] == 'dac_missing' and output['owner'] is None
            if missing and output['health'] == 'ready':
                assert output['owner'] is None
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps({'passed':True,'transitions':rows},indent=2))
                print(json.dumps({'passed':True,'transitions':rows}))
                return
            time.sleep(1)
        raise AssertionError('USB missing-to-ready acceptance did not complete')
    if args.status:
        print(json.dumps(api('status')['output']))
        return
    if args.wait_ready:
        print(json.dumps(wait_ready()))
        return
    if args.retry_only:
        api('recovery/retry', {})
        time.sleep(3)
        print(json.dumps(wait_ready()))
        return
    initial = wait_ready()
    if args.automatic_only:
        attempts = attempt_history(Path.home()/'.config/hifi-streamer/state/recovery.json')
        if sum(time.time()-t < 600 for t in attempts) >= 3:
            raise AssertionError('automatic budget unavailable before fault injection')
    started = time.time()
    service = {'mpd':'hifi-mpd', 'start-limit':'hifi-mpd', 'route':'wireplumber',
               'player':'hifi-soloist', 'session':'wireplumber'}[args.fault]
    if args.fault == 'start-limit':
        dropin = Path.home()/'.config/systemd/user/hifi-mpd.service.d/recovery-test.conf'
        if dropin.exists():
            raise RuntimeError('test override already exists')
        dropin.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['systemctl','--user','stop',service],check=True)
        with maintenance_lock(Path.home()/'.config/hifi-streamer'):
            try:
                dropin.write_text('[Unit]\nStartLimitIntervalSec=60\nStartLimitBurst=2\n'
                                  '[Service]\nExecStartPre=\nExecStop=\nExecStart=\n'
                                  'ExecStart=/usr/bin/false\nRestartSec=0.1\n')
                subprocess.run(['systemctl','--user','daemon-reload'],check=True)
                subprocess.run(['systemctl','--user','reset-failed',service],check=True)
                subprocess.run(['systemctl','--user','restart',service],check=False)
                for _ in range(20):
                    rows = subprocess.check_output(['systemctl','--user','show',service,
                        '-p','ActiveState','-p','NRestarts','-p','Result'],text=True).splitlines()
                    state = dict(row.split('=',1) for row in rows)
                    if state['ActiveState'] == 'failed' and int(state['NRestarts']) >= 2:
                        break
                    time.sleep(.5)
                assert state['ActiveState'] == 'failed' and int(state['NRestarts']) >= 2, state
                # Some systemd versions preserve exit-code after restart throttling.
                before = state['NRestarts']
                attempt = subprocess.run(['systemctl','--user','start',service],capture_output=True)
                assert attempt.returncode != 0, 'rate-limited start unexpectedly succeeded'
                time.sleep(.5)
                after = subprocess.check_output(['systemctl','--user','show',service,
                                                 '-p','NRestarts','--value'],text=True).strip()
                assert after == before, 'start was not throttled'
            finally:
                dropin.unlink(missing_ok=True)
                subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    else:
        subprocess.run(['systemctl','--user','stop',service],check=True)
    if args.fault == 'session':
        subprocess.run(['systemctl','--user','stop','pipewire-pulse'],check=True)
    time.sleep(18)
    output = api('status')['output']
    if output['recovery']['reason'] == 'recovery_exhausted':
        if args.automatic_only:
            raise AssertionError('automatic budget unavailable; wait for its window before testing')
        api('recovery/retry', {})
    recovered = wait_ready(started)
    checks = [{'fault':args.fault, 'passed':True, 'output':recovered}]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'checks':checks},indent=2))
    print(json.dumps({'passed':len(checks)}))


if __name__ == '__main__':
    main()
