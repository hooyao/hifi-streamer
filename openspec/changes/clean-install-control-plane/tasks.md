# Tasks

## 1. Bootstrap behavior

- [x] 1.1 Generate and enable the bounded web service before DAC-dependent generation; add regression coverage for fresh unset selection, absent selected hardware and subsequent available hardware; update both operating-document editions.
- [x] 1.2 Add fail-before-write account preflight with meaningful root/dependency/subordinate-range tests; document account renames, validated image import and separate host/session volume in both languages.
- [x] 1.3 Publish all source states before hardware readiness and preserve optional unconfigured status across stale observations; verify no network calls in status and disabled-source redaction of stale playback.
- [ ] 1.4 Wait for transient control-socket unavailability during cold startup without spending the repair budget; test success, deadline and hardware cancellation, then verify real host reboot, paused readiness, persisted unity gain and fresh playback.
- [ ] 1.5 Prevent a late MPD resume from overriding Pause after direct output becomes observable; reproduce the race with an injected controller pause and pass real pause/seek/stop and both source handoffs.
- [ ] 1.6 Publish per-run/attempt multi-architecture release refs and protect stable aliases from feature-branch dispatch; document mutable compatibility tags in both languages and qualify a real dispatched build against its exported image IDs.

## 2. Acceptance

- [x] 2.1 Verify clean-host web login, authenticated unconfigured/missing status, stopped audio and persistent web availability after reboot.
- [x] 2.2 Verify selection of a connected DAC through the API reaches ready output and passes PCM/FLAC/DoP playback without manually restarting web.
- [ ] 2.3 Pass Linux unit tests, strict OpenSpec checks and required PR CI.
- [x] 2.4 Run a reversible application clean-install regression on the host: empty configuration/data, optional Spotify disabled, web authentication, first DAC selection, fresh audio-unit startup, idempotent reinstall and private-state restoration; require subsequent playback verification.
- [ ] 2.5 Verify immutable GHCR images can be pulled without registry credentials; record deployment limitations if visibility cannot be changed.
