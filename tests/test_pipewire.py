"""Verify handoff does not open the DAC against an active standby clock."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.pipewire import Hardware


class Tests(unittest.TestCase):
    def test_real_sink_opens_after_stream_transfer_and_standby_suspend(self):
        hardware = Hardware(lambda: {'id':'dac', 'card':1})
        hardware.mpd = Mock()
        events = []
        with patch.object(hardware, 'sink', return_value='dac'), \
                patch.object(hardware,'ensure_released'), \
                patch.object(hardware,'move',side_effect=lambda target:events.append(('move',target))), \
                patch('hifi.pipewire.run',side_effect=lambda *args:events.append(args)):
            hardware.for_pipewire()
        self.assertEqual(events, [('pactl','set-default-sink','dac'), ('move','dac'),
                                  ('pactl','suspend-sink','hifi_standby','1'),
                                  ('pactl','suspend-sink','dac','0')])
        hardware.mpd.release.assert_called_once()

    def test_standby_uses_spotify_clock(self):
        hardware = Hardware(lambda: None)
        with patch.object(hardware,'items',return_value=[]), patch('hifi.pipewire.run') as run:
            hardware.standby()
        run.assert_called_once_with('pactl','load-module','module-null-sink',
                                    'sink_name=hifi_standby','rate=44100')

    def test_quiesced_recovery_replaces_old_standby_rate(self):
        hardware = Hardware(lambda: None)
        old = {'name':'hifi_standby','sample_specification':'float32le 2ch 48000Hz','owner_module':42}
        with patch.object(hardware,'items',return_value=[old]), patch('hifi.pipewire.run') as run:
            hardware.standby()
            run.assert_not_called()
            hardware.standby(reconcile=True)
        self.assertEqual(run.call_args_list[0].args, ('pactl','unload-module','42'))
        self.assertEqual(run.call_args_list[1].args[-1], 'rate=44100')

    def test_profile_change_targets_dac_and_preserves_gain(self):
        hardware = Hardware(lambda: {'id':'dac','card':1})
        cards = [{'name':'internal','properties':{'alsa.card':'0'},'active_profile':'off'},
                 {'name':'usb','properties':{'alsa.card':'1'},'active_profile':'analog-stereo',
                  'profiles':{'pro-audio':{'available':True}}}]
        saved = {'id':'dac','channels':[123,123],'mute':True}
        with patch.object(hardware,'items',return_value=cards), \
                patch.object(hardware,'volume_snapshot',return_value=saved), \
                patch.object(hardware,'sink',return_value='usb-sink'), \
                patch.object(hardware,'restore_volume') as restore, patch('hifi.pipewire.run') as run:
            hardware.direct_profile()
        run.assert_called_once_with('pactl','set-card-profile','usb','pro-audio')
        restore.assert_called_once_with(saved)
