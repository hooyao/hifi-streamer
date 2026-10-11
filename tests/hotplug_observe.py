"""Observe a manual USB unplug/replug without resuming audio."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.devices import discover
from hifi.config import Config
from hifi.soloist import Soloist

repo = Path(__file__).resolve().parents[1]
config = Config(Path.home()/'.config/hifi-streamer')
events = []
previous = None
for _ in range(90):
    dac = next((d for d in discover() if d['id'] == config.data['dac']),None)
    current = {'connected':dac is not None,'card':dac['card'] if dac else None}
    if current != previous:
        events.append({'time':time.time(),**current})
        print(json.dumps(events[-1]),flush=True)
        previous = current
    time.sleep(.5)
try:
    playback = Soloist(None,lambda:True).snapshot()
except Exception:
    playback = {'health':'unreachable'}
report = {'events':events,'spotify':playback}
path = repo/'.local-build/hotplug-report.json'
path.write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
