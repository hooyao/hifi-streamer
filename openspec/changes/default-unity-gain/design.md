# Design

## Context

Soloist defaults are duplicated in configuration, deployment, launcher and UI. WirePlumber 0.4 uses linear default-volume 0.064 (40% on the cubic user scale); 0.5 names the setting device.routes.default-sink-volume. Its stored route preference overrides defaults, including preferences created before installation. The API currently creates password sessions and status must remain free of audio-control subprocesses.

## Goals / Non-Goals

**Goals:** Unity defaults, real host-gain control, preservation of later adjustments, immediate password-free operation.

**Non-Goals:** Software mixing for direct DLNA, automatic amplification above 100%, source-authentication changes, new production authentication.

## Decisions

Install version-appropriate WirePlumber default fragments (legacy Lua and modern configuration) with linear unity. Additionally mark fresh application configuration as awaiting one-time host initialization. Recovery initializes its first available sink before ready output and persists completion. Configurations lacking the new marker are treated as existing installations and retain gain. This avoids both stale pre-install 40% state and gain resets on every boot.

Poll actual sink gain in the independent hardware observer; publish a cache keyed by selected DAC/card/generation and expire stale observations. Status itself performs no audio subprocesses. An explicit volume action holds the shared maintenance and control locks, checks readiness/generation, sets only the selected sink, reads the result and completes initialization. WirePlumber persists the route preference; recovery retains its existing snapshot/restore behavior. Mute is observed and preserved.

Keep the host-volume form separate from source configuration and refresh its current value without overwriting an edit. Use a numeric 0–100 control and explicit Apply rather than disruptive source deployment. Missing hardware/route disables it. Explain that DLNA bypasses this control.

Remove sessions/login and password generation. Status publishes a process-scoped CSRF token; same-origin mutations require it. Existing admin.json files are ignored, not copied or displayed. Earlier bootstrap authentication scenarios are superseded by this change; Spotify authentication remains required.

## Risks / Trade-offs

- Unity defaults can be loud → document hardware-volume control and display the 100% defaults clearly.
- Observer data can be stale after hotplug → invalidate by generation, identity, card and age.
- No control-plane authentication → document LAN access explicitly; production authentication is separate work.

## Migration Plan

Apply host files and new web/Soloist images. Keep explicit initial_volume values and WirePlumber state. Old configurations without the initialization marker retain current gain. Rollback requires the prior host source/web pair and does not discard volume or source secrets.
