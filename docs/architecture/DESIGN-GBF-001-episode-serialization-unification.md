# Design Document: Episode Serialization Unification (TASK-GBF-001)

**Architect:** System Design Team
**Date:** 2026-02-07
**Status:** Design Phase Complete - Ready for Implementation
**Complexity:** 4/10 (Low to Medium)
**Related ADR:** ADR-GBF-001

---

## Executive Summary

The GuardKit knowledge layer has evolved two parallel paths for serializing episodes to the Graphiti knowledge graph:

1. **Entity-Level**: Entities embed metadata fields in their `to_episode_body()` output
2. **Client-Level**: `GraphitiClient._inject_metadata()` adds metadata to episode content
3. **Manual Injection**: `seed_helpers._add_episodes()` manually adds metadata dicts

This design document proposes unifying to a **single canonical pattern** (client-level injection) to reduce maintenance burden, improve consistency, and simplify future entity additions.

**Key Outcome:** Cleaner separation of concerns - entities define domain data, client handles infrastructure metadata.

---

## Current Architecture Analysis

### Serialization Path 1: Entity Level

**Current Pattern:**
```python
# Entity defines its own to_episode_body()
class TurnStateEntity:
    def to_episode_body(self) -> dict:
        return {
            "entity_type": "turn_state",      # ← Metadata field
            "id": self.id,                    # ← Domain field
            "feature_id": self.feature_id,    # ← Domain field
            # ... more fields
        }
```

**Issues:**
- Mixes domain and metadata concerns in single method
- Inconsistent: some entities include `entity_type`, some include `created_at`/`updated_at`
- TaskOutcome returns `str` instead of `dict` (breaks abstraction)

### Serialization Path 2: Client Level

**Current Pattern:**
```python
# Client injects metadata when storing
class GraphitiClient:
    async def add_episode(self, name: str, episode_body: str, group_id: str):
        # Manually parse and inject metadata
        body_dict = json.loads(episode_body)
        enriched = self._inject_metadata(body_dict, source, entity_type, entity_id)
        # Store enriched body
```

**Strengths:**
- Single point for metadata injection
- Consistent format across all episodes
- Automatic fallback if metadata missing

**Weakness:**
- `_inject_metadata()` not used consistently by all code paths

### Serialization Path 3: Manual Injection in Seeding

**Current Pattern:**
```python
# seed_helpers manually injects _metadata BEFORE calling add_episode()
async def _add_episodes(client, episodes, group_id):
    for name, body in episodes:
        body["_metadata"] = {
            "source": "guardkit_seeding",
            "version": SEEDING_VERSION,
            # ... metadata
        }
        # Then add_episode() ALSO calls _inject_metadata()
        await client.add_episode(name, json.dumps(body), group_id)
        # Result: Double metadata injection!
```

**Problem:**
- Metadata injected TWICE (once as dict, once as markdown)
- Inconsistent with runtime code paths
- Manual metadata dict construction error-prone

---

## Proposed Architecture

### New Pattern: Client-Level Metadata Injection Only

```
┌─────────────────────────────────────────────────────────┐
│                   Calling Code                          │
│  (seeding, managers, direct operations)                 │
└──────────────────────────┬──────────────────────────────┘
                           │
                           │ Calls with clean body + parameters
                           ▼
┌─────────────────────────────────────────────────────────┐
│              GraphitiClient.add_episode()               │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Input: body_dict, name, source, entity_type, ... │ │
│  │                                                    │ │
│  │ 1. Validate body is dict (no existing metadata)  │ │
│  │ 2. Create EpisodeMetadata with source, version   │ │
│  │ 3. Call _inject_metadata() to merge             │ │
│  │ 4. Serialize to JSON                             │ │
│  │ 5. Store in Graphiti                             │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │
                           │ Stores: clean body + injected metadata
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Graphiti Knowledge Graph               │
│  (episodes with consistent metadata structure)          │
└─────────────────────────────────────────────────────────┘
```

### Entity Method Behavior

**Before:**
```python
class TurnStateEntity:
    def to_episode_body(self) -> dict:
        return {
            "entity_type": "turn_state",       # ← Metadata
            "id": ...,                         # ← Domain
            "feature_id": ...,                 # ← Domain
            "created_at": ...,                 # ← Metadata
            # ... more fields
        }
```

**After:**
```python
class TurnStateEntity:
    def to_episode_body(self) -> dict:
        return {
            # Only domain-specific fields
            "id": ...,
            "feature_id": ...,
            "turn_number": ...,
            # ... rest of domain fields
        }
```

### Seeding Helper Behavior

**Before:**
```python
# Manual metadata dict + _add_episodes() also injects = double injection
body_with_metadata = {
    **body,
    "_metadata": {"source": "...", "version": "..."}  # ← Manual dict
}
await client.add_episode(
    name=name,
    episode_body=json.dumps(body_with_metadata),
    group_id=group_id
    # Missing: source, entity_type, entity_id parameters!
)
```

**After:**
```python
# Clean body + client handles metadata injection
await client.add_episode(
    name=name,
    episode_body=json.dumps(body_dict),  # ← Clean, no metadata
    group_id=group_id,
    source="guardkit_seeding",            # ← Parameters to client
    entity_type="turn_state",
    entity_id=turn_state.id
)
```

---

## Architectural Principles

### 1. Single Responsibility Principle

**Entity Layer Responsibility:**
- Define domain data structure
- Serialize domain fields to dict
- Handle enum/datetime serialization

**Client Layer Responsibility:**
- Generate metadata (source, version, timestamps, entity_id)
- Inject metadata into episode content
- Serialize to JSON for storage

### 2. Separation of Concerns

```
┌─────────────────────┐
│   DOMAIN LAYER      │
│ Entity.to_episode.. │ ← Only domain fields
│     body()          │
└──────────┬──────────┘
           │
           │ Returns clean dict
           ▼
┌─────────────────────────────────┐
│  INFRASTRUCTURE LAYER           │
│ GraphitiClient.add_episode()    │ ← Adds metadata
│ GraphitiClient._inject_metadata │
└──────────────────────────────────┘
           │
           │ Returns: body + metadata
           ▼
┌─────────────────────┐
│  STORAGE LAYER      │
│   Graphiti Graph    │
│  (persistent)       │
└─────────────────────┘
```

### 3. Consistency Pattern

All episodes stored in Graphiti have this structure:

```json
{
  "domain_field_1": "value",
  "domain_field_2": 42,
  // ... all domain fields

  "_metadata": {
    "entity_id": "unique-id",
    "entity_type": "turn_state",
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2025-02-07T12:00:00Z",
    "updated_at": "2025-02-07T12:00:00Z",
    "source_hash": null
  }
}
```

**Key Properties:**
1. All episodes have `_metadata` section
2. All episodes have same metadata fields
3. No metadata fields scattered in body
4. Metadata injected consistently via client

---

## Type System Changes

### Entity `to_episode_body()` Method

**Current Signatures:**
```python
# Inconsistent return types
class TaskOutcome:
    def to_episode_body(self) -> str:        # ← Returns string!
        ...

class TurnStateEntity:
    def to_episode_body(self) -> dict:       # ← Returns dict

class FailedApproachEpisode:
    def to_episode_body(self) -> Dict[str, Any]:  # ← Returns dict
```

**New Signature (All Entities):**
```python
# Consistent return type across all entities
class Entity:
    def to_episode_body(self) -> dict:
        """Return clean domain data as dictionary.

        The returned dict should contain ONLY domain fields.
        Metadata (entity_type, source, created_at, etc.) is injected by
        GraphitiClient.add_episode() - NOT included here.

        Returns:
            Dictionary with domain fields serialized for JSON storage.
        """
```

### Client Method Signature

**Proposed Enhancement:**
```python
class GraphitiClient:
    async def add_episode(
        self,
        name: str,
        episode_body: str,  # JSON string of dict (clean body)
        group_id: str,
        source: str = "direct",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> Episode:
        """Add episode with automatic metadata injection.

        Args:
            name: Episode name
            episode_body: JSON string of clean body dict (no metadata)
            group_id: Episode group identifier
            source: Source identifier (guardkit_seeding, direct, etc)
            entity_type: Type of entity (turn_state, failed_approach, etc)
            entity_id: Unique identifier for this entity

        Returns:
            Created Episode object
        """
```

---

## Data Flow Examples

### Example 1: Seeding Failed Approaches

**New Flow:**

```python
# 1. Create entity with domain data only
failure = FailedApproachEpisode(
    id="FAIL-SUBPROCESS",
    approach="Using subprocess.run() for task-work",
    symptom="Command not found error",
    root_cause="CLI command doesn't exist",
    fix_applied="Use SDK query() method",
    prevention="Check ADR-FB-001",
    context="feature-build"
)

# 2. Entity produces clean dict (no metadata)
body_dict = failure.to_episode_body()
# Result: {
#   "id": "FAIL-SUBPROCESS",
#   "approach": "...",
#   "symptom": "...",
#   "root_cause": "...",
#   "fix_applied": "...",
#   "prevention": "...",
#   "context": "feature-build"
# }

# 3. Client injects metadata
await client.add_episode(
    name=failure.id,
    episode_body=json.dumps(body_dict),
    group_id="failed_approaches",
    source="guardkit_seeding",
    entity_type="failed_approach",
    entity_id=failure.id
)

# 4. Graphiti stores:
# {
#   "id": "FAIL-SUBPROCESS",
#   "approach": "...",
#   "symptom": "...",
#   "root_cause": "...",
#   "fix_applied": "...",
#   "prevention": "...",
#   "context": "feature-build",
#   "_metadata": {
#     "entity_id": "FAIL-SUBPROCESS",
#     "entity_type": "failed_approach",
#     "source": "guardkit_seeding",
#     "version": "1.0.0",
#     "created_at": "2025-02-07T12:00:00Z",
#     "updated_at": "2025-02-07T12:00:00Z",
#     "source_hash": null
#   }
# }
```

### Example 2: Turn State from Manager

```python
# 1. Manager creates entity
turn_state = TurnStateEntity(
    id="TURN-FEAT-GBF-1",
    feature_id="FEAT-GBF",
    task_id="TASK-GBF-001",
    turn_number=1,
    player_summary="Implemented entity cleanup",
    player_decision="implemented",
    coach_decision="approved",
    coach_feedback=None,
    mode=TurnMode.FRESH_START,
    tests_passed=15,
    coverage=85.5,
    started_at=datetime.now(),
    completed_at=datetime.now()
)

# 2. Entity produces clean dict
body = turn_state.to_episode_body()
# {
#   "id": "TURN-FEAT-GBF-1",
#   "feature_id": "FEAT-GBF",
#   "task_id": "TASK-GBF-001",
#   "turn_number": 1,
#   "player_summary": "...",
#   "player_decision": "implemented",
#   "coach_decision": "approved",
#   "coach_feedback": null,
#   "mode": "fresh_start",
#   "tests_passed": 15,
#   "coverage": 85.5,
#   "started_at": "2025-02-07T12:30:00Z",
#   "completed_at": "2025-02-07T12:35:00Z"
# }

# 3. Manager calls client with metadata parameters
await client.add_episode(
    name=turn_state.id,
    episode_body=json.dumps(body),
    group_id="turn_states",
    source="feature_build_orchestrator",
    entity_type="turn_state",
    entity_id=turn_state.id
)
```

---

## Testing Strategy

### Test Category 1: Entity Consistency

**Test:** All entities return `dict` from `to_episode_body()`
```python
def test_all_entities_return_dict():
    # Create instance of each entity type
    # Call to_episode_body()
    # Assert isinstance(result, dict)
```

**Test:** Entity bodies contain no metadata fields
```python
def test_no_metadata_in_entity_bodies():
    METADATA_FIELDS = {"entity_type", "_metadata", "source", "version", ...}
    # For each entity:
    #   body = entity.to_episode_body()
    #   assert not (set(body.keys()) & METADATA_FIELDS)
```

**Test:** Entity serialization of special types
```python
def test_enum_serialization():
    # Enums should be converted to strings

def test_datetime_serialization():
    # Datetimes should be ISO 8601 strings

def test_optional_fields():
    # Optional fields should be excluded if None
```

### Test Category 2: Client Integration

**Test:** Client injects metadata correctly
```python
def test_client_injects_metadata():
    # Create clean body dict
    # Call client.add_episode()
    # Verify metadata injected with correct fields
```

**Test:** Seeding integration
```python
def test_seed_helpers_add_episodes():
    # Create episodes with 4-tuple format
    # Call _add_episodes()
    # Verify client.add_episode() called with correct parameters
```

### Test Category 3: Regression

**Test:** Existing episode-related tests still pass
```python
# Run full test suite
# Verify no test failures introduced
```

---

## Implementation Checklist

### Phase 1: Entity Cleanup
- [ ] `outcome.py` - Convert str → dict, remove metadata fields
- [ ] `turn_state.py` - Remove `entity_type` from body
- [ ] `failed_approach.py` - Remove `entity_type` from body
- [ ] `feature_overview.py` - Remove `entity_type`, `created_at`, `updated_at`
- [ ] `quality_gate_config.py` - Remove `entity_type` from body
- [ ] `role_constraint.py` - Remove `entity_type`, `created_at` from body

### Phase 2: Seeding Helper
- [ ] `seed_helpers.py` - Remove manual metadata injection

### Phase 3: Call Sites (Seeding)
- [ ] `seed_failed_approaches.py`
- [ ] `seed_feature_overviews.py`
- [ ] Other seed_*.py files

### Phase 4: Call Sites (Managers)
- [ ] `failed_approach_manager.py`
- [ ] `outcome_manager.py`

### Phase 5: Testing
- [ ] Create `test_episode_serialization.py`
- [ ] Add consistency tests
- [ ] Run full test suite

### Phase 6: Documentation
- [ ] Update docstrings
- [ ] Update type hints
- [ ] Update comments

---

## Risk Assessment

### Risk Level: **LOW**

**Why:**
- Internal refactoring only (no API changes)
- Client-side metadata injection already exists
- Clear, isolated scope
- Comprehensive test coverage planned

### Mitigation Strategies
1. **Test-First Approach** - Write tests before modifying entities
2. **Incremental Changes** - Phase approach allows verification at each step
3. **Regression Testing** - Full test suite run before completion
4. **Code Review** - Architect review of design before implementation

### Rollback Plan
If issues discovered:
1. Revert changes to entity `to_episode_body()` methods
2. Revert seeding helper changes
3. Restore manual metadata injection
4. Post-mortem on what went wrong

---

## Success Criteria

1. **Consistency**
   - ✓ All entities return `dict` from `to_episode_body()`
   - ✓ No metadata fields in entity bodies
   - ✓ All metadata injected by client

2. **Functionality**
   - ✓ All episodes stored in Graphiti have `_metadata` section
   - ✓ Metadata fields consistent across all episodes
   - ✓ No double metadata injection

3. **Testing**
   - ✓ New consistency tests added and passing
   - ✓ All existing tests pass (no regressions)
   - ✓ Test coverage maintained or improved

4. **Code Quality**
   - ✓ Type hints correct and consistent
   - ✓ Docstrings updated
   - ✓ No technical debt introduced

---

## Related Documentation

- **Architecture Decision:** `docs/architecture/ADR-GBF-001-unified-episode-serialization.md`
- **Implementation Plan:** `tasks/in_progress/TASK-GBF-001-IMPLEMENTATION-PLAN.md`
- **Review Finding:** `tasks/backlog/TASK-REV-C632-graphiti-usage-baseline-analysis.md` (Finding 6)
- **Graphiti Client:** `guardkit/knowledge/graphiti_client.py`

---

## Open Questions for Implementation Team

1. **Client API Enhancement Needed?**
   - Does `GraphitiClient.add_episode()` currently accept `source`, `entity_type`, `entity_id` parameters?
   - If not, should this be added first (separate task) or part of this task?

2. **Backward Compatibility**
   - Are there external callers of `_add_episodes()` we need to support?
   - Should we provide a migration period for old-style calls?

3. **TaskOutcome String Content**
   - The current human-readable text output - should this be preserved in the dict?
   - Should we add a `formatted_text` field with the original output?

4. **Testing Environment**
   - Is Graphiti integration available for testing?
   - Should we mock GraphitiClient for unit tests?

---

**Design prepared by:** Architecture Team
**Ready for:** Implementation Phase (Phase 3)
**Next Step:** Execute TASK-GBF-001 implementation plan
