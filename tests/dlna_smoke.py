"""Run on the renderer host: SSDP + SOAP + generated HTTP audio + USB format."""
import argparse
import functools
import io
import http.server
import json
import re
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import wave
import xml.etree.ElementTree as ET
from http_mp3_fixture import silent_mp3
from pathlib import Path
from xml.sax.saxutils import escape

NS = {'d':'urn:schemas-upnp-org:device-1-0'}
AV = 'urn:schemas-upnp-org:service:AVTransport:1'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def discover(name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto(b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n', ('239.255.255.250', 1900))
    deadline = time.monotonic() + 5
    locations = set()
    while time.monotonic() < deadline:
        try:
            response = sock.recv(8192).decode()
            for line in response.splitlines():
                if line.lower().startswith('location:'):
                    locations.add(line.partition(':')[2].strip())
        except socket.timeout:
            pass
    sock.close()
    for location in sorted(locations):
        try:
            with HTTP.open(location, timeout=5) as response:
                root = ET.fromstring(response.read(65536))
        except (OSError, ValueError, ET.ParseError):
            # A stale advertisement must not hide another reachable renderer.
            continue
        friendly = root.find('.//d:friendlyName', NS)
        if friendly is None or not friendly.text.startswith(name):
            continue
        for service in root.findall('.//d:service', NS):
            if service.find('d:serviceType', NS).text == AV:
                return urllib.parse.urljoin(location, service.find('d:controlURL', NS).text)
    raise RuntimeError('renderer not discovered')


def wait_discover(name, timeout=30):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        try:
            return discover(name)
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError('renderer did not become discoverable within startup deadline')


def soap(url, action, **args):
    fields = ''.join(f'<{key}>{escape(str(value))}</{key}>' for key, value in {'InstanceID':0, **args}.items())
    body = f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:{action} xmlns:u="{AV}">{fields}</u:{action}></s:Body></s:Envelope>'
    request = urllib.request.Request(url, body.encode(), {'Content-Type':'text/xml; charset="utf-8"','SOAPAction':f'"{AV}#{action}"'})
    return ET.fromstring(HTTP.open(request, timeout=5).read())


def field(response, name):
    return next(e.text for e in response.iter() if e.tag.split('}')[-1] == name)


def wait_state(control, state):
    for _ in range(30):
        if field(soap(control, 'GetTransportInfo'), 'CurrentTransportState') == state:
            return
        time.sleep(.2)
    raise AssertionError(f'transport state did not become {state}')


def sample(path, rate, seconds=20):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        # Quiet square wave, short automated tests; listening verification is separate.
        frame = b''.join(struct.pack('<hh', 128 if (i // 100) % 2 else -128, 128 if (i // 100) % 2 else -128) for i in range(rate))
        for _ in range(seconds):
            stream.writeframesraw(frame)


def usb_rate(card, expected, timeout=6):
    path = Path(f'/proc/asound/card{card}/stream0')
    for _ in range(int(timeout/.2)):
        text = path.read_text()
        measured = re.search(r'Momentary freq = (\d+) Hz', text)
        if 'Status: Running' in text and measured and abs(int(measured[1])-expected) <= max(2, expected * .001):
            return text
        if 'Status: Running' in text and f'Rate: {expected}' in text:
            return text
        time.sleep(.2)
    raise AssertionError('USB output did not report expected sample rate: ' + text[:400])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='HiFi Streamer')
    parser.add_argument('--card', type=int, required=True)
    parser.add_argument('--report', type=Path, default=Path('dlna-report.json'))
    parser.add_argument('--dsd', action='store_true')
    args = parser.parse_args()
    control = wait_discover(args.name)
    checks = []
    checks.append({'check':'SSDP discovery','passed':True})
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError):
                pass
        def send_head(self):
            path = Path(self.translate_path(self.path))
            if not path.is_file():
                self.send_error(404)
                return None
            content = path.read_bytes()
            size = len(content)
            match = re.fullmatch(r'bytes=(\d+)-(\d*)', self.headers.get('Range', ''))
            start, end = (int(match[1]), int(match[2]) if match[2] else size-1) if match else (0,size-1)
            if start >= size or end < start:
                self.send_error(416)
                return None
            end = min(end,size-1)
            self.send_response(206 if match else 200)
            self.send_header('Content-Type',self.guess_type(str(path)))
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Content-Length',str(end-start+1))
            if match:
                self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            return io.BytesIO(content[start:end+1])
    with tempfile.TemporaryDirectory() as directory:
        server = http.server.ThreadingHTTPServer(('0.0.0.0',0), functools.partial(Quiet, directory=directory))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        route = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        route.connect((urllib.parse.urlparse(control).hostname, 49152))
        host = route.getsockname()[0]
        route.close()
        try:
            for rate in (44100,48000,96000):
                wav = Path(directory) / f'{rate}.wav'
                sample(wav, rate)
                formats = [wav]
                flac = wav.with_suffix('.flac')
                subprocess.run(['flac','--silent','--force',str(wav),'-o',str(flac)],check=True)
                formats.append(flac)
                if rate in (44100,48000):
                    mp3 = wav.with_suffix('.mp3')
                    mp3.write_bytes(silent_mp3(rate=rate,id3_bytes=16384))
                    formats.append(mp3)
                for path in formats:
                    uri = f'http://{host}:{server.server_port}/{path.name}'
                    soap(control,'Stop')
                    soap(control,'SetAVTransportURI', CurrentURI=uri,CurrentURIMetaData='')
                    soap(control,'Play',Speed=1)
                    wait_state(control,'PLAYING')
                    stream = usb_rate(args.card, rate)
                    soap(control,'Pause')
                    wait_state(control,'PAUSED_PLAYBACK')
                    soap(control,'Seek',Unit='REL_TIME',Target='00:00:05')
                    soap(control,'Play',Speed=1)
                    wait_state(control,'PLAYING')
                    position = field(soap(control,'GetPositionInfo'),'RelTime')
                    assert position >= '00:00:05', position
                    soap(control,'Stop')
                    wait_state(control,'STOPPED')
                    checks.append({'check':f'{rate} {path.suffix} play/pause/seek/stop','passed':True,'position':position,'usb_stream':stream})
            # Standard AVTransport next URI transition and repeated Play.
            first = f'http://{host}:{server.server_port}/44100.wav'
            second = f'http://{host}:{server.server_port}/48000.wav'
            soap(control,'SetAVTransportURI',CurrentURI=first,CurrentURIMetaData='')
            soap(control,'SetNextAVTransportURI',NextURI=second,NextURIMetaData='')
            soap(control,'Play',Speed=1)
            soap(control,'Play',Speed=1)
            soap(control,'Next')
            wait_state(control,'PLAYING')
            usb_rate(args.card,48000)
            checks.append({'check':'next URI and repeated play','passed':True})
            soap(control,'Stop')
            if args.dsd:
                path = Path(directory)/'silence.dsf'
                # DSD64 two-channel 10s silence pattern, DSF planar 4096-byte blocks.
                samples = 2822400*10
                blocks = (samples//8+4095)//4096
                payload = (b'\x69'*4096*2)*blocks
                fmt = b'fmt '+struct.pack('<QIIIIIIQII',52,1,0,2,2,2822400,1,samples,4096,0)
                data = b'data'+struct.pack('<Q',12+len(payload))+payload
                path.write_bytes(b'DSD '+struct.pack('<QQQ',28,28+len(fmt)+len(data),0)+fmt+data)
                soap(control,'SetAVTransportURI',CurrentURI=f'http://{host}:{server.server_port}/silence.dsf',CurrentURIMetaData='')
                soap(control,'Play',Speed=1)
                wait_state(control,'PLAYING')
                stream = usb_rate(args.card,176400)
                checks.append({'check':'DSD64 DoP transport','passed':True,'usb_stream':stream})
                soap(control,'Stop')
            args.report.write_text(json.dumps({'checks':checks},indent=2))
            print(json.dumps({'passed':len(checks),'report':str(args.report)}))
        finally:
            try:
                soap(control,'Stop')
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    main()
