# Automatic audio recovery

English | [简体中文](audio-recovery.zh-CN.md)

The agent observes the configured DAC independently of player polling. A live Spotify or DLNA service does not establish that USB output is available. Status reports hardware availability, output health and recovery stage separately.

## Hardware errors

| Reason | Meaning and action |
| --- | --- |
| `dac_unconfigured` | Select a DAC in configuration. |
| `dac_missing` | No matching USB device; check power and connection. |
| `dac_not_ready` | USB exists but playback/control nodes are incomplete; wait for enumeration or inspect kernel USB errors. |
| `discovery_failed` | Observation failed; availability is unknown. |
| `service_failed` | Service repair failed; inspect bounded diagnostics. |
| `output_stalled` | Playing source has no physical output after grace; staged repair is requested. |
| `maintenance_busy` | Update/configuration owns the shared maintenance lock; recovery waits. |
| `recovery_exhausted` | Automatic restart budget exhausted; inspect the cause and request a manual retry. |

The UI displays persistent output errors. The status endpoint includes `output.hardware`, `output.health` and `output.recovery`. Missing hardware revokes output ownership; software cannot repair an absent cable, unpowered DAC or persistent USB protocol failure.

## Repair policy

Three stable one-second observations precede service recovery. The agent regenerates stale MPD mappings and clears affected start-limit failures, then repairs routing. WirePlumber is restarted only if the sink cannot be assigned. A persistent stalled output or failed narrow repair escalates to recreating the dedicated account's PipeWire/Pulse session and optional player. The agent stays running; configuration/session files and immutable images are preserved.

Automatic recovery permits three disruptive attempts per rolling ten minutes, with 5/20/60-second backoff and a 120-second attempt deadline. The last three timestamps persist across agent restarts. Missing hardware does not repeatedly restart the stack. Manual retry permits one bounded attempt, limited to once per minute. Recovery never resets the USB controller, changes firmware or reboots the host.

Manual retry is available only after a failed recovery with the DAC present; healthy output does not offer a disruptive retry action. A healthy agent restart pauses existing playback and establishes an unowned ready baseline without consuming a service-repair attempt. Direct-output handoff clears the selected node's clock request even if a previous agent process set it.

Recovery restores paused readiness with no owner. Request playback again after it finishes. Software volume is preserved when recreating an existing DAC sink; if no valid volume can be read, the existing host policy/configuration applies. No automatic unity-gain change is made. A full session recreation affects other audio clients in the same account, which is why a dedicated service account is required.

Existing player streams are parked on standby during repair. The real DAC remains the default for newly created streams while its sink is suspended; a fresh playback request enters normal arbitration to release suspension and assign ownership. Keeping standby as the default after repair can leave Soloist's first new stream unlinked on the qualified PipeWire version.

The selected DAC uses the PipeWire Pro Audio profile to address its ALSA `hw` PCM. An analog `front` path can invoke ALSA conversion: a 44.1kHz PipeWire format alone does not prove 44.1kHz USB transport. Repair preserves gain/mute when selecting the hardware profile, reconciles an old 48kHz standby node while sources are paused, and transfers streams before releasing DAC suspension. Verify actual USB feedback after cold boot and handoff.

Soloist acquisition explicitly requests 44.1kHz on the selected hardware node and disables that node's multi-rate following while Spotify owns output. Release removes the node rate request and restores following before direct ALSA playback. This is source-owned hardware configuration, not a global PipeWire clock override; other sources must declare their own rate policy. Check sustained USB feedback across tracks as well as the initial sample.

## Verification

Run Linux unit tests and the integration procedures in the [test guide](../testing/README.md). Deterministic tests cover missing/partial devices, generations, retry persistence and route failures. Hardware acceptance must additionally verify physical unplug/replug, power cycles and playback after recovery. A passed software test does not establish cable health or listening quality.
