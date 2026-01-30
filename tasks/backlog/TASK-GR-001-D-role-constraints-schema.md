---
id: TASK-GR-001-D
title: Create RoleConstraintsEpisode and seed defaults
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, project-seeding, autobuild, role-constraints, mvp-phase-2]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 6
conductor_workspace: gr-mvp-wave6-schemas
complexity: 3
depends_on:
  - TASK-GR-PRE-003-D
---

# Task: Create RoleConstraintsEpisode and seed defaults

## Description

Create the RoleConstraintsEpisode dataclass and seed default Player/Coach constraints. This directly addresses the "Player-Coach role reversal" problem identified in TASK-REV-7549 as a top-5 AutoBuild issue.

## Acceptance Criteria

- [ ] RoleConstraintsEpisode dataclass implemented
- [ ] Default Player constraints seeded during init
- [ ] Default Coach constraints seeded during init
- [ ] Constraints accessible during feature-build
- [ ] Entity ID for upsert (allows customization)

## Implementation Notes

### Schema Definition

```python
@dataclass
class RoleConstraintsEpisode:
    """Role-specific constraints for Player/Coach."""

    entity_type: str = "role_constraints"

    role: str = ""  # "player" | "coach"

    must_do: List[str] = field(default_factory=list)
    must_not_do: List[str] = field(default_factory=list)
    ask_before: List[str] = field(default_factory=list)
    escalate_when: List[str] = field(default_factory=list)

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Role: {self.role.upper()}

        MUST DO:
        {chr(10).join(f'- {m}' for m in self.must_do)}

        MUST NOT DO:
        {chr(10).join(f'- {m}' for m in self.must_not_do)}

        ASK BEFORE:
        {chr(10).join(f'- {a}' for a in self.ask_before)}

        ESCALATE WHEN:
        {chr(10).join(f'- {e}' for e in self.escalate_when)}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return f"role_constraints_{self.role}"
```

### Default Constraints

```python
PLAYER_CONSTRAINTS = RoleConstraintsEpisode(
    role="player",
    must_do=[
        "Implement code according to implementation plan",
        "Read and follow task requirements",
        "Write tests for implemented code",
        "Fix issues identified by Coach",
    ],
    must_not_do=[
        "Validate quality gates",
        "Make architectural decisions",
        "Approve your own work",
        "Change acceptance criteria",
    ],
    ask_before=[
        "Changing architecture from plan",
        "Adding dependencies not in plan",
        "Modifying quality gate profiles",
    ],
    escalate_when=[
        "Requirements are ambiguous",
        "Implementation plan has gaps",
        "Cannot proceed without decision",
    ],
)

COACH_CONSTRAINTS = RoleConstraintsEpisode(
    role="coach",
    must_do=[
        "Validate against acceptance criteria",
        "Run quality gates (tests, coverage, architecture)",
        "Provide specific, actionable feedback",
        "Verify implementation matches plan",
    ],
    must_not_do=[
        "Write implementation code",
        "Modify implementation directly",
        "Skip quality gate checks",
        "Approve without verification",
    ],
    ask_before=[
        "Changing quality gate thresholds",
        "Skipping mandatory checks",
    ],
    escalate_when=[
        "Test failures persist after 3 attempts",
        "Architecture violations detected",
        "Security issues found",
    ],
)
```

### Files to Create

- `src/guardkit/integrations/graphiti/episodes/role_constraints.py`

## Test Requirements

- [ ] Unit tests for schema
- [ ] Unit tests for default constraints
- [ ] Integration test for seeding

## Notes

This directly addresses AutoBuild lesson learned - role reversal was top-5 problem.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
- [TASK-REV-7549 AutoBuild Lessons](../../../../tasks/backlog/TASK-REV-7549-autobuild-lessons-learned-graphiti.md)
