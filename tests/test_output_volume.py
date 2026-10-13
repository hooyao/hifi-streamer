"""Unity initialization, actual gain control and stale-observation isolation."""
import json
import io
import sys
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'modules/audio-agent'))
from hifi.config import Config
from hifi.pipewire import Hardware
from hifi.runtime import Runtime
from output_volume_device_smoke import main as volume_device_smoke, restore_and_report

DAC = {'id':'dac','card':1}


class Tests(unittest.TestCase):
    def test_stalled_volume_read_does_not_block_hardware_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            runtime.recovery.phase = 'ready'
            entered, release, observed = threading.Event(), threading.Event(), threading.Event()
            def stalled_read():
                entered.set()
                release.wait(2)
                return {'percent':100,'mute':False}
            def hardware_observation():
                observed.set()
                runtime.stop.set()
            with patch.object(runtime,'selected',return_value=DAC), \
                 patch.object(runtime.hardware,'volume_status',side_effect=stalled_read), \
                 patch.object(runtime.recovery,'observe',side_effect=hardware_observation):
                volume = threading.Thread(target=runtime.volume_loop)
                volume.start()
                hardware = threading.Thread(target=runtime.hardware_loop)
                try:
                    self.assertTrue(entered.wait(1))
                    hardware.start()
                    self.assertTrue(observed.wait(1),'hardware observer waited for audio server')
                finally:
                    runtime.stop.set()
                    release.set()
                    volume.join(3)
                    if hardware.ident is not None:
                        hardware.join(3)

    def test_fresh_defaults_no_password_and_explicit_preferences_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(directory)
            self.assertEqual(config.data['sources']['spotify']['initial_volume'], 100)
            self.assertFalse(config.data['host_volume_initialized'])
            self.assertFalse((Path(directory)/'admin.json').exists())
            config.update({'sources':{'spotify':{'initial_volume':35}}}, [])
            self.assertEqual(Config(directory).data['sources']['spotify']['initial_volume'], 35)
            self.assertNotIn('host_volume_initialized', config.public())

    def test_fresh_initialization_runs_once_and_legacy_gain_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            with patch.object(runtime.hardware,'sink',return_value='selected'), \
                 patch.object(runtime.hardware,'set_volume') as set_volume:
                runtime.initialize_output_volume()
                runtime.initialize_output_volume()
                set_volume.assert_called_once_with(100)
                saved = json.loads(runtime.config.path.read_text())
                saved.pop('host_volume_initialized')
                runtime.config.path.write_text(json.dumps(saved))
                runtime.config.reload()
                runtime.initialize_output_volume()
                set_volume.assert_called_once_with(100)

    def test_missing_initial_sink_is_deferred(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            with patch.object(runtime.hardware,'sink',side_effect=RuntimeError('no sink')), \
                 patch.object(runtime.hardware,'set_volume') as set_volume:
                runtime.initialize_output_volume()
            set_volume.assert_not_called()
            self.assertFalse(runtime.config.data['host_volume_initialized'])

    def test_set_targets_selected_sink_only_and_preserves_mute(self):
        hardware = Hardware(lambda:DAC)
        with patch.object(hardware,'sink',return_value='selected'), patch('hifi.pipewire.run') as run:
            hardware.set_volume(60)
        run.assert_called_once_with('pactl','set-sink-volume','selected','60%')

    def test_percent_uses_actual_channels_including_muted_output(self):
        hardware = Hardware(lambda:DAC)
        with patch.object(hardware,'volume_snapshot',return_value={'channels':[32768,39322],'mute':True}):
            self.assertEqual(hardware.volume_status(), {'percent':60.0,'mute':True})

    def test_invalid_volume_rejected_before_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            with patch.object(runtime.hardware,'set_volume') as set_volume:
                for data in ({}, {'percent':-1}, {'percent':101}, {'percent':True},
                             {'percent':60.5}, {'percent':'60'}, {'percent':60,'sink':'other'}):
                    with self.subTest(data=data), self.assertRaises(ValueError):
                        runtime.set_output_volume(data)
                with self.assertRaises(RuntimeError):
                    runtime.set_output_volume({'percent':60})
            set_volume.assert_not_called()

    def test_adjustment_reads_actual_gain_and_completes_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            runtime.config.data['dac'] = DAC['id']
            from hifi.config import atomic_json
            atomic_json(runtime.config.path,runtime.config.data)
            runtime.recovery.phase = 'ready'
            with patch.object(runtime,'devices',return_value=[DAC]), \
                 patch.object(runtime.hardware,'volume_status',return_value={'percent':60.0,'mute':True}), \
                 patch.object(runtime.hardware,'set_volume') as set_volume:
                result = runtime.set_output_volume({'percent':60})
                self.assertEqual(result, {'available':True,'percent':60.0,'mute':True})
                runtime.initialize_output_volume()
            set_volume.assert_called_once_with(60)
            self.assertEqual(runtime.config.data['sources']['spotify']['initial_volume'], 100)

    def test_status_uses_cache_and_rejects_stale_generation_card_and_age(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            runtime.config.data['dac'] = DAC['id']
            runtime.recovery.phase = 'ready'
            runtime.volume = {'dac':'dac','card':1,'generation':0,'observed_at':100,'percent':60,'mute':False}
            with patch.object(runtime,'devices',return_value=[DAC]), \
                 patch.object(runtime.hardware,'items',side_effect=AssertionError('blocking call')), \
                 patch('hifi.runtime.time.monotonic',return_value=101):
                self.assertEqual(runtime.status()['output']['volume']['percent'],60)
                runtime.recovery.generation += 1
                self.assertFalse(runtime.status()['output']['volume']['available'])
                runtime.recovery.generation = 0
                runtime.volume['card'] = 2
                self.assertFalse(runtime.status()['output']['volume']['available'])
                runtime.volume['card'] = 1
                runtime.volume['observed_at'] = 0
                self.assertFalse(runtime.status()['output']['volume']['available'])

    def test_wall_clock_rollback_cannot_extend_volume_cache_lifetime(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            runtime.config.data['dac'] = DAC['id']
            runtime.recovery.phase = 'ready'
            with patch.object(runtime,'devices',return_value=[DAC]), \
                 patch.object(runtime.hardware,'volume_status',return_value={'percent':60,'mute':False}), \
                 patch('hifi.runtime.time.monotonic',return_value=100), \
                 patch('hifi.runtime.time.time',return_value=1000):
                runtime.observe_volume()
                self.assertTrue(runtime.volume_status([DAC])['available'])
            with patch('hifi.runtime.time.monotonic',return_value=111), \
                 patch('hifi.runtime.time.time',return_value=1):
                self.assertFalse(runtime.volume_status([DAC])['available'])

    def test_observation_started_during_write_is_discarded_even_on_failure(self):
        for failed_write in (False,True):
            with self.subTest(failed_write=failed_write), tempfile.TemporaryDirectory() as directory:
                runtime = Runtime(REPO,directory)
                runtime.config.data['dac'] = DAC['id']
                from hifi.config import atomic_json
                atomic_json(runtime.config.path,runtime.config.data)
                runtime.recovery.phase = 'ready'
                entered, release = threading.Event(), threading.Event()
                def read_volume():
                    if threading.current_thread() is observer:
                        entered.set()
                        if not release.wait(3):
                            raise RuntimeError('test observer timed out')
                        return {'percent':40,'mute':False}
                    return {'percent':60,'mute':False}
                observer = threading.Thread(target=runtime.observe_volume)
                def write_volume(percent):
                    observer.start()
                    if not entered.wait(1):
                        raise AssertionError('observer did not read during write')
                    if failed_write:
                        raise RuntimeError('hardware write failed')
                with patch.object(runtime,'devices',return_value=[DAC]), \
                     patch.object(runtime.hardware,'volume_status',side_effect=read_volume), \
                     patch.object(runtime.hardware,'set_volume',side_effect=write_volume):
                    try:
                        if failed_write:
                            with self.assertRaisesRegex(RuntimeError,'hardware write failed'):
                                runtime.set_output_volume({'percent':60})
                        else:
                            self.assertEqual(runtime.set_output_volume({'percent':60})['percent'],60)
                    finally:
                        release.set()
                        if observer.ident is not None:
                            observer.join(4)
                    self.assertFalse(observer.is_alive())
                    if failed_write:
                        self.assertIsNone(runtime.volume)
                    else:
                        self.assertEqual(runtime.volume_status([DAC])['percent'],60)

    def test_device_cleanup_restores_exact_snapshot_without_agent_api(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Mock()
            original = {'id':'dac','channels':[12345,23456],'mute':True}
            report = {'passed':False}
            path = Path(directory)/'nested/report.json'
            restore_and_report(runtime,original,report,path)
            runtime.hardware.restore_volume.assert_called_once_with(original)
            self.assertEqual(json.loads(path.read_text()),
                             {'passed':False,'hardware_volume_restored':True})

    def test_device_cleanup_failure_still_writes_failed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Mock()
            runtime.hardware.restore_volume.side_effect = RuntimeError('sink unavailable')
            path = Path(directory)/'nested/report.json'
            with self.assertRaisesRegex(RuntimeError,'sink unavailable'):
                restore_and_report(runtime,{'id':'dac'},{'passed':True},path)
            self.assertEqual(json.loads(path.read_text()),
                             {'passed':False,'hardware_volume_restored':False})

    def test_device_restart_timeout_restores_gain_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            runtime, fresh, http = Mock(), Mock(), Mock()
            original = {'id':'dac','channels':[12345,23456],'mute':True}
            runtime.hardware.volume_snapshot.return_value = original
            fresh.config.data = {'dac':None}
            fresh.config.path = Path(directory)/'fresh.json'
            fresh.hardware.volume_status.side_effect = [{'percent':100},{'percent':60}]
            def response(data):
                value = io.StringIO(json.dumps(data))
                value.headers = {}
                return value
            http.open.side_effect = [
                response({'config':{'dac':'dac','sources':{'spotify':{'initial_volume':100}}},
                          'output':{'health':'ready','volume':{'available':True,'percent':30,'mute':True}}}),
                response({'percent':40}), response({'percent':0}), response({'percent':60}),
                urllib.error.HTTPError('http://localhost',400,'invalid percent',{},None),
            ]
            with patch('sys.argv',['volume-smoke','--report',str(path)]), \
                 patch('output_volume_device_smoke.urllib.request.build_opener',return_value=http), \
                 patch('output_volume_device_smoke.Runtime',side_effect=[runtime,fresh]), \
                 patch('output_volume_device_smoke.subprocess.run') as restart, \
                 patch('output_volume_device_smoke.time.monotonic',side_effect=[0,1,0,121]):
                with self.assertRaisesRegex(AssertionError,'output volume did not become available'):
                    volume_device_smoke()
            restart.assert_called_once_with(['systemctl','--user','restart','hifi-agent'],
                                            check=True,timeout=30)
            runtime.hardware.restore_volume.assert_called_once_with(original)
            self.assertEqual(json.loads(path.read_text()),
                             {'passed':False,'hardware_volume_restored':True})

    def test_observation_racing_with_adjustment_cannot_replace_new_volume(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(REPO,directory)
            runtime.recovery.phase = 'ready'
            def old_observation():
                runtime.volume_revision += 1
                runtime.volume = {'percent':60}
                return {'percent':40,'mute':False}
            with patch.object(runtime,'selected',return_value=DAC), \
                 patch.object(runtime.hardware,'volume_status',side_effect=old_observation):
                runtime.observe_volume()
            self.assertEqual(runtime.volume, {'percent':60})


if __name__ == '__main__':
    unittest.main()
