import logging
import logging.handlers
import tempfile
import time
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.maintenance import trim_cache, transaction, validate_candidate


class Tests(unittest.TestCase):
    def test_invalid_release_metadata(self):
        release={'size':1,'data_version':1}
        for change in ({'size':-1},{'size':True},{'size':float('nan')},{'expires_at':float('nan')},{'expires_at':True},{'data_version':True}):
            with self.assertRaises(ValueError):
                validate_candidate({**release,**change})
    def test_rotation_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            log = logging.handlers.RotatingFileHandler(path/'log',maxBytes=1024,backupCount=2)
            logger = logging.getLogger('pressure-test')
            logger.setLevel(logging.INFO)
            logger.addHandler(log)
            for _ in range(1000):
                logger.info('x' * 100)
            log.close()
            logger.removeHandler(log)
            self.assertLessEqual(sum(f.stat().st_size for f in path.glob('log*')),3072)
            cache = path/'cache'
            cache.mkdir()
            for i in range(5):
                (cache/str(i)).write_bytes(b'x'*500)
            self.assertLessEqual(trim_cache(cache,1024),1024)

    def test_bad_candidate_rollback(self):
        current = {'image':'old','size':1,'data_version':1}
        candidate = {'image':'bad','size':1,'data_version':1}
        activated = []
        def healthy():
            return activated[-1]['image'] == 'old'
        with self.assertRaises(RuntimeError):
            transaction(current,candidate,True,10**10,activated.append,healthy,lambda *a:None)
        self.assertEqual([x['image'] for x in activated],['bad','old'])

    def test_preflight_rejects_disk_and_expiry(self):
        current = {'image':'old','size':1,'data_version':1}
        for free, candidate in ((0,current),(10**10,{**current,'expires_at':time.time()-1})):
            activated = []
            with self.assertRaises(ValueError):
                transaction(current,candidate,True,free,activated.append,lambda:True,lambda *a:None)
            self.assertEqual(activated,[])

    def test_expired_rollback_and_metadata_failure(self):
        current = {'image':'old','size':1,'data_version':1}
        candidate = {'image':'new','size':1,'data_version':1}
        activated = []
        with self.assertRaises(ValueError):
            transaction({**current,'expires_at':time.time()-1},candidate,True,10**10,activated.append,lambda:True,lambda *a:None)
        self.assertEqual(activated,[])
        def fail_commit(*args):
            raise OSError('metadata storage failure')
        with self.assertRaises(OSError):
            transaction(current,candidate,True,10**10,activated.append,lambda:True,fail_commit)
        self.assertEqual([r['image'] for r in activated],['new','old'])
