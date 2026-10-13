# Proposal

## Why

Valid HTTP MP3 from independent DLNA controllers fails during mpg123 initialization with cannot-seek and unrecognized-file errors. The decoder's custom seek callback rejects relative requests made during frame detection.

## What Changes

- Implement bounded absolute, relative and known-end seek translation in the existing mpg123 input callback.
- Add generated silent MP3 regression streams covering HTTP Range, ID3 metadata, VBR, missing filename extensions and sequential input.
- Require successful MP3 decoding/transport control in native image CI and device DLNA acceptance.
- Preserve current image dependencies, implicit-cache limits and direct ALSA output.

## Capabilities

### New Capabilities

- `mpeg-audio-streams`: Reliable HTTP MP3 decoding and transport controls for the required renderer.

### Modified Capabilities

None; main specifications are not yet archived.

## Impact

MPD build patch, native image qualification, generated HTTP fixtures, device smoke tests and bilingual testing/troubleshooting guidance. No host device-tree or global clock changes are needed. The upstream MPD source retains its GPL-2.0-or-later terms.
