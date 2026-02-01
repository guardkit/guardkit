---
complexity: 3
conductor_workspace: gr-mvp-wave6-schemas
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-003-D
feature_id: FEAT-GR-MVP
id: TASK-GR-001-D
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-seeding
- autobuild
- role-constraints
- mvp-phase-2
task_type: feature
title: Create RoleConstraintsEpisode and seed defaults
updated: 2026-02-01 00:00:00+00:00
wave: 6
---

# Task: Create RoleConstraintsEpisode and seed defaults

## Description

Create the RoleConstraintsEpisode dataclass and seed default Player/Coach constraints. This directly addresses the "Player-Coach role reversal" problem identified in TASK-REV-7549 as a top-5 AutoBuild issue.

## Acceptance Criteria

- [x] RoleConstraintsEpisode dataclass implemented (as RoleConstraintFact in guardkit/knowledge/facts/role_constraint.py)
- [x] Default Player constraints seeded during init (PLAYER_CONSTRAINTS defined)
- [x] Default Coach constraints seeded during init (COACH_CONSTRAINTS defined)
- [x] Constraints accessible during feature-build (via load_role_context())
- [x] Entity ID for upsert (stable episode names: role_constraint_{role}_{context})

## Implementation Summary

The implementation differs slightly from the task spec but achieves the same goals:

### Schema Implementation

- **File**: `guardkit/knowledge/facts/role_constraint.py`
- **Class**: `RoleConstraintFact` (equivalent to `RoleConstraintsEpisode`)
- **Method**: `to_episode_body()` converts to Graphiti-compatible format
- **Entity ID**: Episode names follow pattern `role_constraint_{role}_{context}` for stable upsert

### Features Implemented

1. **RoleConstraintFact Dataclass**:
   - role: str (player | coach)
   - context: str (feature-build | autobuild | task-work)
   - primary_responsibility: str
   - must_do: List[str]
   - must_not_do: List[str]
   - ask_before: List[str]
   - good_examples: List[str]
   - bad_examples: List[str]
   - created_at: datetime

2. **Default Constraints**:
   - `PLAYER_CONSTRAINTS` - 5 must_do, 5 must_not_do, 3 ask_before, 3 good_examples, 3 bad_examples
   - `COACH_CONSTRAINTS` - 5 must_do, 5 must_not_do, 3 ask_before, 3 good_examples, 3 bad_examples

3. **Seeding Function**:
   - `seed_role_constraints(graphiti)` in `guardkit/knowledge/seed_role_constraints.py`
   - Creates episodes with stable names for upsert capability
   - Graceful degradation when Graphiti unavailable

4. **Context Loading**:
   - `load_role_context(role, context)` in `guardkit/knowledge/context_loader.py`
   - Returns formatted markdown for injection into Player/Coach prompts
   - Used during feature-build command execution

## Test Results

- **45/45 tests passing** in `tests/knowledge/test_role_constraints.py`
- Tests cover: dataclass creation, serialization, default constraints, seeding, context loading, edge cases

## Files Modified/Created

1. `guardkit/knowledge/facts/role_constraint.py` - RoleConstraintFact dataclass
2. `guardkit/knowledge/seed_role_constraints.py` - Seeding function
3. `guardkit/knowledge/context_loader.py` - load_role_context() function
4. `tests/knowledge/test_role_constraints.py` - Comprehensive test suite

## Implementation Notes

### Schema Definition

```python
@dataclass
class RoleConstraintFact:
    """Hard constraints for Player/Coach roles."""

    role: str  # "player" | "coach"
    context: str  # "feature-build" | "autobuild" | "task-work"
    primary_responsibility: str
    must_do: List[str]
    must_not_do: List[str]
    ask_before: List[str]
    good_examples: List[str] = field(default_factory=list)
    bad_examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "role_constraint",
            "role": self.role,
            "context": self.context,
            ...
        }
```

## Notes

This directly addresses AutoBuild lesson learned - role reversal was top-5 problem.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [TASK-REV-7549 AutoBuild Lessons](../../../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md)
