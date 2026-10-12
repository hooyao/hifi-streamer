# Design

## Context

Soloist uses a Pulse stream and has no sample-rate CLI option. Current acquisition passes 44100 to the selected-node clock controller. Pro Audio hardware can require an explicit node request to avoid a hardware-default rate. Device probes showed matching graph/USB at 44.1, 48 and 96kHz with global force-rate zero.

The official Soloist announcement advertises lossless up to 24-bit/44.1kHz. Current music observed at 44.1kHz is expected; higher synthetic transport rates do not establish upstream Spotify high-rate availability.

## Goals / Non-Goals

**Goals:** Follow decoded PCM on acquisition and later format changes, validate supported output rates, preserve ownership and volume, and keep required DLNA usable.

**Non-Goals:** Reverse resampling inside Soloist, infer encoded Spotify metadata, certify bit-perfect audio, add Native DSD, or change DAC firmware/device trees.

## Decisions

Read Pulse stream sample specifications filtered by source binary; prefer uncorked streams and require one distinct rate. Cache successful validation for an unchanged rate within an adapter incarnation. Validate against the selected USB PCM capabilities and active PipeWire allowed-rates configuration before ownership can be revoked.

The adapter publishes decoded pcm_rate and distinguishes pending stream creation from a malformed/unsupported format. Runtime grants only a healthy supported request. Invalid formats pause the optional source, park its output only if it owns the DAC, and publish a persistent source error without spending global repair budget.

On a changed rate, park the active source stream on standby before suspending the selected sink; an active Pulse client can otherwise retain the hardware. Verify release, change the selected node request, restore gain/mute, move the stream back and suspend standby before resuming output. Unchanged rates do not reconfigure output. The existing direct handoff clears this request, including after agent restart. No global force-rate is written.

## Risks / Trade-offs

- Upstream may always decode at 44.1kHz → expose the observed PCM and document that original-file rate cannot be recovered.
- Format change is observed by polling → allow a bounded transition interval; do not claim gapless switching or per-sample identity.
- Device lacks a source rate → report unsupported instead of hidden resampling; leave required DLNA available.
- Paused or replaced streams can overlap → report ambiguity rather than selecting an arbitrary rate.

## Migration Plan

Deploy host-agent code with existing images. Existing gains/configuration persist. Rollback restores the previous adapter policy; paused handoff clears surviving clock requests before either version starts new output.
