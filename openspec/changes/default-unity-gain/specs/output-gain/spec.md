# Spec Delta

## Purpose

Provide predictable unity-gain defaults and independent user control of the selected host output without changing direct ALSA playback.

## ADDED Requirements

### Requirement: Unity defaults
Fresh application configuration SHALL default Soloist startup volume and the first usable host output to 100%. Explicit existing preferences SHALL be retained during reinstall, restart and recovery.

#### Scenario: First device after installation
- **WHEN** fresh installation acquires its first usable DAC, including a DAC connected later
- **THEN** host output is initialized to 100%/0dB and Soloist startup defaults to 100%

#### Scenario: Existing user preference
- **WHEN** application configuration or host volume already contains an explicit preference
- **THEN** reinstall and recovery retain it instead of repeatedly forcing 100%

### Requirement: Actual host-volume control
The control plane SHALL display actual selected host-output volume and accept integer adjustments from 0 to 100%. This control SHALL affect only the selected PipeWire output, preserve mute, persist through restart and remain independent from Soloist startup volume and direct ALSA DLNA.

#### Scenario: User reduces host gain
- **WHEN** the user submits host volume 60% for a ready DAC
- **THEN** the selected sink reports approximately 60%, other sinks and Soloist startup configuration are unchanged, and the preference survives recovery

#### Scenario: DAC or route unavailable
- **WHEN** the selected DAC, route or current volume observation is unavailable
- **THEN** the UI marks volume unavailable, disables adjustment and does not display a guessed actual volume

#### Scenario: Invalid adjustment
- **WHEN** an adjustment is out of range, fractional, boolean or has unsupported arguments
- **THEN** the API rejects it without changing output
