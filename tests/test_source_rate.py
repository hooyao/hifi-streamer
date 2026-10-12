"""Decoded-rate observation, error isolation and selected-output transitions."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.pipewire import Hardware, PCMFormatError
from hifi.soloist import Soloist
from hifi.runtime import Runtime


def stream(rate, binary='soloist', corked=False):
    return {'sample_specification':f'float32le 2ch {rate}Hz','corked':corked,
            'properties':{'application.process.binary':binary}}


class Tests(unittest.TestCase):
    def test_rate_comes_from_source_and_prefers_active_stream(self):
        hardware=Hardware(lambda:None)
        with patch.object(hardware,'items',return_value=[stream(44100,'browser'),stream(44100,corked=True),stream(48000)]):
            self.assertEqual(hardware.source_rate('soloist'),48000)

    def test_unknown_and_ambiguous_format_never_fall_back(self):
        hardware=Hardware(lambda:None)
        with patch.object(hardware,'items',return_value=[]):
            self.assertIsNone(hardware.source_rate('soloist'))
        with patch.object(hardware,'items',return_value=[stream(44100),stream(96000)]), \
             self.assertRaisesRegex(PCMFormatError,'ambiguous'):
            hardware.source_rate('soloist')
        with patch.object(hardware,'items',return_value=[{'properties':{'application.process.binary':'soloist'}}]), \
             self.assertRaisesRegex(PCMFormatError,'unavailable'):
            hardware.source_rate('soloist')

    def test_capabilities_and_host_configuration_both_must_allow_rate(self):
        hardware=Hardware(lambda:{'card':1})
        capabilities='Playback:\nFormat: S32_LE\nRates: 44100, 48000, 96000\nFormat: SPECIAL DSD_U32_BE\nRates: 384000\nCapture:\nFormat: S32_LE\nRates: 384000\n'
        with patch('hifi.pipewire.Path.read_text',return_value=capabilities), \
             patch('hifi.pipewire.run',return_value="key:'clock.allowed-rates' value:'[ 44100, 48000 ]'"):
            hardware.validate_source_rate(48000)
            with self.assertRaisesRegex(PCMFormatError,'Host clock'):
                hardware.validate_source_rate(96000)
            with self.assertRaisesRegex(PCMFormatError,'DAC does not support'):
                hardware.validate_source_rate(384000)

    def player(self, hardware):
        player=Soloist(hardware,lambda:True)
        player.command=Mock(side_effect=lambda method,**fields:
                            {'logged_in':True} if method=='get_auth_state' else
                            {'status':'playing','is_active':True} if method=='get_state' else {})
        return player

    def test_continuous_playback_range_allows_supported_intermediate_rate(self):
        hardware=Hardware(lambda:{'card':1})
        with patch('hifi.pipewire.Path.read_text',return_value='Playback:\nFormat: S32_LE\nRates: 8000 - 192000 (continuous)\n'), \
             patch('hifi.pipewire.run',return_value="key:'clock.allowed-rates' value:'[ 44100, 48000, 96000 ]'"):
            hardware.validate_source_rate(96000)

    def test_global_forced_clock_is_reported_without_overriding_it(self):
        hardware=Hardware(lambda:{'card':1})
        metadata="key:'clock.allowed-rates' value:'[ 44100, 48000 ]'\nkey:'clock.force-rate' value:'48000'"
        with patch('hifi.pipewire.Path.read_text',return_value='Playback:\nFormat: S32_LE\nRates: 44100, 48000\n'), \
             patch('hifi.pipewire.run',return_value=metadata) as run, \
             self.assertRaisesRegex(PCMFormatError,'Global forced clock'):
            hardware.validate_source_rate(44100)
        self.assertEqual(run.call_count,1)

    def test_failed_owned_rate_change_enters_bounded_output_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Runtime(Path(__file__).resolve().parents[1],directory)
            dlna,spotify=Mock(),Mock()
            dlna.snapshot.return_value={'health':'healthy','active':True,'playback':'stopped'}
            spotify.snapshot.return_value={'health':'healthy','active':True,'playback':'playing'}
            spotify.follow_pcm_rate.side_effect=RuntimeError('clock transition failed')
            runtime.adapters={'dlna':dlna,'spotify':spotify}
            runtime.core.adapters=runtime.adapters
            runtime.core.owner='spotify'
            runtime.recovery.phase='ready'
            runtime.connected,runtime.card=True,1
            with patch.object(runtime,'selected',return_value={'card':1}), \
                 patch.object(runtime.recovery,'schedule') as repair, self.assertRaises(RuntimeError):
                runtime.tick()
            repair.assert_called_once_with('output_stalled')

    def test_acquisition_and_changed_rate_follow_actual_pcm(self):
        hardware=Mock()
        hardware.source_rate.side_effect=[48000,48000,96000]
        player=self.player(hardware)
        self.assertEqual(player.snapshot()['pcm_rate'],48000)
        player.acquire(1)
        hardware.for_pipewire.assert_called_once_with(rate=48000)
        player.snapshot(); player.follow_pcm_rate()
        hardware.follow_rate.assert_not_called()
        player.snapshot(); player.follow_pcm_rate()
        hardware.follow_rate.assert_called_once_with(96000)
        self.assertEqual(hardware.validate_source_rate.call_count,2)

    def test_pending_stream_does_not_open_fixed_rate_output(self):
        hardware=Mock()
        hardware.source_rate.return_value=None
        player=self.player(hardware)
        self.assertTrue(player.snapshot()['rate_pending'])
        with self.assertRaises(PCMFormatError):
            player.acquire(1)
        hardware.for_pipewire.assert_not_called()

    def test_remote_active_device_does_not_probe_local_pcm(self):
        hardware=Mock()
        player=self.player(hardware)
        player.command=Mock(side_effect=lambda method,**fields:
                            {'logged_in':True} if method=='get_auth_state' else
                            {'status':'playing','is_active':False})
        self.assertFalse(player.snapshot()['active'])
        hardware.source_rate.assert_not_called()

    def test_invalid_format_error_persists_after_protective_pause(self):
        hardware=Mock()
        hardware.source_rate.return_value=96000
        hardware.validate_source_rate.side_effect=PCMFormatError('unsupported')
        player=self.player(hardware)
        self.assertEqual(player.snapshot()['health'],'unavailable')
        player.command=Mock(side_effect=lambda method,**fields:
                            {'logged_in':True} if method=='get_auth_state' else {'status':'paused'})
        self.assertEqual(player.snapshot()['error'],'unsupported')
        hardware.for_pipewire.assert_not_called()

    def test_transition_suspends_before_changing_rate_and_preserves_gain(self):
        hardware=Hardware(lambda:{'card':1})
        events=[]
        saved={'channels':[65536,65536],'mute':False}
        with patch.object(hardware,'sink',return_value='selected'), \
             patch.object(hardware,'standby',side_effect=lambda:events.append('standby')), \
             patch.object(hardware,'move',side_effect=lambda target:events.append(('move',target))), \
             patch.object(hardware,'volume_snapshot',return_value=saved), \
             patch.object(hardware,'ensure_released',side_effect=lambda:events.append('closed')), \
             patch.object(hardware,'hardware_rate',side_effect=lambda *args:events.append(args)), \
             patch.object(hardware,'restore_volume',side_effect=lambda value:events.append(value)), \
             patch('hifi.pipewire.run',side_effect=lambda *args:events.append(args)):
            hardware.follow_rate(96000)
        self.assertEqual(events,['standby',('pactl','suspend-sink','hifi_standby','0'),
                                 ('move','hifi_standby'),('pactl','suspend-sink','selected','1'),'closed',
                                 ('selected',96000),saved,('move','selected'),
                                 ('pactl','suspend-sink','hifi_standby','1'),
                                 ('pactl','suspend-sink','selected','0')])

    def test_invalid_optional_request_does_not_revoke_dlna(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=Runtime(Path(__file__).resolve().parents[1],directory)
            dlna,spotify=Mock(),Mock()
            dlna.snapshot.return_value={'health':'healthy','active':True,'playback':'playing'}
            spotify.snapshot.return_value={'health':'unavailable','active':True,'playback':'playing','rate_error':True}
            runtime.adapters={'dlna':dlna,'spotify':spotify}
            runtime.core.adapters=runtime.adapters
            runtime.core.owner='dlna'
            runtime.recovery.phase='ready'
            runtime.connected,runtime.card=True,1
            with patch.object(runtime,'selected',return_value={'card':1}), \
                 patch.object(runtime.hardware,'for_direct') as route, \
                 patch.object(runtime.recovery,'playback_health'), \
                 patch.object(runtime.recovery,'schedule') as repair:
                runtime.tick()
            self.assertEqual(runtime.core.owner,'dlna')
            dlna.release.assert_not_called()
            spotify.command.assert_called_once_with('pause')
            route.assert_not_called(); repair.assert_not_called()

    def test_changed_generation_does_not_resume_new_hardware(self):
        hardware=Hardware(lambda:{'card':1})
        checks=iter([True,False])
        with patch.object(hardware,'sink',return_value='selected'), \
             patch.object(hardware,'volume_snapshot',return_value={}), \
             patch.object(hardware,'standby'), patch.object(hardware,'move'), \
             patch.object(hardware,'ensure_released'), \
             patch.object(hardware,'hardware_rate') as rate, \
             patch('hifi.pipewire.run') as run, self.assertRaisesRegex(RuntimeError,'generation'):
            hardware.follow_rate(48000,valid=lambda:next(checks))
        rate.assert_not_called()
        self.assertNotIn(('pactl','suspend-sink','selected','0'),[call.args for call in run.call_args_list])
