---
id: TASK-GR-001-B
title: Create ProjectOverviewEpisode schema
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-seeding
- schema
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 6
conductor_workspace: gr-mvp-wave6-schemas
complexity: 3
depends_on:
- TASK-GR-PRE-003-D
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:19:31.541091'
  last_updated: '2026-02-01T07:26:50.434017'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:19:31.541091'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create ProjectOverviewEpisode schema

## Description

Create the ProjectOverviewEpisode dataclass that captures high-level project information. This is the "North Star" context that prevents the "no big picture visibility" problem from AutoBuild.

## Acceptance Criteria

- [ ] ProjectOverviewEpisode dataclass implemented
- [ ] Captures project purpose, goals, tech stack
- [ ] Serializable to Graphiti episode format
- [ ] Entity ID generation for upsert support
- [ ] Validation for required fields

## Implementation Notes

### Schema Definition

```python
@dataclass
class ProjectOverviewEpisode:
    """Project overview for North Star context."""

    entity_type: str = "project_overview"

    # Required fields
    project_name: str = ""
    purpose: str = ""  # What does this project do?
    target_users: str = ""  # Who is it for?

    # Tech stack
    primary_language: str = ""
    frameworks: List[str] = field(default_factory=list)
    key_dependencies: List[str] = field(default_factory=list)

    # Goals and constraints
    key_goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Quality info
    testing_strategy: str = ""
    deployment_target: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Project: {self.project_name}

        Purpose: {self.purpose}

        Target Users: {self.target_users}

        Tech Stack:
        - Primary Language: {self.primary_language}
        - Frameworks: {', '.join(self.frameworks)}
        - Key Dependencies: {', '.join(self.key_dependencies)}

        Key Goals:
        {chr(10).join(f'- {g}' for g in self.key_goals)}

        Constraints:
        {chr(10).join(f'- {c}' for c in self.constraints)}

        Testing Strategy: {self.testing_strategy}
        Deployment Target: {self.deployment_target}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return f"project_overview_{self.project_name}"
```

### Files to Create

- `src/guardkit/integrations/graphiti/episodes/project_overview.py`

## Test Requirements

- [ ] Unit tests for schema
- [ ] Unit tests for to_episode_content
- [ ] Unit tests for entity_id generation

## Notes

Can run in parallel with other Wave 6 tasks.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
