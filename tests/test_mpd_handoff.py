"""Do not override a controller pause once direct hardware output is exposed."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.mpd import MPD


class HandoffTests(unittest.TestCase):
    def test_pause_after_hardware_enable_survives_acquisition(self):
        mpd = MPD(SimpleNamespace(for_direct=lambda:None))
        playback = {'state':'paused'}
        def command(text):
            if text == 'pause 0':
                playback['state'] = 'playing'
        def output(name, enabled):
            if name == 'direct' and enabled:
                # A controller observes DAC output and issues Pause immediately.
                playback['state'] = 'paused'
        mpd.command = command
        mpd.output = output
        mpd.acquire(1)
        self.assertEqual(playback['state'],'paused')
