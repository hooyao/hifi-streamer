# Spec Delta

## Purpose

Make DLNA a reliable required source using real discovery and protocol controls with source-rate audio output. This capability defines observable behavior, failure handling and repeatable acceptance criteria for device validation and future extensions.

## ADDED Requirements

### Requirement: Persistent renderer
The system SHALL keep the DLNA renderer discoverable and controllable while Spotify is missing, unhealthy or updating.

#### Scenario: Spotify absent
- **WHEN** Spotify authentication is not configured
- **THEN** SSDP discovery and DLNA playback succeed

### Requirement: Audio format preservation
The system SHALL output supported PCM at its source sample rate through ALSA hw without software volume; DSD SHALL use device-qualified DoP.

#### Scenario: PCM output
- **WHEN** a 96kHz test stream plays
- **THEN** USB output reports 96kHz

### Requirement: Transport control
The renderer SHALL support URI, play, pause, stop and supported seek operations with consistent playback state and position.

#### Scenario: Pause and resume
- **WHEN** a controller pauses and resumes playback
- **THEN** state and hardware output reflect the commands

### Requirement: MPD restart recovery
The system SHALL restart MPD after an isolated abnormal exit, subject to bounded service restart limits, and SHALL allow subsequent controller playback to reacquire direct DAC output. Restored queues SHALL remain paused until a controller requests playback.

#### Scenario: Abrupt MPD exit
- **WHEN** MPD is killed during DLNA playback and its network source remains available
- **THEN** the service restarts, and subsequent controller playback produces the source sample rate with advancing position and no MPD output error

#### Scenario: Direct output disabled before restart
- **WHEN** MPD restarts with direct output previously disabled
- **THEN** a subsequent DLNA Play is observed through standby and normal arbitration restores direct DAC output
