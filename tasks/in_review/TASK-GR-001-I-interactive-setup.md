---
complexity: 3
conductor_workspace: gr-mvp-wave8-cli
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-001-H
feature_id: FEAT-GR-MVP
id: TASK-GR-001-I
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: medium
status: in_review
tags:
- graphiti
- project-seeding
- interactive
- mvp-phase-2
task_type: feature
title: Implement optional interactive setup
updated: 2026-02-01 08:15:00+00:00
wave: 8
---

# Task: Implement optional interactive setup

## Description

Add an optional interactive mode to `guardkit init` that prompts users for project information when CLAUDE.md/README.md parsing is insufficient.

## Acceptance Criteria

- [x] `guardkit init --interactive` prompts for missing info
- [x] Prompts cover: purpose, tech stack, key goals
- [x] Answers are used for Graphiti seeding
- [x] Answers can be saved to CLAUDE.md
- [x] Non-interactive mode remains default

## Implementation Notes

### Interactive Flow

```python
async def interactive_setup(project_name: str) -> ProjectOverviewEpisode:
    """Run interactive setup for project knowledge."""

    console = Console()

    purpose = Prompt.ask(
        "What is the purpose of this project?",
        default="A software project"
    )

    primary_language = Prompt.ask(
        "What is the primary programming language?",
        choices=["python", "typescript", "go", "rust", "java", "other"]
    )

    frameworks = Prompt.ask(
        "What frameworks are you using? (comma-separated)",
        default=""
    ).split(",")

    key_goals = []
    console.print("Enter key goals (empty line to finish):")
    while True:
        goal = Prompt.ask("Goal", default="")
        if not goal:
            break
        key_goals.append(goal)

    return ProjectOverviewEpisode(
        project_name=project_name,
        purpose=purpose,
        primary_language=primary_language,
        frameworks=[f.strip() for f in frameworks if f.strip()],
        key_goals=key_goals,
    )
```

### Save to CLAUDE.md Option

```python
save_to_file = Confirm.ask(
    "Save this information to CLAUDE.md?",
    default=True
)

if save_to_file:
    generate_claude_md(overview)
```

### Files to Modify

- `src/guardkit/cli/commands/init.py` - Add interactive mode

## Test Requirements

- [x] Unit tests for interactive prompts (mocked)
- [x] Test CLAUDE.md generation

## Notes

Nice-to-have for projects without good documentation.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)