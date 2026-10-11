"""Bounded, cancellable audio infrastructure repair."""
import json
import logging
import math
import subprocess
import threading
import time
from pathlib import Path
from .config import atomic_json
from .devices import observe
from .service_lock import maintenance_lock

LOG = logging.getLogger('hifi')


class Cancelled(Exception):
    pass


class Recovery:
    def __init__(self, runtime, clock=time.monotonic, wall=time.time, observer=observe):
        self.runtime, self.clock, self.wall, self.observer = runtime, clock, wall, observer
        self.lock = threading.RLock()
        self.hardware = {'availability': 'unknown', 'reason': 'discovery_failed', 'device': None}
        self.generation, self.stable, self.last_observation = 0, 0, -1
        self.key, self.ready_key = None, None
        self.phase, self.reason = 'waiting', 'discovery_failed'
        self.next_retry, self.last_manual = 0, 0
        self.busy, self.manual, self.stalls = False, False, 0
        self.service_faults, self.next_service_check = 0, 0
        self.path = runtime.config.directory / 'state/recovery.json'
        try:
            self.history = json.loads(self.path.read_text())
            if not isinstance(self.history, dict):
                raise ValueError()
        except (OSError, ValueError):
            self.history = {'attempts': [], 'last_manual': 0}
        values = self.history.get('attempts', [])
        self.attempts = [min(t, self.wall()) for t in values[-3:]
                         if isinstance(t, (int, float)) and math.isfinite(t)] if isinstance(values, list) else []
        manual_time = self.history.get('last_manual', 0)
        self.last_manual = min(manual_time, self.wall()) if isinstance(manual_time, (int, float)) and math.isfinite(manual_time) else 0
        self.had_loss = False
        self.full_used = False
        self.transport_faults = 0
        self.optional_blocked = False
        self.pending_fault = 'service_failed'
        self.boot_checked = False

    def status(self):
        with self.lock:
            hardware = {k: v for k, v in self.hardware.items() if k != 'incarnation'}
            return {'hardware': hardware, 'health': 'ready' if self.phase == 'ready' else 'degraded',
                    'recovery': {'phase': self.phase, 'reason': self.reason,
                                 'attempts': len(self.attempts), 'retry_available':
                                 self.hardware['availability'] == 'ready' and not self.busy
                                 and self.wall() - self.last_manual >= 60,
                                 'next_retry_seconds': max(0, round(self.next_retry - self.clock()))}}

    def invalidate(self):
        with self.lock:
            self.generation += 1
            self.ready_key = None
            self.phase, self.reason = 'waiting', 'maintenance_busy'

    def retry(self):
        with self.lock:
            if self.hardware['availability'] != 'ready' or self.busy:
                raise ValueError('DAC is unavailable or recovery is running')
            if self.wall() - self.last_manual < 60:
                raise ValueError('retry is limited to once per minute')
            self.last_manual = self.wall()
            if self.transport_faults or self.stalls:
                self.pending_fault = 'output_stalled'
            self.manual, self.next_retry, self.ready_key = True, 0, None
            self.save()
            return {'status': 'recovery requested'}

    def save(self):
        boot = Path('/proc/sys/kernel/random/boot_id')
        atomic_json(self.path, {'attempts': self.attempts[-3:], 'last_manual': self.last_manual,
                               'boot_id': boot.read_text().strip() if boot.exists() else 'unknown'})

    def observe(self):
        hardware = self.observer(self.runtime.config.data['dac'])
        now = self.clock()
        with self.lock:
            key = (self.runtime.config.data['dac'], hardware['availability'], hardware.get('incarnation'))
            changed = key != self.key
            self.hardware = {**hardware, 'observed_at': self.wall()}
            if changed:
                if self.boot_checked:
                    self.phase, self.reason = 'waiting', hardware.get('reason') or 'service_failed'
                self.generation += 1
                self.key, self.stable, self.last_observation = key, 0, -1
                self.ready_key = None
                self.runtime.core.owner = None
                self.runtime.core.state = 'disconnected'
                self.runtime.previous.clear()
                self.had_loss = True
            if hardware['availability'] != 'ready':
                self.boot_checked = True
                self.phase, self.reason = 'waiting', hardware['reason']
                self.runtime.core.owner, self.runtime.core.state = None, 'disconnected'
                if changed and not self.busy:
                    threading.Thread(target=self.quiesce, daemon=True).start()
            elif now - self.last_observation >= 1:
                self.stable += 1
                self.last_observation = now
            if hardware['availability'] == 'ready' and self.stable >= 3 and self.ready_key != key:
                if not self.boot_checked:
                    self.boot_checked = True
                    self.phase = 'checking'
                    self.busy = True
                    threading.Thread(target=self.bootstrap, daemon=True).start()
                    return
                self.schedule()

    def bootstrap(self):
        """A healthy agent restart does not consume the repair budget."""
        token = self.generation
        try:
            self.runtime.adapters['dlna'].snapshot()
            self.runtime.hardware.sink()
            if token != self.generation or self.hardware['availability'] != 'ready':
                return
            self.ready_key, self.phase, self.reason = self.key, 'ready', None
            self.runtime.core.state = 'idle'
            self.had_loss = False
        except Exception:
            if token == self.generation:
                self.phase, self.reason = 'waiting', 'service_failed'
        finally:
            self.busy = False

    def schedule(self, reason=None):
        """Coalesce repeated faults; a worker never holds the status lock."""
        with self.lock:
            if reason:
                if reason == 'output_stalled' or self.pending_fault != 'output_stalled':
                    self.pending_fault = reason
            if self.busy or self.clock() < self.next_retry:
                return
            self.attempts = [t for t in self.attempts if self.wall() - t < 600]
            if len(self.attempts) >= 3 and not self.manual:
                self.phase, self.reason = 'failed', 'recovery_exhausted'
                return
            self.busy = True
            self.phase, self.reason = 'recovering', reason or self.pending_fault
            token = self.generation
            threading.Thread(target=self.repair, args=(token,), daemon=True).start()

    def check(self, token, deadline):
        if token != self.generation or self.hardware['availability'] != 'ready':
            raise Cancelled()
        if self.clock() >= deadline:
            raise TimeoutError('recovery deadline')

    def command(self, token, deadline, *args):
        self.check(token, deadline)
        timeout = 90 if args[0] == 'python3' else 15
        result = subprocess.run(args, check=True, capture_output=True, text=True,
                                timeout=max(.1, min(timeout, deadline - self.clock()))).stdout.strip()
        self.check(token, deadline)
        return result

    def services(self, token, deadline, action, *names):
        return self.command(token, deadline, 'systemctl', '--user', action, *names)

    def pause(self, stop_unreachable=True):
        for name, adapter in list(self.runtime.adapters.items()):
            try:
                if name == 'dlna':
                    adapter.command('pause 1')
                    adapter.output('standby', True)
                    adapter.output('direct', False)
                elif adapter.configured():
                    adapter.command('pause')
            except Exception:
                if name != 'dlna' and stop_unreachable:
                    subprocess.run(['systemctl', '--user', 'stop', 'hifi-soloist'],
                                   capture_output=True, timeout=15)

    def quiesce(self):
        token = self.generation
        try:
            with maintenance_lock(self.runtime.config.directory, blocking=False), self.runtime.lock:
                if token == self.generation and self.hardware['availability'] != 'ready':
                    self.pause()
        except (BlockingIOError, OSError, subprocess.TimeoutExpired):
            pass

    def route(self):
        try:
            target = self.runtime.hardware.sink()
        except Exception:
            if not self.runtime.adapters['spotify'].configured():
                return None
            raise
        self.runtime.hardware.standby()
        self.runtime.hardware.move('hifi_standby')
        from .pipewire import run
        run('pactl', 'set-default-sink', 'hifi_standby')
        run('pactl', 'suspend-sink', target, '1')
        standby = next(s for s in self.runtime.hardware.items('sinks') if s['name'] == 'hifi_standby')
        streams = self.runtime.hardware.items('sink-inputs')
        if any(s.get('properties', {}).get('application.process.binary') == 'soloist' and
               s.get('sink') != standby['index'] for s in streams):
            raise RuntimeError('optional stream is unlinked')
        return target

    def repair(self, token):
        deadline = self.clock() + 120
        counted = False
        fault = self.reason
        self.full_used = False
        try:
            with maintenance_lock(self.runtime.config.directory, blocking=False), self.control_lock(token, deadline):
                self.check(token, deadline)
                self.attempts = (self.attempts + [self.wall()])[-3:]
                self.manual = False
                self.save()
                counted = True
                self.pause()
                self.runtime.core.owner, self.runtime.core.state = None, 'switching'
                self.phase = 'services'
                # The parent holds the maintenance lock for the child transaction.
                if self.had_loss:
                    self.command(token, deadline, 'python3', str(self.runtime.repo / 'deploy/manage.py'),
                                 'apply', '--maintenance-held')
                else:
                    state = self.services(token, deadline, 'show', 'hifi-mpd', '-p', 'ActiveState', '--value')
                    if state != 'active':
                        self.services(token, deadline, 'reset-failed', 'hifi-mpd')
                        self.services(token, deadline, 'start', 'hifi-mpd')
                self.runtime.renew_adapters()
                for _ in range(10):
                    self.check(token, deadline)
                    try:
                        self.runtime.adapters['dlna'].snapshot()
                        break
                    except Exception:
                        time.sleep(.5)
                else:
                    raise RuntimeError('MPD did not recover')
                self.runtime.adapters['dlna'].command('pause 1')
                self.phase = 'route'
                try:
                    self.route()
                except Exception:
                    self.services(token, deadline, 'restart', 'wireplumber')
                    time.sleep(2)
                    try:
                        self.route()
                    except Exception:
                        self.full_session(token, deadline)
                spotify = self.runtime.adapters['spotify']
                self.optional_blocked = False
                if spotify.configured():
                    active = self.services(token, deadline, 'show', 'hifi-soloist', '-p', 'ActiveState', '--value')
                    if active not in ('active', 'activating'):
                        result = self.services(token, deadline, 'show', 'hifi-soloist', '-p', 'ExecMainStatus', '--value')
                        if result != '10':
                            self.services(token, deadline, 'reset-failed', 'hifi-soloist')
                            self.services(token, deadline, 'start', 'hifi-soloist')
                            self.runtime.renew_adapters()
                            spotify = self.runtime.adapters['spotify']
                        else:
                            self.optional_blocked = True
                    for _ in range(12):
                        if self.optional_blocked:
                            break
                        self.check(token, deadline)
                        try:
                            spotify.snapshot()
                            break
                        except Exception:
                            time.sleep(.5)
                    else:
                        if not self.full_used:
                            self.full_session(token, deadline)
                # A full session is required for a prior unlinked/stalled player path.
                if fault == 'output_stalled' and not self.full_used:
                    self.full_session(token, deadline)
                self.check(token, deadline)
                self.pause(stop_unreachable=False)
                if self.runtime.adapters['spotify'].configured() and not self.optional_blocked:
                    # A temporarily unavailable control endpoint must leave a paused,
                    # discoverable player after startup, not permanently disabled.
                    try:
                        self.services(token, deadline, 'start', 'hifi-soloist')
                    except subprocess.CalledProcessError:
                        LOG.warning('optional source did not start')
                try:
                    self.route()
                except Exception:
                    if not self.full_used:
                        self.full_session(token, deadline)
                        self.route()
                    else:
                        raise
                self.runtime.previous.clear()
                for name, adapter in self.runtime.adapters.items():
                    try:
                        snapshot = adapter.snapshot()
                        self.runtime.previous[name] = snapshot.get('playback') == 'playing'
                    except Exception:
                        self.runtime.previous[name] = True
                self.runtime.core.owner, self.runtime.core.state = None, 'idle'
                self.check(token, deadline)
                self.ready_key, self.phase, self.reason = self.key, 'ready', None
                self.had_loss = False
                self.pending_fault = 'service_failed'
                self.service_faults, self.transport_faults, self.stalls = 0, 0, 0
                LOG.info('audio recovery completed')
        except BlockingIOError:
            self.phase, self.reason = 'waiting', 'maintenance_busy'
            self.next_retry = self.clock() + 2
        except Cancelled:
            pass
        except Exception as error:
            if counted:
                self.next_retry = self.clock() + (5, 20, 60)[min(len(self.attempts), 3)-1]
            if token == self.generation:
                self.phase, self.reason = 'failed', 'service_failed'
            LOG.warning('audio recovery failed: %s', type(error).__name__)
        finally:
            self.busy = False

    def control_lock(self, token, deadline):
        """Wait for arbitration with a deadline while hardware stays observable."""
        import contextlib
        @contextlib.contextmanager
        def locked():
            acquired = False
            try:
                while not acquired:
                    self.check(token, deadline)
                    acquired = self.runtime.lock.acquire(timeout=.2)
                yield
            finally:
                if acquired:
                    self.runtime.lock.release()
        return locked()

    def full_session(self, token, deadline):
        if self.full_used:
            raise RuntimeError('session recovery already attempted')
        self.full_used = True
        self.phase = 'session'
        try:
            volume = self.runtime.hardware.volume_snapshot()
        except Exception:
            volume = None
        self.pause()
        self.services(token, deadline, 'stop', 'hifi-soloist')
        self.services(token, deadline, 'restart', 'pipewire', 'pipewire-pulse', 'wireplumber')
        for _ in range(10):
            self.check(token, deadline)
            try:
                self.runtime.hardware.sink()
                break
            except Exception:
                time.sleep(.5)
        self.runtime.hardware.restore_volume(volume)
        from .pipewire import run
        target = self.runtime.hardware.sink()
        run('pactl', 'suspend-sink', target, '0')
        run('pactl', 'set-default-sink', target)
        if self.runtime.adapters['spotify'].configured() and not self.optional_blocked:
            try:
                self.services(token, deadline, 'start', 'hifi-soloist')
            except subprocess.CalledProcessError:
                LOG.warning('optional source did not start')
        self.runtime.renew_adapters()
        if self.runtime.adapters['spotify'].configured() and not self.optional_blocked:
            for _ in range(10):
                self.check(token, deadline)
                try:
                    self.runtime.adapters['spotify'].snapshot()
                    self.runtime.adapters['spotify'].command('pause')
                    break
                except Exception:
                    time.sleep(.5)
            else:
                self.services(token, deadline, 'stop', 'hifi-soloist')
                self.optional_blocked = True
        self.route()

    def playback_health(self, snapshots):
        if self.phase != 'ready' or self.busy:
            return
        owner = self.runtime.core.owner
        if self.clock() >= self.next_service_check:
            self.next_service_check = self.clock() + 5
            try:
                state = subprocess.run(['systemctl', '--user', 'is-active', 'hifi-mpd'],
                                       capture_output=True, text=True, timeout=2).stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                state = 'unknown'
            self.service_faults = self.service_faults + 1 if state in ('failed', 'inactive') else 0
            if self.service_faults >= 3:
                self.ready_key = None
                self.schedule('service_failed')
                return
            try:
                self.runtime.hardware.sink()
                route_missing = False
            except Exception:
                route_missing = True
            spotify = snapshots.get('spotify', {})
            optional_unreachable = (spotify.get('health') == 'unreachable' and
                                    self.runtime.adapters['spotify'].configured() and not self.optional_blocked)
            self.transport_faults = self.transport_faults + 1 if route_missing or optional_unreachable else 0
            if self.transport_faults >= 3:
                self.ready_key = None
                self.schedule('route_missing' if route_missing else 'service_failed')
                return
        snapshot = snapshots.get(owner, {})
        if not owner or snapshot.get('playback') != 'playing' or snapshot.get('error'):
            self.stalls = 0
            return
        if self.clock() - self.runtime.core.last_switch < 10:
            return
        try:
            healthy = self.runtime.hardware.output_running(owner)
        except Exception:
            healthy = False
        self.stalls = 0 if healthy else self.stalls + 1
        if self.stalls >= 3:
            self.ready_key = None
            self.schedule('output_stalled')
