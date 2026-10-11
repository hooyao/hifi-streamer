# Tasks

## 1. Hardware observation and control-plane errors

- [x] 1.1 Add independent timestamped USB/ALSA observations and device generations; test cold-start absence, unset selection, partial enumeration, discovery failure and same-card replacement with fake hardware/time.
- [x] 1.2 Publish additive hardware/output/recovery status and persistent web error banners; test `dac_missing` reporting within five seconds despite slow player polling, unknown discovery state, API compatibility and bilingual operating documentation.

## 2. Bounded recovery and maintenance coordination

- [x] 2.1 Add the cancellable recovery worker, three-observation debounce, deadlines/backoff and persistent global attempt budget; test flapping, worker cancellation, clock/boot changes, budget exhaustion and responsive status during blocked repair; document stages and limits in both product-documentation languages.
- [x] 2.2 Serialize configuration, updates and recovery through a shared maintenance lock without holding the status lock during subprocesses; test contention, stale config/device work, update rollback preservation and immediate ownership revocation on device loss.
- [x] 2.3 Add the authenticated rate-limited retry endpoint and UI action; test login/Origin/CSRF, forbidden arbitrary arguments, missing-hardware behavior and bounded manual retry; document operator recovery in both product-documentation languages.

## 3. Service, route and playback restoration

- [x] 3.1 Reconcile stale MPD mappings and affected start-limit failures, renew adapter instances, preserve data/volume and restore paused readiness; test no unexpected resume, same-number nodes, optional disabled/unconfigured/expired sources and stale controller requests; update bilingual architecture/source documentation.
- [x] 3.2 Implement narrow route repair and escalation to complete host-session recreation; test missing sink, unlinked stream, stopped Soloist, fresh socket/transport binding and finite stage/transaction limits; document dedicated-account effects in both product-documentation languages.
- [x] 3.3 Verify playing-owner route/PCM after grace and repeated observations; test wrong/null output, normal idle suspension, silent tracks, transitions and decoder/HTTP errors that must not trigger stack restarts; document output-health semantics in both product-documentation languages.

## 4. Device acceptance

- [x] 4.1 Add and run host fault injection for stale routes, failed/start-limited MPD and unavailable player controls; require automatic repair without manual service restarts, paused readiness and both playback paths; keep redacted reports in ignored/CI artifacts.
- [x] 4.2 Qualify unplug/replug, DAC power cycle, unchanged/changed card enumeration and absent-DAC cold boot; require visible control-plane errors, bounded attempts, no unintended sound, subsequent PCM/FLAC/DoP and Spotify handoff; obtain manual listening confirmation and record support boundaries in bilingual test documentation.
- [x] 4.3 Run Linux unit tests, strict OpenSpec/document checks and relevant image/web checks; submit implementation through PR and confirm required CI passes before accepting the change.
- [ ] 4.4 Verify review regressions: stale hardware clock across agent restarts, healthy retry rejection, missing smoke history and paused bootstrap ownership; require Linux tests, device restart/handoff and required CI to pass.
