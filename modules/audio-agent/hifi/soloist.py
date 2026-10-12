import uuid
import time
from .websocket import Client
from .pipewire import PCMFormatError


class Soloist:
    def __init__(self, hardware, configured):
        self.hardware, self.configured = hardware, configured
        self.instance = str(uuid.uuid4())
        self.client = None
        self.counter = 0
        self.pcm_rate = None
        self.validated_rate = None
        self.applied_rate = None
        self.format_error = None

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
        snapshot = {'running':True, 'authenticated':auth.get('logged_in', False),
                'active':state.get('is_active', False), 'playback':state.get('status', 'unknown'),
                'health':'healthy'}
        if self.hardware and snapshot['playback'] == 'playing' and snapshot['active']:
            try:
                self.pcm_rate = self.hardware.source_rate('soloist')
                if self.pcm_rate is None:
                    self.format_error = None
                    snapshot.update(health='starting', error='Waiting for decoded PCM format', rate_pending=True)
                else:
                    if self.pcm_rate != self.validated_rate:
                        self.hardware.validate_source_rate(self.pcm_rate)
                        self.validated_rate = self.pcm_rate
                    self.format_error = None
            except PCMFormatError as error:
                self.pcm_rate = None
                self.format_error = str(error)
        if self.format_error:
            snapshot.update(health='unavailable', error=self.format_error, rate_error=True)
        snapshot['pcm_rate'] = self.pcm_rate
        return snapshot

    def release(self):
        self.command('pause')
        for _ in range(20):
            if self.command('get_state').get('status') != 'playing':
                break
        else:
            raise RuntimeError('Soloist did not pause')
        self.hardware.for_direct()
        self.applied_rate = None

    def acquire(self, generation):
        if self.pcm_rate is None or self.pcm_rate != self.validated_rate:
            raise PCMFormatError('No validated decoded PCM rate for acquisition')
        self.hardware.for_pipewire(rate=self.pcm_rate)
        self.applied_rate = self.pcm_rate
        self.command('play')

    def follow_pcm_rate(self):
        if (not self.format_error and self.pcm_rate is not None
                and self.pcm_rate == self.validated_rate and self.pcm_rate != self.applied_rate):
            self.hardware.follow_rate(self.pcm_rate)
            self.applied_rate = self.pcm_rate
