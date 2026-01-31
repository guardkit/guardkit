# ADR-GR-001: Episode Upsert Strategy for graphiti-core

## Status
**Accepted**

## Date
2026-01-31

## Context

GuardKit integrates with graphiti-core for graph-based knowledge management. We need to support updating existing episodes when knowledge changes (e.g., code evolves, architecture decisions are updated, or project context changes).

### Research Question
Does graphiti-core support native episode upsert operations, or do we need to implement a custom solution?

### Key Requirements
1. Update existing episodes when their content changes
2. Maintain knowledge consistency across refreshes
3. Support temporal versioning for audit trails
4. Handle concurrent updates safely
5. Preserve knowledge graph integrity

## Decision

**We will implement a custom "Invalidate + Create" pattern** for episode upsert operations.

### Rationale

After researching graphiti-core's native capabilities, we found:

1. **No Native Upsert**: graphiti-core does not provide built-in `upsert_episode()` or `update_episode()` methods
2. **Limited Temporal Support**: Only `reference_time` parameter at creation (sets `valid_at`); no `invalid_at` mechanism
3. **Deletion Available**: Neo4j driver access allows episode deletion via `DETACH DELETE`
4. **Metadata Support**: Episode bodies can include structured metadata for tracking

### Chosen Strategy: Invalidate + Create

```python
async def upsert_episode(
    name: str,
    episode_body: str,
    group_id: str,
    entity_id: str,  # Unique identifier for matching
) -> Optional[str]:
    """
    Pattern:
    1. Search for existing episode by entity_id in metadata
    2. If found: Delete old episode
    3. Create new episode with updated content
    4. Return new episode UUID
    """
```

### Rejected Alternatives

#### Alternative 1: Native Upsert
- **Status**: Not Available
- graphiti-core does not expose this functionality

#### Alternative 2: Delete + Create Without Tracking
- **Rejected**: Loses audit trail
- No version history or temporal tracking

#### Alternative 3: Version Accumulation (Keep All Versions)
- **Rejected**: Storage concerns
- Would require complex "valid as of" queries
- No native invalid_at filtering in search

## Implementation Details

### Metadata Schema for Upsert Support

The existing `EpisodeMetadata` dataclass already includes fields we need:

```python
@dataclass
class EpisodeMetadata:
    source: str           # Origin of knowledge
    version: str          # Semantic version (e.g., "1.2.0")
    created_at: str       # ISO timestamp
    entity_type: str      # Type classification
    updated_at: str       # Last update timestamp
    source_hash: str      # Content hash for change detection
    project_id: str       # Multi-tenant isolation
    entity_id: str        # Unique entity identifier for matching
    expires_at: str       # Optional expiration
    tags: List[str]       # Categorization
```

### Identity Matching Strategy

Use `entity_id` (or composite key `project_id + entity_id`) to identify episodes:

```python
# Example entity_id patterns:
"adr/ADR-001"                          # ADR document
"code/src/auth/login.py"               # Source file
"arch/authentication-system"           # Architecture component
"task/TASK-042"                        # Task knowledge
```

### Implementation Steps (PRE-003-B and PRE-003-C)

1. **PRE-003-B: Implement `episode_exists()`**
   ```python
   async def episode_exists(
       self,
       entity_id: str,
       group_id: str
   ) -> Optional[str]:
       """Returns existing episode UUID or None"""
   ```

2. **PRE-003-C: Implement `upsert_episode()`**
   ```python
   async def upsert_episode(
       self,
       name: str,
       episode_body: str,
       group_id: str,
       entity_id: str
   ) -> Optional[str]:
       """
       1. Check existence via episode_exists()
       2. If exists: Delete old via Neo4j
       3. Create new with incremented version
       4. Return new UUID
       """
   ```

### Temporal Versioning Approach

Since native temporal versioning is limited:

1. **At Creation**: Set `reference_time=datetime.now(timezone.utc)`
2. **In Metadata**: Store `updated_at` timestamp and `version` string
3. **For Audit**: Use `source_hash` to detect content changes
4. **For Expiration**: Use `expires_at` for TTL-based invalidation

### Concurrency Handling

Use optimistic locking with source_hash:

```python
async def upsert_episode(..., expected_hash: Optional[str] = None):
    existing = await self.episode_exists(entity_id, group_id)
    if existing and expected_hash:
        current_hash = await self._get_episode_hash(existing)
        if current_hash != expected_hash:
            raise ConcurrentModificationError(
                f"Episode {entity_id} was modified (expected {expected_hash}, got {current_hash})"
            )
    # Proceed with delete + create
```

## Consequences

### Positive
- **Full Control**: Custom implementation allows GuardKit-specific optimizations
- **Audit Trail**: Metadata includes version history information
- **Flexible Matching**: entity_id can be any unique identifier scheme
- **Change Detection**: source_hash enables incremental updates
- **Multi-Tenant Safe**: project_id scoping prevents cross-project conflicts

### Negative
- **Not Atomic**: Delete + create is two operations (mitigated by transaction logging)
- **No Native History**: Old versions are deleted, not retained
- **Query Overhead**: Must search before upsert to check existence
- **Implementation Effort**: Custom code to maintain

### Mitigations
- Log upsert intent before deletion for recovery
- Consider background archival of deleted episodes (future enhancement)
- Cache existence checks for batch operations
- Comprehensive test coverage for edge cases

## Related Decisions

- **ADR-GR-002**: Entity ID Naming Conventions (TBD)
- **FEAT-GR-PRE-003**: Episode Upsert Logic Feature Spec

## References

- [graphiti-core GitHub](https://github.com/getzep/graphiti)
- [GuardKit GraphitiClient](../guardkit/knowledge/graphiti_client.py)
- [Episode Metadata Schema](../guardkit/integrations/graphiti/metadata.py)
- [FEAT-GR-PRE-003 Design](../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
