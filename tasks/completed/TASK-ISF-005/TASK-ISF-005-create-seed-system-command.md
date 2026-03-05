---
id: TASK-ISF-005
title: Create guardkit graphiti seed-system command
status: completed
completed: 2026-03-04T00:00:00Z
priority: high
complexity: 4
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 3
implementation_mode: task-work
dependencies: []
tags: [graphiti, cli, seed-system, architectural]
---

# TASK-ISF-005: Create guardkit graphiti seed-system Command

## Problem

System/template content (role constraints, implementation modes, template manifest, agents, rules) is re-seeded on every `guardkit init` run, even though this content:
- Doesn't change between projects
- Takes ~25 min to seed
- Causes graph bloat as system groups accumulate duplicate data
- Uses system-scoped groups that aren't cleared by `--project-only`

## Solution

Create a dedicated `guardkit graphiti seed-system` command that seeds all template/system content once. This decouples system seeding from project initialization.

## Design

```bash
# Seed all system content (template, agents, rules, role constraints, impl modes)
guardkit graphiti seed-system [--template fastapi-python] [--force]

# --force: Re-seed even if content already exists (uses upsert)
# --template: Which template to seed (default: detect from project)
```

### What It Seeds

| Group | Content | Source |
|-------|---------|--------|
| templates | Template manifest | Template dir manifest |
| agents | Agent metadata (3 for fastapi) | `.claude/agents/*.md` |
| rules | Rule previews (12 for fastapi) | `.claude/rules/*.md` |
| role_constraints | Player/Coach constraints | `seed_role_constraints.py` |
| implementation_modes | 3 modes | `project_seeding.py` |

### What It Doesn't Seed

| Group | Content | Reason |
|-------|---------|--------|
| project_overview | Project purpose/scope/arch | Project-specific → stays in `guardkit init` |

## Files to Create/Change

- `guardkit/cli/graphiti_commands.py` — Add `seed-system` subcommand
- `guardkit/knowledge/system_seeding.py` — New module: orchestrates system seeding (extracts from current `project_seeding.py` and `template_sync.py`)
- `tests/knowledge/test_system_seeding.py` — Tests for the new module
- `tests/cli/test_graphiti_commands.py` — CLI integration test

## Acceptance Criteria

- [x] `guardkit graphiti seed-system` command exists and works
- [x] Seeds template manifest, agents, rules, role constraints, implementation modes
- [x] Uses `upsert_episode` to avoid duplicates
- [x] `--force` flag re-seeds regardless of existing content
- [x] `--template` flag specifies which template to seed
- [x] Sequential sync (not parallel) for reliability
- [x] Rules use `content_preview` (500 chars), not full content
- [x] All seeded content uses system-scoped groups
- [x] Tests pass with >=80% coverage (94% achieved)

## Testing

```bash
pytest tests/knowledge/test_system_seeding.py -v
pytest tests/cli/test_graphiti_commands.py -v -k seed_system
```
