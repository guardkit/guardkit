# ADR-SP-002: Client-Level Metadata Injection

- **Date**: 2026-02
- **Status**: Accepted (ADR-GBF-001)

## Context

Entity classes were embedding _metadata in to_episode_body(), creating coupling between domain logic and serialization.

## Decision

Unify metadata injection at GraphitiClient._inject_metadata() level. Entity classes return domain data only from to_episode_body(). Client injects _metadata block automatically.

## Consequences

**Positive:**
- Clean separation of concerns
- Consistent metadata across all entity types
- Entities are pure domain objects

**Negative:**
- One more layer of indirection
