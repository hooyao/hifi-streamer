# Tasks

## 1. Decoder and regression

- [ ] 1.1 Reproduce the failure with valid local/HTTP silent MP3, repair bounded SET/CUR/END seeking and MIME registration, and pass native CBR/VBR/ID3/Range/sequential/extensionless playback/control regressions; document the error and decoder contract in both languages.
- [ ] 1.2 Add HTTP MP3 to real DLNA smoke and native image CI; pass fixture, seek-boundary, Linux unit, strict OpenSpec, whitespace, image-size and existing memory gates.

## 2. Device acceptance

- [ ] 2.1 Deploy the qualified ARM64 image with an immutable rollback reference; pass source-rate MP3 SOAP controls, required PCM/FLAC/DoP and both source handoffs; verify LMS and Audio Station MP3 with redacted diagnostics and manual listening if needed.
- [ ] 2.2 Publish the focused PR and pass required CI; preserve the separate unqualified USB cold-boot limitation and do not rerun the cancelled long-duration test.
