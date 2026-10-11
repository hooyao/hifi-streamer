import json
import subprocess
import time
from pathlib import Path


def run(*args):
    process = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if process.returncode:
        raise RuntimeError(f'{args[0]} operation failed')
    return process.stdout.strip()


class Hardware:
    def __init__(self, selected):
        self.selected = selected
        self.mpd = None
        self.owned_clock = False

    def items(self, kind):
        return json.loads(run('pactl', '--format=json', 'list', kind))

    def sink(self):
        dac = self.selected()
        if not dac:
            raise RuntimeError('DAC disconnected')
        sinks = [s for s in self.items('sinks') if str(s.get('properties', {}).get('alsa.card')) == str(dac['card'])]
        if len(sinks) != 1:
            raise RuntimeError('DAC sink not found or ambiguous')
        return sinks[0]['name']

    def direct_profile(self):
        """Use the selected USB device's hardware PCM instead of ALSA front/dmix."""
        dac = self.selected()
        cards = [c for c in self.items('cards') if
                 str(c.get('properties', {}).get('alsa.card')) == str(dac['card'])]
        if len(cards) != 1:
            raise RuntimeError('DAC card missing or ambiguous')
        card = cards[0]
        if card.get('active_profile') == 'pro-audio':
            return
        profile = card.get('profiles', {}).get('pro-audio')
        if not profile or not profile.get('available'):
            raise RuntimeError('DAC hardware profile unavailable')
        try:
            saved = self.volume_snapshot()
        except Exception:
            saved = None
        run('pactl', 'set-card-profile', card['name'], 'pro-audio')
        for _ in range(20):
            try:
                self.sink()
                self.restore_volume(saved)
                return
            except RuntimeError:
                time.sleep(.1)
        raise RuntimeError('DAC hardware sink did not appear')

    def hardware_path_ready(self):
        target = self.sink()
        sink = next(s for s in self.items('sinks') if s['name'] == target)
        return str(sink.get('properties', {}).get('api.alsa.path', '')).startswith('hw:')

    def standby(self, reconcile=False):
        existing = next((s for s in self.items('sinks') if s['name'] == 'hifi_standby'), None)
        if reconcile and existing and not existing.get('sample_specification', '').endswith('44100Hz'):
            # Called only with players paused by the maintenance supervisor.
            run('pactl', 'unload-module', str(existing['owner_module']))
            existing = None
        if not existing:
            run('pactl', 'load-module', 'module-null-sink', 'sink_name=hifi_standby', 'rate=44100')

    def move(self, target):
        for stream in self.items('sink-inputs'):
            if stream.get('properties', {}).get('application.process.binary') == 'soloist':
                run('pactl', 'move-sink-input', str(stream['index']), target)

    def for_direct(self):
        self.standby()
        run('pactl', 'suspend-sink', 'hifi_standby', '0')
        run('pactl', 'set-default-sink', 'hifi_standby')
        self.move('hifi_standby')
        try:
            target = self.sink()
        except RuntimeError:
            target = None
        if target:
            run('pactl', 'suspend-sink', target, '1')
            if self.owned_clock:
                self.hardware_rate(target, None)
        self.owned_clock = False
        self.ensure_released()

    def hardware_rate(self, target, rate):
        sink = next(s for s in self.items('sinks') if s['name'] == target)
        node = int(sink['properties']['object.id'])
        if rate is not None and (type(rate) is not int or not 8000 <= rate <= 768000):
            raise ValueError('invalid hardware rate')
        params = json.dumps({'params':['audio.rate', rate or 0, 'api.alsa.multi-rate', rate is None]})
        run('pw-cli', 'set-param', str(node), 'Props', params)

    def for_pipewire(self, rate=None):
        if self.mpd:
            self.mpd.release()
        self.ensure_released()
        target = self.sink()
        if rate is not None:
            self.hardware_rate(target, rate)
            self.owned_clock = True
        run('pactl', 'set-default-sink', target)
        self.move(target)
        run('pactl', 'suspend-sink', 'hifi_standby', '1')
        run('pactl', 'suspend-sink', target, '0')

    def ensure_released(self):
        dac = self.selected()
        if not dac:
            raise RuntimeError('DAC disconnected')
        status = Path(f"/proc/asound/card{dac['card']}/pcm{dac['pcm']}p/sub0/status")
        stream = Path(f"/proc/asound/card{dac['card']}/stream0")
        for _ in range(20):
            holders = subprocess.run(['fuser', f"/dev/snd/pcmC{dac['card']}D{dac['pcm']}p"], capture_output=True, timeout=2)
            if holders.returncode == 1 and not holders.stdout:
                return
            if status.exists() and status.read_text().strip() == 'closed':
                return
            time.sleep(0.05)
        raise RuntimeError('DAC is still occupied')

    def silence(self):
        if self.mpd:
            try:
                self.mpd.release()
            except Exception:
                pass
        try:
            self.for_direct()
        except Exception:
            # Stop optional player if its control/output cannot be safely released.
            subprocess.run(['systemctl', '--user', 'stop', 'hifi-soloist'], capture_output=True, timeout=15)

    def volume_snapshot(self):
        target = self.sink()
        sink = next(s for s in self.items('sinks') if s['name'] == target)
        return {'id': self.selected()['id'], 'channels':
                [v['value'] for v in sink['volume'].values()], 'mute': sink['mute']}

    def restore_volume(self, saved):
        if saved and saved['id'] == self.selected()['id']:
            run('pactl', 'set-sink-volume', self.sink(), *map(str, saved['channels']))
            run('pactl', 'set-sink-mute', self.sink(), '1' if saved['mute'] else '0')

    def output_running(self, owner):
        dac = self.selected()
        path = Path(f"/proc/asound/card{dac['card']}/pcm{dac['pcm']}p/sub0/status")
        if not path.exists() or 'state: RUNNING' not in path.read_text():
            # Some qualified hosts expose stream feedback but omit PCM status.
            stream = Path(f"/proc/asound/card{dac['card']}/stream0")
            if not stream.exists() or 'Status: Running' not in stream.read_text():
                return False
        if owner == 'spotify':
            sink = next(s for s in self.items('sinks') if s['name'] == self.sink())
            return any(s.get('properties', {}).get('application.process.binary') == 'soloist'
                       and s.get('sink') == sink['index'] for s in self.items('sink-inputs'))
        return True
