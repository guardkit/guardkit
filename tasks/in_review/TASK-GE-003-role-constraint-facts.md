---
complexity: 4
conductor_workspace: graphiti-enhancements-wave1-2
created_at: 2026-01-29 00:00:00+00:00
dependencies: []
estimated_minutes: 90
feature_id: FEAT-GE
id: TASK-GE-003
implementation_mode: task-work
parent_review: TASK-REV-7549
priority: 2
status: in_review
tags:
- graphiti
- facts
- player-coach
- enforcement
task_type: feature
title: Role Constraint Facts for Player-Coach Enforcement
wave: 1
---

# TASK-GE-003: Role Constraint Facts for Player-Coach Enforcement

## Overview

**Priority**: High (Prevents role reversal)
**Dependencies**: None (uses existing Graphiti infrastructure)

## Problem Statement

From TASK-REV-7549 analysis: "Player-Coach Role Reversal" was a recurring problem:
- During long sessions, Player started validating (Coach's job)
- Coach started implementing features (Player's job)
- Led to circular logic and MAX_TURNS_EXCEEDED with no progress

There are no explicit, queryable constraints defining what each role can and cannot do.

## Goals

1. Create RoleConstraintFact dataclass for Player/Coach boundaries
2. Seed role constraints into Graphiti
3. Integrate with session context loading to inject role reminders
4. Provide clear "MUST DO" and "MUST NOT DO" for each role

## Technical Approach

### Fact Definition

```python
# guardkit/knowledge/facts/role_constraint.py

from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class RoleConstraintFact:
    """Hard constraints for Player/Coach roles."""

    # Identity
    role: str  # "player" | "coach"
    context: str  # "feature-build" | "autobuild" | "task-work"

    # Core responsibility
    primary_responsibility: str  # One sentence

    # Constraints
    must_do: List[str]  # Required actions
    must_not_do: List[str]  # Forbidden actions
    ask_before: List[str]  # Actions requiring confirmation

    # Examples
    good_examples: List[str] = field(default_factory=list)
    bad_examples: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "role_constraint",
            "role": self.role,
            "context": self.context,
            "primary_responsibility": self.primary_responsibility,
            "must_do": self.must_do,
            "must_not_do": self.must_not_do,
            "ask_before": self.ask_before,
            "good_examples": self.good_examples,
            "bad_examples": self.bad_examples,
            "created_at": self.created_at.isoformat()
        }
```

### Role Constraint Content

```python
PLAYER_CONSTRAINTS = RoleConstraintFact(
    role="player",
    context="feature-build",
    primary_responsibility="Implement code changes to satisfy acceptance criteria",

    must_do=[
        "Read and understand task requirements before implementing",
        "Write code that satisfies acceptance criteria",
        "Create or modify tests as needed",
        "Report what was implemented and what files changed",
        "Follow architecture decisions (check ADRs before designing)"
    ],

    must_not_do=[
        "Do NOT validate quality gates (that's Coach's job)",
        "Do NOT approve your own work",
        "Do NOT decide if work meets quality thresholds",
        "Do NOT ask for human guidance (you are autonomous)",
        "Do NOT merge code or modify worktree state"
    ],

    ask_before=[
        "Changing architecture or design patterns",
        "Adding new dependencies",
        "Modifying files outside task scope"
    ],

    good_examples=[
        "Player: 'I implemented the auth endpoint in api/auth.py and added tests in tests/test_auth.py'",
        "Player: 'I found ADR-FB-001 specifies SDK query(), so I used that instead of subprocess'"
    ],

    bad_examples=[
        "Player: 'Tests pass with 85% coverage, this meets quality gates' (WRONG - Coach decides this)",
        "Player: 'Should I use JWT or sessions?' (WRONG - autonomous, don't ask)"
    ]
)

COACH_CONSTRAINTS = RoleConstraintFact(
    role="coach",
    context="feature-build",
    primary_responsibility="Validate Player's work against quality gates and acceptance criteria",

    must_do=[
        "Check if acceptance criteria are met",
        "Verify tests pass and coverage meets threshold",
        "Verify architectural compliance (if required)",
        "Provide specific feedback when rejecting",
        "Approve when all quality gates pass"
    ],

    must_not_do=[
        "Do NOT implement code changes (that's Player's job)",
        "Do NOT write tests",
        "Do NOT fix failing tests",
        "Do NOT suggest alternative implementations (just validate)",
        "Do NOT change quality gate thresholds mid-review"
    ],

    ask_before=[
        "Lowering quality thresholds",
        "Skipping quality gates",
        "Overriding failed validations"
    ],

    good_examples=[
        "Coach: 'Tests pass (12/12), coverage 87% (threshold 80%), arch score 72 (threshold 60). APPROVED.'",
        "Coach: 'Tests fail (2 failures in test_auth.py). FEEDBACK: Fix assertion on line 45.'"
    ],

    bad_examples=[
        "Coach: 'I fixed the failing tests and now they pass' (WRONG - Coach doesn't implement)",
        "Coach: 'Maybe try using a different approach' (WRONG - Coach validates, doesn't suggest)"
    ]
)
```

### Seeding Function

```python
async def seed_role_constraints(graphiti):
    """Seed role constraints into Graphiti."""

    constraints = [PLAYER_CONSTRAINTS, COACH_CONSTRAINTS]

    for constraint in constraints:
        await graphiti.add_episode(
            name=f"role_constraint_{constraint.role}_{constraint.context}",
            episode_body=json.dumps(constraint.to_episode_body()),
            group_id="role_constraints"
        )
```

### Context Loading Integration

```python
async def load_role_context(role: str, context: str = "feature-build") -> Optional[str]:
    """Load role constraints for injection into session."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return None

    results = await graphiti.search(
        query=f"role_constraint {role} {context}",
        group_ids=["role_constraints"],
        num_results=1
    )

    if not results:
        return None

    body = results[0].get('body', {})

    lines = [
        f"## {role.upper()} Role Constraints",
        f"**Primary responsibility**: {body.get('primary_responsibility', '')}",
        "",
        "**MUST DO**:",
    ]

    for item in body.get('must_do', []):
        lines.append(f"  - {item}")

    lines.append("")
    lines.append("**MUST NOT DO**:")

    for item in body.get('must_not_do', []):
        lines.append(f"  - {item}")

    return "\n".join(lines)
```

## Acceptance Criteria

- [ ] RoleConstraintFact dataclass created
- [ ] Player and Coach constraints defined and seeded
- [ ] Query function retrieves constraints by role
- [ ] Session context loading includes role constraints when applicable
- [ ] Unit tests for fact serialization
- [ ] Integration test confirms constraints appear in context

## Files to Create/Modify

### New Files
- `guardkit/knowledge/facts/role_constraint.py`
- `guardkit/knowledge/seed_role_constraints.py`
- `tests/knowledge/test_role_constraints.py`

### Modified Files
- `guardkit/knowledge/context_loader.py` (add role loading)
- `guardkit/knowledge/seed_system_context.py` (call seed_role_constraints)

## Testing Strategy

1. **Unit tests**: Test fact serialization and loading
2. **Integration tests**: Seed and query constraints in real Graphiti
3. **Manual test**: Run Player turn, verify constraints visible in context