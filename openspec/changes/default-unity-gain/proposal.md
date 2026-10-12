# Proposal

## Why

Fresh installations apply independent 40% defaults to Soloist and the host output, unexpectedly attenuating Spotify. Users also need direct host-volume control without the current password-login step.

## What Changes

- Default Soloist startup and newly initialized host output to 100%/0dB while preserving explicit existing preferences.
- Expose actual selected PipeWire sink volume and a 0–100% control in the web/API, independently from Soloist startup volume.
- Remove control-plane password/session authentication for this development release; retain same-origin and CSRF checks. Source-service authentication remains unchanged.
- Document that host volume affects PipeWire sources, not direct ALSA DLNA.

## Capabilities

### New Capabilities

- `output-gain`: Unity defaults, actual host-volume observation and persistent user adjustments.
- `control-plane-access`: Password-free device control with same-origin request protection.

### Modified Capabilities

None; no main specifications have been archived. This change supersedes password-authentication expectations in the earlier control-plane bootstrap change.

## Impact

Account installer, WirePlumber defaults, configuration, host runtime, API, Soloist launcher, web UI, integration helpers and bilingual operational documentation. Authentication will be designed separately; this release's device control is available to clients that can reach the LAN endpoint.
