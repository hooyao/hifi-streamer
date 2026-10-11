# Design

## Context

See proposal.md and the architecture/source contract. The target is a systemd Linux host with Python 3.11, rootless Podman and USB audio.

## Goals / Non-Goals

**Goals:** Reproducible behavior, isolated failures and explicit acceptance boundaries.

**Non-Goals:** Unimplemented streaming services, arbitrary hardware certification and unverified bit-perfect claims.

## Decisions

Build MPD in Alpine stages with HTTP, ALSA, PCM/FLAC/MP3/AAC/Vorbis/Opus and DSD support, avoiding the packaged build's large optional dependency set. Use packaged upmpdcli. MPD direct output targets ALSA hw; null output supports handoff intent without consuming unattended tracks. Test SSDP/SOAP with a Range-capable HTTP source. Qualify PCM 44.1/48/96kHz, FLAC and DSD64 DoP, plus long-duration and controller acceptance. Service recovery uses paused queues and normal output arbitration.

## Risks / Trade-offs

External authentication and physical audio behavior require manual acceptance. Network or registry failures must remain observable rather than counted as successful publication. Hardware health checks do not replace listening tests.

## Migration Plan

Run automated checks before deployment. Preserve configuration/session data and a viable rollback image. Recover the affected service on failure without reinstalling the host.
