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

## Implementation Notes

### Actual Implementation (2026-01-31)

The upsert strategy was successfully implemented with the following refinements:

#### 1. Invalidate + Create Pattern (Modified)

Instead of explicit deletion, we leverage Graphiti's temporal model:

```python
async def upsert_episode(...) -> Optional[UpsertResult]:
    """
    Pattern:
    1. Check if episode exists with entity_id
    2. If exists with same content (source_hash match): Skip
    3. If exists with different content: Create new episode
       - Graphiti handles temporal invalidation automatically
       - New episode gets new valid_at timestamp
       - Old episode remains in graph with implicit invalid_at
    4. If not exists: Create new episode
    5. Return UpsertResult with action (created/updated/skipped)
    """
```

**Key Insight**: Graphiti's temporal model means "update" = "create new version". The old version remains queryable at its point in time, providing natural audit trail without explicit deletion.

#### 2. Content-Based Change Detection

The implementation uses `source_hash` for intelligent skip logic:

```python
# Generate hash from content
source_hash = hashlib.sha256(episode_body.encode()).hexdigest()

# Check existence
exists_result = await client.episode_exists(
    entity_id=entity_id,
    group_id=group_id,
    source_hash=source_hash
)

if exists_result.exists and exists_result.exact_match:
    # Content unchanged - skip update entirely
    return UpsertResult.skipped(...)
```

This prevents unnecessary episode creation when content hasn't changed.

#### 3. Metadata Preservation

Original `created_at` is preserved across updates:

```python
if exists_result.exists:
    # Extract original created_at
    original_created_at = exists_result.episode["metadata"]["created_at"]

    # Create new metadata preserving created_at
    metadata = EpisodeMetadata.create_now(...)
    metadata.created_at = original_created_at  # Preserve
    metadata.updated_at = datetime.now(timezone.utc).isoformat()
```

#### 4. Structured Result Types

Two dataclasses provide type-safe results:

**ExistsResult** (`guardkit/integrations/graphiti/exists_result.py`):
- `exists`: Boolean
- `episode`: Episode data if found
- `exact_match`: True if source_hash matches
- `uuid`: Episode UUID if found

**UpsertResult** (`guardkit/integrations/graphiti/upsert_result.py`):
- `action`: "created" | "updated" | "skipped"
- `episode`: Episode data
- `uuid`: New episode UUID
- `previous_uuid`: Old UUID for updates
- Boolean helpers: `was_created`, `was_updated`, `was_skipped`

#### 5. Test Coverage

**Unit Tests** (53+ tests total):
- `tests/unit/integrations/graphiti/test_upsert_result.py` (18 tests)
- `tests/unit/knowledge/test_upsert_episode.py` (14 tests)
- `tests/knowledge/test_episode_exists.py` (21 tests)

**Coverage**: >85% for all upsert-related code

**Test Scenarios Covered**:
- Create when not exists
- Skip when content unchanged (exact match)
- Update when content changed (preserve created_at)
- Graceful degradation (disabled client, errors)
- UUID extraction and override
- Entity ID matching
- Source hash generation and verification
- Namespace prefixing (project vs system groups)
- Metadata parsing from episode body
- Multiple search results handling

#### 6. Documentation

- **Deep Dive**: [Episode Upsert Logic](../deep-dives/graphiti/episode-upsert.md)
- **Integration Guide**: [Graphiti Integration](../guides/graphiti-integration-guide.md)
- **Feature Spec**: [FEAT-GR-PRE-003](../research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)

### Lessons Learned

1. **No Explicit Deletion Needed**: Graphiti's temporal model handles version invalidation naturally
2. **Content Hashing Critical**: Prevents unnecessary episode creation when content unchanged
3. **Metadata in Body**: JSON metadata prefix in episode body enables efficient searching
4. **Graceful Degradation**: All operations return None on error, never raise exceptions
5. **Type Safety**: Dataclasses (UpsertResult, ExistsResult) provide clear, type-safe APIs

### Performance Characteristics

- **Existence Check**: Searches up to 50 results, filters in-memory by entity_id
- **Hash Computation**: SHA-256 is fast (~0.1ms for typical episode content)
- **Skip Rate**: High for repeated ingestion (e.g., seeding runs 2+ times)
- **Update Overhead**: Minimal - new episode creation only when content changed

### Known Limitations

1. **Not Atomic**: Episode creation is not transactional with existence check
2. **Search Limit**: entity_id search capped at 50 results (sufficient for current use)
3. **No Explicit History API**: Old versions accessible via temporal queries only
4. **Single Entity ID**: No composite key support (use concatenation if needed)

## References

- [graphiti-core GitHub](https://github.com/getzep/graphiti)
- [GuardKit GraphitiClient](../guardkit/knowledge/graphiti_client.py)
- [Episode Metadata Schema](../guardkit/integrations/graphiti/metadata.py)
- [FEAT-GR-PRE-003 Design](../docs/research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
- [Episode Upsert Documentation](../deep-dives/graphiti/episode-upsert.md)
- [UpsertResult Implementation](../guardkit/integrations/graphiti/upsert_result.py)
- [ExistsResult Implementation](../guardkit/integrations/graphiti/exists_result.py)
