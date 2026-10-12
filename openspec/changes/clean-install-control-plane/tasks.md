# Tasks

## 1. Bootstrap behavior

- [x] 1.1 Generate and enable the bounded web service before DAC-dependent generation; add regression coverage for fresh unset selection, absent selected hardware and subsequent available hardware; update both operating-document editions.

## 2. Acceptance

- [x] 2.1 Verify clean-host web login, authenticated unconfigured/missing status, stopped audio and persistent web availability after reboot.
- [ ] 2.2 Verify selection of a connected DAC through the API reaches ready output and passes PCM/FLAC/DoP playback without manually restarting web.
- [ ] 2.3 Pass Linux unit tests, strict OpenSpec checks and required PR CI.
