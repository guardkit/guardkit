# ADR-SP-006: Adaptive Ceremony via Complexity Scoring

- **Date**: 2026-01
- **Status**: Accepted

## Context

Full workflow (all phases) is overkill for simple tasks. No workflow is dangerous for complex tasks. "Your Agent Orchestrator Is Too Clever" critique applies to fixed-intensity approaches.

## Decision

Complexity scoring (1-10) gates workflow intensity. Simple tasks (1-3) auto-proceed through most phases. Complex tasks (7-10) get full architectural review, mandatory checkpoints, strict plan auditing. Adversarial intensity scales accordingly: minimal (tests only), standard-light, standard, strict (full requirements + architecture + integration review).

## Consequences

**Positive:**
- Right-sized process for each task
- --micro flag for trivial tasks
- Addresses Ralph Wiggum critique

**Negative:**
- Requires accurate complexity scoring (currently manual/AI-assessed)
