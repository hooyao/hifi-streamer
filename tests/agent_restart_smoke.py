"""Qualify paused ownership and persistent-node clock cleanup on agent restart."""
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.config import Config
from hifi.devices import discover
from hifi.pipewire import Hardware
from hifi.soloist import Soloist
from dlna_smoke import usb_rate


class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(f'/run/user/{os.getuid()}/hifi-streamer/agent.sock')


def main():
    directory = Path.home()/'.config/hifi-streamer'
    config = Config(directory)
    selected = next(d for d in discover() if d['id']==config.data['dac'])
    hardware = Hardware(lambda:selected)
    player = Soloist(None,lambda:True)
    assert player.snapshot()['playback']=='playing', 'Start Spotify playback before this test'
    assert hardware.clock_requested(hardware.sink()), 'Spotify hardware clock is not set'
    path = directory/'state/recovery.json'
    before = json.loads(path.read_text())['attempts'] if path.exists() else []
    player.client.close()
    subprocess.run(['systemctl','--user','restart','hifi-agent'],check=True,timeout=30)

    def status():
        connection = Connection('localhost')
        headers = {'Host':'localhost','Origin':'http://localhost','Content-Type':'application/json'}
        connection.request('GET','/api/status',headers=headers)
        response = connection.getresponse()
        assert response.status==200
        data = json.loads(response.read())
        connection.close()
        return data

    deadline = time.monotonic()+40
    while time.monotonic()<deadline:
        try:
            data = status()
            if data['output']['health']=='ready' and data['sources'].get('spotify',{}).get('playback')=='paused':
                break
        except (OSError,ValueError):
            pass
        time.sleep(.5)
    else:
        raise AssertionError('agent did not restore paused readiness')
    assert data['output']['owner'] is None, data['output']
    assert not data['output']['recovery']['retry_available'], 'healthy retry exposed'
    assert not hardware.clock_requested(hardware.sink()), 'stale hardware clock survived'
    after = json.loads(path.read_text())['attempts'] if path.exists() else []
    assert after==before, 'healthy restart spent recovery budget'
    connection = Connection('localhost')
    connection.request('POST','/api/recovery/retry','{}',
        {'Host':'localhost','Origin':'http://localhost',
         'Content-Type':'application/json','X-CSRF-Token':data['csrf']})
    response = connection.getresponse()
    assert response.status==409, 'healthy retry endpoint accepted a disruption'
    response.read()
    connection.close()
    player = Soloist(None,lambda:True)
    player.command('activate')
    player.command('play')
    usb_rate(selected['card'],44100,timeout=20)
    print(json.dumps({'paused_restart':'passed','stale_clock_cleanup':'passed',
                      'budget_unchanged':True,'healthy_retry_rejected':True,'fresh_playback_hz':44100}))


if __name__=='__main__':
    main()
