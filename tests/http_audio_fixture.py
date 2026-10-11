"""Bounded-memory HTTP WAV fixtures with optional seek support."""
import http.server
import re
import struct
import threading


class VirtualWavServer:
    def __init__(self, seconds=7200, rate=44100, seekable=True):
        payload=rate*4*seconds
        if payload+36>=2**32:
            raise ValueError('fixture exceeds RIFF size limit')
        header=b'RIFF'+struct.pack('<I',36+payload)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,2,rate,rate*4,4,16)+b'data'+struct.pack('<I',payload)
        total=len(header)+payload

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range','')) if seekable else None
                start,end=(int(match[1]),int(match[2]) if match[2] else total-1) if match else (0,total-1)
                end=min(end,total-1)
                if start>=total or end<start:
                    self.send_error(416)
                    return
                self.send_response(206 if match else 200)
                self.send_header('Content-Type','audio/wav')
                if seekable:
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

        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.url=f'http://127.0.0.1:{self.server.server_port}/memory.wav'
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
