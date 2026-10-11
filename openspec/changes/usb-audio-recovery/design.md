# Design

## Context

See [proposal](proposal.md) and [requirements](specs/audio-recovery/spec.md). Runtime currently uses sound-card presence/card number, synchronously runs deployment under its status lock, and equates adapter playback with output health. Startup without a DAC can be treated differently from hotplug; same-number device replacement can retain stale mappings. Hardware routing suppresses release errors and may stop Soloist, but does not supervise its later recovery. Restarting WirePlumber alone can recreate a sink while the player's stream remains unlinked; a complete host session recreation may be necessary. USB `-71` is evidence of protocol failure, not proof of a specific cable/controller defect.

## Goals / Non-Goals

**Goals:** Restore infrastructure automatically after recoverable faults, publish truthful errors, preserve volume/session data and integrate future adapters without service-specific commands in the arbiter.

**Non-Goals:** Repair a physically absent/malfunctioning DAC, infer listening quality from meters, change CPU/kernel/USB power settings, reboot the host, resume unattended playback or fix decoder/media-server errors.

## Decisions

### Observe hardware independently of players

Introduce a lightweight recovery module used by Runtime. Every one-second hardware tick observes configured USB identity, enumeration incarnation (sysfs bus/device identity), playback-device nodes and current card/PCM mapping. Track node device/inode identities to detect mapping changes. Distinguish `unconfigured`, `missing`, `enumerating`, `ready` and `unknown`; never equate a failed scan with absence. Invalidate the generation on disappearance or changed incarnation, including same-card reconnect. Require three stable observations before service repair. Kernel-log matching is bounded supporting diagnosis, not the trigger: log permissions and ring-buffer rotation make it unsuitable as primary state.

Separate hardware observation from potentially slow adapter polling. Cache timestamped adapter/route snapshots; mark stale observations unknown. Otherwise a Soloist timeout could prevent the five-second missing-DAC report.

### Add control-plane output health

Extend status additively with `output.hardware`, `output.health` and `output.recovery`: selected/observed identity, availability, phase, reason code, attempt count, next retry and authenticated-retry eligibility. Existing owner/state remain compatible. Reasons include `dac_unconfigured`, `dac_missing`, `dac_not_ready`, `discovery_failed`, `route_missing`, `service_failed`, `output_stalled`, `maintenance_busy` and `recovery_exhausted`. Publish error from the latest hardware observation even when adapters report playing/healthy. The web UI shows a persistent output banner with stage-specific instructions. A retry endpoint uses the existing login/Origin/CSRF controls, accepts no shell/service arguments and does not treat a missing DAC as repairable hardware.

Inspect PCM status for the discovered playback endpoint. For a playing owner, allow ten seconds of startup/transition grace, then require three consecutive route/PCM failures before repair. Spotify checks its stream's actual sink/link against the selected DAC; DLNA checks direct output and running PCM. Silence level is irrelevant. Suspended idle sinks and paused/stopped sources are normal. A decoder/HTTP error without route evidence stays a source error. Readiness means infrastructure is available, not that music is playing or bit-perfect.

### Serialize finite recovery outside the status lock

Use one background recovery worker with cancellation by device/config generation. Publish state under short locks; subprocesses have explicit timeouts and run outside Runtime's status lock. A single pending request coalesces repeated observations. On physical loss, revoke ownership immediately and pause through bounded commands; stop only a player that cannot be controlled safely. Keep upmpdcli and web/control services available. Never recursively call the arbiter while recovery owns the maintenance lock.

Use a shared file lock for recovery, configuration service regeneration and updates, including the existing update transaction. Hold it for the complete disruptive transaction and recheck generation/config after acquisition. Move configuration regeneration out of the status lock with explicit applying status. If maintenance is busy, wait and keep the hardware fault visible. A DAC disappearing during an update still revokes ownership; cancellation/rollback remains the update transaction's responsibility. Do not change image references during recovery.

### Escalate only as needed

| Stage | Trigger and action | Verification |
| --- | --- | --- |
| Wait for hardware | Missing/incomplete DAC: no repeated stack restarts | Three stable usable observations |
| Reconcile services | Stable returning DAC: pause sources, regenerate affected MPD device mappings, explicitly reset-failed/start affected units, close old adapter transports and create new instance IDs | MPD control/standby available; configured source controls respond or report source-specific failure |
| Repair route | USB/ALSA ready but selected PipeWire sink missing: restart WirePlumber once; if sink exists but stream is unlinked, recreate the affected optional player and reapply route without playing | Selected sink exists and player route can be assigned |
| Recreate session | Narrow repair fails: quiesce sources, stop optional Pulse players, restart the account's PipeWire/Pulse/WirePlumber, wait for sockets/sink, restart eligible players, renew adapters and standby | Required DLNA and output routing ready; optional failures isolated |
| Manual intervention | Budget exhausted or physical hardware stays unusable | Actionable persistent error and authorized retry |

Full-session recreation affects the dedicated service account's audio clients, so it follows a qualified narrow repair rather than running on every hotplug. Restarting the agent itself is unnecessary; the supervisor must survive and observe its own repair. A missing optional player's authentication or exit-10 expiry is not a host-stack failure. Inspect service Result/start-limit state before clearing it, and respect the recovery budget instead of defeating systemd limits every tick.

On the qualified PipeWire version, newly created Soloist streams need the real DAC as their default target. Repair parks existing streams on standby, suspends hardware and then restores the real sink as the default for future streams. Playback remains paused; fresh intent enters arbitration before hardware suspension is released. Recreating players while standby remains the default can leave their first stream unlinked.

An attempt is one disruptive transaction, including finite escalation stages. Use 5/20/60-second retry delays, at most three attempts per rolling ten minutes and at most one full-stack recreation per attempt. Each attempt has a 120-second deadline. Persist the last three attempt timestamps atomically in private state so agent restarts do not replenish the budget; record boot identity and handle wall-clock changes conservatively. Keep a rolling global account budget across USB flapping as well as per-incarnation stage tracking. A fresh stable incarnation permits reconsideration but does not bypass the global budget. Reset successful stage state after 60 seconds healthy; keep budget timestamps until expiry. Manual authenticated retry permits one bounded attempt subject to a 60-second rate limit and does not reboot/reset hardware.

### Restore paused readiness and preserve settings

Save logical source state and generation before repair; never use cached `playing` as permission to resume. Pause/stop eligible sources, preserve configured initial volume and current software volume across host-session recreation, and clear stale intent/seen state by renewing adapter instance IDs. Snapshot/restore volume only for the same selected DAC; do not write unity gain automatically. Persist configuration, API keys, queues and authenticated sessions. Rebuild mappings only after nodes are usable. Ready output has no owner; a fresh controller play transition after the ready baseline enters normal arbitration. Held pre-recovery play requests are cancelled and the UI explains that playback must be requested again.

### Test the actual failure boundaries

Unit tests inject hardware/endpoint snapshots, fake monotonic time, subprocess results and route graphs. Cover cold start absent, partial enumeration, discovery failure, same-card replacement, disappearance mid-repair, stale work, failed service reset, player stop, missing sink/unlinked stream, healthy idle/silent playback, source errors, budget persistence, optional-source absence/expiry and lock contention. Verify status remains responsive during a blocked simulated repair.

Host integration injects stale route/player state and systemd start-limit failure, verifies automatic staged repair without manual service restarts, then DLNA 44.1/48/96kHz/FLAC/DoP and Spotify 44.1kHz handoff. Manual acceptance disconnects/reconnects and power-cycles the DAC with hardware volume low. Normal USB removal can be injected; do not manufacture electrical `-71` faults or short hardware. Hardware that never enumerates must produce an error, not a fabricated recovery success. Listening remains manual. Reports remain ignored or CI artifacts.

## Risks / Trade-offs

- False stall detection → grace, repeated observations and physical route checks; do not classify silence or content errors as stack faults.
- Shared account audio interruption → dedicated account requirement and narrow-first escalation.
- Controller intent races → generation invalidation and paused ready baseline; requests during recovery must be retried.
- Endless flapping or crashes → persistent global budget, bounded logs and explicit operator state.
- Device vanishes during maintenance → revoke output promptly; shared lock prevents conflicting service mutations.

## Migration Plan

Add the supervisor, additive API and protected retry endpoint with deterministic tests, then integrate deployment/update locking and the web banner. Qualify failure injection and physical hotplug before enabling automatic disruptive repair by default. Keep existing image references and data layout. Rollback restores the prior agent/web version and service generation; recovery history contains no credentials and can remain unused by the prior version. Do not mark acceptance tasks complete from mocked tests alone.
