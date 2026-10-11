# Proposal

## Why

A fresh installation without a selected or connected DAC returns from service generation before creating the web service. Operators cannot use the configuration page to complete setup or inspect the output error.

## What Changes

- Generate and enable the web service independently of DAC selection.
- Keep audio services stopped when the selected DAC is unavailable.
- Verify fresh bootstrap with absent hardware, subsequent configuration and restart.

## Capabilities

### New Capabilities

- `control-plane-bootstrap`: Configuration and output status availability before audio hardware is usable.

### Modified Capabilities

None.

## Impact

`deploy/manage.py`, deployment regression tests and bilingual operating instructions. Existing API authentication and audio recovery behavior remain in effect; no image content changes are required.
