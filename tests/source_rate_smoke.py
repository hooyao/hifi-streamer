"""Synthetic decoded-PCM transport acceptance; not a Spotify decoder-rate test."""
import argparse
import json
import os
import pty
import re
import select
import struct
import subprocess
import sys
import tempfile
import termios
import fcntl
import time
import wave
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'modules/audio-agent'))
from hifi.config import Config, atomic_json
from hifi.devices import discover
from hifi.pipewire import Hardware, run
from hifi.mpd import MPD
from hifi.soloist import Soloist
from dlna_smoke import usb_rate


def graph_rates(node):
    master,slave=pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,200,0,0))
    process=subprocess.Popen(['pw-top'],stdin=slave,stdout=slave,stderr=slave,
                             env={**os.environ,'TERM':'xterm'})
    os.close(slave)
    result=b''
    try:
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and len(result)<65536:
            if select.select([master],[],[],.2)[0]:
                result+=os.read(master,8192)
    finally:
        process.terminate(); process.wait(timeout=5); os.close(master)
    text=re.sub(r'\x1b\[[0-9;?]*[A-Za-z]','',result.decode(errors='replace'))
    return {int(rate) for rate in re.findall(rf'R\s+{node}\s+\d+\s+(\d+)',text)}


def restore_after_test(child, hardware, saved):
    """Attempt every cleanup step and restart services even if hardware disappears."""
    try:
        try:
            if child and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
        finally:
            try:
                hardware.for_direct()
            finally:
                hardware.restore_volume(saved)
    finally:
        subprocess.run(['systemctl','--user','start','hifi-soloist','hifi-agent'],check=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    config=Config(Path.home()/'.config/hifi-streamer')
    selected=lambda:next(d for d in discover() if d['id']==config.data['dac'])
    hardware=Hardware(selected)
    hardware.mpd=MPD(None)
    saved=hardware.volume_snapshot()
    history=Path.home()/'.config/hifi-streamer/state/recovery.json'
    before=json.loads(history.read_text()).get('attempts',[]) if history.exists() else []
    real=Soloist(None,lambda:True)
    real.command('pause')
    player=Soloist(hardware,lambda:True)
    # Only control intent is synthetic; Pulse PCM, graph and hardware are real.
    player.command=lambda method,**fields: {'logged_in':True} if method=='get_auth_state' else {'status':'playing','is_active':True}
    child=None
    rows=[]
    try:
        subprocess.run(['systemctl','--user','stop','hifi-agent','hifi-soloist'],check=True)
        hardware.for_direct()
        with tempfile.TemporaryDirectory() as directory:
            for rate in (44100,48000,96000,44100):
                path=Path(directory)/f'{rate}.wav'
                with wave.open(str(path),'wb') as audio:
                    audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(rate)
                    audio.writeframes(bytes(rate*4*10))
                target='hifi_standby' if player.applied_rate is None else hardware.sink()
                child=subprocess.Popen(['paplay','--device',target,
                                        '--property=application.process.binary=soloist',str(path)])
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    state=player.snapshot()
                    if state['health']=='healthy' and state['pcm_rate']==rate:
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError('synthetic Pulse source format unavailable')
                if player.applied_rate is None:
                    player.acquire(1)
                else:
                    player.follow_pcm_rate()
                usb_rate(selected()['card'],rate,timeout=20)
                sink=next(s for s in hardware.items('sinks') if s['name']==hardware.sink())
                rates=graph_rates(int(sink['properties']['object.id']))
                assert rates=={rate},rates
                assert hardware.volume_snapshot()==saved,'gain/mute changed'
                metadata=run('pw-metadata','-n','settings','0')
                assert "key:'clock.force-rate' value:'0'" in metadata
                rows.append({'decoded_pcm_hz':rate,'driver_graph_hz':rate,'usb_hz':rate,'gain_preserved':True})
                child.wait(timeout=20);child=None
                print(f'Synthetic PCM/graph/USB {rate}Hz passed',flush=True)
        hardware.for_direct()
        assert not hardware.clock_requested(hardware.sink()),'rate request survived handoff'
        after=json.loads(history.read_text()).get('attempts',[]) if history.exists() else []
        assert before==after,'synthetic rate test spent recovery budget'
        atomic_json(args.report,{'passed':True,'synthetic_transport_only':True,'checks':rows,'budget_unchanged':True})
    finally:
        restore_after_test(child, hardware, saved)


if __name__=='__main__':
    main()
