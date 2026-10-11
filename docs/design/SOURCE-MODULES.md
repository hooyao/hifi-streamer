# Source-module contract

English | [简体中文](SOURCE-MODULES.zh-CN.md)

## Scope

DLNA is required. Spotify is an optional Soloist adapter. Roon, Apple Music and Amazon Music are future candidates, subject to suitable Linux implementations, authentication, distribution terms and resource requirements.

A source is a logical module, not necessarily one container. DLNA comprises upmpdcli and MPD; Spotify uses Soloist. Common device control must remain independent of service-specific commands.

## Current contract

Module declarations in `modules/sources/*/module.json` include stable ID, interface_version, required flag, adapter, output paths, controls and components. The registry validates interface compatibility and requires DLNA.

Adapters expose an instance ID, snapshot, release and acquire. Snapshots distinguish running, authenticated, active, playback and health. Unreachable adapters report unknown playback rather than pretending to be stopped.

Recovery closes retired control transports and renews adapter instance IDs before returning to paused readiness. Hardware availability and actual output health remain independent from player snapshots; see [automatic recovery](../debugging/audio-recovery.md).

The arbiter consumes source IDs, instance IDs and sequence numbers. It rejects stale/duplicate requests, serializes handoff and grants output only after verified hardware release. This does not give containers unrestricted device access.

MPD-specific direct/null controls belong to the DLNA adapter. Soloist WebSocket commands belong to Spotify. PipeWire stream routing is output infrastructure.

## Extension requirements

1. Confirm a viable Linux implementation and distinguish a remote receiver from a local client.
2. Add an adapter and declare its supported controls/output paths.
3. Provide a verifiable pause/stop/release mechanism, even when upstream cannot pause.
4. Declare bounded dependencies, network ports, secrets, data and cache.
5. Define version, expiry and data-migration/rollback behavior.
6. Run generic arbitration tests, hardware handoff and full DLNA regression.

Adding a new built-in source currently requires registering its adapter factory and configuration schema. Arbitrary third-party plugin loading is not implemented. Missing controls must be represented as unsupported, not fake successes.

## Compatibility criteria

DLNA discovery/control must remain available during optional-source failures. Controllers must receive truthful playback/volume capabilities. A standby output must not silently consume complete tracks.

Validate reachable URLs, play/pause/stop/seek, queue transitions, repeated Play, supported PCM rates, FLAC and device-qualified DoP. Include unplug/replug, network timeout, reboot and long-duration playback. Gapless, Native DSD and additional formats need explicit acceptance cases.
