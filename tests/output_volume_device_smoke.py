"""Qualify actual host gain, password-free API and restart persistence."""
import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'modules/audio-agent'))
from hifi.config import atomic_json
from hifi.runtime import Runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,required=True)
    args = parser.parse_args()
    base = 'http://127.0.0.1:8080'
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {'Origin':base,'Content-Type':'application/json'}

    def api(path,data=None):
        response = http.open(urllib.request.Request(base+'/api/'+path,
                            json.dumps(data).encode() if data is not None else None,headers),timeout=30)
        assert not response.headers.get('Set-Cookie'),'unexpected login cookie'
        result = json.load(response)
        if 'csrf' in result:
            headers['X-CSRF-Token'] = result['csrf']
        return result

    def ready():
        deadline = time.monotonic()+120
        while time.monotonic()<deadline:
            try:
                state = api('status')
                if state['output']['health']=='ready' and state['output']['volume']['available']:
                    return state
            except (OSError,ValueError):
                pass
            time.sleep(.5)
        raise AssertionError('output volume did not become available')

    state = ready()
    selected = state['config']['dac']
    saved = round(state['output']['volume']['percent'])
    saved_mute = state['output']['volume']['mute']
    source_volume = state['config']['sources']['spotify'].get('initial_volume',100)
    runtime = Runtime(REPO,Path.home()/'.config/hifi-streamer')
    original = runtime.hardware.volume_snapshot()
    report = {'passed':False}
    try:
        # Use a private fresh config to qualify one-time initialization on the real sink.
        api('output/volume',{'percent':40})
        with tempfile.TemporaryDirectory() as directory:
            fresh = Runtime(REPO,directory)
            fresh.config.data['dac'] = selected
            atomic_json(fresh.config.path,fresh.config.data)
            fresh.initialize_output_volume()
            assert fresh.hardware.volume_status()['percent']==100
            fresh.hardware.set_volume(60)
            fresh.initialize_output_volume()
            assert fresh.hardware.volume_status()['percent']==60,'initialization reset user gain'
            assert not (Path(directory)/'admin.json').exists()
        assert api('output/volume',{'percent':0})['percent']==0
        assert api('output/volume',{'percent':60})['percent']==60
        try:
            api('output/volume',{'percent':101})
            raise AssertionError('out-of-range volume accepted')
        except urllib.error.HTTPError as error:
            assert error.code==400
        subprocess.run(['systemctl','--user','restart','hifi-agent'],check=True,timeout=30)
        after = ready()
        assert after['output']['volume']['percent']==60,'restart lost host gain'
        assert after['output']['volume']['mute']==saved_mute,'mute changed'
        assert after['config']['sources']['spotify'].get('initial_volume',100)==source_volume
        time.sleep(2)
        subprocess.run(['systemctl','--user','restart','wireplumber'],check=True,timeout=30)
        deadline = time.monotonic()+30
        while time.monotonic()<deadline:
            try:
                actual = runtime.hardware.volume_status()
                if actual['percent']==60 and actual['mute']==saved_mute:
                    break
            except RuntimeError:
                pass
            time.sleep(.5)
        else:
            raise AssertionError('WirePlumber restart lost host gain')
        report.update(passed=True, fresh_unity=True, password_free=True,
                      volume_zero_and_sixty=True, restart_preserved=True,
                      wireplumber_restart_preserved=True, source_setting_unchanged=True)
    finally:
        ready()
        api('output/volume',{'percent':saved})
        runtime.hardware.restore_volume(original)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        atomic_json(args.report,report)
    print(json.dumps(report))


if __name__=='__main__':
    main()
