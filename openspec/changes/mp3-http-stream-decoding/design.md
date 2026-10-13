# Design

## Context

MPD 0.24.5's mpg123 plugin exposes HTTP stream callbacks but accepts only SEEK_SET. libmpg123's frame-validation read-ahead calls SEEK_CUR on seekable input, producing cannot-seek/getformat errors before playback. The plugin also lacks audio/mpeg MIME registration. Current images retain a 16MiB implicit-cache cap and a 128MiB container limit.

## Goals / Non-Goals

**Goals:** Repair the existing decoder callback, validate real HTTP MP3, retain source-rate output and resource budgets.

**Non-Goals:** Add FFmpeg or a second decoder, redesign arbitration, change software gain, or fix DAC USB enumeration during host reboot.

## Decisions

Translate SET/CUR/END to one absolute target while holding the input mutex. Reject unknown END and values outside signed off_t before addition, avoiding signed overflow and unsafe negative-to-unsigned conversion. Return the current position without seeking for a no-op query. Invoke the existing stream Seek with the held lock. Register audio/mpeg for extensionless endpoints.

Keep this as a focused GPL-2.0-or-later patch on the pinned upstream MPD source. Retaining mpg123 avoids adding dependencies or changing output sample behavior. Switching decoder or enabling FFmpeg would hide the callback defect and expand the image surface.

Generate valid silent MPEG-1 Layer III frames with zero side information plus bounded ID3 padding. Validate the fixture through local-file decoding before comparing HTTP failure/success. Native CI exercises CBR/VBR/tagged/extensionless/Range/sequential cases under null output with finite deadlines, then retains the existing HTTP memory gate. Device acceptance uses DLNA SOAP and controller-provided URLs; private media URLs are redacted from output.

An additional known-length 20,850,000-byte CBR fixture exceeds the 16MiB full-file cache cap. Generate only requested chunks from a repeated frame; retain neither the full payload nor a frame list. Forward and backward positioning must advance at the requested time and each produce a new nonzero HTTP Range request, with requests recorded per seek. Small cached fixtures alone cannot qualify this transport path.

Observe both conditions within one finite deadline after each asynchronous seek. MPD may report the requested timestamp before the decoder has issued its HTTP request; require advancement beyond that timestamp rather than immediately inspecting requests or accepting the optimistic position alone.

## Risks / Trade-offs

- Seek translation can overflow or misuse mutable offsets → lock input state and test boundary/unknown-size requests plus actual HTTP transport.
- Synthetic MPEG frames can be invalid → require successful local decoding and advancing position with the same decoder.
- Controller URLs can expire or contain tokens → keep them private and report structural/error summaries only.

## Migration Plan

Build native images in GitHub Actions, qualify the ARM64 artifact, preserve the previous immutable image reference and replace MPD through the maintenance transaction. Return to paused readiness before controller playback. Roll back the reference if required-source qualification fails. No device-tree, clock or secret migration is required.
