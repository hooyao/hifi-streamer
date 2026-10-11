# Proposal

English | [简体中文](proposal.zh-CN.md)

## Why

Provide a shared source contract and lightweight control plane so new services can reuse DAC discovery and ownership.

## What Changes

- Versioned module declarations, isolated adapters and uniform snapshots.
- Stable USB DAC binding, persisted configuration and authenticated web/API access.
- Automated failure and unknown-state tests using fake adapters.

## Capabilities

### New Capabilities

- `source-control`: Provide a shared source contract and lightweight control plane so new services can reuse DAC discovery and ownership.

### Modified Capabilities

None; no accepted base specification exists for this capability.

## Impact

Affects modules, images, deployment, tests and maintained documentation. Automated verification is complemented by hardware acceptance. Incomplete checks remain unchecked.
