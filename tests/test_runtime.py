import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.runtime import Runtime


class Adapter:
    instance = 'live'
    def __init__(self, state):
        self.state = state
        self.acquired = False
    def snapshot(self):
        return {'playback':self.state,'active':True,'health':'healthy'}
    def configured(self):
        return False
    def release(self):
        self.state = 'paused'
    def acquire(self, generation):
        self.acquired = True


class Hardware:
    def ensure_released(self):
        pass
    def silence(self):
        pass


class Tests(unittest.TestCase):
    def test_simultaneous_priority_and_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1],directory)
            runtime.recovery.phase = 'ready'
            adapters = {'dlna':Adapter('playing'),'spotify':Adapter('playing')}
            runtime.adapters = adapters
            runtime.core.adapters = adapters
            runtime.hardware = Hardware()
            runtime.core.hardware = runtime.hardware
            runtime.connected = True
            runtime.card = 1
            with patch.object(runtime,'selected',return_value={'card':1}):
                runtime.tick()
            self.assertEqual(runtime.core.owner,'dlna')
            self.assertFalse(adapters['spotify'].acquired)
            self.assertEqual(adapters['spotify'].state,'paused')
            with patch.object(runtime,'selected',return_value=None):
                runtime.tick()
            self.assertEqual(runtime.core.state,'disconnected')

    def test_failed_optional_snapshot_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1],directory)
            runtime.recovery.phase = 'ready'
            adapters = {'dlna':Adapter('stopped'),'spotify':Adapter('stopped')}
            runtime.adapters = adapters
            with patch.object(runtime,'selected',return_value=None), patch.object(adapters['spotify'],'snapshot',side_effect=RuntimeError()):
                runtime.tick()
            self.assertEqual(runtime.snapshots['dlna']['health'],'healthy')
            self.assertEqual(runtime.snapshots['spotify']['playback'],'unknown')

    def test_fast_controller_stop_play_can_reacquire_without_polling_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(__file__).resolve().parents[1],directory)
            runtime.recovery.phase = 'ready'
            adapters = {'dlna':Adapter('playing'), 'spotify':Adapter('stopped')}
            runtime.adapters, runtime.core.adapters = adapters, adapters
            runtime.hardware = Hardware()
            runtime.core.hardware = runtime.hardware
            runtime.connected, runtime.card = True, 1
            runtime.previous['dlna'] = True
            runtime.core.owner = None
            with patch.object(runtime,'selected',return_value={'card':1}), \
                    patch.object(runtime.recovery,'playback_health'):
                runtime.tick()
            self.assertEqual(runtime.core.owner,'dlna')
