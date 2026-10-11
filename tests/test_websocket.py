import base64
import hashlib
import json
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.websocket import Client, exact


class Tests(unittest.TestCase):
    def test_handshake_mask_and_fragmented_event(self):
        server = socket.socket()
        server.bind(('127.0.0.1',0))
        server.listen()
        errors = []
        def serve():
            try:
                sock,_ = server.accept()
                with sock:
                    request = b''
                    while not request.endswith(b'\r\n\r\n'):
                        request += exact(sock,1)
                    key = next(line.split(b': ')[1] for line in request.splitlines() if line.startswith(b'Sec-WebSocket-Key:'))
                    accept = base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                    sock.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+b'\r\n\r\n')
                    first,second = exact(sock,2)
                    self.assertTrue(second & 128)
                    mask = exact(sock,4)
                    payload = exact(sock,second&127)
                    decoded = bytes(b^mask[i%4] for i,b in enumerate(payload))
                    self.assertEqual(json.loads(decoded),{'type':'command','command':'get_auth_state'})
                    payload = b'{"type":"auth_state","logged_in":false}'
                    sock.sendall(bytes([1,10])+payload[:10]+bytes([128,len(payload)-10])+payload[10:])
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=serve)
        thread.start()
        try:
            client = Client(port=server.getsockname()[1])
            client.send({'type':'command','command':'get_auth_state'})
            self.assertEqual(client.receive()['type'],'auth_state')
            client.close()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors,[])
        finally:
            server.close()
