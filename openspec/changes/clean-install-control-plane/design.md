# Design

## Context

The rootless service generator requires four immutable image references and returns early if discovery cannot match the selected DAC. Web only needs the agent socket, while player units require current ALSA device mappings. See proposal.md for the observed bootstrap failure.

## Goals / Non-Goals

**Goals:** Preserve web availability through fresh setup and absent hardware without starting unsafe audio units.

**Non-Goals:** Reset USB hardware automatically, change authentication, or bypass immutable image validation.

## Decisions

Generate the bounded web unit and enable it before hardware-dependent service generation. Keep the existing shared maintenance lock and stop affected players before the missing-device return. This avoids a second deployment command and makes the existing apply operation sufficient for initial setup.

Retain the existing recovery supervisor for later hardware availability. Do not invent placeholder ALSA mappings or assume a card number to bring up audio services.

Treat failed-state reset as best effort because a newly generated unit may not yet be loaded by systemd. The subsequent checked enable/start command determines whether service startup actually succeeded; existing failed units still receive the reset.

Run read-only account checks before install.sh writes files. Validate local subordinate allocations and their overlap, dependency executables, and user systemd connectivity; verify Podman can initialize the rootless engine. Never automatically reassign ranges belonging to another account. Registry visibility and OCI archive import are explicit deployment prerequisites. Preserve source and host volumes separately; do not silently increase gain on existing installations.

During bootstrap, retry transient socket connection failures under the existing 20-second generation/deadline check. A finite loop also bounds observations under a stationary test clock. This waits for asynchronous container initialization without resetting the persistent disruption budget; invalid protocol responses and permanent errors still enter normal bounded recovery.

## Risks / Trade-offs

- Missing images still prevent application bootstrap → retain explicit immutable-image preflight and document its order.
- Reapplying a selected DAC can stop players → preserve paused recovery and existing configuration semantics.

## Migration Plan

Apply the updated generator using existing immutable images. No image rebuild or private-data migration is needed. Rollback restores the previous generator; existing web units remain usable.
