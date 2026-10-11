"""Controlled low-level sine playback on one DAC; requires listening feedback."""
import argparse
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'modules/audio-agent'))
from hifi.runtime import Runtime
from hifi.pipewire import run

parser = argparse.ArgumentParser()
parser.add_argument('path',choices=['alsa','pipewire'])
parser.add_argument('--dbfs',type=float,default=-36,help='Tone level; 0 is full scale, control listening volume on the DAC')
parser.add_argument('--isolated',action='store_true',help='ALSA test with PipeWire/WirePlumber stopped')
args = parser.parse_args()
if not -90 <= args.dbfs <= 0:
    parser.error('dbfs must be between -90 and 0')
repo = Path(__file__).resolve().parents[1]
runtime = Runtime(repo,Path.home()/'.config/hifi-streamer')
dac = runtime.selected()
if not dac:
    raise SystemExit('No selected DAC')
tone = repo/'.local-build/path-tone.wav'
tone.parent.mkdir(exist_ok=True)
rate = 44100
with wave.open(str(tone),'wb') as stream:
    stream.setnchannels(2)
    stream.setsampwidth(4)
    stream.setframerate(rate)
    # 100ms fades avoid a discontinuity at start/end.
    for second in range(8):
        frames = bytearray()
        for index in range(rate):
            sample_index = second*rate+index
            fade = min(1, sample_index/(rate*.1), (8*rate-1-sample_index)/(rate*.1))
            value = int((2**31-1)*10**(args.dbfs/20)*fade*math.sin(2*math.pi*440*sample_index/rate))
            frames.extend(struct.pack('<ii',value,value))
        stream.writeframesraw(frames)
if args.path == 'alsa':
    if args.isolated:
        subprocess.run(['systemctl','--user','stop','hifi-agent','hifi-soloist','hifi-mpd','pipewire.socket','pipewire-pulse.socket','wireplumber','pipewire-pulse','pipewire'],check=True)
    else:
        runtime.hardware.for_direct()
    subprocess.run(['aplay','-D',f"hw:{dac['card']},0",str(tone)],check=True,timeout=15)
else:
    # This probe runs with all players stopped, so MPD control is unnecessary.
    runtime.hardware.mpd = None
    runtime.hardware.for_pipewire()
    target = runtime.hardware.sink()
    run('pactl','set-sink-volume',target,'100%')
    subprocess.run(['pw-play','--target',target,str(tone)],check=True,timeout=15)
