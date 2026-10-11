# MPD memory budgets

English | [简体中文](mpd-memory.zh-CN.md)

## Container limit

The deployment generator assigns MPD a 128MiB cgroup limit through `podman run --memory=128m`. This is a project budget, not an MPD or Podman default. It must be qualified against real input/decoder workloads; increasing it alone is not a fix for continuing growth.

The cgroup includes anonymous allocations, mapped libraries, cache and other charged pages. Compare `/proc/<pid>/status`, `smaps_rollup` and cgroup memory counters rather than treating container statistics as heap usage.

## HTTP input

MPD 0.24.5 increases libcurl's receive buffer from 16KiB to 512KiB. With the qualified libcurl 8.14.1 runtime and repeated receive pause/resume, large HTTP WAV input exhibits retained-memory growth. The same content from a local file keeps anonymous memory stable. Stopping/clearing the HTTP input releases the retained allocations.

A minimal libcurl program reproduces growth with 512KiB receive buffers while 16KiB buffers remain stable. This identifies the receive/pause combination; it does not prove the exact internal allocation defect for every libcurl release.

`images/mpd/bounded-input.patch` restores 16KiB receive buffers. CI uses synchronized null output and a virtual large HTTP WAV to reject sustained anonymous-memory growth before publication.

## Implicit file cache

Separately, upstream MPD automatically buffers seekable HTTP files up to 128MiB. A 128MiB cache plus process/decoder overhead cannot safely fit a 128MiB container. The patch limits implicit caching to 16MiB; larger files use the underlying seekable stream. The configured decoded audio buffer remains 4MiB. The optional queue-prefetch input cache is not enabled.

## Reproduction

Use `tests/mpd_memory_probe.py` to compare local and HTTP input with the same 7200-second sparse/virtual WAV. It temporarily isolates other controllers, records RSS subdivisions and cleans up playback/fixtures. Reports stay in ignored output directories.

```sh
python3 tests/mpd_memory_probe.py --case http --seconds 180 --report .local-build/http.json
python3 tests/mpd_memory_probe.py --case local --seconds 180 --report .local-build/local.json
python3 tests/mpd_memory_ci.py <image> --engine podman
```

Keep the 128MiB limit during regression. Require bounded growth and complete the long-duration acceptance; a short stable run does not certify a two-hour workload.

With the patched image, the device's180-second large-HTTP/ALSA probe held anonymous RSS at 7876KiB and total RSS at 25428KiB across all samples. The native ARM64 CI timed-null test held anonymous RSS at 7220KiB. The old-image regression exceeds the growth gate. These short checks validate the targeted correction; long-duration release acceptance remains separate.

## Restart recovery

Memory prevention and recovery are separate requirements. The MPD user service uses `Restart=on-failure` with a five-second delay; an OOM exit is a failure. Three failures within 60 seconds trigger systemd's start limit, so a persistent crash loop remains visible rather than restarting indefinitely. After correcting the cause, use `systemctl --user reset-failed hifi-mpd` and `systemctl --user start hifi-mpd`.

MPD restores its queue paused (`restore_paused "yes"`). Recovery does not automatically resume sound. The standby output is explicitly enabled at startup so a controller's Play remains observable even if direct ALSA output was disabled before the crash. The agent then acquires the DAC and enables direct output through normal arbitration. A controller must resend an unavailable network URI if its source has expired.

Run `python3 tests/mpd_restart_smoke.py --card <runtime-card> --report .local-build/mpd-restart.json` on an idle configured host. The test covers a service restart, SIGKILL with automatic restart, and restart with direct output disabled. Each case requires paused restoration followed by DLNA playback at 44.1/96kHz, advancing position and no MPD output error. SIGKILL verifies the abrupt-exit recovery path; it does not inject a real cgroup OOM or establish listening quality. On the qualified ARM fixture all three cases passed; automatic recovery took approximately eight seconds.
