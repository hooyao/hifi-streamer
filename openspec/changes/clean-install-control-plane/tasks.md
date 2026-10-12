# Tasks

## 1. Bootstrap behavior

- [x] 1.1 Generate and enable the bounded web service before DAC-dependent generation; add regression coverage for fresh unset selection, absent selected hardware and subsequent available hardware; update both operating-document editions.
- [x] 1.2 Add fail-before-write account preflight with meaningful root/dependency/subordinate-range tests; document account renames, validated image import and separate host/session volume in both languages.
- [x] 1.3 Publish all source states before hardware readiness and preserve optional unconfigured status across stale observations; verify no network calls in status and disabled-source redaction of stale playback.
- [x] 1.4 Wait for transient control-socket unavailability during cold startup without spending the repair budget; test success, deadline and hardware cancellation, then verify delayed real player startup, paused readiness and fresh playback without budget consumption.
- [x] 1.5 Prevent a late MPD resume from overriding Pause after direct output becomes observable; reproduce the race with an injected controller pause and pass real pause/seek/stop and both source handoffs.
- [x] 1.6 Publish per-run/attempt multi-architecture release refs and protect stable aliases from feature-branch dispatch; document mutable compatibility tags in both languages and qualify a real dispatched build against its exported image IDs.
- [x] 1.7 Recreate an active web container when its generated unit/image changes while keeping it running across unchanged applies; verify unit regressions and all four running container IDs after a qualified digest deployment.

## 2. Acceptance

- [x] 2.1 Verify clean-host web availability, unconfigured/missing status, stopped audio and persistent web availability after reboot.
- [x] 2.2 Verify selection of a connected DAC through the API reaches ready output and passes PCM/FLAC/DoP playback without manually restarting web.
- [x] 2.3 Pass Linux unit tests, strict OpenSpec checks and required PR CI.
- [x] 2.4 Run a reversible application clean-install regression on the host: empty configuration/data, optional Spotify disabled, web status, first DAC selection, fresh audio-unit startup, idempotent reinstall and private-state restoration; require subsequent playback verification.
- [x] 2.5 Verify immutable GHCR images can be pulled without registry credentials; record deployment limitations if visibility cannot be changed.
- [ ] 2.6 Qualify actual full-host reboot with the selected DAC: require automatic USB enumeration, paused readiness, persisted unity gain and fresh playback without operator DAC power cycle; retain the failed hardware result until the environment issue is resolved.
