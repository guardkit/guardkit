# ADR-SP-003: Adversarial Cooperation over Single-Agent

- **Date**: 2026-01
- **Status**: Accepted

## Context

Single-agent approaches (Ralph loops) work for mechanical tasks but fail at integration seams and subjective completion criteria. Block AI research showed g3's adversarial dyad achieved 5/5 completeness vs 2-4.5/5 for single agents. Ablation study: removing Coach feedback made output non-functional.

## Decision

Use Player-Coach adversarial cooperation pattern for AutoBuild. Player implements, Coach independently validates against requirements contract. Player self-report of success is discarded.

## Consequences

**Positive:**
- Higher completion rates for complex tasks
- Independent validation prevents silent failures
- Fresh context per turn

**Negative:**
- Higher token cost (~2x)
- Not needed for simple tasks (addressed by intensity gradient)
