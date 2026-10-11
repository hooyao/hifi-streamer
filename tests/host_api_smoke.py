import json
import urllib.request
from pathlib import Path

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
base = 'http://127.0.0.1:8080'
password = json.loads((Path.home()/'.config/hifi-streamer/admin.json').read_text())['password']
request = urllib.request.Request(base+'/api/login',json.dumps({'password':password}).encode(),{'Content-Type':'application/json','Origin':base})
response = HTTP.open(request,timeout=5)
cookie = response.headers['Set-Cookie'].split(';')[0]
login = json.loads(response.read())
request = urllib.request.Request(base+'/api/status',headers={'Cookie':cookie})
state = json.loads(HTTP.open(request,timeout=5).read())
assert any(d['name'] == 'DX5 II' for d in state['devices'])
assert state['sources']['spotify']['health'] == 'unconfigured'
assert state['sources']['dlna']['health'] == 'healthy'
assert not state['config']['spotify_key_set']
print(json.dumps({'checks':['web login','USB DAC','DLNA healthy','Spotify optional'],'output':state['output']}))
