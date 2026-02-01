---
complexity: 4
dependencies: []
estimate_hours: 1
feature_id: FEAT-0F4A
id: TASK-GR5-006
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-005
task_type: feature
title: Create TurnStateEpisode schema
wave: 2
---

# Create TurnStateEpisode schema

## Description

Create the `TurnStateEpisode` dataclass schema for capturing turn states in feature-build workflows. This addresses TASK-REV-7549 finding on cross-turn learning failure.

## Acceptance Criteria

- [x] Dataclass with all fields from specification
- [x] `to_dict()` method for JSON serialization (implemented as `to_episode_body()`)
- [x] Fields: feature_id, task_id, turn_number, player_decision, coach_decision
- [x] Progress fields: blockers_found, progress_summary, files_modified
- [x] Acceptance criteria status tracking

## Technical Details

**Location**: `guardkit/knowledge/entities/turn_state.py`

**Actual Implementation**:
```python
@dataclass
class TurnStateEntity:
    # Identity
    id: str  # TURN-{feature_id}-{turn_number}
    feature_id: str
    task_id: str
    turn_number: int

    # What happened
    player_summary: str  # What Player implemented/attempted
    player_decision: str  # "implemented" | "failed" | "blocked"
    coach_decision: str  # "approved" | "feedback" | "rejected"
    coach_feedback: Optional[str]

    # Mode and state
    mode: TurnMode  # TurnMode.FRESH_START | RECOVERING_STATE | CONTINUING_WORK

    # Timing (required)
    started_at: datetime
    completed_at: datetime

    # Progress tracking
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""

    # Acceptance criteria tracking
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)

    # Files modified during this turn
    files_modified: List[str] = field(default_factory=list)

    # Quality metrics (optional)
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    coverage: Optional[float] = None
    arch_score: Optional[int] = None
    duration_seconds: Optional[int] = None

    # Learning
    lessons_from_turn: List[str] = field(default_factory=list)
    what_to_try_next: Optional[str] = None

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body (JSON serializable)."""
        ...
```

**Reference**: See FEAT-GR-005 Turn State Episode section.

## Implementation Notes

### Files Created/Modified
- `guardkit/knowledge/entities/turn_state.py` - TurnStateEntity dataclass and TurnMode enum
- `guardkit/knowledge/turn_state_operations.py` - capture/load operations and factory function
- `tests/knowledge/test_turn_state.py` - Comprehensive test suite (54 tests)

### Key Decisions
1. Named `TurnStateEntity` (not `TurnStateEpisode`) for consistency with other entities
2. Method named `to_episode_body()` (not `to_dict()`) to match Graphiti convention
3. Added additional fields beyond spec: `player_summary`, `lessons_from_turn`, `what_to_try_next`, quality metrics
4. TurnMode as enum (not string) for type safety

### Test Coverage
- 54 tests passing
- Covers dataclass creation, serialization, capture/load operations, factory function
- Integration tests for round-trip capture and load
