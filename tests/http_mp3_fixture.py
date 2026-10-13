"""Generated silent MPEG-1 Layer III frames and bounded HTTP transport fixtures."""
import http.server
import math
import re
import threading


def silent_mp3(seconds=20, rate=44100, vbr=False, id3_bytes=0):
    rates = {44100:0, 48000:1, 32000:2}
    if rate not in rates or not 1 <= seconds <= 120 or not 0 <= id3_bytes <= 65536:
        raise ValueError('invalid bounded MP3 fixture')
    frames = []
    # Empty granules have zero part2_3_length/big_values and decode to silence.
    for index in range(math.ceil(seconds*rate/1152)):
        bitrate_index, bitrate = ((5,64) if index%2 else (11,192)) if vbr else (9,128)
        header = 0xfffb0000 | bitrate_index << 12 | rates[rate] << 10
        length = 144000*bitrate//rate
        frames.append(header.to_bytes(4,'big') + bytes(length-4))
    prefix = b''
    if id3_bytes:
        size = bytes((id3_bytes >> shift) & 127 for shift in (21,14,7,0))
        prefix = b'ID3\x03\x00\x00' + size + bytes(id3_bytes)
    return prefix + b''.join(frames)


class LargeMP3:
    """Expose a known-length CBR stream larger than MPD's 16 MiB file cache."""
    def __init__(self):
        self.frame = (0xfffb9064).to_bytes(4,'big') + bytes(417-4)
        self.frames = 50000

    def __len__(self):
        return len(self.frame)*self.frames

    def __getitem__(self, key):
        start,end,step = key.indices(len(self))
        if step != 1 or end-start > 65536:
            raise ValueError('large MP3 reads must be bounded contiguous slices')
        size = max(0,end-start)
        offset = start % len(self.frame)
        repeats = math.ceil((offset+size)/len(self.frame))
        return (self.frame*repeats)[offset:offset+size]


class MP3Server:
    def __init__(self, data, seekable=True, extension=True):
        self.requests = []
        requests = self.requests
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                match = re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range','')) if seekable else None
                start,end = (int(match[1]),int(match[2]) if match[2] else len(data)-1) if match else (0,len(data)-1)
                end = min(end,len(data)-1)
                if start>=len(data) or end<start:
                    self.send_error(416)
                    return
                requests.append({'start':start,'range':bool(match)})
                del requests[:-128]
                self.send_response(206 if match else 200)
                self.send_header('Content-Type','audio/mpeg')
                if seekable:
                    self.send_header('Accept-Ranges','bytes')
                    self.send_header('Content-Length',str(end-start+1))
                    if match:
                        self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                self.end_headers()
                try:
                    for position in range(start,end+1,16384):
                        self.wfile.write(data[position:min(position+16384,end+1)])
                except (BrokenPipeError,ConnectionResetError):
                    pass
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.url = f'http://127.0.0.1:{self.server.server_port}/sample'+('.mp3' if extension else '')
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
