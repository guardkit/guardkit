---
id: TASK-ISF-006
title: Slim guardkit init to project-only Graphiti seeding
status: completed
completed: 2026-03-04T12:00:00Z
completed_location: tasks/completed/TASK-ISF-006/
priority: high
complexity: 3
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 3
implementation_mode: task-work
dependencies: [TASK-ISF-005]
tags: [init, graphiti, performance, architectural]
---

# TASK-ISF-006: Slim Init to Project-Only Seeding

## Problem

`guardkit init` currently performs both project-specific and system-wide Graphiti seeding:

| Step | Current Duration | Content | Scope |
|------|-----------------|---------|-------|
| Step 2 | ~15 min | Project overview + role constraints + impl modes | Mixed (project + system) |
| Step 2.5 | ~25 min | Template manifest + agents + rules | System |
| **Total** | **~35 min** | | |

After TASK-ISF-005 creates `guardkit graphiti seed-system`, init should only seed project-specific content.

## Solution

Modify `guardkit init` Graphiti seeding to:

| Step | New Duration | Content | Scope |
|------|-------------|---------|-------|
| Step 2 | ~5-8 min | Project overview ONLY (2 episodes) | Project |
| Step 2.5 | Skipped | System content seeded via `seed-system` | N/A |
| **Total** | **~5-8 min** | | |

### Changes

1. **Step 2**: Remove role constraint and implementation mode seeding (these are system-scoped, handled by `seed-system`)
2. **Step 2.5**: Make no-op or remove entirely — template/agent/rule sync handled by `seed-system`
3. **Add guidance**: After init, suggest running `guardkit graphiti seed-system` if not already done

## Files to Change

- `guardkit/cli/init.py` — Remove system seeding from Step 2, skip Step 2.5
- `guardkit/knowledge/project_seeding.py` — Remove role constraint and impl mode seeding (or gate behind a flag)
- `tests/cli/test_init.py` — Update tests for slimmed seeding
- `tests/cli/test_init_progress.py` — Update progress tests

## Acceptance Criteria

- [x] `guardkit init` only seeds project_overview episodes (project_purpose, project_scope, project_architecture)
- [x] Role constraints NOT seeded during init (system-scoped)
- [x] Implementation modes NOT seeded during init (system-scoped)
- [x] Template/agent/rule sync NOT run during init (system-scoped)
- [x] Init duration reduced from ~35 min to ~5-8 min
- [x] Post-init message suggests `guardkit graphiti seed-system` if needed
- [x] Existing tests updated and passing
- [x] No regression in project-specific seeding

## Testing

```bash
pytest tests/cli/test_init.py -v
pytest tests/cli/test_init_progress.py -v
```

## Dependencies

- **TASK-ISF-005** must be completed first — the `seed-system` command must exist before we remove system seeding from init
