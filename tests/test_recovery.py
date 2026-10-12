"""Exercise recovery state, persistence, cancellation and hardware observations."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.devices import observe
from hifi.recovery import Recovery, Cancelled
from hifi.service_lock import maintenance_lock


class Tests(unittest.TestCase):
    def fixture(self, directory):
        self.now = 1000
        self.hardware = {'availability': 'ready', 'reason': None,
                         'device': {'card': 1}, 'incarnation': ('usb', 1)}
        runtime = SimpleNamespace(config=SimpleNamespace(directory=Path(directory), data={'dac': 'dac'}),
                                  core=SimpleNamespace(owner='spotify', state='active', last_switch=0),
                                  previous={'spotify': True}, adapters={}, hardware=Mock(), lock=threading.RLock())
        recovery = Recovery(runtime, clock=lambda: self.now, wall=lambda: self.now,
                            observer=lambda _: self.hardware)
        return runtime, recovery

    def test_observation_states_and_same_card_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            with patch.object(recovery, 'schedule'), patch.object(recovery, 'quiesce'):
                self.hardware = {'availability': 'missing', 'reason': 'dac_missing', 'device': None}
                recovery.observe()
                self.assertIsNone(runtime.core.owner)
                self.assertEqual(recovery.status()['recovery']['reason'], 'dac_missing')
                recovery.schedule.assert_not_called()
                self.hardware = {'availability': 'ready', 'reason': None,
                                 'device': {'card': 1}, 'incarnation': ('usb', 1)}
                for _ in range(3):
                    recovery.observe()
                    self.now += 1
                recovery.schedule.assert_called_once()
                generation = recovery.generation
                self.hardware['incarnation'] = ('usb', 2)
                recovery.observe()
                self.assertGreater(recovery.generation, generation)
                with self.assertRaises(Cancelled):
                    recovery.check(generation, self.now+10)

    def test_persistent_budget_and_rate_limited_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.attempts = [998, 999, 1000]
            recovery.save()
            second = Recovery(runtime, clock=lambda: self.now, wall=lambda: self.now)
            second.hardware = self.hardware
            second.schedule()
            self.assertEqual(second.reason, 'recovery_exhausted')
            second.retry()
            with self.assertRaises(ValueError):
                second.retry()
            third = Recovery(runtime, clock=lambda: self.now, wall=lambda: self.now)
            third.hardware = self.hardware
            third.phase = 'failed'
            with self.assertRaises(ValueError):
                third.retry()
            third.hardware = {'availability': 'missing'}
            self.now += 61
            with self.assertRaises(ValueError):
                third.retry()

    def test_status_not_blocked_by_repair_and_lock_contention(self):
        with tempfile.TemporaryDirectory() as directory:
            _, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            with maintenance_lock(directory):
                recovery.repair(0)
            self.assertEqual(recovery.reason, 'maintenance_busy')
            self.assertEqual(recovery.attempts, [])
            gate = threading.Event()
            worker = threading.Thread(target=lambda: gate.wait(2))
            worker.start()
            self.assertEqual(recovery.status()['hardware']['availability'], 'ready')
            gate.set()
            worker.join()

    def test_stall_grace_silence_and_source_error(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.phase = 'ready'
            recovery.next_service_check = self.now + 100
            runtime.hardware.output_running.return_value = True
            playing = {'spotify': {'playback': 'playing'}}
            with patch.object(recovery, 'schedule'):
                recovery.playback_health(playing)
                recovery.schedule.assert_not_called()
                runtime.hardware.output_running.return_value = False
                recovery.playback_health({'spotify': {'playback': 'playing', 'error': 'decoder'}})
                recovery.schedule.assert_not_called()
                runtime.core.last_switch = self.now
                recovery.playback_health(playing)
                self.now += 11
                for _ in range(3):
                    recovery.playback_health(playing)
                recovery.schedule.assert_called_once_with('output_stalled')

    def test_usb_partial_missing_unknown_and_endpoint_incarnation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sound, usb, nodes = (root / name for name in ('sound', 'usb', 'nodes'))
            for path in (sound, usb, nodes):
                path.mkdir()
            self.assertEqual(observe(None, sound, usb, nodes)['availability'], 'unconfigured')
            self.assertEqual(observe('a:b:serial', sound, usb, nodes)['availability'], 'missing')
            device = usb / '1-1'
            device.mkdir()
            for name, value in {'idVendor':'a', 'idProduct':'b', 'serial':'serial',
                                'devnum':'2', 'product':'DAC'}.items():
                (device / name).write_text(value)
            card = sound / 'card1'
            card.mkdir()
            (card / 'device').symlink_to(device, target_is_directory=True)
            (card / 'id').write_text('DAC')
            self.assertEqual(observe('a:b:serial', sound, usb, nodes)['availability'], 'enumerating')
            for name in ('pcmC1D0p', 'controlC1'):
                (nodes / name).touch()
            first = observe('a:b:serial', sound, usb, nodes)
            self.assertEqual(first['availability'], 'ready')
            (device / 'devnum').write_text('3')
            self.assertNotEqual(first['incarnation'], observe('a:b:serial', sound, usb, nodes)['incarnation'])
            self.assertEqual(observe('a:b:serial', sound, root / 'absent', nodes)['availability'], 'unknown')

    def test_narrow_repair_paused_completion_and_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            recovery.key = ('dac', 'ready', ('usb', 1))
            runtime.repo = Path(directory)
            runtime.adapters = {'dlna': Mock(), 'spotify': Mock()}
            runtime.adapters['spotify'].configured.return_value = False
            runtime.adapters['dlna'].snapshot.return_value = {'playback':'paused'}
            runtime.adapters['spotify'].snapshot.return_value = {'playback':'unknown'}
            runtime.renew_adapters = Mock()
            recovery.had_loss = True
            with patch.object(recovery, 'command') as command, patch.object(recovery, 'route'):
                recovery.repair(0)
            self.assertEqual(recovery.phase, 'ready')
            self.assertIsNone(runtime.core.owner)
            self.assertEqual(runtime.previous, {'dlna':False, 'spotify':False})
            self.assertTrue(any('apply' in call.args for call in command.call_args_list))
            runtime.adapters['spotify'].command.assert_not_called()
            before = len(recovery.attempts)
            recovery.hardware = {'availability': 'missing'}
            recovery.repair(0)
            self.assertEqual(len(recovery.attempts), before)

    def test_full_session_once_and_volume_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.adapters = {'dlna': Mock(), 'spotify': Mock()}
            runtime.adapters['spotify'].configured.return_value = False
            runtime.renew_adapters = Mock()
            saved = {'id':'dac', 'channels':[123, 123], 'mute':True}
            runtime.hardware.volume_snapshot.return_value = saved
            with patch.object(recovery, 'services'), patch.object(recovery, 'route'), \
                    patch('hifi.pipewire.run'):
                recovery.full_session(0, self.now+120)
                with self.assertRaises(RuntimeError):
                    recovery.full_session(0, self.now+120)
            runtime.hardware.restore_volume.assert_called_once_with(saved)

    def test_runtime_status_ignores_control_lock(self):
        from hifi.runtime import Runtime
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1], directory)
            acquired, release = threading.Event(), threading.Event()
            def hold():
                with runtime.lock:
                    acquired.set()
                    release.wait(2)
            thread = threading.Thread(target=hold)
            thread.start()
            acquired.wait(1)
            try:
                with patch.object(runtime, 'devices', return_value=[]):
                    self.assertEqual(runtime.status()['output']['hardware']['availability'], 'unknown')
            finally:
                release.set()
                thread.join()

    def test_backward_clock_keeps_budget_and_expired_history_ages_out(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.attempts = [1100, 1200, 1300]
            recovery.save()
            restarted = Recovery(runtime, clock=lambda:self.now, wall=lambda:self.now)
            self.assertEqual(restarted.attempts, [1000, 1000, 1000])
            restarted.hardware = self.hardware
            restarted.schedule()
            self.assertEqual(restarted.reason, 'recovery_exhausted')
            self.now += 601
            with patch('hifi.recovery.threading.Thread') as worker:
                restarted.schedule()
                worker.assert_called_once()

    def test_missing_route_escalates_but_disabled_source_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.phase = 'ready'
            runtime.adapters = {'spotify':Mock()}
            runtime.adapters['spotify'].configured.return_value = False
            runtime.core.owner = None
            runtime.hardware.sink.side_effect = RuntimeError('route missing')
            with patch('hifi.recovery.subprocess.run', return_value=SimpleNamespace(stdout='active')), \
                    patch.object(recovery, 'schedule') as schedule:
                for _ in range(3):
                    recovery.playback_health({'spotify':{'health':'unconfigured'}})
                    self.now += 5
                schedule.assert_not_called()
                runtime.adapters['spotify'].configured.return_value = True
                for _ in range(3):
                    recovery.playback_health({'spotify':{'health':'healthy'}})
                    self.now += 5
                schedule.assert_called_once_with('route_missing')

    def test_configuration_invalidation_and_stale_playback_baseline(self):
        from hifi.runtime import Runtime
        from test_runtime import Adapter, Hardware
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1],directory)
            runtime.recovery.phase = 'ready'
            runtime.adapters = {'dlna':Adapter('playing'), 'spotify':Adapter('stopped')}
            runtime.core.adapters = runtime.adapters
            runtime.hardware = Hardware()
            runtime.core.hardware = runtime.hardware
            runtime.connected, runtime.card = True, 1
            runtime.previous = {'dlna':True}
            runtime.blocked_intents = {'dlna'}
            with patch.object(runtime,'selected',return_value={'card':1}), \
                    patch.object(runtime.recovery,'playback_health'):
                runtime.tick()
                self.assertIsNone(runtime.core.owner)
                runtime.adapters['dlna'].state = 'paused'
                runtime.tick()
                runtime.adapters['dlna'].state = 'playing'
                runtime.tick()
                self.assertEqual(runtime.core.owner, 'dlna')
            generation = runtime.recovery.generation
            runtime.recovery.invalidate()
            self.assertGreater(runtime.recovery.generation, generation)
            self.assertEqual(runtime.recovery.reason, 'maintenance_busy')

    def test_healthy_bootstrap_does_not_spend_restart_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.adapters = {'dlna': Mock(), 'spotify':Mock()}
            runtime.adapters['spotify'].configured.return_value = True
            recovery.attempts = [998, 999, 1000]
            recovery.bootstrap()
            self.assertEqual(recovery.phase, 'ready')
            self.assertEqual(recovery.attempts, [998, 999, 1000])
            runtime.adapters['dlna'].snapshot.side_effect = RuntimeError()
            recovery.bootstrap()
            self.assertEqual(recovery.reason, 'service_failed')

    def test_cold_start_waits_for_control_socket_without_spending_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.adapters = {'dlna':Mock(), 'spotify':Mock()}
            runtime.adapters['dlna'].snapshot.side_effect = [ConnectionRefusedError(), {'playback':'stopped'}]
            runtime.adapters['spotify'].snapshot.return_value = {'playback':'paused'}
            runtime.adapters['spotify'].configured.return_value = True
            recovery.attempts = [998,999,1000]
            with patch('hifi.recovery.time.sleep'):
                recovery.bootstrap()
            self.assertEqual(recovery.phase, 'ready')
            self.assertEqual(recovery.attempts, [998,999,1000])

    def test_startup_socket_wait_has_a_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.adapters = {'dlna':Mock(), 'spotify':Mock()}
            runtime.adapters['dlna'].snapshot.side_effect = ConnectionRefusedError()
            recovery.attempts = [998,999,1000]
            def advance(_):
                self.now += 5
            with patch('hifi.recovery.time.sleep', side_effect=advance):
                recovery.bootstrap()
            self.assertEqual(recovery.reason, 'service_failed')
            self.assertEqual(recovery.attempts, [998,999,1000])
            self.assertLessEqual(runtime.adapters['dlna'].snapshot.call_count, 4)

    def test_startup_socket_wait_cancels_when_hardware_generation_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.adapters = {'dlna':Mock(), 'spotify':Mock()}
            runtime.adapters['dlna'].snapshot.side_effect = ConnectionRefusedError()
            recovery.attempts = [998,999,1000]
            def lose_hardware(_):
                recovery.generation += 1
                recovery.hardware = {'availability':'missing'}
                recovery.phase, recovery.reason = 'waiting', 'dac_missing'
            with patch('hifi.recovery.time.sleep', side_effect=lose_hardware):
                recovery.bootstrap()
            self.assertEqual(recovery.reason, 'dac_missing')
            self.assertFalse(recovery.busy)
            self.assertEqual(recovery.attempts, [998,999,1000])

    def test_paused_route_does_not_require_a_running_stream_link(self):
        from hifi.pipewire import Hardware
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            runtime.hardware = Hardware(lambda: {'id':'dac', 'card':1})
            sinks = [{'name':'dac', 'index':1, 'properties':{'alsa.card':'1'}},
                     {'name':'hifi_standby', 'index':2, 'properties':{}}]
            streams = [{'index':3, 'sink':4294967295,
                        'properties':{'application.process.binary':'soloist'}}]
            with patch.object(runtime.hardware, 'items', side_effect=lambda kind:sinks if kind=='sinks' else streams), \
                    patch('hifi.pipewire.run') as run:
                recovery.route()
                streams[0]['sink'] = 2
                recovery.route()
                defaults = [call.args for call in run.call_args_list if
                            call.args[:2] == ('pactl', 'set-default-sink')]
                self.assertEqual(defaults[-1], ('pactl', 'set-default-sink', 'dac'))

    def test_budget_exhaustion_preserves_stall_cause_for_manual_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            _, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            recovery.attempts = [998,999,1000]
            recovery.schedule('output_stalled')
            self.assertEqual(recovery.reason, 'recovery_exhausted')
            recovery.retry()
            with patch('hifi.recovery.threading.Thread'):
                recovery.schedule()
            self.assertEqual(recovery.reason, 'output_stalled')

    def test_service_lock_blocks_concurrent_update_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            entered = threading.Event()
            done = threading.Event()
            def update():
                with maintenance_lock(directory):
                    entered.set()
                    done.wait(2)
            worker = threading.Thread(target=update)
            worker.start()
            entered.wait(1)
            try:
                with self.assertRaises(BlockingIOError):
                    with maintenance_lock(directory, blocking=False):
                        self.fail('concurrent transaction entered')
            finally:
                done.set()
                worker.join()
            with maintenance_lock(directory, blocking=False):
                pass

    def test_healthy_output_cannot_request_disruptive_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            _, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            recovery.phase = 'ready'
            self.assertFalse(recovery.status()['recovery']['retry_available'])
            with self.assertRaisesRegex(ValueError, 'failed recovery'):
                recovery.retry()
            self.assertFalse(recovery.manual)
            self.assertEqual(recovery.attempts, [])
            recovery.phase = 'failed'
            self.assertTrue(recovery.status()['recovery']['retry_available'])
            recovery.retry()

    def test_smoke_history_handles_fresh_healthy_installation(self):
        from recovery_device_smoke import attempt_history
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'recovery.json'
            self.assertEqual(attempt_history(path), [])
            path.write_text('{"attempts":[123,456]}')
            self.assertEqual(attempt_history(path), [123,456])

    def test_healthy_restart_parks_existing_playback_and_accepts_fresh_intent(self):
        from hifi.runtime import Runtime
        from test_runtime import Adapter, Hardware
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1],directory)
            runtime.adapters = {'dlna':Adapter('playing'),'spotify':Adapter('stopped')}
            runtime.core.adapters = runtime.adapters
            runtime.hardware = Hardware()
            runtime.core.hardware = runtime.hardware
            runtime.connected, runtime.card = True, 1
            recovery = runtime.recovery
            recovery.hardware = {'availability':'ready', 'device':{'card':1}}
            runtime.blocked_intents = {'dlna','spotify'}
            with patch.object(recovery,'route'), patch.object(recovery,'playback_health'), \
                    patch.object(runtime,'selected',return_value={'card':1}):
                recovery.bootstrap()
                self.assertEqual(runtime.adapters['dlna'].state,'paused')
                self.assertIsNone(runtime.core.owner)
                self.assertEqual(recovery.attempts,[])
                runtime.adapters['dlna'].state = 'playing'
                runtime.tick()
                self.assertEqual(runtime.core.owner,'dlna')

    def test_repair_deadline_and_stale_generation_cancel_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            _, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            with patch('hifi.recovery.subprocess.run') as run:
                with self.assertRaises(TimeoutError):
                    recovery.command(0, self.now, 'systemctl', '--user', 'start', 'hifi-mpd')
                run.assert_not_called()
                def replaced(*args, **kwargs):
                    recovery.generation += 1
                    return SimpleNamespace(stdout='')
                run.side_effect = replaced
                with self.assertRaises(Cancelled):
                    recovery.command(0, self.now+30, 'systemctl', '--user', 'start', 'hifi-mpd')

    def test_optional_expiry_preserves_dlna_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, recovery = self.fixture(directory)
            recovery.hardware = self.hardware
            runtime.repo = Path(directory)
            runtime.adapters = {'dlna':Mock(), 'spotify':Mock()}
            runtime.adapters['dlna'].snapshot.return_value = {'playback':'paused'}
            runtime.adapters['spotify'].snapshot.side_effect = RuntimeError('expired')
            runtime.adapters['spotify'].configured.return_value = True
            runtime.renew_adapters = Mock()
            def service(token, deadline, action, *names):
                if 'ExecMainStatus' in names:
                    return '10'
                return 'failed' if action == 'show' else ''
            with patch.object(recovery,'services',side_effect=service), \
                    patch.object(recovery,'route'), patch.object(recovery,'pause'):
                recovery.repair(0)
            self.assertEqual(recovery.phase,'ready')
            self.assertTrue(recovery.optional_blocked)
