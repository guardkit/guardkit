# Episode Upsert Logic

**Purpose**: Understand the episode upsert functionality that enables create-or-update semantics for knowledge graph episodes.

**Related**:
- [Episode Metadata](./episode-metadata.md) - Metadata schema used in episodes
- [Graphiti Integration Guide](../../guides/graphiti-integration-guide.md) - Overall integration guide
- [FEAT-GR-PRE-003](../../research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md) - Original design document

---

## Overview

The episode upsert system provides intelligent create-or-update semantics for knowledge graph episodes. It prevents duplicate episodes while allowing content updates when needed.

### Key Concepts

1. **Entity ID**: Stable identifier for an episode (e.g., `"project-overview-001"`)
2. **Source Hash**: SHA-256 hash of episode content for change detection
3. **Upsert Actions**: `created`, `updated`, or `skipped` based on existence and content matching
4. **Metadata Preservation**: Original `created_at` preserved across updates

---

## Core Components

### 1. UpsertResult Dataclass

Located in `guardkit/integrations/graphiti/upsert_result.py`.

```python
from guardkit.integrations/graphiti.upsert_result import UpsertResult

# Factory methods for each action type
result = UpsertResult.created(episode={"uuid": "abc123", ...})
result = UpsertResult.updated(episode={"uuid": "new-uuid", ...}, previous_uuid="old-uuid")
result = UpsertResult.skipped(episode={"uuid": "existing-uuid", ...})

# Boolean helpers
if result.was_created:
    print(f"Created new episode: {result.uuid}")
elif result.was_updated:
    print(f"Updated episode: {result.uuid} (was: {result.previous_uuid})")
elif result.was_skipped:
    print(f"Skipped (unchanged): {result.uuid}")
```

**Attributes**:
- `action`: Literal["created", "updated", "skipped"]
- `episode`: Episode data dictionary with uuid, content, metadata
- `uuid`: Episode UUID (extracted from episode if not provided)
- `previous_uuid`: For updates, the UUID of the replaced episode

**Properties**:
- `was_created`: Returns `True` if action is "created"
- `was_updated`: Returns `True` if action is "updated"
- `was_skipped`: Returns `True` if action is "skipped"

### 2. ExistsResult Dataclass

Located in `guardkit/integrations/graphiti/exists_result.py`.

```python
from guardkit.integrations.graphiti.exists_result import ExistsResult

# Factory methods
result = ExistsResult.not_found()
result = ExistsResult.found(episode={"uuid": "abc", ...}, exact_match=True)

# Check existence
if result.exists:
    if result.exact_match:
        print("Episode exists with identical content")
    else:
        print("Episode exists but content changed")
```

**Attributes**:
- `exists`: Boolean indicating if episode was found
- `episode`: Episode data if found, None otherwise
- `exact_match`: True if source_hash matches (content identical)
- `uuid`: Episode UUID if found

### 3. Episode Existence Check

The `GraphitiClient.episode_exists()` method checks if an episode exists by entity_id.

```python
from guardkit.knowledge.graphiti_client import get_graphiti

client = get_graphiti()

# Check existence with optional content hash verification
result = await client.episode_exists(
    entity_id="project-overview-001",
    group_id="project_overview",
    source_hash="abc123..."  # Optional: verify content unchanged
)

if result.exists:
    if result.exact_match:
        # Content is identical, skip update
        pass
    else:
        # Episode exists but content changed, can update
        pass
```

**How it works**:
1. Searches for episodes in the specified group
2. Parses JSON metadata from episode body
3. Matches by `entity_id` in metadata
4. If `source_hash` provided, checks for exact content match
5. Returns first exact match, or first entity_id match if no exact match

### 4. Upsert Operation

The `GraphitiClient.upsert_episode()` method implements the full upsert logic.

```python
from guardkit.knowledge.graphiti_client import get_graphiti

client = get_graphiti()

result = await client.upsert_episode(
    name="Project Overview",
    episode_body="Updated project description...",
    group_id="project_overview",
    entity_id="project-overview-001",
    source="user_added",
    entity_type="project_overview",
    source_hash="optional-precomputed-hash"  # Computed if not provided
)

if result.was_created:
    print(f"Created: {result.uuid}")
elif result.was_updated:
    print(f"Updated: {result.uuid} (replaced {result.previous_uuid})")
elif result.was_skipped:
    print(f"Skipped: {result.uuid} (content unchanged)")
```

**Upsert Logic**:

```
1. Generate source_hash from content (if not provided)
2. Check if episode exists with entity_id
3. If NOT exists:
   - Create new episode with version=1
   - Set created_at and updated_at
   - Return UpsertResult.created()
4. If exists AND exact content match:
   - Return UpsertResult.skipped() (no changes)
5. If exists BUT content changed:
   - Preserve original created_at
   - Set new updated_at
   - Create new episode (invalidate-and-create strategy)
   - Return UpsertResult.updated()
```

---

## Metadata Preservation

When updating an episode, the original `created_at` timestamp is preserved:

```python
# First creation
result = await client.upsert_episode(
    name="Feature Spec",
    episode_body="Initial spec...",
    entity_id="feat-001",
    group_id="feature_specs"
)
# result.episode["metadata"]["created_at"] = "2025-01-01T10:00:00Z"

# Update (preserves created_at)
result = await client.upsert_episode(
    name="Feature Spec",
    episode_body="Updated spec...",
    entity_id="feat-001",
    group_id="feature_specs"
)
# result.episode["metadata"]["created_at"] = "2025-01-01T10:00:00Z"  (preserved)
# result.episode["metadata"]["updated_at"] = "2025-01-15T14:30:00Z"  (new)
```

---

## Content Hash Generation

Source hash is automatically computed from episode body:

```python
import hashlib

episode_body = "Your episode content here..."
source_hash = hashlib.sha256(episode_body.encode()).hexdigest()

# Pass to upsert (or let it compute automatically)
result = await client.upsert_episode(
    ...,
    episode_body=episode_body,
    source_hash=source_hash  # Optional: pre-compute for efficiency
)
```

---

## Graceful Degradation

All upsert operations gracefully degrade when Graphiti is disabled or unavailable:

```python
# Client disabled or not initialized
result = await client.upsert_episode(...)
# Returns None instead of raising exception

# Check before using
if result:
    print(f"Action: {result.action}")
else:
    print("Graphiti unavailable, operation skipped")
```

---

## Testing

### Unit Tests

**UpsertResult Tests**: `tests/unit/integrations/graphiti/test_upsert_result.py`
- Factory method creation
- UUID extraction and override
- Action validation
- Boolean helper properties
- Edge cases (empty episode, same UUIDs, etc.)

**Episode Exists Tests**: `tests/knowledge/test_episode_exists.py`
- ExistsResult dataclass validation
- Entity ID matching
- Source hash exact matching
- Group namespace prefixing
- Metadata parsing from episode body
- Multiple results handling
- Graceful degradation

**Upsert Episode Tests**: `tests/unit/knowledge/test_upsert_episode.py`
- Create when not exists
- Skip when exact match
- Update when content changed
- Timestamp preservation (created_at, updated_at)
- Source hash generation and usage
- Entity ID handling
- Graceful degradation

### Integration Tests

Integration tests require Neo4j running and are marked with `@pytest.mark.integration`.

Run integration tests:
```bash
pytest -m integration --run-integration
```

---

## Usage Examples

### Basic Upsert

```python
from guardkit.knowledge.graphiti_client import get_graphiti

client = get_graphiti()

# First call - creates new episode
result = await client.upsert_episode(
    name="Task Status",
    episode_body="Task TASK-001 is in progress",
    group_id="task_statuses",
    entity_id="task-001-status"
)
assert result.was_created

# Second call with same content - skips
result = await client.upsert_episode(
    name="Task Status",
    episode_body="Task TASK-001 is in progress",  # Same content
    group_id="task_statuses",
    entity_id="task-001-status"
)
assert result.was_skipped

# Third call with different content - updates
result = await client.upsert_episode(
    name="Task Status",
    episode_body="Task TASK-001 is completed",  # Changed
    group_id="task_statuses",
    entity_id="task-001-status"
)
assert result.was_updated
assert result.previous_uuid is not None
```

### Conditional Update

```python
# Check first, then decide
exists = await client.episode_exists(
    entity_id="important-episode",
    group_id="important_group"
)

if exists.exists and not exists.exact_match:
    # Episode exists but content differs
    result = await client.upsert_episode(
        name="Important Episode",
        episode_body="New content...",
        group_id="important_group",
        entity_id="important-episode"
    )
    if result.was_updated:
        print(f"Updated episode: {result.uuid}")
```

### Batch Upsert

```python
# Upsert multiple episodes
episodes = [
    ("Task 1", "Content 1", "tasks", "task-001"),
    ("Task 2", "Content 2", "tasks", "task-002"),
    ("Task 3", "Content 3", "tasks", "task-003"),
]

results = []
for name, body, group, entity_id in episodes:
    result = await client.upsert_episode(
        name=name,
        episode_body=body,
        group_id=group,
        entity_id=entity_id
    )
    results.append(result)

# Summarize
created = sum(1 for r in results if r and r.was_created)
updated = sum(1 for r in results if r and r.was_updated)
skipped = sum(1 for r in results if r and r.was_skipped)

print(f"Created: {created}, Updated: {updated}, Skipped: {skipped}")
```

---

## Temporal Versioning

Graphiti uses a temporal model with `valid_at` and `invalid_at` timestamps:

- When we "update" an episode, we create a new episode version
- The old version remains in the graph but becomes invalid
- Graphiti can query point-in-time states
- Our `created_at` metadata tracks original creation time across versions

```
Timeline:
T1: Create episode (valid_at=T1, invalid_at=null)
T2: Update episode → Old: (valid_at=T1, invalid_at=T2)
                     New: (valid_at=T2, invalid_at=null, created_at=T1)
```

---

## Error Handling

```python
result = await client.upsert_episode(...)

if result is None:
    # Graphiti disabled or error occurred
    # Check logs for details
    pass
elif result.was_created:
    # Successfully created
    pass
elif result.was_updated:
    # Successfully updated
    pass
elif result.was_skipped:
    # Content unchanged, no action needed
    pass
```

All exceptions are caught internally and logged. Operations never raise exceptions; they return `None` on error.

---

## Best Practices

1. **Use Stable Entity IDs**: Choose entity_id values that uniquely identify the logical entity (e.g., task ID, feature ID)

2. **Let Source Hash Auto-Compute**: Unless you're computing it once for multiple operations, let the system generate the hash

3. **Check Return Value**: Always check if result is None (graceful degradation)

4. **Use Appropriate Actions**:
   - `was_created`: Initialize dependent state
   - `was_updated`: Refresh caches, notify subscribers
   - `was_skipped`: No-op, avoid unnecessary work

5. **Preserve Metadata**: Don't manually set `created_at` on updates; the system preserves it automatically

6. **Use Consistent Entity IDs**: Same entity should always use the same entity_id across updates

---

## Performance Considerations

- **Entity ID Search**: Searches by entity_id query up to 50 results and filter in-memory
- **Source Hash**: SHA-256 computation is fast but avoid recomputing unnecessarily
- **Batch Operations**: Consider batching if upserting many episodes
- **Graceful Degradation**: No performance impact when Graphiti is disabled

---

## See Also

- [Episode Metadata Schema](./episode-metadata.md)
- [Graphiti Project Namespaces](../../guides/graphiti-project-namespaces.md)
- [Graphiti Integration Guide](../../guides/graphiti-integration-guide.md)
- [FEAT-GR-PRE-003 Design](../../research/graphiti-refinement/FEAT-GR-PRE-003-episode-upsert-logic.md)
