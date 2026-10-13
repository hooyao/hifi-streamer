# Spec Delta

## Purpose

Restore usable audio infrastructure after selected-DAC or host-session faults, with truthful control-plane errors, exclusive output ownership and bounded automatic repair.

## ADDED Requirements

### Requirement: Missing DAC reporting
The control plane SHALL report the configured DAC as unavailable within five seconds of a successful observation confirming its absence, revoke output ownership and show an actionable error in the web UI. Player/service liveness SHALL NOT imply output readiness. An unset DAC selection SHALL be reported separately from an absent configured DAC.

#### Scenario: Configured DAC absent
- **WHEN** no matching configured DAC is found
- **THEN** the API reports `dac_missing`, output is disconnected with no owner, and the web UI asks the operator to check DAC power and USB connection

#### Scenario: Discovery fails
- **WHEN** hardware discovery cannot complete
- **THEN** the API reports `discovery_failed` with unknown hardware availability instead of asserting the DAC is absent or healthy

#### Scenario: Partial enumeration
- **WHEN** the matching USB device exists but a usable playback endpoint does not
- **THEN** the API/UI report `dac_not_ready` rather than ready output

### Requirement: Stable reconnection
The system SHALL reconcile a reappearing configured DAC using its current device incarnation and usable endpoints, even if its card number is unchanged. Three consecutive successful observations at least one second apart SHALL be required before disruptive recovery. Disappearance during recovery SHALL invalidate the attempt and revoke output.

#### Scenario: Same card number returns
- **WHEN** a DAC returns with its old card number but new device nodes
- **THEN** stale mappings and events are retired before readiness is restored

### Requirement: Bounded staged repair
The system SHALL repair failed services and stale routes using the smallest affected scope first. Recovery SHALL have finite timeouts, backoff and a persistent automatic restart budget of at most three disruptive attempts in ten minutes across device incarnations. Exhaustion SHALL report `recovery_exhausted`; a rate-limited same-origin CSRF-protected retry SHALL permit one bounded attempt.

#### Scenario: Host route missing
- **WHEN** a usable DAC exists but its host audio route remains missing
- **THEN** bounded session repair is attempted and the API reports recovery progress or failure

#### Scenario: Hardware stays absent
- **WHEN** the configured DAC remains absent
- **THEN** the system reports the hardware error without repeatedly restarting the audio stack or rebooting the host

### Requirement: Paused and exclusive restoration
Recovery SHALL restore readiness with output paused and no owner, preserve configuration/session data and software volume, and require a fresh post-recovery controller request before enabling playback. An unconfigured, disabled or expired optional source SHALL NOT block DLNA readiness. Automatic repair SHALL NOT grant simultaneous DAC access.

#### Scenario: Player remains playing on null output
- **WHEN** recovery finishes after the player continued reporting playback without a DAC
- **THEN** stale playback intent is suppressed and sound stays paused until a fresh controller request

#### Scenario: Optional source cannot recover
- **WHEN** DLNA is ready but Spotify authentication or binary expiry prevents startup
- **THEN** DLNA can play and Spotify has its own actionable error

### Requirement: Physical route verification
The control plane SHALL distinguish infrastructure readiness from actual hardware playback. A playing owner SHALL be checked against its selected-DAC route and PCM running state after a startup grace period. Silence, variable sample content or a normal suspended idle sink SHALL NOT alone trigger repair. Unsupported media and inaccessible media URLs SHALL remain source errors.

#### Scenario: Playing source has an unlinked stream
- **WHEN** a source claims to play but repeated observations show no selected-DAC route or running PCM after the grace period
- **THEN** output is reported degraded and bounded recovery is scheduled

### Requirement: Maintenance-safe observable recovery
Recovery SHALL serialize disruptive actions with configuration changes and updates, cancel stale device-generation work and keep status queries responsive. The API/UI SHALL expose recovery phase, reason, attempt count and retry availability without secrets. Diagnostics and attempt history SHALL remain bounded.

#### Scenario: Update is running
- **WHEN** a fault is observed while an update owns the maintenance lock
- **THEN** the fault remains visible and repair waits without changing images or services owned by the transaction
