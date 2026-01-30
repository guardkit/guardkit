# FEAT-GR-PRE-000: Seeding Metadata Update

> **Purpose**: Update the existing Graphiti seeding infrastructure to use standardized metadata schema.
>
> **Priority**: High (Prerequisite)
> **Estimated Complexity**: 2
> **Dependencies**: None (first prerequisite)
> **Blocks**: FEAT-GR-PRE-002 (Episode Metadata Schema)

---

## Problem Statement

The current seeding in `seeding.py` creates episodes without standardized metadata:

```python
# Current format
("guardkit_overview", {
    "entity_type": "product",  # Present but not standardized
    "name": "GuardKit",
    "description": "...",
    # Missing: source_type, version, timestamps, project_id
})
```

This causes issues:

1. **No source tracking** - Can't tell seeding data from user-added data
2. **No versioning** - Can't track when knowledge was updated
3. **No timestamps** - Can't query by recency
4. **Inconsistent with new features** - FEAT-GR-PRE-002 defines metadata schema that existing data doesn't follow

---

## Proposed Solution

### 1. Create Seeding Helper with Metadata

```python
# guardkit/knowledge/seeding_utils.py

from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import json
import logging

logger = logging.getLogger(__name__)

# Seeding metadata version - increment when schema changes
SEEDING_METADATA_VERSION = "2.0.0"


def create_seeding_metadata(
    entity_type: str,
    group_id: str
) -> Dict[str, Any]:
    """Create standard metadata for seeded episodes.
    
    Args:
        entity_type: Type of entity being seeded
        group_id: Group ID for the episode
        
    Returns:
        Metadata dictionary to include in episode body
    """
    now = datetime.now(timezone.utc).isoformat()
    
    return {
        "entity_type": entity_type,
        "source_type": "system_seeding",
        "source_command": "guardkit graphiti seed",
        "project_id": None,  # System knowledge, not project-specific
        "version": 1,
        "seeding_version": SEEDING_METADATA_VERSION,
        "confidence": 1.0,
        "created_at": now,
        "updated_at": now
    }


def wrap_episode_with_metadata(
    body: Dict[str, Any],
    entity_type: str,
    group_id: str
) -> Dict[str, Any]:
    """Wrap episode body with standard metadata.
    
    Args:
        body: Original episode body
        entity_type: Type of entity
        group_id: Group ID
        
    Returns:
        Episode body with _metadata field added
    """
    # Ensure entity_type is in body (for backward compat queries)
    body["entity_type"] = entity_type
    
    # Add metadata block
    body["_metadata"] = create_seeding_metadata(entity_type, group_id)
    
    return body


async def add_episodes_with_metadata(
    client,
    episodes: List[Tuple[str, Dict[str, Any]]],
    group_id: str,
    entity_type: str,
    category_name: str
) -> None:
    """Add multiple episodes with standard metadata.
    
    Replaces the _add_episodes helper in seeding.py with metadata support.
    
    Args:
        client: GraphitiClient instance
        episodes: List of (name, body_dict) tuples
        group_id: Group ID for all episodes
        entity_type: Entity type for all episodes
        category_name: Human-readable name for logging
    """
    if not client.enabled:
        logger.debug(f"Skipping {category_name} seeding - client disabled")
        return
    
    for name, body in episodes:
        try:
            # Wrap with metadata
            body_with_metadata = wrap_episode_with_metadata(
                body.copy(),  # Don't mutate original
                entity_type,
                group_id
            )
            
            await client.add_episode(
                name=name,
                episode_body=json.dumps(body_with_metadata),
                group_id=group_id
            )
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")
```

### 2. Update Seeding Version

```python
# Updates to seeding.py

SEEDING_VERSION = "2.0.0"  # Increment from 1.0.0 to indicate metadata support
```

### 3. Add Clear Command

```python
# guardkit/cli/graphiti.py - new command

@graphiti.command("clear")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm clearing all Graphiti data"
)
@click.option(
    "--system-only",
    is_flag=True,
    help="Only clear system knowledge (preserve project knowledge)"
)
def clear(confirm: bool, system_only: bool):
    """Clear Graphiti knowledge graph data.
    
    WARNING: This permanently deletes knowledge from Neo4j.
    
    Use --system-only to preserve project-specific knowledge
    while clearing system seeding data.
    
    Examples:
    
        guardkit graphiti clear --confirm
        
        guardkit graphiti clear --system-only --confirm
    """
    if not confirm:
        console.print("[yellow]This will permanently delete Graphiti data.[/yellow]")
        console.print("Run with --confirm to proceed.")
        console.print("")
        console.print("Options:")
        console.print("  --confirm      Required to proceed with deletion")
        console.print("  --system-only  Only clear system knowledge groups")
        return
    
    asyncio.run(_cmd_clear(system_only))


async def _cmd_clear(system_only: bool) -> None:
    """Async implementation of clear command."""
    
    client, settings = _get_client_and_config()
    
    if not settings.enabled:
        console.print("[yellow]Graphiti is disabled in configuration.[/yellow]")
        return
    
    console.print(f"Connecting to Neo4j at {settings.neo4j_uri}...")
    
    try:
        initialized = await client.initialize()
    except Exception as e:
        console.print(f"[red]Error connecting to Graphiti: {e}[/red]")
        raise SystemExit(1)
    
    try:
        if not initialized or not client.enabled:
            console.print("[yellow]Graphiti not available.[/yellow]")
            return
        
        console.print("[green]Connected[/green]")
        
        if system_only:
            console.print("Clearing system knowledge groups...")
            groups_to_clear = [
                "product_knowledge",
                "command_workflows",
                "quality_gate_phases",
                "technology_stack",
                "feature_build_architecture",
                "architecture_decisions",
                "failure_patterns",
                "component_status",
                "integration_points",
                "templates",
                "agents",
                "patterns",
                "rules",
                "failed_approaches",
                "quality_gate_configs",
                "feature_overviews",
                "role_constraints",
            ]
            
            for group_id in groups_to_clear:
                await _clear_group(client, group_id)
                console.print(f"  [green]✓[/green] Cleared {group_id}")
        else:
            console.print("Clearing all Graphiti data...")
            await _clear_all_data(client)
            console.print("[green]✓[/green] All data cleared")
        
        # Clear seeding marker
        clear_seeding_marker()
        console.print("[green]✓[/green] Seeding marker cleared")
        
        console.print("")
        console.print("[bold green]Clear complete![/bold green]")
        console.print("Run 'guardkit graphiti seed' to re-seed system knowledge.")
        
    finally:
        await client.close()


async def _clear_group(client, group_id: str) -> None:
    """Clear all episodes in a specific group."""
    if not client._graphiti:
        return
    
    try:
        driver = client._graphiti.driver
        async with driver.session() as session:
            await session.run(
                "MATCH (e:Episode) WHERE e.group_id = $group_id DETACH DELETE e",
                group_id=group_id
            )
    except Exception as e:
        logger.warning(f"Error clearing group {group_id}: {e}")


async def _clear_all_data(client) -> None:
    """Clear all data from Neo4j."""
    if not client._graphiti:
        return
    
    try:
        driver = client._graphiti.driver
        async with driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
    except Exception as e:
        logger.warning(f"Error clearing all data: {e}")
```

### 4. Update Seeding Functions

Update each seeding function to use metadata. Example for `seed_product_knowledge`:

```python
# Updated seed_product_knowledge in seeding.py

from guardkit.knowledge.seeding_utils import add_episodes_with_metadata

async def seed_product_knowledge(client) -> None:
    """Seed core product knowledge about GuardKit."""
    if not client or not client.enabled:
        return
    
    episodes = [
        ("guardkit_overview", {
            "name": "GuardKit",
            "tagline": "Lightweight AI-Assisted Development with Quality Gates",
            "description": "GuardKit is a lightweight, pragmatic task workflow system...",
            "target_users": ["solo developers", "small teams", "AI-augmented development"],
            "competitive_differentiator": "Quality gates that prevent broken code"
        }),
        # ... other episodes
    ]
    
    # Use new helper with metadata
    await add_episodes_with_metadata(
        client,
        episodes,
        group_id="product_knowledge",
        entity_type="product",
        category_name="product knowledge"
    )
```

---

## Success Criteria

1. **Seeding uses metadata** - All seeded episodes include `_metadata` block
2. **Clear command works** - Can clear system knowledge or all data
3. **Backward compatible queries** - Old queries still work (entity_type at top level)
4. **Seeding marker updated** - Version bumped to 2.0.0

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-PRE-000A | Create `seeding_utils.py` with metadata helpers | 1h |
| TASK-GR-PRE-000B | Add `clear` command to CLI | 1.5h |
| TASK-GR-PRE-000C | Update all seeding functions to use metadata | 2h |
| TASK-GR-PRE-000D | Add tests | 1h |
| TASK-GR-PRE-000E | Update documentation | 0.5h |

**Total Estimate**: 6 hours

---

## Usage

### Clear and Re-seed with Metadata

```bash
# Clear existing data
guardkit graphiti clear --confirm

# Re-seed with metadata
guardkit graphiti seed

# Verify
guardkit graphiti verify
```

### Clear System Only (Future Use)

```bash
# When you have project knowledge you want to keep
guardkit graphiti clear --system-only --confirm
guardkit graphiti seed
```

---

## Episode Body Format (After Update)

```json
{
  "entity_type": "product",
  "name": "GuardKit",
  "tagline": "Lightweight AI-Assisted Development with Quality Gates",
  "description": "...",
  "target_users": ["solo developers", "small teams"],
  "_metadata": {
    "entity_type": "product",
    "source_type": "system_seeding",
    "source_command": "guardkit graphiti seed",
    "project_id": null,
    "version": 1,
    "seeding_version": "2.0.0",
    "confidence": 1.0,
    "created_at": "2025-01-30T12:00:00Z",
    "updated_at": "2025-01-30T12:00:00Z"
  }
}
```

Note: `entity_type` is duplicated at top level for backward compatible queries.

---

## Dependency on FEAT-GR-PRE-002

This feature creates a simple metadata schema inline. When FEAT-GR-PRE-002 is implemented, `seeding_utils.py` should be updated to use the formal `EpisodeMetadata` class:

```python
# After FEAT-GR-PRE-002
from guardkit.knowledge.episode_metadata import EpisodeMetadata, SourceType

def create_seeding_metadata(entity_type: str, group_id: str) -> Dict[str, Any]:
    metadata = EpisodeMetadata(
        entity_type=entity_type,
        source_type=SourceType.SYSTEM_SEEDING.value,
        source_command="guardkit graphiti seed"
    )
    return metadata.to_dict()
```
