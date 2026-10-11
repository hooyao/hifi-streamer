# Proposal

English | [简体中文](proposal.zh-CN.md)

## Why

Bound resource consumption on memory- and storage-constrained ARM devices while building compact images remotely.

## What Changes

- Native ARM64/AMD64 GitHub Actions builds with GHCR publication and configurable registry references.
- Image-size gates, runtime resource budgets and rotating logs.
- Per-module update preflight, expiry checks, health commit and rollback.

## Capabilities

### New Capabilities

- `bounded-runtime`: Bound resource consumption on memory- and storage-constrained ARM devices while building compact images remotely.

### Modified Capabilities

None; no accepted base specification exists for this capability.

## Impact

Affects modules, images, deployment, tests and maintained documentation. Automated verification is complemented by hardware acceptance. Incomplete checks remain unchecked.
