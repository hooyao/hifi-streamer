import uuid
import time
from .websocket import Client


class Soloist:
    def __init__(self, hardware, configured):
        self.hardware, self.configured = hardware, configured
        self.instance = str(uuid.uuid4())
        self.client = None
        self.counter = 0

    def command(self, method, **fields):
        if not self.client:
            self.client = Client()
        try:
            self.client.send({'type':'command', 'command':method, **fields})
            expected = {'get_auth_state':'auth_state', 'get_state':'playback_state'}.get(method, 'command_result')
            deadline = time.monotonic() + 3
            for _ in range(32):
                if time.monotonic() > deadline:
                    raise TimeoutError('Soloist response deadline')
                response = self.client.receive()
                if response.get('type') == 'error':
                    raise RuntimeError('Soloist rejected control')
                if response.get('type') == expected and (expected != 'command_result' or response.get('command') == method):
                    return response
            raise RuntimeError('Soloist control response missing')
        except Exception:
            self.client.close()
            self.client = None
            raise

    def snapshot(self):
        if not self.configured():
            return {'running':False, 'authenticated':False, 'active':False,
                    'playback':'unknown', 'health':'unconfigured'}
        auth = self.command('get_auth_state')
        state = self.command('get_state') if auth.get('logged_in') else {}
        return {'running':True, 'authenticated':auth.get('logged_in', False),
                'active':state.get('is_active', False), 'playback':state.get('status', 'unknown'),
                'health':'healthy'}

    def release(self):
        self.command('pause')
        for _ in range(20):
            if self.command('get_state').get('status') != 'playing':
                break
        else:
            raise RuntimeError('Soloist did not pause')
        self.hardware.for_direct()

    def acquire(self, generation):
        self.hardware.for_pipewire()
        self.command('play')
