import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.config import Config
from hifi.core import Arbiter
from hifi.devices import discover
from hifi.registry import load


class Fake:
    def __init__(self):
        self.instance = 'current'
        self.events = []
        self.fail = False
    def release(self):
        self.events.append('release')
        if self.fail:
            raise RuntimeError('release failed')
    def acquire(self, generation):
        self.events.append(('acquire', generation))
    def ensure_released(self):
        self.events.append('verified')
    def silence(self):
        self.events.append('silence')


class Tests(unittest.TestCase):
    def test_third_source_and_old_events(self):
        adapters = {name: Fake() for name in ('dlna', 'spotify', 'third')}
        hardware = Fake()
        core = Arbiter(adapters, hardware, 0)
        self.assertTrue(core.request('dlna', 'current', 1))
        self.assertTrue(core.request('third', 'current', 1))
        self.assertEqual(core.owner, 'third')
        self.assertFalse(core.request('spotify', 'retired', 10))
        self.assertFalse(core.request('dlna', 'current', 1))
        core.disconnect()
        self.assertEqual(core.state, 'disconnected')

    def test_release_failure_does_not_grant(self):
        adapters = {'dlna': Fake(), 'spotify': Fake()}
        core = Arbiter(adapters, Fake(), 0)
        core.request('dlna', 'current', 1)
        adapters['dlna'].fail = True
        with self.assertRaises(RuntimeError):
            core.request('spotify', 'current', 1)
        self.assertEqual(adapters['spotify'].events, [])
        self.assertIsNone(core.owner)
        self.assertEqual(core.state, 'error')

    def test_config_validation_and_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Config(directory)
            for change in ({'sources': {'dlna': {'enabled': False}}}, {'dac': 'missing'}, {'sources': {'third': {}}}):
                with self.assertRaises(ValueError):
                    config.update(change, [])
            config.update({'spotify_key': 'private', 'dac': 'usb'}, [{'id': 'usb'}])
            self.assertNotIn('private', json.dumps(config.public()))
            self.assertEqual(Config(directory).data['dac'], 'usb')
            other = Config(directory)
            other.update({'sources':{'spotify':{'enabled':True}}}, [{'id':'usb'}])
            config.reload()
            self.assertTrue(config.data['sources']['spotify']['enabled'])
            config.update({'sources':{'spotify':{'initial_volume':100}}},[{'id':'usb'}])
            self.assertEqual(config.public()['sources']['spotify']['initial_volume'],100)
            with self.assertRaises(ValueError):
                config.update({'sources':{'spotify':{'initial_volume':101}}},[{'id':'usb'}])

    def test_usb_reenumeration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            usb = root / 'usb/1-4'
            usb.mkdir(parents=True)
            for key, value in {'idVendor':'152a','idProduct':'8750','serial':'stable','product':'DAC'}.items():
                (usb / key).write_text(value)
            sound = root / 'sound'
            sound.mkdir()
            card = sound / 'card1'
            card.mkdir()
            (card / 'device').symlink_to(usb, target_is_directory=True)
            (card / 'id').write_text('II')
            first = discover(sound)[0]
            card.rename(sound / 'card7')
            second = discover(sound)[0]
            self.assertEqual(first['id'], second['id'])
            self.assertEqual(second['card'], 7)

    def test_registry(self):
        modules = load(Path(__file__).resolve().parents[1] / 'modules/sources')
        self.assertTrue(modules['dlna']['required'])
        self.assertFalse(modules['spotify']['required'])


if __name__ == '__main__':
    unittest.main()
