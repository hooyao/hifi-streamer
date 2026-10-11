import copy
import json
import os
import secrets
from pathlib import Path

DEFAULT = {'version': 1, 'dac': None, 'mode': 'auto', 'priority': 'dlna',
           'sources': {'dlna': {'enabled': True, 'name': 'HiFi Streamer'},
                       'spotify': {'enabled': False, 'name': 'HiFi Streamer Spotify'}}}


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


class Config:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'config.json'
        self.data = json.loads(self.path.read_text()) if self.path.exists() else copy.deepcopy(DEFAULT)
        self.auth = self.directory / 'admin.json'
        if not self.path.exists():
            atomic_json(self.path, self.data)
        if not self.auth.exists():
            atomic_json(self.auth, {'password': secrets.token_urlsafe(24)})

    def password(self):
        return json.loads(self.auth.read_text())['password']

    def has_key(self):
        return (self.directory / 'spotify-key').exists()

    def reload(self):
        """Observe configuration changed by the installer or another control process."""
        self.data = json.loads(self.path.read_text())

    def update(self, changes, devices):
        if not isinstance(changes, dict) or not isinstance(changes.get('sources', {}), dict):
            raise ValueError('configuration must be an object')
        if set(changes) - {'dac', 'mode', 'priority', 'sources', 'spotify_key'}:
            raise ValueError('unknown configuration field')
        data = copy.deepcopy(self.data)
        for key in ('dac', 'mode', 'priority'):
            if key in changes:
                data[key] = changes[key]
        if data['dac'] is not None and data['dac'] not in {d['id'] for d in devices}:
            raise ValueError('DAC is not connected')
        if data['mode'] not in ('auto', 'dlna', 'spotify') or data['priority'] not in ('dlna', 'spotify'):
            raise ValueError('invalid source policy')
        for module, fields in changes.get('sources', {}).items():
            if not isinstance(fields, dict):
                raise ValueError('source configuration must be an object')
            allowed = {'enabled', 'name', 'initial_volume'} if module == 'spotify' else {'enabled','name'}
            if module not in data['sources'] or set(fields) - allowed:
                raise ValueError('unknown source configuration')
            if 'initial_volume' in fields and (type(fields['initial_volume']) is not int or not 0 <= fields['initial_volume'] <= 100):
                raise ValueError('initial volume must be an integer from 0 to 100')
            if 'enabled' in fields and type(fields['enabled']) is not bool:
                raise ValueError('enabled must be boolean')
            if module == 'dlna' and fields.get('enabled') is False:
                raise ValueError('DLNA is required')
            if 'name' in fields and (not isinstance(fields['name'], str) or not 1 <= len(fields['name']) <= 64 or any(ord(c) < 32 for c in fields['name']) or fields['name'] != fields['name'].strip()):
                raise ValueError('invalid display name')
            data['sources'][module].update(fields)
        secret = changes.get('spotify_key')
        if secret is not None and (not isinstance(secret, str) or not 1 <= len(secret) <= 4096 or '\n' in secret):
            raise ValueError('invalid Spotify key')
        if secret is not None:
            path = self.directory / 'spotify-key'
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(secret)
        atomic_json(self.path, data)
        self.data = data
        return self.public()

    def public(self):
        return {**copy.deepcopy(self.data), 'spotify_key_set': self.has_key()}
