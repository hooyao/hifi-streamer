import http.client
import json
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.api import handler
from hifi.config import Config


class Runtime:
    def __init__(self, directory):
        self.config = Config(directory)
        self.recovery = Mock()
        self.recovery.retry.return_value = {'status': 'recovery requested'}
        self.set_output_volume = Mock(return_value={'available':True,'percent':60,'mute':False})
    def status(self):
        return {'config':self.config.public()}
    def apply(self, data):
        return self.config.update(data, [])


class Tests(unittest.TestCase):
    def test_password_free_access_csrf_volume_and_secret(self):
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
                code, status, cookie = request('status')
                self.assertEqual(code, 200)
                self.assertIsNone(cookie)
                csrf = status['csrf']
                self.assertEqual(request('login', {}, csrf=csrf)[0], 404)
                self.assertEqual(request('config', {'mode':'dlna'})[0], 403)
                self.assertEqual(request('config', {'mode':'dlna'}, csrf=csrf, origin=False)[0], 403)
                self.assertEqual(request('config', {'spotify_key':'secret'}, csrf=csrf)[0], 200)
                self.assertNotIn('secret', json.dumps(request('status')[1]))
                self.assertEqual(request('output/volume', {'percent':60})[0], 403)
                self.assertEqual(request('output/volume', {'percent':60}, csrf=csrf, origin=False)[0], 403)
                runtime.set_output_volume.assert_not_called()
                self.assertEqual(request('output/volume', {'percent':60}, csrf=csrf)[1]['percent'], 60)
                runtime.set_output_volume.side_effect = ValueError('invalid percent')
                self.assertEqual(request('output/volume', {'percent':101}, csrf=csrf)[0], 400)
                runtime.set_output_volume.side_effect = RuntimeError('missing DAC')
                self.assertEqual(request('output/volume', {'percent':60}, csrf=csrf)[0], 409)
                self.assertEqual(request('recovery/retry', {})[0], 403)
                self.assertEqual(request('recovery/retry', {}, csrf=csrf, origin=False)[0], 403)
                self.assertEqual(request('recovery/retry', {'command':'reboot'}, csrf=csrf)[0], 400)
                self.assertEqual(request('recovery/retry', {}, csrf=csrf)[0], 202)
                runtime.recovery.retry.side_effect = ValueError('DAC unavailable')
                self.assertEqual(request('recovery/retry', {}, csrf=csrf)[0], 409)
            finally:
                server.shutdown()
                server.server_close()
