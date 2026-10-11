"""Serialize service mutations across deployment, updates and recovery."""
import contextlib
import fcntl
import os
from pathlib import Path


@contextlib.contextmanager
def maintenance_lock(directory, blocking=True):
    path = Path(directory) / 'maintenance.lock'
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(path, os.O_CREAT | os.O_RDWR, 0o600), 'a') as stream:
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(stream, flags)
        yield
