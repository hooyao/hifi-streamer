"""Requires a paired Soloist session; verifies both output paths on the host."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.soloist import Soloist
from hifi.mpd import MPD
from dlna_smoke import usb_rate

parser = argparse.ArgumentParser()
parser.add_argument('--card',type=int,required=True)
parser.add_argument('--report',type=Path,default=Path('spotify-switch-report.json'))
args = parser.parse_args()
soloist = Soloist(None,lambda:True)
assert soloist.snapshot()['authenticated'], 'Pair using the Spotify app first'
soloist.command('activate')
soloist.command('play')
usb_rate(args.card,44100)
subprocess.run([sys.executable,str(Path(__file__).with_name('dlna_smoke.py')),'--card',str(args.card),'--dsd','--report',str(args.report.with_suffix('.dlna.json'))],check=True)
assert soloist.snapshot()['playback'] == 'paused', 'DLNA did not pause Spotify'
soloist.command('activate')
soloist.command('play')
stream = usb_rate(args.card,44100)
assert MPD(None).snapshot()['playback'] != 'playing'
outputs = MPD(None).command('outputs')
assert 'outputenabled: 0' in outputs
args.report.write_text(json.dumps({'switch':'spotify -> dlna/doP -> spotify','usb_stream':stream,'mpd_outputs':outputs},indent=2))
print('Bidirectional switch passed; Spotify output restored to 44100Hz')
