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
        self.snapshots = {}
        self.sequence = {name:0 for name in self.modules}
        self.previous = {}
        self.connected = False
        self.card = None
        self.lock = threading.RLock()
        self.stop = threading.Event()

    def devices(self):
        return discover()

    def selected(self):
        return next((d for d in self.devices() if d['id'] == self.config.data['dac']), None)

    def status(self):
        with self.lock:
            return {'devices':self.devices(), 'config':self.config.public(),
                    'sources':dict(self.snapshots), 'output':{'owner':self.core.owner, 'state':self.core.state}}

    def apply(self, changes):
        with self.lock:
            old = json.loads(json.dumps(self.config.data))
            result = self.config.update(changes, self.devices())
            changed_runtime = old['dac'] != self.config.data['dac'] or old['sources'] != self.config.data['sources'] or 'spotify_key' in changes
            if changed_runtime:
                self.core.disconnect()
                only_spotify = old['dac'] == self.config.data['dac'] and old['sources']['dlna'] == self.config.data['sources']['dlna']
                command = ['python3', str(self.repo / 'deploy/manage.py'), 'apply'] + (['--only', 'soloist'] if only_spotify else [])
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
            selected = self.selected()
            if not selected:
                if self.connected:
                    self.core.disconnect()
                self.connected = False
                self.core.state = 'disconnected'
            elif not self.connected or self.card != selected['card']:
                # Container device mappings can become stale after USB re-enumeration.
                if self.core.state == 'disconnected' or self.card is not None and self.card != selected['card']:
                    subprocess.run(['python3', str(self.repo / 'deploy/manage.py'), 'apply'], check=True, timeout=90,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.connected = True
                self.card = selected['card']
                self.core.state = 'idle'
            for name, adapter in self.adapters.items():
                try:
                    snapshot = adapter.snapshot()
                except Exception:
                    snapshot = {'running':False, 'authenticated':False, 'active':False, 'playback':'unknown', 'health':'unreachable'}
                self.snapshots[name] = snapshot
            policy = self.config.data['mode']
            priority = self.config.data['priority']
            order = [priority] + [name for name in self.adapters if name != priority]
            switched = False
            for name in order:
                snapshot = self.snapshots[name]
                playing = snapshot['playback'] == 'playing' and snapshot.get('active', False)
                edge = playing and not self.previous.get(name, False)
                if not switched and playing and self.core.owner != name and (policy == name or policy == 'auto' and (edge or self.core.owner is None)) and selected:
                    self.sequence[name] += 1
                    granted = self.core.request(name, self.adapters[name].instance, self.sequence[name], force=policy != 'auto')
                    if not granted:
                        continue
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

    def loop(self):
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
