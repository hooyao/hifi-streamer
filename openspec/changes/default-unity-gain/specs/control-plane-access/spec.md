# Spec Delta

## Purpose

Allow immediate device operation during development without a password while preventing unintended requests from other browser origins.

## ADDED Requirements

### Requirement: Password-free control plane
The current control plane SHALL expose status and device controls without password login or session cookies. Installation SHALL NOT generate a control-plane password. Source-service credentials SHALL remain private and source authentication SHALL remain unchanged.

#### Scenario: Open the page
- **WHEN** a client opens the deployed web page
- **THEN** status and controls are available without a login form, password or session

#### Scenario: Source secret configured
- **WHEN** a Soloist API key is configured
- **THEN** status exposes only its presence and never its value

### Requirement: Same-origin mutations
State-changing requests SHALL require a matching Origin and the current CSRF token obtained from status. Status observation SHALL remain responsive independently of slow audio operations.

#### Scenario: Cross-origin request
- **WHEN** a mutation has a different Origin or an absent/invalid CSRF token
- **THEN** the API rejects the request without invoking the action
