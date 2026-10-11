# Testing

English | [简体中文](README.zh-CN.md)

## Automated checks

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

Unit tests cover configuration validation, credentials redaction, HTTP auth/CSRF, module registry, third-source arbitration, stale events, release failure, hotplug state, WebSocket framing, log/cache bounds and update rollback/preflight.

## Hardware integration

Run as the service account on a configured host. Hardware tests change playback; use low DAC/amplifier volume and avoid other controllers during exclusive tests.

```sh
python3 tests/dlna_smoke.py --card <runtime-card> --dsd --report .local-build/dlna.json
python3 tests/soloist_restart_smoke.py
python3 tests/mpd_restart_smoke.py --card <runtime-card> --report .local-build/mpd-restart.json
python3 tests/spotify_switch_smoke.py --card <runtime-card> --report .local-build/switch.json
sh tests/podman_tmpfs_smoke.sh
```

DLNA smoke checks SSDP and AVTransport URI/play/pause/seek/stop, 44.1/48/96kHz WAV/FLAC, next URI, repeated Play and optional DSD64 DoP. USB async feedback uses 0.1% frequency tolerance; this is not a bit-perfect comparison.

Spotify tests require a paired account and verify output handoff and configured startup volume after restart. `host_api_smoke.py` targets the unconfigured-Spotify state and a DX5 II fixture; do not use it as a generic installed-device health check.

MPD restart testing covers planned and abrupt exits, paused queue restoration and disabled-direct-output recovery. It requires subsequent DLNA output at 44.1/96kHz with advancing position. See [MPD memory and recovery](../debugging/mpd-memory.md) for recovery limits.

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
