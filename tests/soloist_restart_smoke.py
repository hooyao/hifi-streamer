"""Verify configured startup volume survives an actual user-service restart."""
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.config import Config
from hifi.soloist import Soloist

config = Config(Path.home()/'.config/hifi-streamer')
expected = config.data['sources']['spotify'].get('initial_volume',100)
subprocess.run(['systemctl','--user','restart','hifi-soloist'],check=True)
for attempt in range(30):
    client = Soloist(None,lambda:True)
    try:
        if client.snapshot()['authenticated']:
            state = client.command('get_state')
            assert state.get('volume') == expected, f"expected {expected}, got {state.get('volume')}"
            print(json.dumps({'restart':'passed','initial_volume':state['volume'],'authenticated':True}))
            break
    except (OSError,RuntimeError):
        pass
    finally:
        if client.client:
            client.client.close()
    time.sleep(1)
else:
    raise SystemExit('Soloist did not restore authenticated state after restart')
