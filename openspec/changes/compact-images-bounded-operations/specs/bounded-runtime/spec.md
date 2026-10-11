# Spec Delta

English | [简体中文](../../translations/zh-CN/specs/bounded-runtime/spec.md)

## Purpose

Bound resource consumption on memory- and storage-constrained ARM devices while building compact images remotely. This capability defines observable behavior, failure handling and repeatable acceptance criteria for device validation and future extensions.

## ADDED Requirements

### Requirement: Bounded logs
The system SHALL bound application, container and host logs and diagnostic exports so storage does not grow indefinitely with runtime.

#### Scenario: Log pressure
- **WHEN** generated logs exceed their configured capacity
- **THEN** older data rotates and storage remains within budget

### Requirement: Remote compact images
The release process SHALL build ARM64/AMD64 images, verify startup and enforce uncompressed image-size gates.

#### Scenario: Oversized image
- **WHEN** a built image exceeds its component budget
- **THEN** CI rejects publication

### Requirement: Safe module update
The system SHALL update a fixed image when output is idle and storage is sufficient, then roll back failed health to a compatible unexpired version.

#### Scenario: Unhealthy candidate
- **WHEN** the candidate image fails startup
- **THEN** the healthy previous version is restored and DLNA remains available
