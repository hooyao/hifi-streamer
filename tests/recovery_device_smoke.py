"""Inject service/route faults and verify automatic paused recovery on a host."""
import argparse
import http.client
import json
import socket
import subprocess
import time
from pathlib import Path


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(f'/run/user/{__import__("os").getuid()}/hifi-streamer/agent.sock')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--retry-only', action='store_true')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--fault', choices=['mpd', 'route', 'player', 'session'], default='mpd')
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
            attempts = json.loads(history_path.read_text())['attempts'] if history_path.exists() else []
            if output['health'] == 'ready' and (after is None or any(t >= after for t in attempts)):
                if after is not None:
                    assert output['owner'] is None
                return output
            time.sleep(1)
        raise AssertionError('automatic recovery did not finish')

    password = json.loads((Path.home()/'.config/hifi-streamer/admin.json').read_text())['password']
    api('login', {'password':password})
    if args.status:
        print(json.dumps(api('status')['output']))
        return
    if args.retry_only:
        api('recovery/retry', {})
        time.sleep(3)
        print(json.dumps(wait_ready()))
        return
    initial = wait_ready()
    started = time.time()
    service = {'mpd':'hifi-mpd', 'route':'wireplumber', 'player':'hifi-soloist', 'session':'wireplumber'}[args.fault]
    subprocess.run(['systemctl','--user','stop',service],check=True)
    if args.fault == 'session':
        subprocess.run(['systemctl','--user','stop','pipewire-pulse'],check=True)
    time.sleep(18)
    output = api('status')['output']
    if output['recovery']['reason'] == 'recovery_exhausted':
        api('recovery/retry', {})
    recovered = wait_ready(started)
    checks = [{'fault':args.fault, 'passed':True, 'output':recovered}]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'checks':checks},indent=2))
    print(json.dumps({'passed':len(checks)}))


if __name__ == '__main__':
    main()
