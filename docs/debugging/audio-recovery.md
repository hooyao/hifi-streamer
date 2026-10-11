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
| `recovery_exhausted` | Automatic restart budget exhausted; inspect the cause and request an authorized retry. |

The UI displays persistent output errors. The authenticated status endpoint includes `output.hardware`, `output.health` and `output.recovery`. Missing hardware revokes output ownership; software cannot repair an absent cable, unpowered DAC or persistent USB protocol failure.

## Repair policy

Three stable one-second observations precede service recovery. The agent regenerates stale MPD mappings and clears affected start-limit failures, then repairs routing. WirePlumber is restarted only if the sink cannot be assigned. A persistent stalled output or failed narrow repair escalates to recreating the dedicated account's PipeWire/Pulse session and optional player. The agent stays running; configuration/session files and immutable images are preserved.

Automatic recovery permits three disruptive attempts per rolling ten minutes, with 5/20/60-second backoff and a 120-second attempt deadline. The last three timestamps persist across agent restarts. Missing hardware does not repeatedly restart the stack. Manual retry permits one bounded attempt, limited to once per minute. Recovery never resets the USB controller, changes firmware or reboots the host.

Recovery restores paused readiness with no owner. Request playback again after it finishes. Software volume is preserved when recreating an existing DAC sink; if no valid volume can be read, the existing host policy/configuration applies. No automatic unity-gain change is made. A full session recreation affects other audio clients in the same account, which is why a dedicated service account is required.

## Verification

Run Linux unit tests and the integration procedures in the [test guide](../testing/README.md). Deterministic tests cover missing/partial devices, generations, retry persistence and route failures. Hardware acceptance must additionally verify physical unplug/replug, power cycles and playback after recovery. A passed software test does not establish cable health or listening quality.
