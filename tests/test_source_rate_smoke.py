"""Failure-path cleanup must not leave the audio services offline."""
import subprocess
import unittest
from unittest.mock import Mock, patch

from source_rate_smoke import restore_after_test


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
