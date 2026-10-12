# Architecture

English | [简体中文](AUDIO-ARCHITECTURE.zh-CN.md)

## Components

| Component | Placement | Responsibility |
| --- | --- | --- |
| MPD | Rootless Podman | HTTP decoding, ALSA PCM/DoP output |
| upmpdcli | Rootless Podman | DLNA/OpenHome protocol and MPD control |
| Soloist | Rootless Podman | Spotify Connect and PipeWire Pulse output |
| PipeWire/WirePlumber | Host user services | DAC routing and standby output |
| audio-agent | Host user service | Discovery, adapters, configuration and serialized ownership |
| Web | Rootless Podman | Static UI and proxy to a private Unix socket |
| Installer | Explicit root setup | Dependencies, device access and journal budgets |

The web container has no Podman management socket or arbitrary shell API.

## Audio paths

```text
DLNA -> upmpdcli -> MPD -> ALSA hw -> DAC
Spotify -> Soloist -> PipeWire Pulse -> DAC
Web -> private Unix socket -> audio-agent
```

Controllers provide reachable media URLs. A NAS mount/local library is unnecessary. MPD decodes compressed streams. Direct output disables ALSA conversions and software mixing. DoP is qualified per DAC; Native DSD and bit-perfect need separate evidence.

## Discovery and handoff

USB VID/PID, serial or physical port establish identity. Resolve ALSA card numbers and PipeWire node IDs at runtime.

Only one source owns the selected DAC. Output states are disconnected, idle, switching, active and error; owner is a source ID. Serialize handoff, revoke the old path and check hardware release before acquisition.

DLNA handoff moves Spotify to standby, suspends the hardware sink and enables MPD direct output. Spotify handoff pauses MPD, enables null output and resumes the hardware sink. Playback intent and ownership are distinct.

Spotify output follows the PCM rate actually supplied by Soloist through Pulse. A supported changed rate parks the stream briefly, retunes only the selected DAC node and restores it without changing gain/mute or forcing a global clock. Stable formats do not repeatedly reopen the device. Unknown formats wait; malformed, ambiguous or unsupported formats report a source error and cannot revoke a healthy DLNA owner. Direct handoff clears the source-owned request. This matches decoded PCM, not hidden encoded-file metadata or conversion already performed inside Soloist.

Unplugging revokes output. Reconnection regenerates mappings and may rebuild containers. Playback stays paused by default.

The [recovery supervisor](../debugging/audio-recovery.md) observes hardware independently of slow player control, publishes output-health errors and repairs services/routes within a persistent retry budget. Deployment, updates and recovery share a maintenance lock; status queries remain responsive while services are repaired.

## Networks and storage

Media containers use host networking for discovery. MPD and Soloist control endpoints bind to loopback. Web listens on 8080; this development release has no password/session authentication. Matching Origin and a process-scoped CSRF token protect state changes. Host-output gain is independent from source startup volume and direct ALSA output; cached selected-sink observations keep status responsive during audio operations.

Configuration/secrets use the service account's private XDG directory. Session data is separate from bounded cache. Inject secrets at runtime, never in images.

Podman 4.3 uses explicit systemd user units rather than assuming Quadlet. Containers use crun, supplementary device groups, immutable images, read-only roots and resource limits.

Images are built on native ARM64/AMD64 CI runners. See [operations](../OPERATIONS.md) for budgets and updates, and the [source contract](SOURCE-MODULES.md) for extension boundaries.
