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
                run.assert_any_call('systemctl','--user','enable','--now','hifi-mpd','hifi-upmpdcli')
                subprocess_run.assert_any_call(
                    ['systemctl','--user','reset-failed','hifi-mpd','hifi-upmpdcli'],
                    check=False, stderr=manage.subprocess.DEVNULL)


if __name__ == '__main__':
    unittest.main()
