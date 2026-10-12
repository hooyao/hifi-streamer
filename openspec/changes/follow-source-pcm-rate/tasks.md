# Tasks

## 1. Source format and output control

- [x] 1.1 Observe Soloist PCM format, reject ambiguity/unsupported rates before ownership changes and publish pending/error status; unit-test rate parsing, source isolation and no fixed fallback; update bilingual source/operations documentation.
- [x] 1.2 Follow changed rates on the selected node while preserving gain/mute and clearing requests for DLNA; unit-test unchanged polling, transition order, selected-node scope and restart cleanup; update bilingual architecture/troubleshooting documentation.

## 2. Acceptance

- [x] 2.1 Add/run synthetic Pulse transport tests at 44.1/48/96kHz and live format changes; verify client/graph/USB agreement, global force-rate zero, gain preservation and no unexpected recovery budget use; document that synthetic PCM does not qualify upstream Spotify formats.
- [x] 2.2 Verify real Soloist decoded PCM equals DAC output, both DLNA handoffs, restart and manual listening; preserve required DLNA when the optional source format is invalid.
- [ ] 2.3 Pass Linux unit tests, strict OpenSpec/document checks and required PR CI; publish a focused PR depending on the clean-install fixes.
