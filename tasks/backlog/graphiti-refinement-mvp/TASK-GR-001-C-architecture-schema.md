---
id: TASK-GR-001-C
title: Create ProjectArchitectureEpisode schema
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
complexity: 2
depends_on:
- TASK-GR-PRE-003-D
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:19:31.542243'
  last_updated: '2026-02-01T07:26:23.739673'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-01T07:19:31.542243'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:24:23.507069'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create ProjectArchitectureEpisode schema

## Description

Create the ProjectArchitectureEpisode dataclass that captures system architecture patterns. This prevents "architectural drift" by maintaining consistent architecture context.

## Acceptance Criteria

- [ ] ProjectArchitectureEpisode dataclass implemented
- [ ] Captures architecture patterns, layers, components
- [ ] Serializable to Graphiti episode format
- [ ] Entity ID generation for upsert support

## Implementation Notes

### Schema Definition

```python
@dataclass
class ProjectArchitectureEpisode:
    """Project architecture patterns."""

    entity_type: str = "project_architecture"

    # Architecture style
    architecture_style: str = ""  # "layered", "clean", "hexagonal", "microservices"
    pattern_description: str = ""

    # Layers/modules
    layers: List[str] = field(default_factory=list)  # ["domain", "application", "infrastructure"]
    key_modules: List[str] = field(default_factory=list)

    # Patterns used
    design_patterns: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)

    # File organization
    directory_structure: str = ""  # Brief description
    naming_conventions: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Architecture Style: {self.architecture_style}

        Description: {self.pattern_description}

        Layers:
        {chr(10).join(f'- {l}' for l in self.layers)}

        Key Modules:
        {chr(10).join(f'- {m}' for m in self.key_modules)}

        Design Patterns:
        {chr(10).join(f'- {p}' for p in self.design_patterns)}

        Conventions:
        {chr(10).join(f'- {c}' for c in self.conventions)}

        Directory Structure: {self.directory_structure}

        Naming Conventions: {self.naming_conventions}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return "project_architecture_main"
```

### Files to Create

- `src/guardkit/integrations/graphiti/episodes/project_architecture.py`

## Test Requirements

- [ ] Unit tests for schema
- [ ] Unit tests for to_episode_content

## Notes

Can run in parallel with other Wave 6 tasks.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
