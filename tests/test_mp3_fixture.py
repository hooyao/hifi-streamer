"""Validate bounded MPEG fixture structure and HTTP byte-range semantics."""
import unittest
import urllib.error
import urllib.request
from http_mp3_fixture import LargeMP3, MP3Server, silent_mp3


class Tests(unittest.TestCase):
    def test_large_fixture_is_generated_in_bounded_slices_and_serves_far_ranges(self):
        data = LargeMP3()
        self.assertGreater(len(data),16*1024*1024)
        self.assertLess(len(data.frame),1024)
        self.assertEqual(data[410:430],(data.frame*2)[410:430])
        self.assertEqual(data[len(data)-10:len(data)],data.frame[-10:])
        with self.assertRaises(ValueError):data[:]
        server = MP3Server(data)
        http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            start = 17*1024*1024+123
            request = urllib.request.Request(server.url,headers={'Range':f'bytes={start}-{start+999}'})
            with http.open(request,timeout=3) as response:
                self.assertEqual(response.status,206)
                self.assertEqual(response.headers['Content-Length'],'1000')
                self.assertEqual(response.headers['Content-Range'],f'bytes {start}-{start+999}/{len(data)}')
                self.assertEqual(response.read(),data[start:start+1000])
            self.assertEqual(server.requests,[{'start':start,'range':True}])
        finally:
            server.close()

    def test_frames_are_valid_layer_three_and_variable_bitrate(self):
        for vbr in (False,True):
            data = silent_mp3(seconds=1,vbr=vbr,id3_bytes=16384)
            size = 0
            for value in data[6:10]:size = (size<<7)|value
            self.assertEqual(size,16384)
            position = 10+size
            bitrates = set()
            count = 0
            while position<len(data):
                header = int.from_bytes(data[position:position+4],'big')
                self.assertEqual(header>>21,2047)
                self.assertEqual((header>>19)&3,3)
                self.assertEqual((header>>17)&3,1)
                index = (header>>12)&15
                bitrate = {5:64,9:128,11:192}[index]
                bitrates.add(bitrate)
                position += 144000*bitrate//44100
                count += 1
            self.assertEqual(position,len(data))
            self.assertGreaterEqual(count*1152,44100)
            self.assertEqual(len(bitrates),2 if vbr else 1)

    def test_http_ranges_and_extensionless_sequential_input(self):
        data = silent_mp3(seconds=1)
        http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for seekable in (True,False):
            server = MP3Server(data,seekable,extension=False)
            try:
                request = urllib.request.Request(server.url,headers={'Range':'bytes=10-25'})
                with http.open(request,timeout=3) as response:
                    self.assertEqual(response.headers['Content-Type'],'audio/mpeg')
                    self.assertEqual(response.status,206 if seekable else 200)
                    self.assertEqual(response.read(),data[10:26] if seekable else data)
                    self.assertEqual(response.headers.get('Content-Length'), '16' if seekable else None)
                if seekable:
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        http.open(urllib.request.Request(server.url,headers={'Range':'bytes=999999-'}),timeout=3)
                    self.assertEqual(error.exception.code,416)
            finally:
                server.close()

    def test_fixture_size_and_rate_are_bounded(self):
        for arguments in ({'seconds':0},{'seconds':121},{'rate':96000},{'id3_bytes':65537}):
            with self.assertRaises(ValueError):silent_mp3(**arguments)
