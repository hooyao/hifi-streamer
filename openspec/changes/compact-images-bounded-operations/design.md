# Design

## Context

See proposal.md and the architecture/source contract. The target is a systemd Linux host with Python 3.11, rootless Podman and USB audio.

## Goals / Non-Goals

**Goals:** Reproducible behavior, isolated failures and explicit acceptance boundaries.

**Non-Goals:** Unimplemented streaming services, arbitrary hardware certification and unverified bit-perfect claims.

## Decisions

Use minimal runtime dependencies and multi-stage builds. Gate uncompressed image sizes at MPD 200MiB, upmpdcli 160MiB, Soloist 180MiB, web 40MiB. Bound agent logs to 1MiB×3, container logs to 2MiB, journal to 32MiB and cache to 128MiB. Update immutable registry digests or verified local image IDs. Check idle output, space, data compatibility and rollback expiry; serialize updates and restore service plus metadata on failure. CI image content size and device-inspected storage size are distinct metrics.

MPD HTTP receive buffering stays at 16KiB for the qualified libcurl runtime. Implicit per-file caching is capped at 16MiB independently of the 128MiB container budget. CI rejects sustained HTTP anonymous-memory growth using a large virtual WAV and timed null output.

## Risks / Trade-offs

External authentication and physical audio behavior require manual acceptance. Network or registry failures must remain observable rather than counted as successful publication. Hardware health checks do not replace listening tests.

## Migration Plan

Run automated checks before deployment. Preserve configuration/session data and a viable rollback image. Recover the affected service on failure without reinstalling the host.
