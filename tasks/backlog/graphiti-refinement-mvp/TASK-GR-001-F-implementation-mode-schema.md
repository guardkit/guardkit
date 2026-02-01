---
id: TASK-GR-001-F
title: Create ImplementationModeEpisode and seed defaults
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-seeding
- autobuild
- implementation-modes
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 6
conductor_workspace: gr-mvp-wave6-schemas
complexity: 2
depends_on:
- TASK-GR-PRE-003-D
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:19:31.555114'
  last_updated: '2026-02-01T07:27:33.176475'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:19:31.555114'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create ImplementationModeEpisode and seed defaults

## Description

Create the ImplementationModeEpisode dataclass and seed default mode descriptions. This addresses the "direct vs task-work confusion" identified in AutoBuild lessons.

## Acceptance Criteria

- [ ] ImplementationModeEpisode dataclass implemented
- [ ] Default modes: direct, task-work, manual
- [ ] Modes seeded during project init
- [ ] When-to-use guidance captured
- [ ] Pitfalls documented for each mode

## Implementation Notes

### Schema Definition

```python
@dataclass
class ImplementationModeEpisode:
    """Implementation mode patterns and guidance."""

    entity_type: str = "implementation_mode"

    mode: str = ""  # "direct" | "task-work" | "manual"
    invocation_method: str = ""  # "sdk_query" | "subprocess" | "inline"
    result_location_pattern: str = ""
    state_recovery_strategy: str = ""

    when_to_use: List[str] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Implementation Mode: {self.mode}

        Invocation: {self.invocation_method}
        Results Location: {self.result_location_pattern}
        State Recovery: {self.state_recovery_strategy}

        WHEN TO USE:
        {chr(10).join(f'- {w}' for w in self.when_to_use)}

        PITFALLS:
        {chr(10).join(f'- {p}' for p in self.pitfalls)}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return f"implementation_mode_{self.mode}"
```

### Default Modes

```python
IMPLEMENTATION_MODE_DEFAULTS = {
    "direct": ImplementationModeEpisode(
        mode="direct",
        invocation_method="inline",
        result_location_pattern="In current context",
        state_recovery_strategy="None needed - atomic execution",
        when_to_use=[
            "Simple, low-complexity tasks (1-3)",
            "No quality gates needed",
            "Quick fixes or documentation",
        ],
        pitfalls=[
            "No automatic testing",
            "No architectural review",
            "Easy to skip quality checks",
        ],
    ),
    "task-work": ImplementationModeEpisode(
        mode="task-work",
        invocation_method="subprocess",
        result_location_pattern=".claude/task-plans/{task_id}-implementation-plan.md",
        state_recovery_strategy="Resume from task file state",
        when_to_use=[
            "Medium to high complexity tasks (4+)",
            "Quality gates required",
            "Features, not just fixes",
        ],
        pitfalls=[
            "Task file must exist before invocation",
            "State persisted in markdown",
            "Subprocess coordination required",
        ],
    ),
    "manual": ImplementationModeEpisode(
        mode="manual",
        invocation_method="human",
        result_location_pattern="Varies",
        state_recovery_strategy="Human-driven",
        when_to_use=[
            "Research tasks",
            "Human decision required",
            "External tooling needed",
        ],
        pitfalls=[
            "No automation",
            "Manual tracking required",
        ],
    ),
}
```

### Files to Create

- `src/guardkit/integrations/graphiti/episodes/implementation_mode.py`

## Test Requirements

- [ ] Unit tests for schema
- [ ] Unit tests for default modes

## Notes

Simpler schema - fewer fields than role constraints or quality gates.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
