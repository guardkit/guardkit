# Research: graphiti-core Upsert Capabilities

**Task**: TASK-GR-PRE-003-A
**Date**: 2026-01-31
**Status**: Complete

## Executive Summary

graphiti-core **does not support native episode upsert operations**. The recommended implementation strategy is **Invalidate + Create** pattern using metadata-based identity matching.

---

## Research Questions & Answers

### Q1: Does graphiti-core support native episode upsert?

**Answer: NO**

graphiti-core only provides:
- `add_episode()` - Create new episodes
- `search()` - Query existing episodes
- Neo4j driver access for deletion

There is no `update_episode()`, `upsert_episode()`, or `modify_episode()` method available.

### Q2: How does temporal versioning work in graphiti-core?

**Answer: Limited Support**

**Available:**
- `reference_time` parameter at episode creation sets `valid_at` timestamp
- `valid_at` field returned in search results (read-only)

**NOT Available:**
- No `invalid_at` mechanism for marking episodes as superseded
- No native versioning system
- No "as of" temporal queries
- `valid_at` cannot be updated after creation

**Workaround:**
Use metadata fields in episode body:
```python
{
    "updated_at": "2026-01-31T12:00:00Z",
    "version": "1.2.0",
    "expires_at": "2027-01-31T12:00:00Z"  # Optional TTL
}
```

### Q3: Can we invalidate old episodes and create new ones?

**Answer: YES (via deletion)**

**Deletion Methods Available:**
```python
# Via Neo4j driver (available in GraphitiClient)
async def _clear_group(self, group_id: str) -> int:
    """Delete all episodes in a group"""
    result = await session.run(
        """
        MATCH (e:Episode {group_id: $group_id})
        DETACH DELETE e
        RETURN count(e)
        """,
        group_id=group_id
    )

# Bulk deletion methods
await client.clear_all()             # Delete everything
await client.clear_system_groups()   # Delete system knowledge
await client.clear_project_groups()  # Delete project knowledge
```

**Single Episode Deletion** (to be implemented in PRE-003-C):
```python
async def delete_episode(self, episode_uuid: str) -> bool:
    """Delete specific episode by UUID"""
    result = await session.run(
        """
        MATCH (e:Episode {uuid: $uuid})
        DETACH DELETE e
        RETURN count(e) as deleted
        """,
        uuid=episode_uuid
    )
```

### Q4: What are the performance implications of each approach?

| Strategy | Performance | Pros | Cons |
|----------|-------------|------|------|
| **Invalidate + Create** | Good | Clean, predictable | Two operations |
| **Delete + Create** | Same as above | Simple | Loses all history |
| **Version Accumulation** | Degrades over time | Full history | Storage bloat, complex queries |

**Recommendation**: Invalidate + Create with metadata versioning for audit trails.

### Q5: How do we handle concurrent updates?

**Recommended: Optimistic Locking with source_hash**

```python
# 1. Include source_hash in metadata
metadata = {
    "source_hash": hashlib.sha256(content.encode()).hexdigest()[:16]
}

# 2. Check hash before upsert
async def upsert_episode(..., expected_hash: Optional[str] = None):
    existing = await self.episode_exists(entity_id, group_id)
    if existing and expected_hash:
        current_hash = await self._get_episode_hash(existing)
        if current_hash != expected_hash:
            raise ConcurrentModificationError()
    # Proceed...
```

**Alternative: Last-Writer-Wins**
- Simpler but may lose changes
- Acceptable for idempotent sources (e.g., file content refresh)

---

## API Reference

### Current graphiti-core API (via GraphitiClient)

```python
# Episode Creation
async def add_episode(
    name: str,
    episode_body: str,
    group_id: str,
    scope: Optional[str] = None
) -> Optional[str]:
    """
    Creates a new episode in the knowledge graph.

    Args:
        name: Human-readable episode name
        episode_body: Content (can include JSON metadata)
        group_id: Logical grouping identifier
        scope: Optional scope filter

    Returns:
        Episode UUID or None on failure
    """

# Episode Search
async def search(
    query: str,
    group_ids: Optional[List[str]] = None,
    num_results: int = 10,
    scope: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Semantic search across episodes.

    Returns list of dicts with:
        - uuid: Episode identifier
        - fact: Content snippet
        - name: Episode name
        - created_at: Creation timestamp
        - valid_at: Temporal validity marker
        - score: Relevance score
    """

# Bulk Deletion
async def clear_all() -> Dict[str, int]
async def clear_system_groups() -> Dict[str, int]
async def clear_project_groups() -> Dict[str, int]
async def get_clear_preview() -> Dict[str, Any]
```

### Proposed API Extensions (PRE-003-B, PRE-003-C)

```python
# Episode Existence Check
async def episode_exists(
    entity_id: str,
    group_id: str
) -> Optional[str]:
    """
    Check if episode with entity_id exists.

    Returns:
        Episode UUID if exists, None otherwise
    """

# Episode Upsert
async def upsert_episode(
    name: str,
    episode_body: str,
    group_id: str,
    entity_id: str,
    expected_hash: Optional[str] = None
) -> Optional[str]:
    """
    Insert or update episode by entity_id.

    Pattern:
        1. Search for existing by entity_id
        2. If found: Delete old episode
        3. Create new episode
        4. Return new UUID

    Raises:
        ConcurrentModificationError: If expected_hash mismatches
    """
```

---

## Metadata Schema

The `EpisodeMetadata` dataclass supports upsert tracking:

```python
@dataclass
class EpisodeMetadata:
    # Identity
    source: str           # "code", "adr", "task", etc.
    entity_id: str        # Unique identifier for matching
    entity_type: str      # "file", "document", "component"
    project_id: str       # Multi-tenant isolation

    # Versioning
    version: str          # Semantic version "1.0.0"
    created_at: str       # ISO timestamp (first creation)
    updated_at: str       # ISO timestamp (last update)
    source_hash: str      # Content hash for change detection

    # Lifecycle
    expires_at: str       # Optional TTL
    tags: List[str]       # Categorization
```

---

## Implementation Recommendations

### For PRE-003-B (episode_exists)

```python
async def episode_exists(
    self,
    entity_id: str,
    group_id: str
) -> Optional[str]:
    """
    Search episodes and check metadata for entity_id match.

    Strategy:
    1. Search with entity_id as query term
    2. Parse metadata from results
    3. Return UUID if entity_id matches
    """
    results = await self.search(
        query=f"entity_id:{entity_id}",
        group_ids=[group_id],
        num_results=10
    )

    for result in results:
        metadata = self._parse_metadata(result.get("fact", ""))
        if metadata and metadata.get("entity_id") == entity_id:
            return result.get("uuid")

    return None
```

### For PRE-003-C (upsert_episode)

```python
async def upsert_episode(
    self,
    name: str,
    episode_body: str,
    group_id: str,
    entity_id: str,
    expected_hash: Optional[str] = None
) -> Optional[str]:
    """
    Upsert pattern: Check -> Delete -> Create
    """
    # 1. Check existence
    existing_uuid = await self.episode_exists(entity_id, group_id)

    # 2. Optimistic lock check (if requested)
    if existing_uuid and expected_hash:
        current = await self._get_episode(existing_uuid)
        current_hash = self._extract_hash(current)
        if current_hash != expected_hash:
            raise ConcurrentModificationError(
                f"Episode modified: expected {expected_hash}, got {current_hash}"
            )

    # 3. Delete old if exists
    if existing_uuid:
        await self._delete_episode(existing_uuid)

    # 4. Create new
    return await self.add_episode(
        name=name,
        episode_body=episode_body,
        group_id=group_id
    )
```

---

## Key Files Referenced

| File | Purpose |
|------|---------|
| `guardkit/knowledge/graphiti_client.py` | Main GraphitiClient implementation |
| `guardkit/integrations/graphiti/metadata.py` | EpisodeMetadata dataclass |
| `docs/architecture/graphiti-architecture.md` | Architecture documentation |
| `docs/guides/graphiti-integration-guide.md` | Integration guide |

---

## Conclusion

**Recommended Strategy**: Invalidate + Create pattern with metadata-based identity matching.

**Next Steps**:
1. **PRE-003-B**: Implement `episode_exists()` method
2. **PRE-003-C**: Implement `upsert_episode()` method with optimistic locking
3. Consider future enhancement for version archival (optional)

**Decision Recorded**: See [ADR-GR-001-upsert-strategy.md](../../adr/ADR-GR-001-upsert-strategy.md)
