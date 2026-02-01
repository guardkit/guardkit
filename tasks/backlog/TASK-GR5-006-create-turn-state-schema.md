---
id: TASK-GR5-006
title: Create TurnStateEpisode schema
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: task-work
complexity: 4
estimate_hours: 1
dependencies: []
---

# Create TurnStateEpisode schema

## Description

Create the `TurnStateEpisode` dataclass schema for capturing turn states in feature-build workflows. This addresses TASK-REV-7549 finding on cross-turn learning failure.

## Acceptance Criteria

- [ ] Dataclass with all fields from specification
- [ ] `to_dict()` method for JSON serialization
- [ ] Fields: feature_id, task_id, turn_number, player_decision, coach_decision
- [ ] Progress fields: blockers_found, progress_summary, files_modified
- [ ] Acceptance criteria status tracking

## Technical Details

**Location**: `guardkit/knowledge/turn_state.py`

**Schema**:
```python
@dataclass
class TurnStateEpisode:
    entity_type: str = "turn_state"
    feature_id: str = ""
    task_id: str = ""
    turn_number: int = 0
    player_decision: str = ""
    coach_decision: str = ""  # "APPROVED" | "REJECTED" | "FEEDBACK"
    feedback_summary: str = ""
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""
    files_modified: List[str] = field(default_factory=list)
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)
    mode: str = "FRESH_START"
```

**Reference**: See FEAT-GR-005 Turn State Episode section.
