# Proposal

English | [简体中文](proposal.zh-CN.md)

## Why

Integrate optional Soloist playback with a required DLNA source while keeping DAC arbitration extensible beyond two sources.

## What Changes

- Soloist container, dedicated adapter and local WebSocket state.
- Source-ID-based serialized handoff, failure silence and hotplug recovery.
- Optional-source isolation and third-adapter contract tests.

## Capabilities

### New Capabilities

- `source-arbitration`: Integrate optional Soloist playback with a required DLNA source while keeping DAC arbitration extensible beyond two sources.

### Modified Capabilities

None; no accepted base specification exists for this capability.

## Impact

Affects modules, images, deployment, tests and maintained documentation. Automated verification is complemented by hardware acceptance. Incomplete checks remain unchecked.
