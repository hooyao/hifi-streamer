"""Selected graph-rate observation and failure-path service cleanup."""
import subprocess
import unittest
from unittest.mock import Mock, patch

from source_rate_smoke import graph_rates, restore_after_test


class GraphMonitorTests(unittest.TestCase):
    def test_batch_monitor_reads_only_the_running_selected_node(self):
        output = '''S   ID  QUANT   RATE    WAIT    BUSY   W/Q   B/Q  ERR FORMAT NAME
C   53      0      0    ---     ---   ---   ---     0        selected
R  153   1024  96000    1us     2us   0.0   0.0     0        other
R   53   1024  44100    1us     2us   0.0   0.0     0 S32LE  selected
S   ID  QUANT   RATE    WAIT    BUSY   W/Q   B/Q  ERR FORMAT NAME
R   53   1024  44100    1us     2us   0.0   0.0     0 S32LE  selected
'''
        with patch('source_rate_smoke.subprocess.check_output',return_value=output) as command:
            self.assertEqual(graph_rates(53),{44100})
        command.assert_called_once_with(['pw-top','--batch-mode','--iterations','3'],
                                        text=True,timeout=8)

    def test_monitor_retains_a_rate_change_instead_of_accepting_only_the_last_row(self):
        with patch('source_rate_smoke.subprocess.check_output',
                   return_value='R 53 1024 48000\nR 53 1024 96000\n'):
            self.assertEqual(graph_rates(53),{48000,96000})

    def test_missing_suspended_or_malformed_selected_node_cannot_pass(self):
        for output in ('','S 53 0 0\n','R 153 1024 44100\n','R 53 1024 unknown\n'):
            with self.subTest(output=output), \
                 patch('source_rate_smoke.subprocess.check_output',return_value=output):
                with self.assertRaisesRegex(AssertionError,'No running driver graph rate'):
                    graph_rates(53)

    def test_monitor_timeout_or_process_failure_cannot_pass(self):
        for error in (subprocess.TimeoutExpired('pw-top',8),
                      subprocess.CalledProcessError(1,'pw-top')):
            with self.subTest(error=type(error).__name__), \
                 patch('source_rate_smoke.subprocess.check_output',side_effect=error):
                with self.assertRaises(type(error)):
                    graph_rates(53)


class CleanupTests(unittest.TestCase):
    def test_route_failure_still_restores_volume_and_restarts_services(self):
        hardware = Mock()
        hardware.for_direct.side_effect = RuntimeError('DAC disappeared')
        saved = {'channels': [65536, 65536], 'mute': False}
        with patch('source_rate_smoke.subprocess.run') as run:
            with self.assertRaisesRegex(RuntimeError, 'DAC disappeared'):
                restore_after_test(None, hardware, saved)
        hardware.restore_volume.assert_called_once_with(saved)
        run.assert_called_once_with(
            ['systemctl', '--user', 'start', 'hifi-soloist', 'hifi-agent'], check=True)

    def test_volume_failure_still_restarts_services(self):
        hardware = Mock()
        hardware.restore_volume.side_effect = RuntimeError('sink unavailable')
        with patch('source_rate_smoke.subprocess.run') as run:
            with self.assertRaisesRegex(RuntimeError, 'sink unavailable'):
                restore_after_test(None, hardware, {})
        hardware.for_direct.assert_called_once_with()
        run.assert_called_once()

    def test_stuck_player_is_killed_before_route_cleanup(self):
        child, hardware = Mock(), Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('paplay', 5), None]
        calls = Mock()
        calls.attach_mock(child, 'child')
        calls.attach_mock(hardware, 'hardware')
        with patch('source_rate_smoke.subprocess.run') as run:
            restore_after_test(child, hardware, {})
        child.terminate.assert_called_once_with()
        child.kill.assert_called_once_with()
        self.assertEqual(child.wait.call_count, 2)
        self.assertLess(calls.mock_calls.index(unittest.mock.call.child.kill()),
                        calls.mock_calls.index(unittest.mock.call.hardware.for_direct()))
        run.assert_called_once()

    def test_restart_failure_is_not_reported_as_success(self):
        with patch('source_rate_smoke.subprocess.run',
                   side_effect=subprocess.CalledProcessError(1, 'systemctl')):
            with self.assertRaises(subprocess.CalledProcessError):
                restore_after_test(None, Mock(), {})


if __name__ == '__main__':
    unittest.main()
