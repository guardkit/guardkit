---
id: TASK-GR-PID-001
title: Always use explicit project_id from config (no auto-detection from directory)
status: completed
created: 2026-02-04T16:30:00Z
updated: 2026-02-04T18:00:00Z
completed: 2026-02-04T18:00:00Z
priority: high
tags: [graphiti, knowledge-graph, project-isolation, configuration]
task_type: implementation
complexity: 4
parent_review: TASK-REV-2F28
test_results:
  status: passed
  coverage: 85
  last_run: 2026-02-04T17:45:00Z
---

# Task: Always use explicit project_id from config

## Context

Review TASK-REV-2F28 identified that Graphiti's default behavior of auto-detecting project_id from the current working directory name causes knowledge to be orphaned when repositories are moved or cloned to different locations.

**Decision**: Always use explicit project_id stored in `.guardkit/graphiti.yaml`. This provides:
- Repository can be moved/renamed without orphaning knowledge
- Multiple clones of same repo share the same knowledge namespace
- No confusing questions for users about Graphiti namespacing

## Current Behavior (Problem)

```python
# graphiti_client.py:207-211
if self.config.project_id is not None:
    self._project_id = self.config.project_id
elif auto_detect_project:
    self._project_id = normalize_project_id(get_current_project_name())  # Uses cwd name!
```

And in CLI (`graphiti.py:42-57`):
```python
def _get_client_and_config() -> tuple[GraphitiClient, GraphitiSettings]:
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        # ... other fields
        # BUG: settings.project_id is NOT passed to GraphitiConfig!
    )
```

## Desired Behavior

1. **During `guardkit init`**:
   - Detect project name from directory (one-time)
   - Store in `.guardkit/graphiti.yaml` as `project_id: "my-project"`
   - This becomes the permanent identifier

2. **During all Graphiti operations**:
   - Load `project_id` from `.guardkit/graphiti.yaml`
   - Use it for all group_id prefixing
   - Never auto-detect from directory name

3. **Fallback (if no config)**:
   - Only for backwards compatibility or first run
   - Auto-detect from directory name
   - Emit warning: "No explicit project_id configured, using directory name"

## Implementation Plan

### Phase 1: Fix GraphitiConfig/Client Integration

**File**: `guardkit/cli/graphiti.py`

```python
def _get_client_and_config() -> tuple[GraphitiClient, GraphitiSettings]:
    settings = load_graphiti_config()
    config = GraphitiConfig(
        enabled=settings.enabled,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        timeout=settings.timeout,
        project_id=settings.project_id,  # ADD THIS LINE
    )
    client = GraphitiClient(config)
    return client, settings
```

### Phase 2: Update guardkit init to Write project_id

**File**: `guardkit/cli/init.py` (or wherever init logic lives)

During init:
1. Detect project name from directory
2. Normalize it
3. Write to `.guardkit/graphiti.yaml`:

```yaml
# .guardkit/graphiti.yaml
enabled: true
neo4j_uri: bolt://localhost:7687
neo4j_user: neo4j
neo4j_password: password123
timeout: 30.0
project_id: "youtube-transcript-mcp"  # Set during init, never changes
```

### Phase 3: Add Warning for Missing project_id

**File**: `guardkit/knowledge/graphiti_client.py`

In `GraphitiClient.__init__`:

```python
def __init__(self, config: Optional[GraphitiConfig] = None, auto_detect_project: bool = True):
    self.config = config or GraphitiConfig()

    if self.config.project_id is not None:
        self._project_id = self.config.project_id
    elif auto_detect_project:
        # Fallback - emit warning
        self._project_id = normalize_project_id(get_current_project_name())
        logger.warning(
            f"No explicit project_id configured, using directory name '{self._project_id}'. "
            "Run 'guardkit init' or set project_id in .guardkit/graphiti.yaml for portable configuration."
        )
    else:
        self._project_id = None
```

### Phase 4: Update All Client Instantiation Points

Search for all places that create `GraphitiClient` and ensure they pass `project_id` from config:

**Files to update** (from exploration):
- `guardkit/cli/graphiti.py` - `_get_client_and_config()`
- `guardkit/cli/init.py` - init command
- `guardkit/knowledge/seeding.py` - if it creates client
- `guardkit/knowledge/project_seeding.py` - if it creates client
- Any other CLI commands that use Graphiti directly

### Phase 5: Update Tests

**Test files to update**:
- `tests/knowledge/test_graphiti_client_project_id.py`
- `tests/knowledge/test_graphiti_group_prefixing.py`
- `tests/integration/graphiti/test_project_init.py`
- `tests/integration/graphiti/test_multi_project_namespace.py`

New test cases:
1. `test_project_id_loaded_from_config_file`
2. `test_project_id_survives_directory_rename`
3. `test_warning_emitted_when_no_config`
4. `test_init_writes_project_id_to_config`

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/cli/graphiti.py` | Pass `settings.project_id` to GraphitiConfig |
| `guardkit/cli/init.py` | Write `project_id` to graphiti.yaml during init |
| `guardkit/knowledge/graphiti_client.py` | Add warning when falling back to auto-detect |
| `guardkit/knowledge/config.py` | Already supports project_id (no change needed) |
| Tests (multiple) | Add tests for new behavior |

## Files to NOT Modify

These files use the client but don't create it - they'll automatically get the fix:
- All seeding modules (`seed_*.py`)
- All knowledge managers (`*_manager.py`)
- All context loaders (`*_context*.py`)
- All parsers (`parsers/*.py`)

## Acceptance Criteria

- [x] `guardkit init` writes `project_id` to `.guardkit/graphiti.yaml`
- [x] All Graphiti operations use `project_id` from config
- [x] Moving/renaming directory does NOT change the project namespace
- [x] Warning logged when falling back to directory-based detection
- [x] Existing tests pass
- [x] New tests verify config-based project_id behavior

## Migration Notes

**For existing users** (just you):
1. Run `guardkit init` in your project
2. It will create/update `.guardkit/graphiti.yaml` with explicit `project_id`
3. If you have existing knowledge, it will remain accessible (same project name)
4. Future moves/clones will preserve the namespace

**No breaking changes** - fallback to directory detection ensures backwards compatibility.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Break existing projects without config | Fallback to auto-detect with warning |
| Tests fail due to missing config | Mock config in tests |
| Init doesn't create .guardkit dir | Ensure dir creation before writing yaml |

## Related Files

- Review report: `.claude/reviews/TASK-REV-2F28-graphiti-isolation-review.md`
- Config module: `guardkit/knowledge/config.py`
- Client module: `guardkit/knowledge/graphiti_client.py`
- Project module: `guardkit/integrations/graphiti/project.py`
