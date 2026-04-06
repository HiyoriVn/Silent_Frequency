# Research Protocol

## Purpose

This document defines how Silent Frequency should be used as a research artifact.

It exists to keep implementation, data collection, and evaluation consistent.

## Research Questions

The exact research questions may evolve, but the protocol assumes interest in areas such as:

- adaptive difficulty effectiveness
- gameplay-enhanced language learning engagement
- interaction traces in educational escape-room systems
- backend-owned progression reliability

## Experimental Conditions

At minimum, the project currently supports:

- `static`
- `adaptive`

Gameplay v2 should be treated as a separate experimental factor when used in evaluation.

## Artifact Validity Requirements

For a valid research run:

- the session flow must be reproducible
- content versions must be known
- the feature-flag state must be recorded
- telemetry logging must be enabled and verified
- frontend and backend versions must be traceable

## Data Collection Requirements

Record at least:

- session condition
- session mode
- attempt outcomes
- response times
- hint usage
- progression completion
- telemetry availability status

## Threats to Validity

Typical threats include:

- seed/content drift between runs
- undocumented feature-flag differences
- frontend/backend contract mismatch
- telemetry truncation affecting interpretation
- small pilot size or biased participant selection

## Reproducibility Checklist

For each experimental run:

1. record commit hash
2. record migration state
3. record content version assumptions
4. record environment configuration
5. record feature-flag values
6. record validation steps performed before data collection

## Reporting Guidance

When writing thesis or paper material:

- clearly separate implemented behavior from proposed future behavior
- distinguish observational telemetry from canonical scoring data
- state limitations of pilot-scale evidence
- avoid claims that exceed the measured data
