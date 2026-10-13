"""Qualify real MP3 decoding and HTTP controls with a bounded null-output container."""
import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.mpd import MPD
from http_mp3_fixture import MP3Server, silent_mp3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    parser.add_argument('--engine',choices=['docker','podman'],default='docker')
    parser.add_argument('--report',type=Path)
    args = parser.parse_args()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        port = probe.getsockname()[1]
    name = 'hifi-mp3-'+uuid.uuid4().hex[:10]
    report = {'passed':False,'checks':[]}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        local = root/'local.mp3'
        local.write_bytes(silent_mp3())
        config = root/'mpd.conf'
        config.write_text(f'''music_directory "/fixture"
log_file "/dev/stdout"
bind_to_address "127.0.0.1"
port "{port}"
database {{
    plugin "simple"
    path "/tmp/database"
}}
audio_output {{
    type "null"
    name "timed"
    sync "yes"
}}
''')
        mpd = MPD(None,port=port)
        def wait_play(minimum=.25, maximum=None):
            deadline = time.monotonic()+12
            while time.monotonic()<deadline:
                state = mpd.snapshot()
                if state.get('error'):
                    raise AssertionError('MP3 decoder reported an error')
                elapsed = float(state.get('elapsed') or 0)
                if state['playback']=='playing' and elapsed>=minimum and (maximum is None or elapsed<maximum):
                    assert state['format'].split(':')[0]=='44100',state['format']
                    return state
                time.sleep(.1)
            raise AssertionError('MP3 playback did not advance')
        def play(uri):
            mpd.command('stop');mpd.command('clear');mpd.command('clearerror')
            mpd.command('add "'+uri+'"');mpd.command('play')
            return wait_play()
        try:
            subprocess.run([args.engine,'run','-d','--name',name,'--network=host','--memory=128m',
                            '--pids-limit=32','--read-only','--tmpfs=/tmp:rw,size=16m',
                            '-v',f'{config}:/etc/mpd.conf:ro','-v',f'{root}:/fixture:ro',args.image],
                           check=True,stdout=subprocess.DEVNULL)
            deadline = time.monotonic()+30
            while time.monotonic()<deadline:
                try:mpd.command('status');break
                except (OSError,RuntimeError):time.sleep(.25)
            else:raise AssertionError('MPD control port unavailable')
            play('local.mp3')
            report['checks'].append({'case':'local fixture validity','passed':True})
            print('Local generated MP3 passed',flush=True)
            cases = [('cbr',False,0,True,True),('id3',False,16384,True,True),
                     ('vbr',True,0,True,True),('extensionless',False,0,True,False),
                     ('sequential',False,16384,False,False)]
            for label,vbr,id3,seekable,extension in cases:
                server = MP3Server(silent_mp3(vbr=vbr,id3_bytes=id3),seekable,extension)
                try:
                    play(server.url)
                    mpd.command('pause 1')
                    assert mpd.snapshot()['playback']=='paused'
                    mpd.command('pause 0');wait_play()
                    if seekable:
                        mpd.command('seekcur 8')
                        state = wait_play(minimum=7.5)
                        assert float(state['elapsed'])>=7.5,state['elapsed']
                        mpd.command('seekcur 2')
                        state = wait_play(minimum=1.5,maximum=7)
                        assert 1.5<=float(state['elapsed'])<7,state['elapsed']
                    mpd.command('stop')
                    assert mpd.snapshot()['playback']=='stopped'
                    report['checks'].append({'case':label,'passed':True,'http_requests':server.requests})
                    print('HTTP MP3 '+label+' passed',flush=True)
                finally:
                    server.close()
            report['passed'] = True
        finally:
            subprocess.run([args.engine,'rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if args.report:
                args.report.parent.mkdir(parents=True,exist_ok=True)
                args.report.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    main()
