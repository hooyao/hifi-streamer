# Spec Delta

English | [简体中文](../../translations/zh-CN/specs/source-control/spec.md)

## Purpose

Provide a shared source contract and lightweight control plane so new services can reuse DAC discovery and ownership. This capability defines observable behavior, failure handling and repeatable acceptance criteria for device validation and future extensions.

## ADDED Requirements

### Requirement: Independent source state
The system SHALL expose running, authentication, playback, output and health separately for each source. An unreachable source SHALL report unknown playback rather than stopped.

#### Scenario: Optional source unavailable
- **WHEN** an optional source becomes unreachable
- **THEN** DLNA remains independently queryable and the unavailable source reports unknown

### Requirement: Configuration authorization
The system SHALL restrict configuration writes to authenticated sessions, hide secrets and reject unknown modules, invalid configuration and cross-origin requests.

#### Scenario: Invalid configuration
- **WHEN** a write selects an unknown DAC or source
- **THEN** the write fails and the previous configuration is retained

### Requirement: Stable DAC binding
The system SHALL identify the DAC by USB identity, resolve changed card numbers at runtime and stop hardware output on disconnection.

#### Scenario: Card number changes
- **WHEN** the same USB DAC re-enumerates
- **THEN** the binding still identifies the original DAC
