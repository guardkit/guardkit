# ADR-SP-004: Progressive Disclosure for Token Optimization

- **Date**: 2025-11
- **Status**: Accepted

## Context

Loading all agent context and knowledge into every prompt wastes tokens and dilutes relevance. Context windows have practical limits even when technically large.

## Decision

Implement progressive disclosure: core/ext file splits for agents, frontmatter-based agent selection, token budgets per context category, job-specific context assembly.

## Consequences

**Positive:**
- Dramatically reduced token usage
- More relevant context per prompt
- Agents only loaded when matched

**Negative:**
- Requires careful budget tuning
- ext files may be stale if not maintained
