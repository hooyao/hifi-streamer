import json
import subprocess
import sys
import re
from pathlib import Path

BUDGET = {'mpd':200, 'upmpdcli':160, 'soloist':180, 'web':40}
component, image = sys.argv[1:]
info = json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
assert info['Size'] <= BUDGET[component] * 1048576, f"image too large: {info['Size']}"
commands = {'mpd':['--entrypoint','mpd',image,'--version'],
            'upmpdcli':['--entrypoint','upmpdcli',image,'-v'],
            'soloist':[image,'--version'],
            'web':['--entrypoint','nginx',image,'-e','/dev/stderr','-t']}
result = subprocess.run(['docker','run','--rm',*commands[component]], capture_output=True,text=True,timeout=20)
assert result.returncode == 0, result.stderr
report = {'component':component,'bytes':info['Size'],'id':info['Id'],'version':result.stdout+result.stderr,'data_version':1}
if component == 'soloist':
    match = re.search(r'build (\d+)',report['version'])
    assert match, 'Soloist build timestamp not reported'
    report['build_timestamp'] = int(match[1])
    report['expires_at'] = int(match[1]) + 90*86400
Path('image-report.json').write_text(json.dumps(report,indent=2))
