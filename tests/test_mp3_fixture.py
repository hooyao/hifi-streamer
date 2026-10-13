"""Validate bounded MPEG fixture structure and HTTP byte-range semantics."""
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch
from http_mp3_fixture import LargeMP3, MP3Server, silent_mp3
from mpd_mp3_ci import wait_range_seek


class Tests(unittest.TestCase):
    def test_forward_seek_may_advance_on_existing_http_stream(self):
        server,mpd = Mock(),Mock()
        server.requests = []
        mpd.snapshot.return_value = {'playback':'playing','elapsed':1000.3,'format':'44100:16:2'}
        self.assertEqual(wait_range_seek(mpd,server,1000,0,require_range=False),[])

    def test_seek_waits_for_delayed_range_and_actual_advancement(self):
        server, mpd = Mock(), Mock()
        server.requests = [{'start':100,'range':True}]
        observations = iter((1000,1000,1000.3))
        def snapshot():
            elapsed = next(observations)
            if elapsed==1000.3:
                server.requests.append({'start':20000000,'range':True})
            return {'playback':'playing','elapsed':elapsed,'format':'44100:16:2'}
        mpd.snapshot.side_effect = snapshot
        with patch('mpd_mp3_ci.time.sleep') as sleep:
            result = wait_range_seek(mpd,server,1000,1)
        self.assertEqual(result,[{'start':20000000,'range':True}])
        self.assertEqual(sleep.call_count,2)

    def test_seek_cannot_pass_without_new_range_or_playback_advancement(self):
        for requests,elapsed in (([],1000.5),([{'start':1,'range':True}],1000)):
            with self.subTest(requests=requests,elapsed=elapsed):
                server,mpd = Mock(),Mock()
                server.requests = requests
                mpd.snapshot.return_value = {'playback':'playing','elapsed':elapsed,'format':'44100:16:2'}
                with patch('mpd_mp3_ci.time.monotonic',side_effect=[0,.1,.2,.4]), \
                     patch('mpd_mp3_ci.time.sleep'):
                    with self.assertRaisesRegex(AssertionError,'did not advance with a new nonzero HTTP Range'):
                        wait_range_seek(mpd,server,1000,0,timeout=.3)

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
