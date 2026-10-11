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

    def standby(self):
        if not any(s['name'] == 'hifi_standby' for s in self.items('sinks')):
            run('pactl', 'load-module', 'module-null-sink', 'sink_name=hifi_standby')

    def move(self, target):
        for stream in self.items('sink-inputs'):
            if stream.get('properties', {}).get('application.process.binary') == 'soloist':
                run('pactl', 'move-sink-input', str(stream['index']), target)

    def for_direct(self):
        self.standby()
        run('pactl', 'set-default-sink', 'hifi_standby')
        self.move('hifi_standby')
        run('pactl', 'suspend-sink', self.sink(), '1')
        self.ensure_released()

    def for_pipewire(self):
        if self.mpd:
            self.mpd.release()
        self.ensure_released()
        target = self.sink()
        run('pactl', 'suspend-sink', target, '0')
        run('pactl', 'set-default-sink', target)
        self.move(target)

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
