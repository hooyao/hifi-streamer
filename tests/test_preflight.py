"""Exercise account validation before an installer can write service files."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('hifi_preflight', Path(__file__).resolve().parents[1]/'deploy/preflight.py')
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def test_engine_must_report_rootless_even_with_successful_exit(self):
        for output in ('true\n', 'false\n', '', 'unexpected\n'):
            with self.subTest(output=output), \
                 patch.object(preflight.os, 'getuid', return_value=1000), \
                 patch.object(preflight.shutil, 'which', return_value='/usr/bin/fixture'), \
                 patch.object(preflight.pwd, 'getpwuid', return_value=Mock(pw_name='renderer')), \
                 patch.object(preflight, 'check_ranges'), \
                 patch.object(preflight.subprocess, 'run', side_effect=[
                     Mock(returncode=0), Mock(returncode=0, stdout=output)]) as run:
                if output.strip() == 'true':
                    preflight.check()
                else:
                    with self.assertRaisesRegex(ValueError, 'engine is rootless'):
                        preflight.check()
                self.assertEqual(run.call_args.kwargs['stdout'], preflight.subprocess.PIPE)

    def ranges(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'subuid'
            path.write_text(text)
            preflight.check_ranges(path, 'renderer', 1000)

    def test_valid_named_and_numeric_allocations(self):
        self.ranges('renderer:100000:65536\nother:200000:65536\n')
        self.ranges('1000:100000:65536\n')

    def test_stale_account_or_small_range_rejected(self):
        for text in ('oldname:100000:65536\n', 'renderer:100000:1000\n'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'current account'):
                self.ranges(text)

    def test_overlapping_allocations_rejected(self):
        for text in ('renderer:100000:65536\nother:150000:65536\n',
                     'renderer:100000:65536\n1000:100000:65536\n'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'overlap'):
                self.ranges(text)

    def test_invalid_or_missing_file_is_actionable(self):
        with self.assertRaisesRegex(ValueError, 'invalid'):
            self.ranges('renderer:not-a-number:65536\n')
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            preflight.check_ranges('/definitely/missing/subuid', 'renderer', 1000)

    def test_root_rejected_before_engine_initialization(self):
        with patch.object(preflight.os, 'getuid', return_value=0), \
             patch.object(preflight.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'service account'):
            preflight.check()
        run.assert_not_called()

    def test_missing_dependencies_rejected_before_engine_initialization(self):
        with patch.object(preflight.os, 'getuid', return_value=1000), \
             patch.object(preflight.shutil, 'which', return_value=None), \
             patch.object(preflight.subprocess, 'run') as run, self.assertRaisesRegex(ValueError, 'host-setup'):
            preflight.check()
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
