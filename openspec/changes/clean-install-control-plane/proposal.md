# Proposal

## Why

A fresh installation without a selected or connected DAC returns from service generation before creating the web service. Operators cannot use the configuration page to complete setup or inspect the output error.

## What Changes

- Generate and enable the web service independently of DAC selection.
- Keep audio services stopped when the selected DAC is unavailable.
- Verify fresh bootstrap with absent hardware, subsequent configuration and restart.
- Reject incomplete rootless account prerequisites before installing account services.
- Document validated OCI import, separate host/session gain, and image visibility preflight.
- Preserve a qualified multi-architecture image tag per workflow run and attempt; scheduled rebuilds must not erase previous build identities.

## Capabilities

### New Capabilities

- `control-plane-bootstrap`: Configuration and output status availability before audio hardware is usable.
- `qualified-image-release`: Distinct image release identity for each successful build and compatibility alias publication.

### Modified Capabilities

None.

## Impact

`deploy/install.sh`, account preflight, `deploy/manage.py`, deployment regression tests and bilingual operating instructions. Existing API authentication and audio recovery behavior remain in effect; no image content changes are required.
