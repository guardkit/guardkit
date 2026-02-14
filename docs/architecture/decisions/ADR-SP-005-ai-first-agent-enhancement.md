# ADR-SP-005: AI-First Agent Enhancement with Static Fallback

- **Date**: 2025-11
- **Status**: Accepted

## Context

Agent files need stack-specific examples and boundary sections. Pure static generation creates generic content. Pure AI generation can fail.

## Decision

AI-first enhancement with static fallback. Hybrid mode: try AI enhancement, fall back to static (creates "Related Templates" section only) if AI fails. Never-fails guarantee.

## Consequences

**Positive:**
- 9/10 quality when AI succeeds
- 100% reliability via fallback
- Template-specific examples

**Negative:**
- 2-5 minute duration (vs instant for static)
- Requires OpenAI/Anthropic API access
