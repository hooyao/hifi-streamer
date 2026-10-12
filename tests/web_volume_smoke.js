// Exercise browser handlers without external dependencies or an audio device.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../modules/web/index.html'), 'utf8');
assert(!html.includes('loginForm'));
const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(match =>
  [match[1], {value: '', hidden: false, disabled: false, textContent: '', replaceChildren() {}}]));
let current = {available: true, percent: 100, mute: false};
const writes = [];
const context = vm.createContext({
  document: {getElementById: id => elements[id], createElement: () => ({})},
  setInterval() {},
  fetch: async (url, options) => {
    if (url === '/api/output/volume') {
      writes.push(JSON.parse(options.body));
      current = {...current, percent: writes.at(-1).percent};
      return {ok: true, json: async () => current};
    }
    return {ok: true, json: async () => ({csrf: 'fixture', devices: [], sources: {},
      output: {health: 'ready', volume: current},
      config: {sources: {dlna: {name: 'DLNA'}, spotify: {name: 'Spotify', enabled: false}}}})};
  }
});
vm.runInContext(html.match(/<script>([\s\S]*)<\/script>/)[1], context);
(async () => {
  await context.refresh(true);
  assert.equal(elements.hostVolume.disabled, false);
  assert.equal(elements.hostVolume.value, 100);
  assert.equal(elements.initialVolume.value, 100);
  elements.hostVolume.value = '60';
  elements.hostVolume.oninput();
  await context.refresh();
  assert.equal(elements.hostVolume.value, '60', 'poll overwrote an unsaved edit');
  await elements.volumeForm.onsubmit({preventDefault() {}});
  assert.deepEqual(writes, [{percent: 60}]);
  assert.equal(elements.hostVolume.value, 60);
  current = {available: false, percent: null, mute: null};
  await context.refresh();
  assert.equal(elements.hostVolume.disabled, true);
  assert.equal(elements.applyVolume.disabled, true);
  assert.equal(elements.hostVolume.value, '');
  console.log('Web volume handlers passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
