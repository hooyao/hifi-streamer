"""Verify virtual WAV headers and HTTP byte-range semantics."""
import struct
import unittest
import urllib.request
from http_audio_fixture import VirtualWavServer


class FixtureTests(unittest.TestCase):
    def test_virtual_header_and_range(self):
        fixture=VirtualWavServer(seconds=7200)
        http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            request=urllib.request.Request(fixture.url,headers={'Range':'bytes=0-43'})
            with http.open(request,timeout=2) as response:
                header=response.read()
                self.assertEqual(response.status,206)
                self.assertEqual(len(header),44)
                self.assertEqual(header[:4],b'RIFF')
                self.assertEqual(struct.unpack('<I',header[40:44])[0],44100*4*7200)
            request=urllib.request.Request(fixture.url,headers={'Range':'bytes=44-59'})
            with http.open(request,timeout=2) as response:
                self.assertEqual(response.read(),bytes(16))
                self.assertEqual(response.headers['Content-Length'],'16')
        finally:
            fixture.close()
