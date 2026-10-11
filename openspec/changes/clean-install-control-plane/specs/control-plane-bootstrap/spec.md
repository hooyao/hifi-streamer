# Spec Delta

## Purpose

Provide authenticated configuration and actionable output status on a fresh host before a usable audio device has been selected.

## ADDED Requirements

### Requirement: Hardware-independent control-plane startup

After validated images are recorded and deployment is applied, the system SHALL enable the web control plane even when no DAC is selected or the selected DAC is absent. Audio services SHALL remain stopped until the selected DAC is usable.

#### Scenario: Fresh installation with no selected DAC
- **WHEN** deployment is applied with no selected DAC
- **THEN** the web login is available, authenticated status reports `dac_unconfigured`, and no audio service is started

#### Scenario: Selected DAC is missing
- **WHEN** deployment is applied with a persisted selection whose DAC is absent
- **THEN** authenticated status reports `dac_missing`, the web remains available, and audio services remain stopped

#### Scenario: Configure available hardware
- **WHEN** an operator selects an available DAC through the authenticated configuration page
- **THEN** the audio services are generated and output becomes ready without requiring a manual web service restart
