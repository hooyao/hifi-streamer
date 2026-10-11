"""Service-independent serial DAC arbitration."""
import threading
import time


class Arbiter:
    def __init__(self, adapters, hardware, cooldown=1.0):
        self.adapters, self.hardware = adapters, hardware
        self.owner = None
        self.state = 'idle'
        self.generation = 0
        self.cooldown = cooldown
        self.last_switch = 0
        self.seen = {}
        self.lock = threading.RLock()

    def request(self, source, instance, sequence, force=False):
        with self.lock:
            if source not in self.adapters:
                raise ValueError('unknown source')
            previous = self.seen.get(source)
            # Adapters supply a stable current process instance; retired events are rejected.
            if instance != self.adapters[source].instance:
                return False
            if previous and previous[0] == instance and sequence <= previous[1]:
                return False
            if self.owner == source:
                self.seen[source] = (instance, sequence)
                return True
            if not force and time.monotonic() - self.last_switch < self.cooldown:
                return False
            self.seen[source] = (instance, sequence)
            self.state = 'switching'
            self.generation += 1
            try:
                if self.owner:
                    self.adapters[self.owner].release()
                else:
                    self.hardware.silence()
                self.hardware.ensure_released()
                self.owner = None
                self.adapters[source].acquire(self.generation)
                self.owner, self.state = source, 'active'
                self.last_switch = time.monotonic()
                return True
            except Exception:
                self.owner, self.state = None, 'error'
                self.hardware.silence()
                raise

    def disconnect(self):
        with self.lock:
            self.generation += 1
            try:
                self.hardware.silence()
            finally:
                self.owner, self.state = None, 'disconnected'
