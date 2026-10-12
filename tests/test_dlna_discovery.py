"""Discovery tolerates stale responders and bounded first-start advertising delay."""
import io
import unittest
from unittest.mock import patch
import dlna_smoke


class Socket:
    def settimeout(self, timeout):
        pass
    def sendto(self, packet, destination):
        pass
    def recv(self, size):
        return b'HTTP/1.1 200 OK\r\nLOCATION: http://fixture/description.xml\r\n'
    def close(self):
        pass


class DiscoveryTests(unittest.TestCase):
    def test_malformed_location_does_not_hide_valid_renderer(self):
        sock = Socket()
        sock.recv = lambda size: (b'HTTP/1.1 200 OK\r\nLOCATION: http://[broken\r\n'
                                 b'LOCATION: http://fixture/description.xml\r\n')
        description = b'''<root xmlns="urn:schemas-upnp-org:device-1-0"><device>
            <friendlyName>HiFi Streamer</friendlyName><serviceList><service>
            <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
            <controlURL>/control</controlURL></service></serviceList></device></root>'''
        with patch.object(dlna_smoke.socket, 'socket', return_value=sock), \
             patch.object(dlna_smoke.time, 'monotonic', side_effect=[0, 1, 6]), \
             patch.object(dlna_smoke.HTTP, 'open', side_effect=[
                 ValueError('Invalid IPv6 URL'), io.BytesIO(description)]) as open_url:
            self.assertEqual(dlna_smoke.discover('HiFi Streamer'), 'http://fixture/control')
        self.assertEqual(open_url.call_count, 2)

    def test_unreachable_description_is_not_an_uncaught_network_error(self):
        with patch.object(dlna_smoke.socket, 'socket', return_value=Socket()), \
             patch.object(dlna_smoke.time, 'monotonic', side_effect=[0,1,6]), \
             patch.object(dlna_smoke.HTTP, 'open', side_effect=OSError('connection refused')), \
             self.assertRaisesRegex(RuntimeError, 'renderer not discovered'):
            dlna_smoke.discover('HiFi Streamer')

    def test_first_start_advertisement_is_retried(self):
        with patch.object(dlna_smoke, 'discover', side_effect=[RuntimeError(), 'http://fixture/control']), \
             patch.object(dlna_smoke.time, 'monotonic', side_effect=[0,1,2]), \
             patch.object(dlna_smoke.time, 'sleep'):
            self.assertEqual(dlna_smoke.wait_discover('HiFi Streamer'), 'http://fixture/control')

    def test_first_start_has_a_finite_deadline(self):
        with patch.object(dlna_smoke, 'discover', side_effect=RuntimeError()), \
             patch.object(dlna_smoke.time, 'monotonic', side_effect=[0,1,31]), \
             patch.object(dlna_smoke.time, 'sleep'), self.assertRaisesRegex(RuntimeError, 'deadline'):
            dlna_smoke.wait_discover('HiFi Streamer')
