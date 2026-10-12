# Repository guide

English | [简体中文](AGENTS.zh-CN.md)

HiFi Streamer is a modular Linux network audio renderer. DLNA is required; Spotify is an optional source adapter.

## Working references

Read the relevant architecture and source contract before changing a module. Use the following guides for contribution rules, validation commands and detailed operations.

[Contributing](CONTRIBUTING.md) | [Testing](docs/testing/README.md) | [Operations](docs/OPERATIONS.md) | [Architecture](docs/design/AUDIO-ARCHITECTURE.md) | [Source contract](docs/design/SOURCE-MODULES.md)

## Module index

| Module | Responsibility | Source entry points |
| --- | --- | --- |
| Host agent | Service lifecycle, discovery and control loop | [Entry point](modules/audio-agent/hifi/__main__.py), [Runtime](modules/audio-agent/hifi/runtime.py), [Discovery](modules/audio-agent/hifi/devices.py) |
| Output arbitration | Exclusive DAC ownership and audio routing | [Arbiter](modules/audio-agent/hifi/core.py), [PipeWire](modules/audio-agent/hifi/pipewire.py), [Rates](modules/audio-runtime/10-rates.conf) |
| Source registry | Built-in declarations and interface validation | [Registry](modules/audio-agent/hifi/registry.py), [Declarations](modules/sources/) |
| DLNA | Required renderer and direct ALSA output | [Declaration](modules/sources/dlna/module.json), [Adapter](modules/audio-agent/hifi/mpd.py), [MPD image](images/mpd/), [upmpdcli image](images/upmpdcli/) |
| Spotify | Optional Soloist control and Pulse output | [Declaration](modules/sources/spotify/module.json), [Adapter](modules/audio-agent/hifi/soloist.py), [WebSocket](modules/audio-agent/hifi/websocket.py), [Image](images/soloist/) |
| Configuration and API | Persistent configuration, output volume and device control | [Configuration](modules/audio-agent/hifi/config.py), [API](modules/audio-agent/hifi/api.py) |
| Web UI | Device/source configuration and update controls | [UI](modules/web/index.html), [Proxy](modules/web/nginx.conf), [Image](images/web/) |
| Installation | Host dependencies and rootless service generation | [Host setup](deploy/host-setup.sh), [Account preflight](deploy/preflight.py), [Account setup](deploy/install.sh), [Service generator](deploy/manage.py) |
| Updates and maintenance | Candidate observation, preflight and rollback | [Transaction](deploy/update.py), [Observation](deploy/check-updates.py), [Maintenance](modules/audio-agent/hifi/maintenance.py) |
| CI and verification | Repository checks and native image builds | [Workflows](.github/workflows/), [Image gate](images/check.py), [Tests](tests/) |
| Specifications | Behavior changes and acceptance tasks | [OpenSpec](openspec/) |
