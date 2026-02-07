# ADR-GBF-001: Unified Episode Serialization Pattern

## Status
**Accepted and Implemented** (TASK-GBF-001, 2026-02-07)

## Context

### Current Problem

The GuardKit codebase has evolved two parallel paths for serializing episodes to Graphiti:

1. **Entity-Level Serialization** (via `to_episode_body()`)
   - Entities return dicts with fields embedded (sometimes including metadata fields like `entity_type`, `created_at`, `updated_at`)
   - Example: `TurnStateEntity.to_episode_body()` returns dict with `entity_type`, `turned_state`, timestamps
   - Example: `TaskOutcome.to_episode_body()` returns **human-readable string** (the outlier)

2. **Client-Level Serialization** (via `GraphitiClient._inject_metadata()`)
   - Adds metadata block (source, version, created_at, updated_at, source_hash, entity_id) to episode
   - Appends markdown section to episode body

3. **Manual Injection in Seeding** (via `seed_helpers._add_episodes()`)
   - Manually injects `_metadata` dict into body BEFORE calling `add_episode()`
   - Then `add_episode()` ALSO injects metadata via `_inject_metadata()`
   - Result: Episodes get metadata twice (once as dict, once as markdown)

### Inconsistency Patterns

**Problem 1: Double Metadata Injection**
- Episodes created via `seed_helpers._add_episodes()` get metadata from two sources:
  - Dict: `body["_metadata"] = {...}`
  - Markdown: `_inject_metadata()` appends block
- Creates duplication and maintenance burden

**Problem 2: Inconsistent Return Types**
- 5 entities return `dict` from `to_episode_body()`
- `TaskOutcome` returns `str` (human-readable text) - inconsistent with others
- Callers must handle both types

**Problem 3: Inconsistent Metadata in Entity Bodies**
| Entity | Fields in Body |
|--------|---|
| TurnStateEntity | `entity_type` |
| FailedApproachEpisode | `entity_type` |
| FeatureOverviewEntity | `entity_type`, `created_at`, `updated_at` |
| QualityGateConfigFact | `entity_type`, `version`, `effective_from` |
| RoleConstraintFact | `entity_type`, `created_at` |

**Problem 4: Seeding vs Runtime Patterns Diverge**
- Seeding: manual `_metadata` dict injection → `add_episode()` injects again
- Runtime (managers): only `add_episode()` metadata injection
- Direct seeding (seed_failed_approaches): no `_metadata`, only `add_episode()`

### Impact of Current State

1. **Maintenance Burden**: Two serialization paths to maintain
2. **Subtle Bugs**: Risk of metadata fields diverging
3. **Test Fragility**: Tests must account for both paths
4. **Inconsistent Semantics**: What "metadata" means is ambiguous
5. **Future Scalability**: Adding new entity types requires deciding which path to follow

## Decision

**Adopt client-level metadata injection as the canonical pattern.**

### Rationale

1. **Single Responsibility Principle**
   - `to_episode_body()` responsibility: Return clean domain data only
   - `GraphitiClient.add_episode()` responsibility: Add infrastructure metadata (source, version, timestamps)

2. **Automatic Fallback**
   - `GraphitiClient.add_episode()` already generates `EpisodeMetadata` if missing
   - No need to manually create metadata at entity level

3. **Consistent Format**
   - All metadata goes through `_inject_metadata()` → consistent markdown format
   - No mixed dict/markdown metadata

4. **Zero Breaking Changes**
   - Public API unchanged (call sites remain the same)
   - Only internal implementation changes

5. **Extensibility**
   - New entities just implement simple `to_episode_body()` returning clean dict
   - Metadata automatically handled by client

## Implementation Strategy

### Phase 1: Standardize Entity `to_episode_body()` Methods

**Remove all metadata fields from entity bodies:**

```python
# BEFORE (TurnStateEntity)
def to_episode_body(self) -> dict:
    return {
        "entity_type": "turn_state",  # ← REMOVE: metadata concern
        "id": self.id,
        "feature_id": self.feature_id,
        # ... rest of domain fields
    }

# AFTER
def to_episode_body(self) -> dict:
    return {
        "id": self.id,
        "feature_id": self.feature_id,
        # ... only domain fields
    }
```

**Affected files:**
- `guardkit/knowledge/entities/turn_state.py` - Remove `entity_type`
- `guardkit/knowledge/entities/failed_approach.py` - Remove `entity_type`
- `guardkit/knowledge/entities/feature_overview.py` - Remove `entity_type`, `created_at`, `updated_at`
- `guardkit/knowledge/facts/quality_gate_config.py` - Remove `entity_type` from body
- `guardkit/knowledge/facts/role_constraint.py` - Remove `entity_type`, `created_at` from body

**Special case: TaskOutcome**
- Currently returns `str`, must return `dict` for consistency
- Convert human-readable text to structured dict:

```python
# BEFORE
def to_episode_body(self) -> str:
    lines = []
    lines.append(f"Outcome ID: {self.id}")
    # ... more text
    return "\n".join(lines)

# AFTER
def to_episode_body(self) -> dict:
    return {
        "id": self.id,
        "outcome_type": self.outcome_type.value,
        "task_id": self.task_id,
        "task_title": self.task_title,
        "success": self.success,
        "summary": self.summary,
        "approach_used": self.approach_used,
        "patterns_used": self.patterns_used,
        # ... all other fields as dict
    }
```

### Phase 2: Fix Seeding Pattern

**Remove manual metadata injection from `seed_helpers._add_episodes()`:**

```python
# BEFORE
async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    for name, body in episodes:
        try:
            # Manually inject metadata
            body_with_metadata = {
                **body,
                "_metadata": {
                    "source": "guardkit_seeding",
                    "version": SEEDING_VERSION,
                    # ...
                }
            }
            await client.add_episode(
                name=name,
                episode_body=json.dumps(body_with_metadata),
                group_id=group_id
            )

# AFTER
async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    for name, body_dict, entity_type, entity_id in episodes:
        try:
            # Let client.add_episode() handle metadata
            await client.add_episode(
                name=name,
                episode_body=json.dumps(body_dict),  # Clean body only
                group_id=group_id,
                source="guardkit_seeding",
                entity_type=entity_type,
                entity_id=entity_id
            )
```

**Note:** This assumes `GraphitiClient.add_episode()` accepts optional `source`, `entity_type`, `entity_id` parameters. If not, this ADR should be split into:
- ADR-GBF-001a: Entity serialization cleanup
- ADR-GBF-001b: Client-level metadata API enhancement

### Phase 3: Update Call Sites

Callers of seeding helpers need to pass entity_type:

```python
# In seed_failed_approaches.py
episodes = [
    (
        failed_approach.id,
        failed_approach.to_episode_body(),
        "failed_approach",  # entity_type
        failed_approach.id  # entity_id
    )
    for failed_approach in approaches
]
await _add_episodes(client, episodes, group_id, "Failed Approaches")
```

**Call sites to update:**
- `guardkit/knowledge/seed_failed_approaches.py`
- `guardkit/knowledge/seed_feature_overviews.py`
- Any other seeding module using `_add_episodes()`

Managers calling `add_episode()` directly:
- `guardkit/knowledge/failed_approach_manager.py`
- `guardkit/knowledge/outcome_manager.py`

Add `entity_type` parameter to each `add_episode()` call.

### Phase 4: Add Consistency Tests

Create `tests/unit/test_episode_serialization.py`:

```python
def test_all_entities_return_dict_from_to_episode_body():
    """Verify all entities return dict (not str) from to_episode_body()."""
    entities = [
        TaskOutcome(...),
        TurnStateEntity(...),
        FailedApproachEpisode(...),
        FeatureOverviewEntity(...),
        QualityGateConfigFact(...),
        RoleConstraintFact(...)
    ]

    for entity in entities:
        body = entity.to_episode_body()
        assert isinstance(body, dict), f"{entity.__class__.__name__} must return dict"

def test_entity_bodies_contain_no_metadata_fields():
    """Verify entity bodies don't contain metadata fields."""
    # These should be injected by client only
    METADATA_FIELDS = {"entity_type", "_metadata", "source", "created_at", "updated_at", "source_hash"}

    entities = [
        TaskOutcome(...),
        TurnStateEntity(...),
        # ... etc
    ]

    for entity in entities:
        body = entity.to_episode_body()
        body_keys = set(body.keys())
        metadata_present = body_keys & METADATA_FIELDS
        assert not metadata_present, f"{entity.__class__.__name__} contains metadata: {metadata_present}"

def test_graphiti_client_injects_metadata():
    """Verify GraphitiClient properly injects metadata."""
    client = GraphitiClient(enabled=True)
    body = {"id": "test", "value": "data"}

    with patch.object(client, '_inject_metadata') as mock_inject:
        mock_inject.return_value = json.dumps({**body, "_metadata": {...}})

        # Call add_episode and verify metadata was injected
        await client.add_episode(
            name="test",
            episode_body=json.dumps(body),
            source="guardkit_seeding",
            entity_type="test_entity"
        )

        mock_inject.assert_called_once()
```

## Consequences

### Positive
1. **Single Serialization Path** - Eliminates dual metadata injection
2. **Consistency** - All entities follow same pattern: clean domain data
3. **Simplicity** - New entities just implement `to_episode_body()`, metadata is automatic
4. **Maintainability** - One place to change if metadata requirements evolve
5. **Type Safety** - All `to_episode_body()` return `dict` consistently
6. **Better Separation** - Entity layer concerns vs infrastructure layer concerns

### Negative
1. **Requires API Changes** - `GraphitiClient.add_episode()` needs `entity_type`, `entity_id`, `source` parameters
2. **Migration Effort** - Update all call sites (moderate effort, ~15-20 call sites)
3. **Testing Complexity** - Must verify no metadata in entity bodies (new test discipline)

### Neutral
1. **No Performance Impact** - Metadata injection happens once instead of twice (slight improvement)
2. **No Breaking Changes** - Public APIs unchanged, internal implementation only

## Alternatives Considered

### Alternative 1: Entity-Level Metadata (Rejected)
**Approach:** Move metadata injection to entity `to_episode_body()` methods

**Why rejected:**
- Violates Single Responsibility Principle
- Entities need to know about `source`, `version`, `entity_id` (infrastructure concerns)
- Makes testing harder (must mock metadata generation)
- Harder to extend (every entity implements same metadata logic)

### Alternative 2: Hybrid with Manual Override (Rejected)
**Approach:** Entity level default, client level override

**Why rejected:**
- More complex, harder to reason about
- Potential for metadata conflicts
- Two paths to maintain anyway

## Related Decisions

- **ADR-GR-001**: Graphiti context injection patterns
- **TASK-GBF-001**: Implementation task for this ADR

## References

**Findings from TASK-REV-C632:**
- Finding 6: Episode serialization dual-path issue identified
- Link: `tasks/backlog/TASK-REV-C632-graphiti-usage-baseline-analysis.md`

**Files to Review:**
- `guardkit/knowledge/graphiti_client.py` - `_inject_metadata()` method
- `guardkit/knowledge/seed_helpers.py` - Manual injection logic
- `guardkit/knowledge/entities/` - All entity `to_episode_body()` implementations
- `guardkit/knowledge/facts/` - Fact `to_episode_body()` implementations
