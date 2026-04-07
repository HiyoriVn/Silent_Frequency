<!-- CHANGELOG: pass-2 canonical rewrite preserving research validity, evaluation discipline, and cross-phase plan intent -->

# Research Protocol

## Scope

This document defines how Silent Frequency should be treated as a research artifact.

It exists to keep:

- implementation behavior
- data collection
- telemetry interpretation
- evaluation procedures
- pilot and thesis reporting

consistent and reproducible.

---

## 1. Research Purpose

Silent Frequency supports research in adaptive educational gameplay and software-engineering-backed interactive learning systems.

In the current thesis prototype, the artifact is specifically intended to support questions about:

- whether a room-based chapter can support English-learning tasks in a coherent gameplay flow
- whether backend-owned adaptive support can be integrated without breaking gameplay structure
- how players interact with puzzle, clue, and support systems
- how mastery-aware adaptation affects pacing, hint use, or challenge level
- whether the prototype is stable enough for pilot-scale controlled evaluation

### Scope Rule

The current thesis prototype is not a standardized proficiency-testing system.

It should be treated as a prototype for adaptive learning support inside a chapter-based game experience.

---

## 2. Research Conditions and Factors

At minimum, the project currently supports:

- `static`
- `adaptive`

Gameplay mode should be treated as a separate factor:

- `phase3`
- `gameplay_v2`

### Important Rule

Do not silently mix gameplay mode and condition in later analysis.

Recommended segmentation:

- Phase-3 static
- Phase-3 adaptive
- gameplay_v2 static
- gameplay_v2 adaptive

Where sample size is too small, report limitations explicitly rather than combining incompatible cohorts.

---

## 3. Chapter and Content Versioning

Because the current thesis prototype is centered on a single playable chapter, each research run should record chapter-level content assumptions explicitly.

Record at minimum:

- chapter identifier
- chapter version or content revision
- room/zone content revision where relevant
- puzzle content revision
- feature-flag state
- build or commit hash

### Rule

Do not combine sessions from materially different chapter builds in one analysis group unless the content differences are explicitly documented and justified.

---

## 4. Artifact Validity Requirements

For a valid research run:

- session flow must be reproducible
- content versions must be known
- feature-flag state must be recorded
- migration state must be known
- telemetry logging must be enabled and validated
- backend and frontend versions must be traceable
- gameplay mode must be immutable for the session
- canonical attempts must remain the scoring source of truth

---

## 5. Data Collection Requirements

Record at minimum:

- session id
- participant code or pseudonymous identifier
- condition
- mode
- attempt outcomes
- response times
- hint usage
- progression completion
- telemetry availability and health
- relevant feature-flag values
- commit hash or deploy version

For gameplay v2, also record:

- `game_state_version` behavior where relevant
- stale-state conflicts
- action diversity
- whether `metadata.source="gameplay_v2"` is present for modal attempts

For the current thesis prototype, also record where applicable:

- pre-test result or initialization band
- chapter identifier
- chapter completion status
- zone traversal summary
- hint resource usage (for example battery-based hint economy if enabled)
- vocabulary board or journal access behavior when relevant
- post-run questionnaire or post-test availability

---

## 6. Telemetry Interpretation Rules

Telemetry is useful for:

- flow completion analysis
- interaction sequence inspection
- dead-end action analysis
- hint usage patterns
- vocabulary board or journal consultation behavior
- recovery behavior after conflicts
- mapping room actions to learning attempts

Telemetry is not authoritative for:

- scoring
- mastery
- progression
- final learning outcomes
- standardized language proficiency claims

Research claims should not be based on telemetry alone.

Canonical attempt data and known experimental conditions must remain the primary basis for learning-related claims.

---

## 7. Threats to Validity

Typical threats include:

### Internal validity risks

- seed/content drift between runs
- hidden feature-flag changes
- frontend/backend contract mismatch
- stale-state recovery bugs affecting measured UX
- canonical attempt behavior changing during pilot

### Construct validity risks

- using telemetry proxies as if they were learning outcomes
- mixing exploratory gameplay time with puzzle-solving time without clear distinction
- ambiguous interpretation of hint usage

### External validity risks

- small pilot size
- biased participant recruitment
- internal-only testers
- gameplay_v2 not yet representative of broader deployment conditions

### Analysis validity risks

- mixed cohorts without explicit segmentation
- ignoring trace truncation
- missing telemetry coverage
- undocumented content changes between runs

### Chapter-prototype validity risks

- single-chapter scope may limit generalizability
- puzzle quality may vary across mechanics or zones
- narrative support elements may affect engagement independently of adaptation
- pre-test initialization may be too coarse for strong learning claims
- chapter-specific asset or UI issues may distort evaluation results

---

## 8. Reproducibility Checklist

For every experimental run:

1. record repository commit hash
2. record migration state
3. record seed/content version assumptions
4. record environment configuration
5. record feature-flag values
6. record session mode policy
7. record validation steps performed before data collection
8. record known incidents or hotfixes during the run

---

## 9. Cross-phase Research Guardrails

These rules should hold across implementation phases:

- backend authority must be preserved
- telemetry must remain observational only
- no client-side scoring
- no client-side progression decisions
- gameplay_v2 features must remain versioned and feature-gated
- new room/item content must pass seed validation before use in research
- effects should be applied atomically and logged consistently
- gameplay_v2 must be enabled per session through explicit mode assignment

---

## 10. Evaluation Guidance by Implementation Phase

### Canonical Phase-3

Focus on:

- progression completion
- correctness patterns
- BKT growth
- adaptive vs static comparison
- hint behavior
- response time distribution

### Gameplay v2

In addition to canonical metrics, examine:

- action diversity
- dead-end action ratio
- conflict recovery rate
- time-to-first-hint
- time from `open_puzzle` effect to attempt submission
- mapping from gameplay actions to learning attempts

### Single-chapter thesis prototype

For the current thesis prototype, evaluation should focus on:

- chapter completion rate
- puzzle completion patterns
- hint dependence
- dead-end or confusion points
- adaptive vs static support behavior where applicable
- player-reported clarity and engagement
- integrity of canonical attempt and mastery data

### Important Note

Because the prototype currently centers on one playable chapter, conclusions should be reported as prototype-scale findings rather than broad claims about all future chapters or all English-learning contexts.

---

## 11. Research Operations Guidance

Before data collection starts:

- confirm tests pass
- confirm telemetry exists
- confirm content is validated
- confirm mode and condition assignment rules
- confirm feature-flag state
- confirm rollback path
- confirm participant privacy/export plan

During a pilot:

- document environment changes immediately
- do not mix undocumented content changes into active data collection
- keep participant grouping explicit
- do not widen rollout while critical contract bugs remain open

After a pilot:

- review telemetry completeness
- review canonical attempt data integrity
- review pilot incidents
- identify validity threats before writing conclusions

---

## 12. Reporting Guidance

When writing thesis or paper sections:

- clearly separate implemented behavior from proposed future behavior
- distinguish observational telemetry from canonical scoring data
- state mode and condition segmentation explicitly
- report limitations of pilot-scale evidence
- avoid claims that exceed the measured data
- document feature-flag and environment assumptions

Recommended structure for reporting:

1. artifact description
2. implementation scope
3. experimental conditions
4. data collection pipeline
5. threats to validity
6. results
7. limitations
8. future work

For thesis reporting, explicitly distinguish:

- implemented single-chapter prototype behavior
- preserved baseline/legacy flow
- proposed future multi-chapter expansion

Avoid presenting proposed future systems as if they were already implemented and evaluated.
