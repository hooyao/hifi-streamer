import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from .config import Config
from .core import Arbiter
from .devices import discover
from .mpd import MPD
from .pipewire import Hardware
from .registry import load
from .soloist import Soloist
from .recovery import Recovery

LOG = logging.getLogger('hifi')


class Runtime:
    def __init__(self, repo, directory):
        self.repo = Path(repo)
        self.config = Config(directory)
        self.modules = load(self.repo / 'modules/sources')
        self.hardware = Hardware(self.selected)
        factories = {'mpd':lambda: MPD(self.hardware),
                     'soloist':lambda: Soloist(self.hardware, lambda: self.config.has_key() and self.config.data['sources']['spotify']['enabled'])}
        self.adapters = {name: factories[m['adapter']]() for name, m in self.modules.items()}
        self.hardware.mpd = self.adapters['dlna']
        self.core = Arbiter(self.adapters, self.hardware)
        self.snapshots = {name: {'running':False, 'authenticated':False, 'active':False,
                                'playback':'unknown', 'health':'unreachable', 'observed_at':0}
                          for name in self.modules}
        self.sequence = {name:0 for name in self.modules}
        self.previous = {}
        self.blocked_intents = set()
        self.connected = False
        self.card = None
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.volume = None
        self.volume_revision = 0
        self.volume_lock = threading.Lock()
        self.recovery = Recovery(self)
        self.core.valid_output = lambda: self.recovery.phase == 'ready'

    def renew_adapters(self):
        for adapter in self.adapters.values():
            client = getattr(adapter, 'client', None)
            if client:
                client.close()
        self.adapters = {'dlna': MPD(self.hardware),
                         'spotify': Soloist(self.hardware, lambda: self.config.has_key() and
                                           self.config.data['sources']['spotify']['enabled'])}
        self.hardware.mpd = self.adapters['dlna']
        self.core.adapters = self.adapters
        self.core.seen.clear()

    def devices(self):
        return discover()

    def selected(self):
        return next((d for d in self.devices() if d['id'] == self.config.data['dac']), None)

    def status(self):
        try:
            devices = self.devices()
        except OSError:
            devices = []
        snapshots = {name: dict(value) for name, value in self.snapshots.items()}
        for name, value in snapshots.items():
            configured = getattr(self.adapters[name], 'configured', None)
            if configured and not configured():
                value.update(running=False, authenticated=False, active=False,
                             health='unconfigured', playback='unknown')
            elif time.time() - value.get('observed_at', 0) > 10:
                value.update(health='unreachable', playback='unknown')
        return {'devices':devices, 'config':self.config.public(),
                'sources':snapshots, 'output':{'owner':self.core.owner, 'state':self.core.state,
                                                        **self.recovery.status(),
                                                        'volume':self.volume_status(devices)}}

    def volume_status(self, devices):
        value = self.volume
        selected = next((d for d in devices if d['id'] == self.config.data['dac']), None)
        if (value and selected and value['dac'] == selected['id'] and value['card'] == selected['card']
                and value['generation'] == self.recovery.generation and time.monotonic()-value['observed_at'] <= 10
                and self.recovery.phase == 'ready'):
            return {'available':True, 'percent':value['percent'], 'mute':value['mute']}
        return {'available':False, 'percent':None, 'mute':None}

    def observe_volume(self):
        with self.volume_lock:
            revision, generation = self.volume_revision, self.recovery.generation
        value = None
        try:
            selected = self.selected()
            if selected and self.recovery.phase == 'ready':
                value = {**self.hardware.volume_status(), 'dac':selected['id'], 'card':selected['card'],
                         'generation':generation, 'observed_at':time.monotonic()}
        except Exception:
            pass
        with self.volume_lock:
            if revision == self.volume_revision and generation == self.recovery.generation:
                self.volume = value

    def initialize_output_volume(self):
        if self.config.data.get('host_volume_initialized', True):
            return
        try:
            self.hardware.sink()
        except RuntimeError:
            if self.adapters['spotify'].configured():
                raise
            return
        token = self.recovery.generation
        self.hardware.set_volume(100)
        if token != self.recovery.generation:
            raise RuntimeError('Selected DAC changed during volume initialization')
        self.config.complete_volume_initialization()

    def set_output_volume(self, data):
        from .service_lock import maintenance_lock
        if (set(data) != {'percent'} or type(data['percent']) is not int
                or not 0 <= data['percent'] <= 100):
            raise ValueError('percent must be an integer from 0 to 100; no other arguments are accepted')
        with maintenance_lock(self.config.directory, blocking=False), self.lock:
            self.config.reload()
            if self.recovery.phase != 'ready' or not self.selected():
                raise RuntimeError('Selected DAC output is unavailable')
            token = self.recovery.generation
            with self.volume_lock:
                self.volume_revision += 1
                self.volume = None
            try:
                self.hardware.set_volume(data['percent'])
            finally:
                # Reject observations started during the write, including failed writes.
                with self.volume_lock:
                    self.volume_revision += 1
                    self.volume = None
            if token != self.recovery.generation:
                raise RuntimeError('Selected DAC changed during volume adjustment')
            self.config.complete_volume_initialization()
            self.observe_volume()
            result = self.volume_status(self.devices())
            if not result['available']:
                raise RuntimeError('Selected DAC volume cannot be confirmed')
            return result

    def apply(self, changes):
        from .service_lock import maintenance_lock
        with maintenance_lock(self.config.directory):
            old = json.loads(json.dumps(self.config.data))
            result = self.config.update(changes, self.devices())
            changed_runtime = old['dac'] != self.config.data['dac'] or old['sources'] != self.config.data['sources'] or 'spotify_key' in changes
            if changed_runtime:
                self.recovery.invalidate()
                with self.lock:
                    self.core.disconnect()
                only_spotify = old['dac'] == self.config.data['dac'] and old['sources']['dlna'] == self.config.data['sources']['dlna']
                command = ['python3', str(self.repo / 'deploy/manage.py'), 'apply', '--maintenance-held'] + (['--only', 'soloist'] if only_spotify else [])
                subprocess.run(command, check=True, timeout=90,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.connected = False if not only_spotify else self.connected
                self.previous.clear()
            if old['mode'] != self.config.data['mode']:
                self.previous.clear()
            return result

    def tick(self):
        with self.lock:
            self.config.reload()
            if self.recovery.phase != 'ready':
                return
            selected = self.selected()
            if not selected:
                if self.connected:
                    self.core.disconnect()
                self.connected = False
                self.core.state = 'disconnected'
            elif not self.connected or self.card != selected['card']:
                self.connected = True
                self.card = selected['card']
                self.core.state = 'idle'
            for name, adapter in self.adapters.items():
                try:
                    snapshot = adapter.snapshot()
                except Exception:
                    snapshot = {'running':False, 'authenticated':False, 'active':False, 'playback':'unknown', 'health':'unreachable'}
                    if name == 'spotify' and self.recovery.optional_blocked:
                        snapshot.update(health='unavailable', error='Soloist cannot start or respond; inspect diagnostics')
                self.snapshots[name] = snapshot
                self.snapshots[name]['observed_at'] = time.time()
            if self.recovery.phase != 'ready':
                return
            spotify = self.snapshots.get('spotify', {})
            if spotify.get('rate_error') and spotify.get('playback') == 'playing' and spotify.get('active'):
                self.adapters['spotify'].command('pause')
                if self.core.owner == 'spotify':
                    self.hardware.for_direct()
                    self.core.owner, self.core.state = None, 'idle'
            policy = self.config.data['mode']
            priority = self.config.data['priority']
            order = [priority] + [name for name in self.adapters if name != priority]
            switched = False
            for name in order:
                snapshot = self.snapshots[name]
                playing = (snapshot['playback'] == 'playing' and snapshot.get('active', False)
                           and snapshot.get('health') == 'healthy')
                edge = playing and not self.previous.get(name, False)
                if not playing:
                    self.blocked_intents.discard(name)
                fresh = edge or self.core.owner is None and name not in self.blocked_intents
                if not switched and playing and fresh and name not in self.blocked_intents and self.core.owner != name and (policy == name or policy == 'auto') and selected:
                    token = self.recovery.generation
                    self.sequence[name] += 1
                    try:
                        granted = self.core.request(name, self.adapters[name].instance, self.sequence[name], force=policy != 'auto')
                    except Exception:
                        self.recovery.ready_key = None
                        self.recovery.schedule('output_stalled')
                        raise
                    if not granted:
                        continue
                    if token != self.recovery.generation:
                        self.core.disconnect()
                        return
                    switched = True
                self.previous[name] = playing
                if switched and self.core.owner != name and edge:
                    # A simultaneous losing request must not silently consume the track.
                    self.adapters[name].release()
            if self.core.owner and self.snapshots[self.core.owner]['health'] == 'unreachable':
                self.core.disconnect()
            elif self.core.owner and self.snapshots[self.core.owner]['playback'] == 'stopped':
                self.hardware.silence()
                self.core.owner, self.core.state = None, 'idle'
            if (self.core.owner == 'spotify' and spotify.get('playback') == 'playing'
                    and spotify.get('active') and spotify.get('health') == 'healthy'):
                token = self.recovery.generation
                try:
                    self.adapters['spotify'].follow_pcm_rate(valid=lambda:
                        token == self.recovery.generation and self.recovery.phase == 'ready'
                        and self.core.owner == 'spotify')
                except Exception:
                    self.recovery.ready_key = None
                    self.recovery.schedule('output_stalled')
                    raise
                if token != self.recovery.generation:
                    self.core.disconnect()
                    return
            self.recovery.playback_health(self.snapshots)

    def hardware_loop(self):
        failures = 0
        while not self.stop.is_set():
            try:
                self.config.reload()
                self.recovery.observe()
                failures = 0
            except Exception:
                failures += 1
                if failures == 1 or failures % 60 == 0:
                    LOG.warning('hardware observation failed')
            self.stop.wait(1)

    def volume_loop(self):
        while not self.stop.is_set():
            self.observe_volume()
            self.stop.wait(2)

    def loop(self):
        threading.Thread(target=self.hardware_loop, daemon=True).start()
        threading.Thread(target=self.volume_loop, daemon=True).start()
        failures = 0
        while not self.stop.is_set():
            try:
                self.tick()
                failures = 0
            except Exception as error:
                failures += 1
                if failures == 1 or failures % 60 == 0:
                    LOG.warning('control cycle failed: %s', type(error).__name__)
            self.stop.wait(1)
