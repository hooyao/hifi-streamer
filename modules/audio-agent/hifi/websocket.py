"""Small RFC6455 client for the loopback Soloist control channel."""
import base64
import hashlib
import json
import os
import socket
import struct


def exact(sock, count):
    result = b''
    while len(result) < count:
        chunk = sock.recv(count - len(result))
        if not chunk:
            raise RuntimeError('WebSocket disconnected')
        result += chunk
    return result


class Client:
    def __init__(self, host='127.0.0.1', port=24879):
        self.sock = socket.create_connection((host, port), timeout=2)
        self.sock.settimeout(2)
        key = base64.b64encode(os.urandom(16)).decode()
        request = f'GET / HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
        self.sock.sendall(request.encode())
        response = b''
        while not response.endswith(b'\r\n\r\n') and len(response) < 8192:
            response += exact(self.sock, 1)
        accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        if not response.startswith(b'HTTP/1.1 101') or accept not in response:
            self.close()
            raise RuntimeError('WebSocket upgrade failed')

    def send(self, message, opcode=1):
        if isinstance(message, dict):
            message = json.dumps(message)
        data = message.encode() if isinstance(message, str) else message
        mask = os.urandom(4)
        size = len(data)
        header = bytes([0x80 | opcode, 0x80 | size]) if size < 126 else bytes([0x80 | opcode, 0xfe]) + struct.pack('!H', size)
        self.sock.sendall(header + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data)))

    def receive(self):
        fragments = b''
        while True:
            first, second = exact(self.sock, 2)
            size = second & 127
            if size == 126:
                size = struct.unpack('!H', exact(self.sock, 2))[0]
            elif size == 127:
                size = struct.unpack('!Q', exact(self.sock, 8))[0]
            if size > 65536:
                raise RuntimeError('WebSocket frame too large')
            mask = exact(self.sock, 4) if second & 128 else None
            data = exact(self.sock, size)
            if mask:
                data = bytes(c ^ mask[i % 4] for i, c in enumerate(data))
            opcode = first & 15
            if opcode == 8:
                raise RuntimeError('WebSocket closed')
            if opcode == 9:
                self.send(data, 10)
                continue
            if opcode == 10:
                continue
            fragments += data
            if len(fragments) > 65536:
                raise RuntimeError('WebSocket message too large')
            if first & 128:
                return json.loads(fragments)

    def close(self):
        self.sock.close()
