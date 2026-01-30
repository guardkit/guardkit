# FEAT-GR-PRE-003: Episode Upsert Logic

> **Purpose**: Enable episode updates and duplicate handling to support `--force` flags and knowledge updates.
>
> **Priority**: High (Prerequisite)
> **Estimated Complexity**: 3
> **Dependencies**: FEAT-GR-PRE-002 (Episode Metadata Schema)
> **Blocks**: FEAT-GR-002 (Context Addition Command)

---

## Problem Statement

Currently, `add_episode` always creates new episodes with no duplicate detection:

```python
# Current behavior - always creates new
await client.add_episode(
    name="feature_spec_FEAT-SKEL-001",
    episode_body=json.dumps(spec),
    group_id="feature_specs"
)

# Running again creates a duplicate!
await client.add_episode(
    name="feature_spec_FEAT-SKEL-001",  # Same name
    episode_body=json.dumps(updated_spec),
    group_id="feature_specs"
)
```

This causes issues:

1. **Duplicates accumulate** - Re-running seeding creates duplicates
2. **No update capability** - Can't update existing knowledge
3. **No `--force` support** - FEAT-GR-002 needs `--force` flag for re-parsing files
4. **No version tracking** - Can't see history of changes

---

## Proposed Solution

### 1. Episode Existence Check

```python
# guardkit/knowledge/episode_operations.py

from typing import Optional, List, Dict, Any
from .graphiti_client import GraphitiClient


async def episode_exists(
    client: GraphitiClient,
    name: str,
    group_id: str
) -> bool:
    """Check if an episode with this name exists in the group.
    
    Uses a targeted search for the exact episode name.
    
    Args:
        client: GraphitiClient instance
        name: Episode name to check
        group_id: Group ID to search in
        
    Returns:
        True if episode exists, False otherwise
    """
    if not client.enabled:
        return False
    
    try:
        # Search for exact name match
        results = await client.search(
            query=f'name:"{name}"',
            group_ids=[group_id],
            num_results=1
        )
        
        # Check if any result matches exactly
        for result in results:
            if result.get("name") == name:
                return True
            # Also check body for name field
            body = result.get("body", {})
            if isinstance(body, dict) and body.get("name") == name:
                return True
        
        return False
    except Exception:
        return False


async def find_episode_by_name(
    client: GraphitiClient,
    name: str,
    group_id: str
) -> Optional[Dict[str, Any]]:
    """Find an episode by exact name.
    
    Args:
        client: GraphitiClient instance
        name: Episode name to find
        group_id: Group ID to search in
        
    Returns:
        Episode dict if found, None otherwise
    """
    if not client.enabled:
        return None
    
    try:
        results = await client.search(
            query=f'name:"{name}"',
            group_ids=[group_id],
            num_results=5  # Get a few in case of partial matches
        )
        
        # Find exact match
        for result in results:
            if result.get("name") == name:
                return result
        
        return None
    except Exception:
        return None
```

### 2. Upsert Logic

```python
# guardkit/knowledge/episode_operations.py (continued)

from datetime import datetime, timezone
import json


class UpsertResult:
    """Result of an upsert operation."""
    
    def __init__(
        self,
        success: bool,
        action: str,  # "created" | "updated" | "skipped" | "failed"
        episode_id: Optional[str] = None,
        error: Optional[str] = None,
        previous_version: Optional[int] = None
    ):
        self.success = success
        self.action = action
        self.episode_id = episode_id
        self.error = error
        self.previous_version = previous_version


async def upsert_episode(
    client: GraphitiClient,
    name: str,
    episode_body: Dict[str, Any],
    group_id: str,
    force: bool = False
) -> UpsertResult:
    """Insert or update an episode.
    
    Behavior:
    - If episode doesn't exist: Create it
    - If episode exists and force=False: Skip (return existing)
    - If episode exists and force=True: Update it (increment version)
    
    Args:
        client: GraphitiClient instance
        name: Episode name (unique within group)
        episode_body: Episode content as dictionary
        group_id: Group ID for storage
        force: If True, update existing episodes
        
    Returns:
        UpsertResult with action taken and result details
    """
    if not client.enabled:
        return UpsertResult(
            success=False,
            action="failed",
            error="Graphiti client is disabled"
        )
    
    try:
        # Check if episode exists
        existing = await find_episode_by_name(client, name, group_id)
        
        if existing:
            if not force:
                return UpsertResult(
                    success=True,
                    action="skipped",
                    episode_id=existing.get("uuid"),
                    error="Episode already exists (use force=True to update)"
                )
            
            # Update: increment version in metadata
            previous_version = _get_episode_version(existing)
            episode_body = _increment_version(episode_body, previous_version)
            episode_body = _update_timestamps(episode_body)
            
            # Note: Graphiti doesn't have a native update operation
            # We use temporal invalidation: old becomes invalid, new is created
            # The old episode's valid_at/invalid_at handles history
            
            result = await client.add_episode(
                name=name,
                episode_body=json.dumps(episode_body),
                group_id=group_id
            )
            
            if result:
                return UpsertResult(
                    success=True,
                    action="updated",
                    episode_id=result,
                    previous_version=previous_version
                )
            else:
                return UpsertResult(
                    success=False,
                    action="failed",
                    error="Failed to create updated episode"
                )
        else:
            # Create new episode
            episode_body = _set_initial_version(episode_body)
            episode_body = _set_created_timestamp(episode_body)
            
            result = await client.add_episode(
                name=name,
                episode_body=json.dumps(episode_body),
                group_id=group_id
            )
            
            if result:
                return UpsertResult(
                    success=True,
                    action="created",
                    episode_id=result
                )
            else:
                return UpsertResult(
                    success=False,
                    action="failed",
                    error="Failed to create episode"
                )
    
    except Exception as e:
        return UpsertResult(
            success=False,
            action="failed",
            error=str(e)
        )


def _get_episode_version(episode: Dict[str, Any]) -> int:
    """Extract version from episode body."""
    body = episode.get("body", episode)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return 0
    
    if isinstance(body, dict):
        metadata = body.get("_metadata", {})
        return metadata.get("version", 1)
    
    return 1


def _increment_version(body: Dict[str, Any], previous: int) -> Dict[str, Any]:
    """Increment version in episode body."""
    if "_metadata" not in body:
        body["_metadata"] = {}
    body["_metadata"]["version"] = previous + 1
    return body


def _set_initial_version(body: Dict[str, Any]) -> Dict[str, Any]:
    """Set initial version in episode body."""
    if "_metadata" not in body:
        body["_metadata"] = {}
    body["_metadata"]["version"] = 1
    return body


def _update_timestamps(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update timestamp in episode body."""
    if "_metadata" not in body:
        body["_metadata"] = {}
    body["_metadata"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    return body


def _set_created_timestamp(body: Dict[str, Any]) -> Dict[str, Any]:
    """Set created timestamp in episode body."""
    if "_metadata" not in body:
        body["_metadata"] = {}
    now = datetime.now(timezone.utc).isoformat()
    body["_metadata"]["created_at"] = now
    body["_metadata"]["updated_at"] = now
    return body
```

### 3. Batch Upsert Support

```python
# guardkit/knowledge/episode_operations.py (continued)

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class BatchUpsertResult:
    """Result of batch upsert operation."""
    
    total: int
    created: int
    updated: int
    skipped: int
    failed: int
    results: List[Tuple[str, UpsertResult]]


async def batch_upsert_episodes(
    client: GraphitiClient,
    episodes: List[Tuple[str, Dict[str, Any], str]],  # (name, body, group_id)
    force: bool = False
) -> BatchUpsertResult:
    """Upsert multiple episodes.
    
    Args:
        client: GraphitiClient instance
        episodes: List of (name, body, group_id) tuples
        force: If True, update existing episodes
        
    Returns:
        BatchUpsertResult with counts and individual results
    """
    results = []
    counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    
    for name, body, group_id in episodes:
        result = await upsert_episode(client, name, body, group_id, force)
        results.append((name, result))
        counts[result.action] = counts.get(result.action, 0) + 1
    
    return BatchUpsertResult(
        total=len(episodes),
        created=counts["created"],
        updated=counts["updated"],
        skipped=counts["skipped"],
        failed=counts["failed"],
        results=results
    )
```

### 4. GraphitiClient Extension

Add convenience methods to the client:

```python
# Additions to guardkit/knowledge/graphiti_client.py

class GraphitiClient:
    """Extended with upsert support."""
    
    async def upsert_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        force: bool = False
    ) -> Optional[str]:
        """Insert or update an episode.
        
        Args:
            name: Episode name
            episode_body: Episode content (JSON string or dict)
            group_id: Group ID
            force: If True, update existing
            
        Returns:
            Episode UUID if successful, None otherwise
        """
        from .episode_operations import upsert_episode
        
        body = episode_body
        if isinstance(body, str):
            import json
            body = json.loads(body)
        
        result = await upsert_episode(self, name, body, group_id, force)
        return result.episode_id if result.success else None
    
    async def upsert_project_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        force: bool = False
    ) -> Optional[str]:
        """Insert or update a project-namespaced episode.
        
        Automatically prefixes group_id with project namespace.
        """
        namespaced_group = self.get_project_group_id(group_id)
        return await self.upsert_episode(name, episode_body, namespaced_group, force)
```

---

## Success Criteria

1. **Duplicate detection works** - `episode_exists` correctly identifies existing episodes
2. **Upsert creates when new** - New episodes are created normally
3. **Upsert skips when exists (no force)** - Existing episodes not modified without `--force`
4. **Upsert updates when exists (with force)** - Existing episodes updated with version increment
5. **Version tracking** - Version increments on update
6. **Batch support** - Can upsert multiple episodes efficiently

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-PRE-003A | Create `episode_operations.py` with existence check | 1h |
| TASK-GR-PRE-003B | Implement `upsert_episode` function | 2h |
| TASK-GR-PRE-003C | Implement version tracking helpers | 0.5h |
| TASK-GR-PRE-003D | Implement `batch_upsert_episodes` | 1h |
| TASK-GR-PRE-003E | Add convenience methods to GraphitiClient | 0.5h |
| TASK-GR-PRE-003F | Add tests | 1.5h |
| TASK-GR-PRE-003G | Update documentation | 0.5h |

**Total Estimate**: 7 hours

---

## Usage Examples

### Single Upsert

```python
from guardkit.knowledge.episode_operations import upsert_episode

# First time - creates
result = await upsert_episode(
    client,
    name="feature_spec_FEAT-SKEL-001",
    episode_body={"id": "FEAT-SKEL-001", "title": "Walking Skeleton"},
    group_id="feature_specs",
    force=False
)
print(result.action)  # "created"

# Second time (no force) - skips
result = await upsert_episode(
    client,
    name="feature_spec_FEAT-SKEL-001",
    episode_body={"id": "FEAT-SKEL-001", "title": "Updated Title"},
    group_id="feature_specs",
    force=False
)
print(result.action)  # "skipped"

# With force - updates
result = await upsert_episode(
    client,
    name="feature_spec_FEAT-SKEL-001",
    episode_body={"id": "FEAT-SKEL-001", "title": "Updated Title"},
    group_id="feature_specs",
    force=True
)
print(result.action)  # "updated"
print(result.previous_version)  # 1
# New version is 2
```

### Client Convenience Method

```python
client = get_graphiti()

# Upsert project episode
episode_id = await client.upsert_project_episode(
    name="feat_skel_001",
    episode_body=json.dumps(spec),
    group_id="feature_specs",
    force=True
)
```

### Batch Upsert

```python
from guardkit.knowledge.episode_operations import batch_upsert_episodes

episodes = [
    ("feat_001", {"id": "FEAT-001"}, "feature_specs"),
    ("feat_002", {"id": "FEAT-002"}, "feature_specs"),
    ("feat_003", {"id": "FEAT-003"}, "feature_specs"),
]

result = await batch_upsert_episodes(client, episodes, force=False)
print(f"Created: {result.created}, Skipped: {result.skipped}")
```

---

## Integration with FEAT-GR-002

The `add-context` command will use upsert:

```python
# In context_ingestor.py

async def ingest_file(
    file_path: Path,
    context_type: str,
    force: bool = False
) -> IngestResult:
    """Ingest a file using upsert logic."""
    
    # Parse file...
    parsed = parser.parse(file_path)
    
    # Upsert instead of add
    result = await upsert_episode(
        client,
        name=generate_episode_name(parsed),
        episode_body=parsed.to_dict(),
        group_id=group_id,
        force=force
    )
    
    return IngestResult(
        file_path=file_path,
        success=result.success,
        action=result.action,
        error=result.error
    )
```

---

## Temporal Versioning Notes

Graphiti supports temporal versioning via `valid_at` and `invalid_at` on episodes:

- When we "update" an episode, we're actually creating a new one
- Graphiti's temporal model means the old version is still queryable at past points in time
- We increment our `version` field in `_metadata` for easy tracking
- This gives us both point-in-time queries (Graphiti's temporal) and simple version numbers (our metadata)
