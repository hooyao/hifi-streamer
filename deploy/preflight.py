#!/usr/bin/env python3
"""Check dedicated rootless-account prerequisites without changing allocations."""
import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path


def check_ranges(path, account, uid):
    allocations = []
    try:
        rows = Path(path).read_text().splitlines()
    except OSError as error:
        raise ValueError(f'{path} is unavailable; configure unique subordinate ID ranges') from error
    for number, row in enumerate(rows, 1):
        if not row.strip() or row.lstrip().startswith('#'):
            continue
        try:
            owner, start, count = row.split(':')
            start, count = int(start), int(count)
            if start < 1 or count < 1:
                raise ValueError()
        except ValueError as error:
            raise ValueError(f'{path} line {number} is invalid; repair subordinate allocations') from error
        allocations.append((owner, start, start+count))
    selected = [entry for entry in allocations if entry[0] in (account, str(uid))]
    if not any(end-start >= 65536 for _, start, end in selected):
        raise ValueError(f'{path}: current account needs a unique contiguous range of at least 65536 IDs; '
                         'check mappings after account creation or rename')
    for own in selected:
        for other in allocations:
            if other is own:
                continue
            if max(own[1], other[1]) < min(own[2], other[2]):
                raise ValueError(f'{path}: subordinate ranges overlap; assign unused ranges before installation')


def check():
    if os.getuid() == 0:
        raise ValueError('run install.sh as the dedicated service account; use root only for host-setup.sh')
    if sys.version_info < (3, 11):
        raise ValueError('Python 3.11 or later is required')
    missing = [name for name in ('podman','crun','newuidmap','newgidmap','pactl','pw-cli','systemctl','loginctl')
               if not shutil.which(name)]
    if missing:
        raise ValueError('missing dependencies: '+', '.join(missing)+'; run sudo sh deploy/host-setup.sh')
    account = pwd.getpwuid(os.getuid()).pw_name
    for path in ('/etc/subuid', '/etc/subgid'):
        check_ranges(path, account, os.getuid())
    for command, message, expected in (
        (['systemctl','--user','show','default.target','-p','LoadState'],
         'user systemd is unavailable; log in through SSH as the service account and enable linger', None),
        (['podman','info','--format','{{.Host.Security.Rootless}}'],
         'rootless Podman initialization failed; verify subordinate IDs, crun, current login groups '
         'and that the selected engine is rootless', 'true')):
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE if expected else subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError(message) from error
        if result.returncode or expected and result.stdout.strip() != expected:
            raise ValueError(message)


if __name__ == '__main__':
    try:
        check()
    except ValueError as error:
        print(f'Preflight failed: {error}', file=sys.stderr)
        raise SystemExit(1)
    print('Rootless account preflight passed')
