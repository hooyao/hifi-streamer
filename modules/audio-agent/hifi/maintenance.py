import shutil
import time
import math
from pathlib import Path


def trim_cache(directory, budget=128 * 1048576):
    directory = Path(directory)
    files = []
    for path in directory.rglob('*'):
        if path.is_file() and not path.is_symlink():
            stat = path.stat()
            files.append((stat.st_mtime, stat.st_size, path))
    total = sum(size for _, size, _ in files)
    for _, size, path in sorted(files):
        if total <= budget:
            break
        path.unlink(missing_ok=True)
        total -= size
    return total


def validate_candidate(candidate, now=None):
    now = time.time() if now is None else now
    if type(candidate.get('data_version')) is not int or candidate['data_version'] != 1:
        raise ValueError('incompatible data version')
    if type(candidate.get('size')) is not int or not 0 <= candidate['size'] <= 512*1048576:
        raise ValueError('invalid release size')
    if 'expires_at' in candidate:
        expires = candidate['expires_at']
        if type(expires) not in (int,float) or not math.isfinite(expires):
            raise ValueError('invalid expiry timestamp')
        if expires <= now:
            raise ValueError('expired binary')


def transaction(current, candidate, idle, free, activate, healthy, commit):
    if not idle:
        raise ValueError('update requires idle output')
    if free < candidate['size'] * 2 + 256 * 1048576:
        raise ValueError('insufficient disk space')
    validate_candidate(candidate)
    # Fail closed before replacing a working version if no compatible rollback exists.
    validate_candidate(current)
    try:
        activate(candidate)
        if not healthy():
            raise RuntimeError('candidate failed health check')
        commit(candidate, current)
    except Exception:
        activate(current)
        if not healthy():
            raise RuntimeError('rollback failed health check')
        raise
