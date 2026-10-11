"""Reject sustained HTTP input-memory growth using synchronized null output."""
import argparse
import json
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.mpd import MPD
from http_audio_fixture import VirtualWavServer

parser=argparse.ArgumentParser()
parser.add_argument('image')
parser.add_argument('--engine',choices=['docker','podman'],default='docker')
parser.add_argument('--seconds',type=int,default=120)
args=parser.parse_args()
if args.seconds<60:
    parser.error('test requires at least60 seconds')
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0))
    port=probe.getsockname()[1]
name='hifi-memory-'+uuid.uuid4().hex[:10]
http=VirtualWavServer()
report={'image':args.image,'samples':[]}
with tempfile.TemporaryDirectory() as directory:
    config=Path(directory)/'mpd.conf'
    config.write_text(f'''music_directory "/tmp"
log_file "/dev/stdout"
bind_to_address "127.0.0.1"
port "{port}"
database {{
    plugin "simple"
    path "/tmp/database"
}}
audio_buffer_size "4096"
audio_output {{
    type "null"
    name "timed"
    sync "yes"
}}
''')
    try:
        subprocess.run([args.engine,'run','-d','--name',name,'--network=host','--memory=128m',
                        '-v',f'{config}:/etc/mpd.conf:ro',args.image],check=True,stdout=subprocess.DEVNULL)
        mpd=MPD(None,port=port)
        for _ in range(60):
            try:
                mpd.command('status')
                break
            except (OSError,RuntimeError):
                time.sleep(1)
        mpd.command('add "'+http.url+'"')
        mpd.command('play')
        started=time.monotonic()
        while time.monotonic()-started<args.seconds:
            snapshot=mpd.snapshot()
            assert snapshot['playback']=='playing',snapshot
            status=subprocess.check_output([args.engine,'exec',name,'cat','/proc/1/status'],text=True)
            anon=int(re.search(r'^RssAnon:\s+(\d+)',status,re.M)[1])
            report['samples'].append({'seconds':round(time.monotonic()-started),'anon_kib':anon})
            time.sleep(10)
        steady=[s['anon_kib'] for s in report['samples'] if s['seconds']>=30]
        assert steady and max(steady)<32*1024,report
        assert max(steady)-min(steady)<3*1024,report
        report['status']='passed'
        print(json.dumps(report))
    except Exception:
        subprocess.run([args.engine,'logs','--tail','30',name],check=False)
        raise
    finally:
        subprocess.run([args.engine,'rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        http.close()
