import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.soloist import Soloist


class Socket:
    def __init__(self):
        self.sent = []
    def send(self, message):
        self.sent.append(message)
    def receive(self):
        command = self.sent[-1]['command']
        if command == 'get_auth_state':
            return {'type':'auth_state','logged_in':True,'is_active':True}
        if command == 'get_state':
            return {'type':'playback_state','status':'paused','is_active':True}
        return {'type':'command_result','command':command}
    def close(self):
        pass


class Tests(unittest.TestCase):
    def test_documented_wire_protocol(self):
        with patch('hifi.soloist.Client',Socket):
            adapter = Soloist(None,lambda:True)
            state = adapter.snapshot()
            self.assertTrue(state['authenticated'])
            self.assertEqual(state['playback'],'paused')
            adapter.command('pause')
            self.assertEqual(adapter.client.sent[-1],{'type':'command','command':'pause'})
            adapter.command('set_volume',volume=100)
            self.assertEqual(adapter.client.sent[-1],{'type':'command','command':'set_volume','volume':100})

    def test_unconfigured_does_not_connect(self):
        with patch('hifi.soloist.Client',side_effect=AssertionError('should not connect')):
            self.assertEqual(Soloist(None,lambda:False).snapshot()['health'],'unconfigured')
