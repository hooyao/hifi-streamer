"""Isolated MPD memory comparison with identical large WAV content."""
import argparse
import http.server
import json
import re
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.runtime import Runtime

parser=argparse.ArgumentParser()
parser.add_argument('--case',choices=['local','http','stream'],required=True)
parser.add_argument('--seconds',type=int,default=180)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
runtime=Runtime(repo,Path.home()/'.config/hifi-streamer')
rate=44100
payload=rate*4*7200
header=b'RIFF'+struct.pack('<I',36+payload)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,rate,rate*4,4,16)+b'data'+struct.pack('<I',payload)
total=len(header)+payload

class Stream(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def do_GET(self):
        match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
        start,end=(int(match[1]),int(match[2]) if match[2] else total-1) if match else (0,total-1)
        end=min(end,total-1)
        self.send_response(206 if match else 200)
        self.send_header('Content-Type','audio/wav')
        if args.case!='stream':
            self.send_header('Content-Length',str(end-start+1))
            self.send_header('Accept-Ranges','bytes')
            if match:
                self.send_header('Content-Range',f'bytes {start}-{end}/{total}')
        self.end_headers()
        try:
            if start<len(header):
                content=header[start:min(end+1,len(header))]
                self.wfile.write(content)
                start+=len(content)
            zeros=bytes(65536)
            while start<=end:
                count=min(65536,end-start+1)
                self.wfile.write(zeros[:count])
                start+=count
        except (BrokenPipeError,ConnectionResetError):
            pass

server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Stream)
threading.Thread(target=server.serve_forever,daemon=True).start()
fixture=Path.home()/'.local/share/hifi-streamer/mpd/memory-probe.wav'
if args.case=='local':
    with fixture.open('wb') as stream:
        stream.write(header)
        stream.truncate(total)
    uri='memory-probe.wav'
else:
    uri=f'http://127.0.0.1:{server.server_port}/memory.wav'
report={'case':args.case,'duration_seconds':args.seconds,'media_bytes':total,'samples':[]}
mpd=runtime.adapters['dlna']
try:
    subprocess.run(['systemctl','--user','stop','hifi-agent','hifi-upmpdcli'],check=True)
    runtime.adapters['spotify'].command('pause')
    mpd.command('stop')
    mpd.command('clear')
    runtime.hardware.for_direct()
    mpd.output('direct',True)
    mpd.output('standby',False)
    if args.case=='local':
        mpd.command('update')
        for _ in range(20):
            if not any(row.startswith('updating_db:') for row in mpd.command('status')):
                break
            time.sleep(.5)
    mpd.command('add "'+uri+'"')
    mpd.command('play')
    started=time.monotonic()
    while time.monotonic()-started<args.seconds:
        status=mpd.snapshot()
        assert status['playback']=='playing',status
        pid=int(subprocess.check_output(['podman','inspect','hifi-mpd','--format','{{.State.Pid}}']))
        text=Path(f'/proc/{pid}/status').read_text()
        row={'seconds':round(time.monotonic()-started),'pid':pid,'elapsed':status['elapsed']}
        for key in ('VmRSS','RssAnon','RssFile','RssShmem'):
            match=re.search(r'^'+key+r':\s+(\d+)',text,re.M)
            row[key+'_kib']=int(match[1]) if match else 0
        report['samples'].append(row)
        args.report.write_text(json.dumps(report,indent=2))
        print(json.dumps(row),flush=True)
        time.sleep(15)
    report['status']='passed'
except Exception as error:
    report['status']='failed'
    report['error']=str(error)
    raise
finally:
    try:
        mpd.command('stop')
        mpd.command('clear')
        pid=int(subprocess.check_output(['podman','inspect','hifi-mpd','--format','{{.State.Pid}}']))
        report['after_stop']=Path(f'/proc/{pid}/status').read_text()
    except (OSError,RuntimeError):
        report['cleanup_error']='MPD unavailable after playback'
    args.report.write_text(json.dumps(report,indent=2))
    fixture.unlink(missing_ok=True)
    if args.case=='local':
        try:
            mpd.command('update')
        except (OSError,RuntimeError):
            pass
    server.shutdown()
    server.server_close()
    subprocess.run(['systemctl','--user','start','hifi-upmpdcli','hifi-agent'],check=True)
