#!/usr/bin/env python3
"""Generate bounded rootless services from the selected device and module config."""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'modules/audio-agent'))
from hifi.config import Config, atomic_json
from hifi.devices import discover
from hifi.service_lock import maintenance_lock

HOME = Path.home()
CONFIG = HOME / '.config/hifi-streamer'
DATA = HOME / '.local/share/hifi-streamer'
UNITS = HOME / '.config/systemd/user'
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))


def run(*args):
    subprocess.run(args, check=True)


def quote(value):
    # systemd unit strings are not shell commands, but percent has specifier semantics.
    value = str(value)
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('invalid unit argument')
    return '"' + value.replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"') + '"'


def unit(name, args, memory, after=''):
    text = f'''[Unit]
Description=HiFi Streamer {name}
After=network-online.target {after}
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
ExecStartPre=-/usr/bin/podman rm -f hifi-{name}
ExecStart=/usr/bin/podman run --name hifi-{name} --pull=never --network=host --runtime=crun --userns=keep-id --user {os.getuid()}:{os.getgid()} --group-add keep-groups --cap-drop=ALL --security-opt=no-new-privileges --log-driver=k8s-file --log-opt=max-size=2097152 --memory={memory}m --pids-limit=64 --read-only --tmpfs=/tmp:rw,size=16m --stop-timeout=10 {' '.join(quote(a) for a in args)}
ExecStop=/usr/bin/podman stop --ignore -t 10 hifi-{name}
Restart=on-failure
RestartSec=5
RestartPreventExitStatus=10
TimeoutStartSec=60
TimeoutStopSec=30
StandardOutput=null
StandardError=journal
LogRateLimitIntervalSec=30s
LogRateLimitBurst=20

[Install]
WantedBy=default.target
'''
    (UNITS / f'hifi-{name}.service').write_text(text)


def images():
    path = CONFIG / 'images.json'
    if not path.exists():
        raise RuntimeError('images.json missing: pull/build and record immutable image IDs first')
    result = json.loads(path.read_text())
    for name in ('mpd', 'upmpdcli', 'soloist', 'web'):
        if name not in result or not re.fullmatch(r'(?:[a-zA-Z0-9._:/-]+@)?sha256:[a-f0-9]{64}', result[name]):
            raise ValueError('image must use immutable digest or local image ID')
    return result


def apply(only=None, maintenance_held=False):
    if not maintenance_held:
        with maintenance_lock(CONFIG):
            return apply(only, maintenance_held=True)
    config = Config(CONFIG)
    refs = images()
    selected = next((d for d in discover() if d['id'] == config.data['dac']), None)
    for directory in (DATA / 'mpd', DATA / 'upmpdcli', DATA / 'soloist/data', DATA / 'soloist/cache', UNITS):
        directory.mkdir(parents=True, exist_ok=True)
    stop_units = ['hifi-soloist'] if only == 'soloist' else ['hifi-upmpdcli', 'hifi-mpd', 'hifi-soloist']
    subprocess.run(['systemctl', '--user', 'stop', *stop_units], check=False)
    if not selected:
        return
    mpd_config = f'''music_directory "/var/lib/mpd"
playlist_directory "/var/lib/mpd"
db_file "/var/lib/mpd/database"
state_file "/var/lib/mpd/state"
sticker_file "/var/lib/mpd/sticker.sql"
log_file "/dev/stdout"
log_level "default"
bind_to_address "127.0.0.1"
port "6600"
restore_paused "yes"
audio_buffer_size "4096"
audio_output {{
    type "alsa"
    name "direct"
    device "hw:{selected['card']},0"
    mixer_type "none"
    auto_resample "no"
    auto_channels "no"
    auto_format "no"
    dop "yes"
    always_on "no"
}}
audio_output {{
    type "null"
    name "standby"
    enabled "yes"
    mixer_type "none"
}}
'''
    (CONFIG / 'mpd.conf').write_text(mpd_config)
    (CONFIG / 'upmpdcli.conf').write_text(f'''mpdhost = 127.0.0.1
mpdport = 6600
friendlyname = {config.data['sources']['dlna']['name']}
upnpport = 49152
cachedir = /var/cache/upmpdcli
logfilename = stderr
loglevel = 2
openhome = 1
''')
    unit('mpd', ['--device', f"/dev/snd/pcmC{selected['card']}D0p", '--device', f"/dev/snd/controlC{selected['card']}",
                 '-v',f'{CONFIG}/mpd.conf:/etc/mpd.conf:ro','-v',f'{DATA}/mpd:/var/lib/mpd:rw',refs['mpd']],128,'pipewire-pulse.service')
    unit('upmpdcli', ['-v',f'{CONFIG}/upmpdcli.conf:/etc/upmpdcli.conf:ro','-v',f'{DATA}/upmpdcli:/var/cache/upmpdcli:rw',refs['upmpdcli']],96,'hifi-mpd.service')
    unit('web', ['-v',f'{RUNTIME}/hifi-streamer:/run/hifi:ro',refs['web']],32,'hifi-agent.service')
    unit('soloist', ['-e','HOME=/data','-e',f"INITIAL_VOLUME={config.data['sources']['spotify'].get('initial_volume',40)}",'-e',f"DEVICE_NAME={config.data['sources']['spotify']['name']}",'-e','PULSE_SERVER=unix:/run/pulse/native',
                     '-v',f'{RUNTIME}/pulse:/run/pulse:ro','-v',f'{CONFIG}/spotify-key:/run/secrets/spotify-key:ro',
                     '-v',f'{DATA}/soloist/data:/data/.local/share/soloist:rw','--tmpfs','/data/.cache/soloist:rw,size=128m,mode=1777',refs['soloist']],256,'pipewire-pulse.service')
    run('systemctl','--user','daemon-reload')
    if only is None:
        run('systemctl','--user','reset-failed','hifi-mpd','hifi-upmpdcli')
        run('systemctl','--user','enable','--now','hifi-mpd','hifi-upmpdcli')
    if config.data['sources']['spotify']['enabled'] and config.has_key():
        subprocess.run(['systemctl','--user','enable','--now','hifi-soloist'], check=False)
    else:
        run('systemctl','--user','disable','hifi-soloist')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['apply','record-images'])
    parser.add_argument('--only',choices=['soloist'])
    parser.add_argument('--maintenance-held', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.action == 'apply':
        apply(args.only, args.maintenance_held)
    else:
        refs = {name:'sha256:' + subprocess.check_output(['podman','image','inspect',f'localhost/hifi-{name}:dev','--format','{{.Id}}'],text=True).strip().removeprefix('sha256:') for name in ('mpd','upmpdcli','soloist','web')}
        atomic_json(CONFIG / 'images.json', refs)
