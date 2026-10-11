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

    def test_source_clock_applies_before_open_and_clears_on_release(self):
        hardware = Hardware(lambda: {'id':'dac','card':2})
        hardware.mpd = Mock()
        events = []
        with patch.object(hardware,'sink',return_value='dac'), \
                patch.object(hardware,'ensure_released'), patch.object(hardware,'standby'), \
                patch.object(hardware,'move'), \
                patch.object(hardware,'hardware_rate',side_effect=lambda *args:events.append(('rate',*args))), \
                patch('hifi.pipewire.run',side_effect=lambda *args:events.append(args)):
            hardware.for_pipewire(rate=44100)
            self.assertTrue(hardware.owned_clock)
            self.assertLess(events.index(('rate','dac',44100)),
                            events.index(('pactl','suspend-sink','dac','0')))
            hardware.for_direct()
            self.assertIn(('rate','dac',None),events)
            self.assertFalse(hardware.owned_clock)

    def test_clock_parameters_address_only_selected_node(self):
        import json
        hardware = Hardware(lambda: {'id':'dac','card':2})
        sinks = [{'name':'dac','properties':{'object.id':'44'}},
                 {'name':'other','properties':{'object.id':'99'}}]
        with patch.object(hardware,'items',return_value=sinks), patch('hifi.pipewire.run') as run:
            hardware.hardware_rate('dac',44100)
        args = run.call_args.args
        self.assertEqual(args[:4],('pw-cli','set-param','44','Props'))
        self.assertEqual(json.loads(args[4])['params'],
                         ['audio.rate',44100,'api.alsa.multi-rate',False])
