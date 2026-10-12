# Spec Delta

## Purpose

Keep installation artifacts traceable to one qualified image build even when scheduled workflows rebuild the same source revision.

## ADDED Requirements

### Requirement: Per-build multi-architecture identity

A successful image build SHALL publish a multi-architecture release reference containing the source revision, workflow run ID and run attempt. Later workflows building the same revision SHALL preserve earlier release references. Installation SHALL resolve and pin image digests rather than treating compatibility tags as immutable.

#### Scenario: Scheduled rebuild of the same revision
- **WHEN** two successful workflow runs build the same source revision
- **THEN** each run has a distinct qualified release reference and the earlier reference remains available

#### Scenario: Retry a failed architecture
- **WHEN** a failed architecture is rebuilt within a workflow run while another architecture is reused
- **THEN** the final release combines the qualified architecture outputs of that run and records the final run attempt

### Requirement: Protected compatibility aliases

Stable and source-revision compatibility aliases SHALL be published only by main or version-tag workflows. A manually dispatched feature-branch build SHALL publish its qualified release without replacing production aliases.

#### Scenario: Feature-branch release qualification
- **WHEN** a manually dispatched feature-branch workflow succeeds
- **THEN** its per-build release is published and stable/main compatibility aliases are unchanged
