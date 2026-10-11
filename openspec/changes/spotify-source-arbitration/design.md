# Design

English | [简体中文](design.zh-CN.md)

## Context

See proposal.md and the architecture/source contract. The target is a systemd Linux host with Python 3.11, rootless Podman and USB audio.

## Goals / Non-Goals

**Goals:** Reproducible behavior, isolated failures and explicit acceptance boundaries.

**Non-Goals:** Unimplemented streaming services, arbitrary hardware certification and unverified bit-perfect claims.

## Decisions

Expose snapshot/release/acquire operations and stable instance IDs. Keep service-specific controls in adapters; serialize ownership with a lock and generation checks. Query Soloist through its persistent local WebSocket, not recurring podman exec. Use a standby PipeWire sink and explicit hardware suspension. On unsafe release, fail closed rather than enabling both paths. An unconfigured key must not block DLNA.

## Risks / Trade-offs

External authentication and physical audio behavior require manual acceptance. Network or registry failures must remain observable rather than counted as successful publication. Hardware health checks do not replace listening tests.

## Migration Plan

Run automated checks before deployment. Preserve configuration/session data and a viable rollback image. Recover the affected service on failure without reinstalling the host.
