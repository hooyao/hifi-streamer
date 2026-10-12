import json
import urllib.request

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
base = 'http://127.0.0.1:8080'
request = urllib.request.Request(base+'/api/status')
state = json.loads(HTTP.open(request,timeout=5).read())
assert any(d['name'] == 'DX5 II' for d in state['devices'])
assert state['sources']['spotify']['health'] == 'unconfigured'
assert state['sources']['dlna']['health'] == 'healthy'
assert not state['config']['spotify_key_set']
print(json.dumps({'checks':['password-free status','USB DAC','DLNA healthy','Spotify optional'],'output':state['output']}))
