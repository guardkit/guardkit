# Episode Metadata Schema

Deep-dive into Graphiti episode metadata schema used by GuardKit for tracking, versioning, and deduplication.

## Overview

All episodes seeded into Graphiti include a `_metadata` block that provides:
- **Version tracking**: Know which seeding version created the episode
- **Deduplication**: Prevent duplicate episodes across re-seeding
- **Provenance tracking**: Track where knowledge came from
- **Update detection**: Detect when content has changed
- **Unique identification**: Consistent entity IDs for relationships

## Metadata Schema

### Complete Schema

```json
{
  "_metadata": {
    "source": "string",           // Source of the episode
    "version": "string",           // Seeding version (semver)
    "created_at": "ISO8601",       // UTC timestamp when created
    "updated_at": "ISO8601",       // UTC timestamp of last update
    "source_hash": "string|null",  // SHA256 hash of source file
    "entity_id": "string"          // Unique entity identifier
  }
}
```

### Field Descriptions

#### `source` (required, string)

Identifies where the episode originated from.

**Values:**
- `"guardkit_seeding"`: System context seeded by GuardKit
- `"project_seeding"`: Project-specific knowledge
- `"user_interaction"`: Knowledge from user conversations
- `"feature_build"`: Knowledge from feature-build sessions
- `"task_work"`: Knowledge from task-work sessions

**Example:**
```json
{
  "_metadata": {
    "source": "guardkit_seeding"
  }
}
```

---

#### `version` (required, string)

Seeding version in semantic versioning format (MAJOR.MINOR.PATCH).

Tracks which version of GuardKit created this episode, enabling:
- Detection of outdated knowledge
- Selective re-seeding by version
- Version-specific query filtering

**Example:**
```json
{
  "_metadata": {
    "version": "1.0.0"
  }
}
```

**Version bumping:**
- **MAJOR**: Breaking changes to schema or significant knowledge rewrites
- **MINOR**: New knowledge categories or significant additions
- **PATCH**: Bug fixes, clarifications, minor updates

---

#### `created_at` (required, ISO8601 timestamp)

UTC timestamp when episode was first created.

**Format:** ISO 8601 with timezone (always UTC)

**Example:**
```json
{
  "_metadata": {
    "created_at": "2024-01-30T12:00:00+00:00"
  }
}
```

**Usage:**
- Audit trail of when knowledge was added
- Age-based queries (e.g., "show recent additions")
- Freshness indicators

---

#### `updated_at` (required, ISO8601 timestamp)

UTC timestamp of last update to this episode.

**Format:** ISO 8601 with timezone (always UTC)

**Example:**
```json
{
  "_metadata": {
    "updated_at": "2024-01-30T14:30:00+00:00"
  }
}
```

**Usage:**
- Track when knowledge was last refreshed
- Detect stale knowledge
- Update notification triggers

**Note:** On creation, `updated_at` = `created_at`

---

#### `source_hash` (optional, string or null)

SHA256 hash of the source file that generated this episode.

**Values:**
- **null**: Generated/synthetic content (not file-based)
- **string**: 64-character hex SHA256 hash

**Example:**
```json
{
  "_metadata": {
    "source_hash": "a3b5c7d9e1f2a3b5c7d9e1f2a3b5c7d9e1f2a3b5c7d9e1f2a3b5c7d9e1f2a3b5"
  }
}
```

**Usage:**
- Detect when source file has changed
- Skip re-seeding if hash matches
- Incremental updates (only changed files)

**System context episodes:** Always `null` (generated, not file-based)

---

#### `entity_id` (required, string)

Unique identifier for this episode entity, used for deduplication.

**Format:** Snake_case string, typically `{category}_{name}`

**Example:**
```json
{
  "_metadata": {
    "entity_id": "command_task_work"
  }
}
```

**Generation:**
- System context: Uses episode name from seeding function
- File-based: Uses file path or name
- User interactions: Generated UUID or conversation ID

**Usage:**
- **Deduplication**: Prevent duplicate episodes with same entity_id
- **Updates**: Replace episode with matching entity_id
- **Relationships**: Reference entities consistently across episodes

---

## Example Episodes with Metadata

### System Context Episode

```json
{
  "entity_type": "command",
  "name": "/task-work",
  "purpose": "Implement a task through the 5-phase quality gate workflow",
  "syntax": "/task-work TASK-XXX [--mode=standard|tdd|bdd]",
  "phases_executed": "Phase 1 -> Phase 2 -> Phase 2.5 -> Phase 3 -> Phase 4 -> Phase 5",
  "_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2024-01-30T12:00:00+00:00",
    "updated_at": "2024-01-30T12:00:00+00:00",
    "source_hash": null,
    "entity_id": "command_task_work"
  }
}
```

### Template Episode

```json
{
  "entity_type": "template",
  "id": "fastapi-python",
  "name": "Python FastAPI Backend",
  "description": "Production-ready FastAPI template",
  "language": "Python",
  "frameworks": ["FastAPI", "SQLAlchemy", "Pydantic"],
  "_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2024-01-30T12:05:00+00:00",
    "updated_at": "2024-01-30T12:05:00+00:00",
    "source_hash": null,
    "entity_id": "template_fastapi_python"
  }
}
```

### Failed Approach Episode

```json
{
  "entity_type": "failed_approach",
  "approach_id": "subprocess_to_cli",
  "symptom": "subprocess.CalledProcessError for guardkit task-work",
  "root_cause": "guardkit task-work CLI command does not exist",
  "fix": "Use SDK query() with slash command in prompt",
  "prevention": "Never use subprocess for task-work invocation",
  "_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2024-01-30T12:10:00+00:00",
    "updated_at": "2024-01-30T12:10:00+00:00",
    "source_hash": null,
    "entity_id": "failed_approach_subprocess_to_cli"
  }
}
```

---

## Metadata Injection

Metadata is automatically injected by the `_add_episodes()` function in `guardkit/knowledge/seeding.py`:

```python
async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    """Add episodes with automatic metadata injection."""
    for name, body in episodes:
        # Inject metadata block
        timestamp = datetime.now(timezone.utc).isoformat()
        body_with_metadata = {
            **body,
            "_metadata": {
                "source": "guardkit_seeding",
                "version": SEEDING_VERSION,
                "created_at": timestamp,
                "updated_at": timestamp,
                "source_hash": None,
                "entity_id": name,
            }
        }

        await client.add_episode(
            name=name,
            episode_body=json.dumps(body_with_metadata),
            group_id=group_id
        )
```

**Key points:**
- Metadata is added automatically - episode definitions don't include it
- `created_at` and `updated_at` are set to current UTC time
- `entity_id` defaults to episode name (can be overridden)
- `source_hash` is `None` for generated content

---

## Deduplication Strategy

The `entity_id` field enables deduplication:

### Simple Deduplication

Check if episode with same `entity_id` already exists:

```cypher
MATCH (e:Episode {entity_id: $entity_id})
RETURN e
```

If exists, decide:
- **Replace**: Delete old, insert new
- **Update**: Modify existing episode
- **Skip**: Keep existing, don't add new

### Version-Aware Deduplication

Only replace if version has changed:

```cypher
MATCH (e:Episode {entity_id: $entity_id})
WHERE e.metadata.version < $new_version
DELETE e
```

### Hash-Based Deduplication

For file-based episodes, skip if hash matches:

```cypher
MATCH (e:Episode {entity_id: $entity_id})
WHERE e.metadata.source_hash = $source_hash
RETURN e  // Skip seeding
```

---

## Version Management

### Checking Seeding Version

The seeding marker file stores the version:

```json
{
  "seeded": true,
  "version": "1.0.0",
  "timestamp": "2024-01-30T12:00:00+00:00"
}
```

### Selective Re-Seeding

Re-seed only if version has changed:

```python
def needs_reseeding(client_version: str) -> bool:
    """Check if re-seeding is needed."""
    marker = load_marker_file()
    if not marker:
        return True

    # Compare versions
    return marker["version"] != client_version
```

### Version Queries

Find episodes by version:

```python
async def find_episodes_by_version(client, version: str):
    """Find all episodes created by specific version."""
    results = await client.search(
        query=f"metadata.version:{version}",
        num_results=1000
    )
    return results
```

---

## Update Detection

### Timestamp-Based

Find episodes updated after a certain time:

```python
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)
cutoff_iso = cutoff.isoformat()

# Find episodes updated in last 30 days
results = await client.search(
    query=f"metadata.updated_at > {cutoff_iso}",
    num_results=100
)
```

### Hash-Based

Detect when source file has changed:

```python
import hashlib

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()

def has_file_changed(file_path: Path, stored_hash: str) -> bool:
    """Check if file hash has changed."""
    current_hash = compute_file_hash(file_path)
    return current_hash != stored_hash
```

---

## Provenance Tracking

The `source` field enables provenance queries:

### Find System Context

```python
results = await client.search(
    query="metadata.source:guardkit_seeding",
    num_results=1000
)
```

### Find User-Generated Knowledge

```python
results = await client.search(
    query="metadata.source:user_interaction",
    num_results=100
)
```

### Find Feature-Build Knowledge

```python
results = await client.search(
    query="metadata.source:feature_build",
    num_results=50
)
```

---

## Schema Evolution

### Adding New Fields

To add new metadata fields:

1. Update `_add_episodes()` to include new field
2. Bump `SEEDING_VERSION` (minor version)
3. Document new field in this guide
4. Re-seed with `--force`

**Example:**
```python
body_with_metadata = {
    **body,
    "_metadata": {
        "source": "guardkit_seeding",
        "version": SEEDING_VERSION,
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_hash": None,
        "entity_id": name,
        "new_field": "new_value",  # New field
    }
}
```

### Deprecating Fields

To deprecate a field:

1. Mark as deprecated in this guide
2. Continue populating (backwards compatibility)
3. After 2 major versions, remove field
4. Bump `SEEDING_VERSION` (major version)

---

## Best Practices

### 1. Use Consistent Entity IDs

```python
# Good: Consistent format
"command_task_work"
"template_fastapi_python"
"pattern_dependency_injection"

# Bad: Inconsistent format
"taskWork"
"template-fastapi"
"pattern_dep_inj"
```

### 2. Always Include All Required Fields

```python
# Good: All required fields present
"_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2024-01-30T12:00:00+00:00",
    "updated_at": "2024-01-30T12:00:00+00:00",
    "source_hash": None,
    "entity_id": "command_task_work"
}

# Bad: Missing fields
"_metadata": {
    "source": "guardkit_seeding",
    "version": "1.0.0"
}
```

### 3. Use UTC Timestamps

```python
# Good: UTC timezone
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()

# Bad: Local time without timezone
timestamp = datetime.now().isoformat()
```

### 4. Compute Source Hash for Files

```python
# Good: Hash actual file content
source_hash = hashlib.sha256(file.read_bytes()).hexdigest()

# Bad: Use file path as hash
source_hash = str(hash(file_path))
```

### 5. Bump Version Appropriately

- **Major (1.0.0 → 2.0.0)**: Breaking schema changes
- **Minor (1.0.0 → 1.1.0)**: New fields, new categories
- **Patch (1.0.0 → 1.0.1)**: Bug fixes, typos

---

## Validation

### Required Field Validation

```python
def validate_metadata(metadata: dict) -> bool:
    """Validate metadata has all required fields."""
    required = ["source", "version", "created_at", "updated_at", "source_hash", "entity_id"]
    return all(field in metadata for field in required)
```

### Timestamp Validation

```python
from datetime import datetime

def validate_timestamp(timestamp: str) -> bool:
    """Validate ISO8601 timestamp."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.tzinfo is not None  # Must have timezone
    except ValueError:
        return False
```

### Version Validation

```python
import re

def validate_version(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))
```

---

## See Also

- [Graphiti Commands Guide](../../guides/graphiti-commands.md) - CLI command reference
- [Graphiti Integration Guide](../../guides/graphiti-integration-guide.md) - Overall architecture
- [Seeding Module](../../../guardkit/knowledge/seeding.py) - Implementation details
- [TASK-GR-PRE-000-A](../../../tasks/in_review/TASK-GR-PRE-000-A-add-metadata-to-seeding.md) - Metadata implementation task
