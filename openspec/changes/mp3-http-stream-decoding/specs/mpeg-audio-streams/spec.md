# Spec Delta

## Purpose

Decode controller-provided HTTP MPEG audio reliably while preserving bounded resources and the renderer's transport behavior.

## ADDED Requirements

### Requirement: HTTP MP3 decoding
The required renderer SHALL decode valid MP3 over HTTP, including constant/variable bitrate, ID3 metadata and extensionless audio/mpeg URLs. Seekable sources SHALL support play, pause/resume and positioning; sequential sources SHALL support playback without requiring random access.

#### Scenario: Tagged MP3 with HTTP Range
- **WHEN** a controller submits a valid tagged MP3 with Range support
- **THEN** decoding starts, position advances, and supported pause/resume/seek operations succeed

#### Scenario: Sequential MP3 without an extension
- **WHEN** a server provides valid audio/mpeg without a filename extension or Range support
- **THEN** the renderer starts and advances playback without falsely reporting an unrecognized file

### Requirement: Bounded input seeking
The MPEG input callback SHALL translate valid absolute, relative and known-end offsets safely. It SHALL reject negative targets, integer overflow and unknown-end requests without allocating full-file caches or invalidating other sources.

#### Scenario: Relative frame validation
- **WHEN** the decoder reads ahead and seeks relative to its current position
- **THEN** valid offsets reach the requested byte position and position queries do not reopen the stream

#### Scenario: Invalid seek request
- **WHEN** the requested target is below zero, exceeds the signed offset range or requires an unknown end
- **THEN** the callback returns a seek failure without invoking the underlying stream at an invalid position
