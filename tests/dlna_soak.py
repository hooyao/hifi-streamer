"""Continuous DLNA silence stream, generated on demand without a large fixture."""
import argparse
import http.server
import json
import re
import socket
import struct
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path
from dlna_smoke import discover, soap, field, wait_state, usb_rate

parser = argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,default=7200)
parser.add_argument('--media-seconds',type=int,default=None)
parser.add_argument('--card',type=int,required=True)
parser.add_argument('--report',type=Path,required=True)
args = parser.parse_args()
if not 60 <= args.seconds <= 7200:
    parser.error('duration must be 60..7200 seconds')
rate = 44100
media_seconds = args.media_seconds if args.media_seconds is not None else args.seconds+60
if not args.seconds <= media_seconds <= 7200+60:
    parser.error('media duration must cover the test and stay within 7260 seconds')
payload = rate*4*media_seconds
header = b'RIFF'+struct.pack('<I',36+payload)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,rate,rate*4,4,16)+b'data'+struct.pack('<I',payload)
total = len(header)+payload

class Stream(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def do_GET(self):
        match = re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
        start,end = (int(match[1]),int(match[2]) if match[2] else total-1) if match else (0,total-1)
        end = min(end,total-1)
        if start>=total or end<start:
            self.send_error(416)
            return
        self.send_response(206 if match else 200)
        self.send_header('Content-Type','audio/wav')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Length',str(end-start+1))
        if match:
            self.send_header('Content-Range',f'bytes {start}-{end}/{total}')
        self.end_headers()
        try:
            if start<len(header):
                part=header[start:min(end+1,len(header))]
                self.wfile.write(part)
                start+=len(part)
            zero=bytes(65536)
            while start<=end:
                count=min(len(zero),end-start+1)
                self.wfile.write(zero[:count])
                start+=count
        except (BrokenPipeError,ConnectionResetError):
            pass

server=http.server.ThreadingHTTPServer(('0.0.0.0',0),Stream)
threading.Thread(target=server.serve_forever,daemon=True).start()
report={'started':time.time(),'duration_seconds':args.seconds,'media_seconds':media_seconds,'samples':[],'status':'running'}
args.report.parent.mkdir(parents=True,exist_ok=True)
def save():
    temp=args.report.with_suffix('.tmp')
    temp.write_text(json.dumps(report,indent=2))
    temp.replace(args.report)
control=discover('HiFi Streamer')
route=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
route.connect((urllib.parse.urlparse(control).hostname,1900))
host=route.getsockname()[0]
route.close()
try:
    soap(control,'Stop')
    uri=f'http://{host}:{server.server_port}/soak.wav'
    soap(control,'SetAVTransportURI',CurrentURI=uri,CurrentURIMetaData='')
    soap(control,'Play',Speed=1)
    wait_state(control,'PLAYING')
    usb_rate(args.card,rate,timeout=30)
    started=time.monotonic()
    previous=-1
    while time.monotonic()-started<args.seconds:
        state=field(soap(control,'GetTransportInfo'),'CurrentTransportState')
        assert state=='PLAYING',state
        usb_rate(args.card,rate)
        info=soap(control,'GetPositionInfo')
        assert field(info,'TrackURI')==uri,'another controller replaced the soak URI'
        position=field(info,'RelTime')
        parts=list(map(int,position.split(':')))
        elapsed=parts[0]*3600+parts[1]*60+parts[2]
        assert elapsed>=previous,'position moved backwards'
        previous=elapsed
        memory=Path('/proc/meminfo').read_text()
        available=int(re.search(r'MemAvailable:\s+(\d+)',memory)[1])
        row={'wall_seconds':round(time.monotonic()-started),'position':position,'available_kib':available}
        pid=int(subprocess.check_output(['podman','inspect','hifi-mpd','--format','{{.State.Pid}}'],text=True))
        status=Path(f'/proc/{pid}/status').read_text()
        row['mpd_pid']=pid
        for key in ('VmRSS','RssAnon','RssFile','RssShmem'):
            match=re.search(r'^'+key+r':\s+(\d+)',status,re.M)
            row[key+'_kib']=int(match[1]) if match else 0
        temperature=Path('/sys/class/thermal/thermal_zone0/temp')
        if temperature.exists():
            row['temperature_millic']=int(temperature.read_text())
        if len(report['samples'])%4==0:
            row['containers']=subprocess.check_output(['podman','stats','--no-stream','--format','{{.Name}} {{.MemUsage}}'],text=True,timeout=10).strip()
        report['samples'].append(row)
        save()
        time.sleep(min(15,max(0,args.seconds-(time.monotonic()-started))))
    report['status']='passed'
    report['elapsed_seconds']=round(time.monotonic()-started)
except Exception as error:
    report['status']='failed'
    report['error']=str(error)
    raise
finally:
    report['finished']=time.time()
    save()
    soap(control,'Stop')
    server.shutdown()
    server.server_close()
