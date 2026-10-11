# Proposal

English | [简体中文](proposal.zh-CN.md)

## Why

Make DLNA a reliable required source using real discovery and protocol controls with source-rate audio output.

## What Changes

- Independent MPD/upmpdcli containers with host discovery and loopback MPD control.
- Direct ALSA and device-qualified DoP without software mixing.
- Automated SSDP, SOAP, HTTP audio and USB output checks.

## Capabilities

### New Capabilities

- `dlna-rendering`: Make DLNA a reliable required source using real discovery and protocol controls with source-rate audio output.

### Modified Capabilities

None; no accepted base specification exists for this capability.

## Impact

Affects modules, images, deployment, tests and maintained documentation. Automated verification is complemented by hardware acceptance. Incomplete checks remain unchecked.
