# Design

## Context

See proposal.md and the architecture/source contract. The target is a systemd Linux host with Python 3.11, rootless Podman and USB audio.

## Goals / Non-Goals

**Goals:** Reproducible behavior, isolated failures and explicit acceptance boundaries.

**Non-Goals:** Unimplemented streaming services, arbitrary hardware certification and unverified bit-perfect claims.

## Decisions

Use a Python 3.11 standard-library host agent and a static web container proxying a private Unix socket. Keep service commands in adapters and load built-in declarations through the registry. Persist configuration atomically and secrets with mode 0600; require Origin validation and CSRF for writes; control-plane authentication is deferred. This avoids a large always-on framework.

## Risks / Trade-offs

External authentication and physical audio behavior require manual acceptance. Network or registry failures must remain observable rather than counted as successful publication. Hardware health checks do not replace listening tests.

## Migration Plan

Run automated checks before deployment. Preserve configuration/session data and a viable rollback image. Recover the affected service on failure without reinstalling the host.
