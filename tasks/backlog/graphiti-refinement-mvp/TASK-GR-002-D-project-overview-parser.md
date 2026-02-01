---
id: TASK-GR-002-D
title: Implement ProjectOverviewParser
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- context-addition
- parser
- project-overview
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 7
conductor_workspace: gr-mvp-wave7-parsers
complexity: 3
depends_on:
- TASK-GR-002-A
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:30:15.463389'
  last_updated: '2026-02-01T07:39:45.399949'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:30:15.463389'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement ProjectOverviewParser

## Description

Implement a parser for project overview documents (CLAUDE.md, README.md) specifically for the add-context command. This is similar to TASK-GR-001-G but designed for explicit context addition.

## Acceptance Criteria

- [ ] Parse CLAUDE.md format
- [ ] Parse README.md format
- [ ] Extract: purpose, tech stack, architecture, patterns
- [ ] Create project overview episode
- [ ] Handle partial/missing sections gracefully

## Implementation Notes

### Parser Implementation

```python
class ProjectOverviewParser(BaseParser):
    """Parser for project overview documents."""

    @property
    def parser_type(self) -> str:
        return "project-overview"

    @property
    def supported_extensions(self) -> List[str]:
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this is a project overview."""
        filename = Path(file_path).name.lower()
        return filename in ["claude.md", "readme.md"]

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse project overview into episode."""
        episodes = []

        # Extract sections
        purpose = self._extract_purpose(content)
        tech_stack = self._extract_tech_stack(content)
        architecture = self._extract_architecture(content)

        # Create overview episode
        overview_content = f"""
        Project Overview

        Purpose:
        {purpose}

        Technology Stack:
        {tech_stack}

        Architecture:
        {architecture}
        """

        episode = EpisodeData(
            content=overview_content,
            group_id="project_overview",
            entity_type="project_overview",
            entity_id="project_overview_main",
            metadata={"source_path": file_path}
        )
        episodes.append(episode)

        # If architecture is rich, create separate episode
        if len(architecture) > 500:
            arch_episode = EpisodeData(
                content=architecture,
                group_id="project_architecture",
                entity_type="project_architecture",
                entity_id="project_architecture_main",
                metadata={"source_path": file_path}
            )
            episodes.append(arch_episode)

        return ParseResult(episodes=episodes, warnings=[], success=True)
```

### Files to Create

- `src/guardkit/integrations/graphiti/parsers/project_overview.py`

## Test Requirements

- [ ] Unit tests with sample CLAUDE.md
- [ ] Unit tests with sample README.md
- [ ] Test section extraction
- [ ] Test missing sections handling

## Notes

Reuses logic from TASK-GR-001-G but as a registered parser.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
