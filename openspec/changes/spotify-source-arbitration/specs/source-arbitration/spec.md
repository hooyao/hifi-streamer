# Spec Delta

English | [简体中文](../../translations/zh-CN/specs/source-arbitration/spec.md)

## Purpose

Integrate optional Soloist playback with a required DLNA source while keeping DAC arbitration extensible beyond two sources. This capability defines observable behavior, failure handling and repeatable acceptance criteria for device validation and future extensions.

## ADDED Requirements

### Requirement: Exclusive handoff
The system SHALL release the previous hardware path before granting DAC access. Failed handoff SHALL revoke ownership and silence output.

#### Scenario: Release fails
- **WHEN** the old source cannot confirm hardware release
- **THEN** the new source is not granted hardware output

### Requirement: Extensible ownership
The system SHALL represent owners by stable source IDs and reject events from retired adapter instances.

#### Scenario: Third source
- **WHEN** a compatible third adapter is registered
- **THEN** it can participate without changing the arbitration flow

### Requirement: Optional Spotify
The system SHALL preserve DLNA while Spotify is unconfigured, unauthenticated, stopped or expired and expose its error state.

#### Scenario: No API key
- **WHEN** the host starts without a Soloist API key
- **THEN** DLNA works and Spotify reports unconfigured
