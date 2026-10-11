"""Thirty-second listening test with host clocks controlled by the caller."""
import subprocess
import sys
import time
from pathlib import Path
from hifi.runtime import Runtime
from hifi.pipewire import run

repo = Path(sys.argv[1])
subprocess.run(['systemctl','--user','start','pipewire','pipewire-pulse','wireplumber'],check=True)
time.sleep(3)
runtime = Runtime(repo,Path.home()/'.config/hifi-streamer')
# This isolated diagnostic intentionally leaves MPD stopped.
runtime.hardware.mpd = None
runtime.hardware.for_pipewire()
run('pactl','set-sink-volume',runtime.hardware.sink(),'100%')
subprocess.run(['systemctl','--user','start','hifi-soloist'],check=True)
time.sleep(5)
soloist = runtime.adapters['spotify']
try:
    assert soloist.snapshot()['authenticated'], 'Spotify session not yet authenticated'
    soloist.command('activate')
    soloist.command('set_volume',volume=100)
    soloist.command('play')
    print('FIXED-CPU SPOTIFY TEST START (60 seconds)',flush=True)
    for _ in range(12):
        time.sleep(5)
        print(soloist.snapshot(),flush=True)
finally:
    soloist.command('pause')
    print('FIXED-CPU SPOTIFY TEST END; paused',flush=True)
