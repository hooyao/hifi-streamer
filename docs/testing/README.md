# Testing

English | [简体中文](README.zh-CN.md)

## Automated checks

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

Unit tests cover configuration validation, credentials redaction, password-free HTTP access/Origin/CSRF and host-volume isolation, module registry, third-source arbitration, stale events, release failure, hotplug state, WebSocket framing, log/cache bounds and update rollback/preflight.

## Hardware integration

The MP3 transport regression also serves a known-length 20,850,000-byte stream generated in bounded chunks, larger than MPD's 16MiB full-file cache cap. Each forward/backward seek must produce a new nonzero HTTP Range request and reach the requested playback position; the report records requests per seek.

Native MPD images run `tests/mpd_mp3_ci.py <image>` against generated silent MPEG-1 Layer III frames. Local decoding validates the fixture before HTTP CBR/VBR, ID3, extensionless audio/mpeg and sequential-input tests; seekable inputs verify forward/backward positioning and pause/resume. The build also compiles `images/mpd/seek-test.cxx` against the decoder's exact offset helper to reject negative/overflow/unknown-end requests. No media files or additional codecs are required. Device DLNA smoke includes tagged MP3 at 44.1/48kHz, PCM/FLAC at 44.1/48/88.2/96kHz and qualified DoP. It verifies the current URI before/after USB checks and after a rate timeout, so another controller replacing the fixture is reported as interference rather than conversion.

`tests/output_volume_device_smoke.py --report <private-report-path>` qualifies password-free status, fresh host-unity initialization, 0%/60% adjustments, rejection of 101%, agent/WirePlumber restart persistence, source-setting independence and restoration of the prior host gain. It briefly changes software volume and restarts those user services; keep hardware volume low. The unit tests separately cover unavailable/stale routes and adjustment isolation.

See [automatic audio recovery](../debugging/audio-recovery.md) for output-health states and bounded repair behavior.

Run as the service account on a configured host. Hardware tests change playback; use low DAC/amplifier volume and avoid other controllers during exclusive tests.

```sh
python3 tests/dlna_smoke.py --card <runtime-card> --dsd --report .local-build/dlna.json
python3 tests/soloist_restart_smoke.py
python3 tests/agent_restart_smoke.py
python3 tests/mpd_restart_smoke.py --card <runtime-card> --report .local-build/mpd-restart.json
python3 tests/recovery_device_smoke.py --fault mpd --automatic-only --report .local-build/recovery.json
python3 tests/spotify_switch_smoke.py --card <runtime-card> --report .local-build/switch.json
sh tests/podman_tmpfs_smoke.sh
```

DLNA smoke checks SSDP and AVTransport URI/play/pause/seek/stop, 44.1/48/96kHz WAV/FLAC, next URI, repeated Play and optional DSD64 DoP. USB async feedback uses 0.1% frequency tolerance; this is not a bit-perfect comparison.

Spotify tests require a paired account and verify output handoff and configured startup volume after restart. `host_api_smoke.py` targets the unconfigured-Spotify state and a DX5 II fixture; do not use it as a generic installed-device health check.

Agent restart smoke requires Spotify already playing with its hardware clock request set. It verifies paused restart with no owner, persistent-node clock cleanup, unchanged recovery budget, rejected healthy retry and fresh 44.1kHz playback.

MPD restart testing covers planned and abrupt exits, paused queue restoration and disabled-direct-output recovery. It requires subsequent DLNA output at 44.1/96kHz with advancing position. See [MPD memory and recovery](../debugging/mpd-memory.md) for recovery limits.

Recovery fault injection accepts `mpd`, `start-limit`, `player`, `route` or `session`. Wait for available automatic budget before using `--automatic-only`; otherwise the test fails rather than silently counting manual retry as automatic acceptance. It stops services and requires paused ready output. The start-limit test holds the maintenance lock while temporarily injecting failed startup and removes its override before permitting repair. Physical hotplug/power-cycle and subsequent playback/listening remain separate checks.

## Reversible application clean-install test

On a dedicated configured host, the following temporarily replaces application configuration, data and generated units, then restores the private state in a `finally` block. It interrupts playback and leaves output paused. Keep hardware volume low, avoid other controllers, and retain the private backup until restoration is checked. It does not reflash the OS, change subordinate allocations, or reset the host's PipeWire volume. Omit `--dsd` for PCM-only hardware. No long-duration test is run.

```sh
python3 tests/clean_install_smoke.py --replace-app-state --dsd --report .local-build/clean-install.json
```

Acceptance includes an empty configuration, unconfigured optional Spotify, password-free web status, missing selected hardware, idempotent configuration preservation, first API DAC selection, newly loaded audio units, unchanged web process and actual DLNA formats/controls. A passed report also needs `private_state_restored: true`; keep failures distinct from successful restore. First-start discovery retries for a bounded period and skips unreachable/stale advertisements.

## Decoded source-rate following

```sh
python3 tests/source_rate_smoke.py --report .local-build/source-rate.json
```

This dedicated-host test temporarily stops agent/Soloist, supplies synthetic Pulse PCM through the adapter at 44.1→48→96→44.1kHz, and verifies client format, driver graph, USB, unchanged gain/mute, global force-rate zero, unchanged repair history and rate cleanup. It restores paused services and runs no long-duration soak. It qualifies transport, not Spotify's decoder or encoded catalog formats. Real Soloist acceptance also requires observed PCM/USB agreement, both DLNA handoffs, restart and listening confirmation.

## Long-duration test

```sh
python3 tests/dlna_soak.py --card <runtime-card> --seconds 7200 --report .local-build/soak.json
```

The test generates a silence WAV HTTP stream on demand. It checks renderer URI, playback position, USB output and memory; another controller changing the URI fails the test. The report's final status must be passed before counting acceptance.

## Update integration

`tests/update_device_smoke.py` exercises the real web updater with an incompatible cached image, checks rollback/healthy commit and ensures DLNA is not restarted. It requires idle DAC output and existing immutable images.

Generated reports and raw logs are local/CI artifacts, not tracked documentation. Keep only redacted reproducible test definitions and qualification boundaries in the repository.

## Manual acceptance

Validate LMS Bridge and Audio Station against target formats, pause/seek/next and queue behavior. Validate Spotify listening quality, both handoff directions, DAC unplug/replug without automatic resume, and full-host reboot. Record controller versions and DAC capabilities in release acceptance artifacts.

Protocol/USB checks cannot establish listening quality. Do not certify Native DSD, gapless or all DACs from one fixture.

## Hardware profile

See [M401A qualification](m401a.md). CPU-clock diagnosis scripts are fixture-only and are not generic installation defaults.
