import hmac
import json
import secrets
import socketserver
import threading
import time
import subprocess
from pathlib import Path
from .config import atomic_json
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler


class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    slots = threading.BoundedSemaphore(16)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def handler(runtime):
    sessions = {}
    failures = {}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def setup(self):
            self.request.settimeout(10)
            super().setup()

        def log_message(self, *args):
            pass

        def reply(self, code, data, cookie=None):
            encoded = json.dumps(data).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(encoded)))
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(encoded)

        def session(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie', ''))
                token = cookie['hifi_session'].value
            except (KeyError, ValueError):
                return None
            value = sessions.get(token)
            return value if value and value['expires'] > time.time() else None

        def origin_ok(self):
            origin = self.headers.get('Origin', '')
            host = self.headers.get('Host', '')
            return bool(host) and origin in ('http://' + host, 'https://' + host)

        def do_GET(self):
            session = self.session()
            if not session:
                return self.reply(401, {'error':'login required'})
            if self.path == '/api/status':
                return self.reply(200, {**runtime.status(), 'csrf':session['csrf']})
            if self.path == '/api/diagnostics':
                path = runtime.config.directory / 'state/agent.log'
                text = ''
                if path.exists():
                    with path.open('rb') as stream:
                        stream.seek(max(0, path.stat().st_size - 65536))
                        text = stream.read(65536).decode(errors='replace')
                return self.reply(200, {'log':'\n'.join(text.splitlines()[-200:])})
            if self.path == '/api/updates':
                path = runtime.config.directory / 'state/updates.json'
                return self.reply(200, json.loads(path.read_text()) if path.exists() else {})
            self.reply(404, {'error':'not found'})

        def do_POST(self):
            if not self.origin_ok():
                return self.reply(403, {'error':'invalid origin'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 8192:
                    return self.reply(413, {'error':'request too large'})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, json.JSONDecodeError):
                return self.reply(400, {'error':'invalid JSON'})
            if self.path == '/api/login':
                identity = self.headers.get('X-Real-IP', 'local')
                now = time.time()
                recent = [t for t in failures.get(identity, []) if t > now - 60]
                if len(recent) >= 5:
                    return self.reply(429, {'error':'try later'})
                password = data.get('password', '')
                if not isinstance(password, str) or not hmac.compare_digest(password, runtime.config.password()):
                    failures[identity] = recent + [now]
                    if len(failures) > 256:
                        failures.clear()
                    return self.reply(401, {'error':'invalid password'})
                for key in list(sessions):
                    if sessions[key]['expires'] < now:
                        del sessions[key]
                if len(sessions) >= 32:
                    sessions.pop(next(iter(sessions)))
                token = secrets.token_urlsafe(32)
                sessions[token] = {'csrf':secrets.token_urlsafe(24), 'expires':now + 3600}
                return self.reply(200, {'csrf':sessions[token]['csrf']}, f'hifi_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600')
            session = self.session()
            if not session or not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session['csrf']):
                return self.reply(403, {'error':'invalid session or CSRF token'})
            if self.path == '/api/config':
                try:
                    return self.reply(200, runtime.apply(data))
                except ValueError as error:
                    return self.reply(400, {'error':str(error)})
                except Exception:
                    return self.reply(503, {'error':'configuration saved; deployment failed, inspect diagnostics'})
            if self.path == '/api/update':
                component = data.get('component')
                if component not in ('soloist','web') or data.get('action') not in ('update','rollback'):
                    return self.reply(400, {'error':'invalid update request'})
                try:
                    if data['action'] == 'rollback':
                        candidate = json.loads((runtime.config.directory / f'{component}-previous.json').read_text())
                    else:
                        values = json.loads((runtime.config.directory / 'state/updates.json').read_text())
                        candidate = values[component]['candidate']
                    if candidate.get('component') != component:
                        raise ValueError('candidate component differs')
                    path = runtime.config.directory / 'pending-release.json'
                    atomic_json(path,candidate)
                    subprocess.run(['systemd-run','--user','--collect','--unit=hifi-update','--property=MemoryMax=96M',
                                    '--property=StandardOutput=null','--property=StandardError=journal',
                                    '/usr/bin/python3',str(runtime.repo / 'deploy/update.py'),str(path)],check=True,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                    return self.reply(202, {'status':'update requested; monitor diagnostics'})
                except Exception:
                    return self.reply(409, {'error':'no verified update/rollback candidate, or update already running'})
            self.reply(404, {'error':'not found'})

    return Handler
