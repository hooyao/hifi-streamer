"""Verify MPD service/crash recovery and subsequent DLNA hardware output."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules/audio-agent'))
from hifi.mpd import MPD
from dlna_smoke import discover, field, soap, usb_rate, wait_state
from http_audio_fixture import VirtualWavServer


def pid():
    return int(subprocess.check_output(
        ['podman', 'inspect', 'hifi-mpd', '--format', '{{.State.Pid}}'],
        text=True, stderr=subprocess.DEVNULL))


def wait_restart(old):
    started = time.monotonic()
    while time.monotonic() - started < 40:
        try:
            current = pid()
            if current and current != old and MPD(None).snapshot()['running']:
                return round(time.monotonic() - started, 2)
        except (subprocess.CalledProcessError, OSError, RuntimeError):
            pass
        time.sleep(.5)
    raise AssertionError('MPD did not recover within 40 seconds')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--card', type=int, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    control = discover('HiFi Streamer')
    fixtures = [VirtualWavServer(seconds=600, rate=rate) for rate in (44100, 96000)]
    checks = []

    def play(fixture):
        soap(control, 'Stop')
        soap(control, 'SetAVTransportURI', CurrentURI=fixture.url, CurrentURIMetaData='')
        soap(control, 'Play', Speed=1)
        wait_state(control, 'PLAYING')
        usb_rate(args.card, 44100 if fixture is fixtures[0] else 96000, timeout=30)
        before = field(soap(control, 'GetPositionInfo'), 'RelTime')
        time.sleep(3)
        after = field(soap(control, 'GetPositionInfo'), 'RelTime')
        assert after > before, 'playback position did not advance'
        assert not MPD(None).snapshot()['error'], 'MPD output error'

    try:
        for case in ('service restart', 'SIGKILL automatic restart', 'disabled direct output restart'):
            play(fixtures[0])
            if case == 'disabled direct output restart':
                MPD(None).release()
                time.sleep(2)
                outputs = MPD(None).command('outputs')
                assert 'outputenabled: 0' in outputs, outputs
            old = pid()
            if case == 'SIGKILL automatic restart':
                subprocess.run(['podman', 'kill', '--signal', 'KILL', 'hifi-mpd'], check=True)
            else:
                subprocess.run(['systemctl', '--user', 'restart', 'hifi-mpd'], check=True)
            recovery = wait_restart(old)
            time.sleep(3)
            assert MPD(None).snapshot()['playback'] != 'playing', 'unexpected automatic resume'
            for fixture in fixtures:
                play(fixture)
            checks.append({'case': case, 'passed': True, 'recovery_seconds': recovery,
                           'rates': [44100, 96000], 'position_advances': True})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'checks': checks}, indent=2))
        print(json.dumps({'passed': len(checks), 'checks': checks}))
    finally:
        try:
            soap(control, 'Stop')
        finally:
            for fixture in fixtures:
                fixture.close()


if __name__ == '__main__':
    main()
