# Implementation Plan: TASK-GBF-001 - Unify Episode Serialization

## Overview

Unify the dual episode serialization paths (entity-level and client-level) to use a single canonical pattern: **client-level metadata injection**. This refactoring is low-complexity, high-impact work with clear acceptance criteria.

**Complexity Score:** 4/10
**Estimated Duration:** 2-3 hours
**Risk Level:** Low (internal refactoring, no API changes)
**Testing Burden:** Medium (new consistency tests required)

## Architecture Decision

See `/docs/architecture/ADR-GBF-001-unified-episode-serialization.md` for full decision rationale.

**Decision:** Use `GraphitiClient.add_episode()` as the single point for metadata injection.

**Consequence:**
- All entity `to_episode_body()` methods return clean domain data (dict only)
- No metadata fields embedded in entity bodies
- All metadata (source, version, timestamps, entity_id) injected by client

## Scope & Deliverables

### Deliverable 1: Entity Serialization Cleanup
Standardize all entity `to_episode_body()` implementations to return clean dicts (no metadata fields).

**Files to modify (8 files):**

1. ✓ `guardkit/knowledge/entities/outcome.py`
   - Change return type from `str` to `dict`
   - Convert human-readable text to structured dict

2. ✓ `guardkit/knowledge/entities/turn_state.py`
   - Remove `entity_type` from body dict
   - Keep domain fields: `id`, `feature_id`, `task_id`, `turn_number`, `player_summary`, etc.

3. ✓ `guardkit/knowledge/entities/failed_approach.py`
   - Remove `entity_type` from body dict
   - Keep: `id`, `approach`, `symptom`, `root_cause`, `fix_applied`, etc.

4. ✓ `guardkit/knowledge/entities/feature_overview.py`
   - Remove: `entity_type`, `created_at`, `updated_at` from body dict
   - Keep: `id`, `name`, `tagline`, `purpose`, `what_it_is`, `what_it_is_not`, etc.

5. ✓ `guardkit/knowledge/facts/quality_gate_config.py`
   - Remove `entity_type` from body dict
   - Keep: `id`, `name`, `task_type`, `complexity_range`, `arch_review_required`, etc.

6. ✓ `guardkit/knowledge/facts/role_constraint.py`
   - Remove: `entity_type`, `created_at` from body dict
   - Keep: `role`, `context`, `primary_responsibility`, `must_do`, `must_not_do`, etc.

7. ✓ `guardkit/knowledge/entities/` (other entities if they exist)
   - Audit any other entities for metadata fields

**Refactoring Pattern (all entities):**

```python
# BEFORE
def to_episode_body(self) -> dict:
    return {
        "entity_type": "turn_state",    # ← REMOVE
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

**Special Case: TaskOutcome**

Currently returns `str` from `to_episode_body()`. Must change to return `dict`:

```python
# BEFORE
def to_episode_body(self) -> str:
    lines = []
    lines.append(f"Outcome ID: {self.id}")
    lines.append(f"Outcome Type: {self.outcome_type.value}")
    # ... 20+ more lines
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
        "problems_encountered": self.problems_encountered,
        "lessons_learned": self.lessons_learned,
        "tests_written": self.tests_written,
        "test_coverage": self.test_coverage,
        "review_cycles": self.review_cycles,
        "started_at": self.started_at.isoformat() if self.started_at else None,
        "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        "duration_minutes": self.duration_minutes,
        "feature_id": self.feature_id,
        "related_adr_ids": self.related_adr_ids,
    }
```

### Deliverable 2: Seeding Helper Cleanup
Remove manual metadata injection from `seed_helpers._add_episodes()`.

**File to modify (1 file):**

8. ✓ `guardkit/knowledge/seed_helpers.py`

**Changes:**

```python
# BEFORE
async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    if not client.enabled:
        logger.debug(f"Skipping {category_name} seeding - client disabled")
        return

    for name, body in episodes:
        try:
            # Inject metadata block into body (TASK-GR-PRE-000-A)
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
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")

# AFTER
async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    """Add multiple episodes to Graphiti with error handling.

    Episodes are passed as (name, body_dict, entity_type, entity_id) tuples.
    The client automatically injects metadata (source, version, timestamps, etc).

    Args:
        client: GraphitiClient instance
        episodes: List of (name, body_dict, entity_type, entity_id) tuples
        group_id: Group ID for all episodes
        category_name: Human-readable category name for logging
    """
    if not client.enabled:
        logger.debug(f"Skipping {category_name} seeding - client disabled")
        return

    for name, body_dict, entity_type, entity_id in episodes:
        try:
            # Client.add_episode() automatically injects metadata
            await client.add_episode(
                name=name,
                episode_body=json.dumps(body_dict),
                group_id=group_id,
                source="guardkit_seeding",
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")
```

### Deliverable 3: Update Seeding Call Sites
Pass tuples with (name, body_dict, entity_type, entity_id) to `_add_episodes()`.

**Files to modify (6 files):**

9. ✓ `guardkit/knowledge/seed_failed_approaches.py`
   - Update episode construction to 4-tuple with entity_type

10. ✓ `guardkit/knowledge/seed_feature_overviews.py`
    - Update episode construction to 4-tuple with entity_type

11. ✓ Other seed_*.py files (if they exist)
    - Audit and update any others using `_add_episodes()`

### Deliverable 4: Update Manager Call Sites
Ensure managers calling `add_episode()` directly pass entity_type.

**Files to modify (2 files):**

12. ✓ `guardkit/knowledge/failed_approach_manager.py`
    - Pass `entity_type="failed_approach"` to `add_episode()` calls

13. ✓ `guardkit/knowledge/outcome_manager.py`
    - Pass `entity_type="task_outcome"` to `add_episode()` calls
    - Update to handle TaskOutcome's new dict return type

### Deliverable 5: Add Consistency Tests
Create new test file verifying metadata consistency.

**File to create (1 file):**

14. ✓ `tests/unit/test_episode_serialization.py` (NEW)

**Test cases:**

```python
import pytest
from guardkit.knowledge.entities.outcome import TaskOutcome, OutcomeType
from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
from guardkit.knowledge.entities.failed_approach import FailedApproachEpisode, Severity
from guardkit.knowledge.entities.feature_overview import FeatureOverviewEntity
from guardkit.knowledge.facts.quality_gate_config import QualityGateConfigFact
from guardkit.knowledge.facts.role_constraint import RoleConstraintFact
from datetime import datetime

# Test 1: All entities return dict type
def test_all_entities_return_dict():
    """All to_episode_body() implementations must return dict, not str."""

    # Create minimal instances of each entity
    entities = [
        TaskOutcome(
            id="OUT-001",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-001",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Done"
        ),
        TurnStateEntity(
            id="TURN-001",
            feature_id="FEAT-001",
            task_id="TASK-001",
            turn_number=1,
            player_summary="Worked",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=datetime.now(),
            completed_at=datetime.now()
        ),
        FailedApproachEpisode(
            id="FAIL-001",
            approach="Test approach",
            symptom="Test symptom",
            root_cause="Test cause",
            fix_applied="Test fix",
            prevention="Test prevention",
            context="test"
        ),
        FeatureOverviewEntity(
            id="FEAT-001",
            name="Test Feature",
            tagline="Test tagline",
            purpose="Test purpose",
            what_it_is=["Is feature"],
            what_it_is_not=["Is not assistant"],
            invariants=["Rule 1"],
            architecture_summary="Test",
            key_components=["Comp1"],
            key_decisions=["ADR-001"]
        ),
        QualityGateConfigFact(
            id="QG-001",
            name="Test Config",
            task_type="feature",
            complexity_range=(1, 3),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=60.0,
            lint_required=True,
            rationale="Test rationale"
        ),
        RoleConstraintFact(
            role="player",
            context="test",
            primary_responsibility="Do work",
            must_do=["Work"],
            must_not_do=["Cheat"],
            ask_before=["Major change"]
        )
    ]

    for entity in entities:
        body = entity.to_episode_body()
        assert isinstance(body, dict), \
            f"{entity.__class__.__name__}.to_episode_body() must return dict, got {type(body).__name__}"
        assert len(body) > 0, \
            f"{entity.__class__.__name__}.to_episode_body() returns empty dict"


# Test 2: Entity bodies contain no metadata fields
def test_entity_bodies_no_metadata_fields():
    """Entity bodies should NOT contain metadata fields (injected by client)."""

    METADATA_FIELDS = {
        "entity_type",
        "_metadata",
        "source",
        "version",
        "source_hash",
    }

    # Create minimal instances
    entities = [
        TaskOutcome(
            id="OUT-001",
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-001",
            task_title="Test",
            task_requirements="Test",
            success=True,
            summary="Done"
        ),
        TurnStateEntity(
            id="TURN-001",
            feature_id="FEAT-001",
            task_id="TASK-001",
            turn_number=1,
            player_summary="Worked",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=datetime.now(),
            completed_at=datetime.now()
        ),
        FailedApproachEpisode(
            id="FAIL-001",
            approach="Test",
            symptom="Test",
            root_cause="Test",
            fix_applied="Test",
            prevention="Test",
            context="test"
        ),
        FeatureOverviewEntity(
            id="FEAT-001",
            name="Test",
            tagline="Test",
            purpose="Test",
            what_it_is=["Yes"],
            what_it_is_not=["No"],
            invariants=["Rule"],
            architecture_summary="Test",
            key_components=["C"],
            key_decisions=["A"]
        ),
        QualityGateConfigFact(
            id="QG-001",
            name="Test",
            task_type="feature",
            complexity_range=(1, 3),
            arch_review_required=False,
            arch_review_threshold=None,
            test_pass_required=True,
            coverage_required=True,
            coverage_threshold=60.0,
            lint_required=True,
            rationale="Test"
        ),
        RoleConstraintFact(
            role="player",
            context="test",
            primary_responsibility="Do",
            must_do=["Do"],
            must_not_do=["Don't"],
            ask_before=[]
        )
    ]

    for entity in entities:
        body = entity.to_episode_body()
        assert isinstance(body, dict)

        body_keys = set(body.keys())
        metadata_present = body_keys & METADATA_FIELDS

        assert not metadata_present, \
            f"{entity.__class__.__name__} body contains metadata fields: {metadata_present}. " \
            f"Metadata should be injected by GraphitiClient, not embedded in entity body."


# Test 3: Entity timestamps serialized correctly
def test_entity_timestamps_serialized():
    """Datetime fields should be serialized to ISO 8601 strings."""

    outcome = TaskOutcome(
        id="OUT-001",
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-001",
        task_title="Test",
        task_requirements="Test",
        success=True,
        summary="Done",
        started_at=datetime(2025, 2, 1, 10, 30, 0),
        completed_at=datetime(2025, 2, 1, 11, 30, 0)
    )

    body = outcome.to_episode_body()

    # Check ISO 8601 format
    assert isinstance(body["started_at"], str)
    assert isinstance(body["completed_at"], str)
    assert "T" in body["started_at"]  # ISO 8601 format marker
    assert "2025-02-01T10:30:00" == body["started_at"]
    assert "2025-02-01T11:30:00" == body["completed_at"]


# Test 4: Entity enums serialized to strings
def test_entity_enums_serialized():
    """Enum fields should be serialized to their string values."""

    outcome = TaskOutcome(
        id="OUT-001",
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-001",
        task_title="Test",
        task_requirements="Test",
        success=True,
        summary="Done"
    )

    body = outcome.to_episode_body()

    # Check enum is serialized to string
    assert body["outcome_type"] == "TASK_COMPLETED"
    assert isinstance(body["outcome_type"], str)

    # Also test TurnStateEntity
    turn = TurnStateEntity(
        id="TURN-001",
        feature_id="FEAT-001",
        task_id="TASK-001",
        turn_number=1,
        player_summary="Worked",
        player_decision="implemented",
        coach_decision="approved",
        coach_feedback=None,
        mode=TurnMode.FRESH_START,
        started_at=datetime.now(),
        completed_at=datetime.now()
    )

    body = turn.to_episode_body()
    assert body["mode"] == "fresh_start"
    assert isinstance(body["mode"], str)
```

### Deliverable 6: Update Type Hints (if applicable)
Ensure all type hints reflect dict return type from `to_episode_body()`.

**Files to audit (all entity files):**
- Verify type hints match implementation (all return `dict`)
- Update docstrings

## Implementation Order

**Recommended execution order (dependency order):**

1. **Phase 1 (~40 min):** Entity serialization cleanup
   - Modify 6 entity/fact files to remove metadata from bodies
   - Handle TaskOutcome special case (str → dict conversion)
   - Type hint verification

2. **Phase 2 (~20 min):** Seeding helper cleanup
   - Modify `seed_helpers._add_episodes()` to accept 4-tuples
   - Update docstring with new signature

3. **Phase 3 (~30 min):** Update seeding call sites
   - Modify 6 seed_*.py files to pass 4-tuples
   - Update episode construction logic

4. **Phase 4 (~20 min):** Update manager call sites
   - Modify 2 manager files to pass entity_type
   - Handle TaskOutcome dict return

5. **Phase 5 (~30 min):** Add tests
   - Create `test_episode_serialization.py`
   - Run test suite, verify all tests pass
   - Check test coverage for new tests

**Total: ~2-2.5 hours**

## Acceptance Criteria Mapping

| Acceptance Criteria | Deliverable | Status |
|---|---|---|
| All episodes use single serialization pattern | ADR + Phase 2 | ✓ |
| No episode missing standard metadata fields | Phase 4 + Tests | ✓ |
| Existing tests continue to pass | Phase 5 | ✓ |
| New test verifying metadata consistency | Deliverable 5 | ✓ |

## Testing Strategy

### Unit Tests
- Test each entity's `to_episode_body()` independently
- Verify no metadata fields in bodies
- Verify proper serialization of timestamps, enums

### Integration Tests
- Test `_add_episodes()` with mock client
- Test manager `add_episode()` calls with entity_type
- Verify metadata properly injected by client

### Regression Tests
- Run full test suite to ensure no breaking changes
- Check existing episode-related tests still pass

## Risk Analysis

### Risk: Low

**Why?**
- Internal refactoring only, no API changes
- All changes are isolated to entity layer and seeding layer
- Metadata injection logic already exists in client
- Clear, well-defined scope

**Mitigation Strategies:**
1. Comprehensive tests for metadata consistency
2. Run full test suite before marking complete
3. Keep changes focused (no scope creep)

## Success Metrics

1. ✓ All entity `to_episode_body()` methods return `dict` (no `str`)
2. ✓ No entity bodies contain metadata fields
3. ✓ `_add_episodes()` accepts 4-tuples (name, body, entity_type, entity_id)
4. ✓ All call sites updated to pass entity_type
5. ✓ New consistency tests added and passing
6. ✓ Full test suite passes
7. ✓ Code review approval from team

## Notes

- **BREAKING INTERNAL CHANGE:** The signature of `_add_episodes()` changes from 2-tuple to 4-tuple. Must update all call sites.
- **New Assumption:** `GraphitiClient.add_episode()` accepts `source`, `entity_type`, `entity_id` parameters. If not currently implemented, this must be added first (minor client enhancement).
- **TaskOutcome Special Case:** Converting from human-readable string to structured dict is the main complexity in this task. Ensure the dict representation captures all the information from the original string.

## Related Files

- Architecture Decision: `/docs/architecture/ADR-GBF-001-unified-episode-serialization.md`
- Original Review Finding: `tasks/backlog/TASK-REV-C632-graphiti-usage-baseline-analysis.md` (Finding 6)
- Graphiti Client: `guardkit/graphiti_client.py`
- Entities: `guardkit/knowledge/entities/`
- Facts: `guardkit/knowledge/facts/`
