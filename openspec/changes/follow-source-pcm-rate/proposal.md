# Proposal

## Why

Spotify acquisition currently requests 44100Hz regardless of the PCM format produced by Soloist. A fixed host rate can introduce unnecessary conversion and prevents a source from changing its output format.

## What Changes

- Observe the active source's actual Pulse PCM rate and match the selected DAC/graph to it.
- Follow format changes while Spotify owns output without a global forced clock.
- Report missing, ambiguous or unsupported PCM formats without silently using 44100Hz or disturbing required DLNA playback.
- Verify real Spotify PCM/output agreement and synthetic 44.1/48/96kHz transport changes, preserving gain and paused recovery.

## Capabilities

### New Capabilities

- `source-rate-following`: Selected-output clock follows observable decoded PCM format.

### Modified Capabilities

None; no main specs have been archived yet.

## Impact

Soloist adapter, shared PipeWire output control, runtime source status, unit/device tests and bilingual architecture/operations/testing documentation. No container image change is required. This observes decoded PCM, not hidden Spotify encoded-file metadata, and cannot reverse conversion performed inside Soloist.
