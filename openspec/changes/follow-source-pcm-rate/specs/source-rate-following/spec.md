# Spec Delta

## Purpose

Match the selected output to decoded source PCM without imposing an unrelated fixed Spotify rate.

## ADDED Requirements

### Requirement: Match observable source PCM

When Spotify acquires output, the system SHALL use the observable Soloist PCM rate if supported by the selected DAC and host clock configuration. It SHALL expose that decoded rate separately from hidden encoded-file metadata and SHALL NOT silently replace an unknown or unsupported rate with 44100Hz.

#### Scenario: Available 48000Hz decoded stream
- **WHEN** Soloist supplies unambiguous supported 48000Hz PCM
- **THEN** the selected PipeWire graph and USB output use 48000Hz

#### Scenario: Upstream decoder outputs 44100Hz
- **WHEN** Soloist supplies 44100Hz PCM
- **THEN** output uses 44100Hz without asserting the encoded file had that rate or was bit-perfect

#### Scenario: Unsupported or ambiguous format
- **WHEN** the source PCM rate is malformed, unsupported or ambiguous
- **THEN** source status reports the error, no fixed-rate fallback is used, and current DLNA playback is not revoked by the invalid request

### Requirement: Follow rate changes during playback

While Spotify owns output, a supported changed decoded rate SHALL update the selected output within bounded observations. Clock changes SHALL preserve gain/mute, keep global force-rate unset, and release source-owned rate requests on handoff to DLNA. Stable unchanged formats SHALL NOT reopen the DAC every poll.

#### Scenario: 44100Hz changes to 96000Hz
- **WHEN** active decoded PCM changes from 44100Hz to supported 96000Hz
- **THEN** output follows 96000Hz after observation without changing listening gain

#### Scenario: Handoff to direct playback
- **WHEN** DLNA obtains ownership
- **THEN** Spotify's node rate request is cleared and direct ALSA can use the DLNA format

#### Scenario: No stream yet
- **WHEN** playback intent arrives before a decoded PCM stream is observable
- **THEN** status reports pending format and acquisition waits rather than guessing a rate or declaring healthy hardware output
