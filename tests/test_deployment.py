"""Verify control-plane bootstrap without usable audio hardware."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hifi_deploy_manage', REPO/'deploy/manage.py')
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class BootstrapTests(unittest.TestCase):
    def test_discovery_failure_keeps_web_and_disables_stale_audio_units(self):
        refs = {name:'sha256:'+'a'*64 for name in ('mpd','upmpdcli','soloist','web')}
        for failure in (None, OSError('sysfs disappeared'), ValueError('invalid card')):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                units = root/'units'
                units.mkdir()
                enabled = {'hifi-upmpdcli', 'hifi-mpd', 'hifi-soloist'}
                for name in enabled:
                    (units/f'{name}.service').write_text('[Install]\nWantedBy=default.target\n')
                config = manage.Config(root/'config')
                config.data['dac'] = 'fixture'
                manage.atomic_json(config.path, config.data)
                events = []
                def command(*args):
                    events.append(args)
                    if 'disable' in args:
                        enabled.difference_update(args[4:])
                def discovery():
                    self.assertIn(('systemctl','--user','enable','--now','hifi-web'), events)
                    if failure:
                        raise failure
                    return []
                with patch.multiple(manage, CONFIG=root/'config', DATA=root/'data',
                                    UNITS=units, RUNTIME=root/'run'), \
                     patch.object(manage,'images',return_value=refs), \
                     patch.object(manage,'discover',side_effect=discovery), \
                     patch.object(manage,'run',side_effect=command) as run, \
                     patch.object(manage.subprocess,'run') as subprocess_run:
                    manage.apply(only='soloist', maintenance_held=True)
                    run.assert_any_call('systemctl','--user','disable','--now',
                                        'hifi-upmpdcli','hifi-mpd','hifi-soloist')
                    subprocess_run.assert_called_with(
                        ['systemctl','--user','stop','hifi-upmpdcli','hifi-mpd','hifi-soloist'], check=False)
                self.assertFalse(enabled, 'stale audio services remain enabled for boot')
                self.assertTrue((units/'hifi-web.service').exists())

    def test_changed_web_image_restarts_but_idempotent_apply_keeps_web(self):
        refs = {name:'sha256:'+'a'*64 for name in ('mpd','upmpdcli','soloist','web')}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.multiple(manage, CONFIG=root/'config', DATA=root/'data',
                                UNITS=root/'units', RUNTIME=root/'run'), \
                 patch.object(manage,'images',return_value=refs), \
                 patch.object(manage,'discover',return_value=[]), \
                 patch.object(manage,'run') as run, \
                 patch.object(manage.subprocess,'run') as subprocess_run:
                subprocess_run.return_value.returncode = 3
                manage.apply(maintenance_held=True)
                run.reset_mock()
                refs['web'] = 'sha256:'+'b'*64
                subprocess_run.return_value.returncode = 0
                manage.apply(maintenance_held=True)
                run.assert_any_call('systemctl','--user','restart','hifi-web')
                self.assertIn(refs['web'],(root/'units/hifi-web.service').read_text())
                run.reset_mock()
                manage.apply(maintenance_held=True)
                self.assertFalse(any('restart' in call.args for call in run.call_args_list))

    def test_web_survives_missing_selection_and_later_audio_setup(self):
        device = {'id':'fixture', 'card':2}
        refs = {name:'sha256:'+'a'*64 for name in ('mpd','upmpdcli','soloist','web')}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = manage.Config(root/'config')
            with patch.multiple(manage, CONFIG=root/'config', DATA=root/'data',
                                UNITS=root/'units', RUNTIME=root/'run'), \
                 patch.object(manage, 'images', return_value=refs), \
                 patch.object(manage, 'discover', return_value=[]) as discovery, \
                 patch.object(manage, 'run') as run, \
                 patch.object(manage.subprocess, 'run') as subprocess_run:
                for selected in (None, 'fixture'):
                    config.data['dac'] = selected
                    manage.atomic_json(config.path, config.data)
                    manage.apply(maintenance_held=True)
                    web = (root/'units/hifi-web.service').read_text()
                    self.assertIn('--memory=32m', web)
                    self.assertIn('hifi-agent.service', web)
                    self.assertFalse((root/'units/hifi-mpd.service').exists())
                    run.assert_any_call('systemctl','--user','enable','--now','hifi-web')
                    self.assertFalse(any('hifi-mpd' in call.args and 'enable' in call.args
                                         for call in run.call_args_list))
                    subprocess_run.assert_called_with(
                        ['systemctl','--user','stop','hifi-upmpdcli','hifi-mpd','hifi-soloist'], check=False)
                discovery.return_value = [device]
                subprocess_run.return_value.returncode = 1
                manage.apply(maintenance_held=True)
                self.assertIn('/dev/snd/pcmC2D0p', (root/'units/hifi-mpd.service').read_text())
                self.assertIn('INITIAL_VOLUME=100', (root/'units/hifi-soloist.service').read_text())
                run.assert_any_call('systemctl','--user','enable','--now','hifi-mpd','hifi-upmpdcli')
                subprocess_run.assert_any_call(
                    ['systemctl','--user','reset-failed','hifi-mpd','hifi-upmpdcli'],
                    check=False, stderr=manage.subprocess.DEVNULL)
                config.reload()
                config.data['sources']['spotify']['initial_volume'] = 35
                manage.atomic_json(config.path, config.data)
                manage.apply(maintenance_held=True)
                self.assertIn('INITIAL_VOLUME=35', (root/'units/hifi-soloist.service').read_text())


if __name__ == '__main__':
    unittest.main()
