# Proposal

English | [简体中文](proposal.zh-CN.md)

## Why

USB protocol failures can remove the DAC, leave MPD in a service start-limit failure, and leave PipeWire/Soloist with unusable routes after the DAC returns. Device rediscovery alone does not restore the complete audio path, so recovery needs observable stages and bounded automatic repair.

## What Changes

- Distinguish missing hardware, incomplete enumeration, missing host routes, failed services and playback-path failure.
- Add a serialized recovery supervisor with stable-device debounce, device generations, staged repair, retry budgets and maintenance coordination.
- Rebuild stale container mappings, reset affected service failures and recreate host audio sessions only when narrower repairs fail.
- Restore readiness with playback paused; require fresh controller intent before resuming sound.
- Expose recovery state and actionable reasons in the status API/web UI; keep logs bounded.
- Add deterministic fault-injection tests and device acceptance for USB loss/reappearance, stale routes and service failures.

## Capabilities

### New Capabilities

- `audio-recovery`: Automatic bounded restoration of the selected DAC's services and output infrastructure after device/session faults.

### Modified Capabilities

None. No accepted base specs currently exist. This extends the active source-control, arbitration and DLNA designs while preserving exclusive ownership and paused reconnect behavior.

## Impact

Affects host runtime/discovery, output routing, adapter lifecycle, deployment/update coordination, status API/web UI, tests and bilingual operating documentation. Uses existing Python/systemd/Podman/PipeWire dependencies. Automatic kernel/USB-controller resets, host reboots, firmware changes and repair of faulty cables or expired media URLs are outside scope.
