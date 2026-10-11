import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.api import handler
from hifi.config import Config


class Runtime:
    def __init__(self, directory):
        self.config = Config(directory)
    def status(self):
        return {'config':self.config.public()}
    def apply(self, data):
        return self.config.update(data, [])


class Tests(unittest.TestCase):
    def test_auth_csrf_and_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(directory)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(runtime))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(path, data=None, cookie='', csrf='', origin=True):
                    connection = http.client.HTTPConnection(*server.server_address)
                    headers = {'Origin':f'http://127.0.0.1:{server.server_port}' if origin else 'http://attacker', 'Cookie':cookie, 'X-CSRF-Token':csrf}
                    connection.request('POST' if data is not None else 'GET', '/api/'+path, json.dumps(data) if data is not None else None, headers)
                    response = connection.getresponse()
                    result = response.status, json.loads(response.read()), response.getheader('Set-Cookie')
                    connection.close()
                    return result
                self.assertEqual(request('status')[0], 401)
                self.assertEqual(request('login', {'password':'bad'})[0], 401)
                code, login, cookie = request('login', {'password':runtime.config.password()})
                self.assertEqual(code, 200)
                self.assertEqual(request('config', {'mode':'dlna'}, cookie)[0], 403)
                self.assertEqual(request('config', {'mode':'dlna'}, cookie, login['csrf'], False)[0], 403)
                self.assertEqual(request('config', {'spotify_key':'secret'}, cookie, login['csrf'])[0], 200)
                self.assertNotIn('secret', json.dumps(request('status', cookie=cookie)[1]))
            finally:
                server.shutdown()
                server.server_close()
