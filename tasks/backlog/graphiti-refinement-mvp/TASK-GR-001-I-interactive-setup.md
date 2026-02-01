---
id: TASK-GR-001-I
title: Implement optional interactive setup
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: medium
tags:
- graphiti
- project-seeding
- interactive
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 8
conductor_workspace: gr-mvp-wave8-cli
complexity: 3
depends_on:
- TASK-GR-001-H
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:55:27.991051'
  last_updated: '2026-02-01T08:07:04.605890'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:55:27.991051'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement optional interactive setup

## Description

Add an optional interactive mode to `guardkit init` that prompts users for project information when CLAUDE.md/README.md parsing is insufficient.

## Acceptance Criteria

- [ ] `guardkit init --interactive` prompts for missing info
- [ ] Prompts cover: purpose, tech stack, key goals
- [ ] Answers are used for Graphiti seeding
- [ ] Answers can be saved to CLAUDE.md
- [ ] Non-interactive mode remains default

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

- [ ] Unit tests for interactive prompts (mocked)
- [ ] Test CLAUDE.md generation

## Notes

Nice-to-have for projects without good documentation.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
