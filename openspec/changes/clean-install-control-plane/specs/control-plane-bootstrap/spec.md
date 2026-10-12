# Spec Delta

## Purpose

Provide authenticated configuration and actionable output status on a fresh host before a usable audio device has been selected.

## ADDED Requirements

### Requirement: Hardware-independent control-plane startup

After validated images are recorded and deployment is applied, the system SHALL enable the web control plane even when no DAC is selected or the selected DAC is absent. Audio services SHALL remain stopped until the selected DAC is usable.

#### Scenario: Fresh installation with no selected DAC
- **WHEN** deployment is applied with no selected DAC
- **THEN** the web login is available, authenticated status reports `dac_unconfigured`, and no audio service is started
- **AND** status lists required DLNA and optional Spotify with truthful unknown/unconfigured states before any player polling

#### Scenario: Selected DAC is missing
- **WHEN** deployment is applied with a persisted selection whose DAC is absent
- **THEN** authenticated status reports `dac_missing`, the web remains available, and audio services remain stopped

#### Scenario: Configure available hardware
- **WHEN** an operator selects an available DAC through the authenticated configuration page
- **THEN** the audio services are generated and output becomes ready without requiring a manual web service restart

#### Scenario: Apply a different verified web image
- **WHEN** an operator applies deployment references containing a different verified web image
- **THEN** the active web service is recreated with that image, while an unchanged deployment does not restart web

### Requirement: Account installation preflight

The account installer SHALL reject root execution, missing rootless dependencies, unavailable user systemd, and missing or overlapping subordinate ID ranges before writing application configuration or service units. Errors SHALL identify the prerequisite and corrective action without exposing secrets or modifying account allocations.

#### Scenario: Renamed account has stale subordinate mappings
- **WHEN** the current account has no usable subordinate UID or GID allocation
- **THEN** installation fails before writing application files and explains that the account needs unique subordinate ranges

#### Scenario: Valid dedicated account
- **WHEN** dependencies, subordinate ranges and the user systemd manager are available
- **THEN** account installation proceeds without replacing existing credentials or source sessions

### Requirement: Bounded cold-start control readiness

On a host or agent restart with usable hardware, the system SHALL wait for transiently unavailable player control sockets within a cancellable startup deadline before treating their absence as a repair fault. Healthy startup SHALL preserve the existing repair budget and return to paused output readiness.

#### Scenario: Container active before control socket
- **WHEN** a player control socket initially refuses connections and becomes available within the startup deadline
- **THEN** output reaches paused readiness without consuming a repair attempt

#### Scenario: Control socket never becomes available
- **WHEN** a player control socket remains unavailable through the startup deadline
- **THEN** startup exits the wait and reports a fault for the bounded recovery supervisor
