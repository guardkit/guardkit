# Feature: Seed Quality Fixes (FEAT-SQF)

## Problem

After FEAT-ISF (Init Seeding Fixes) completed and validated, TASK-REV-49AB identified 3 remaining bugs in the `guardkit graphiti seed` command path:

1. **Template timeout cascade** — `"templates"` gets the default 120s timeout but template episodes need 111-150s on a clean graph, causing 3 consecutive timeouts that trip the circuit breaker and silently skip 5+ subsequent seed categories
2. **Misleading seed summary** — The orchestrator logs "Seeded {category}" even when the circuit breaker blocked all episodes (0 created), giving false confidence
3. **Pattern examples path bug** — `seed_pattern_examples.py` uses a relative path that resolves against CWD (target project) instead of the guardkit installation, so it has never worked when running from a target project

## Solution

Three targeted fixes, all low-risk and independently deployable:

1. **TASK-FIX-b06f**: Add `elif group_id == "templates": episode_timeout = 180.0` (1 line)
2. **TASK-FIX-bbbd**: Return `(created, skipped)` from `_add_episodes()`, use in orchestrator logging (~20 lines)
3. **TASK-FIX-ec01**: Replace `Path(".claude/rules/patterns")` with `Path(__file__).resolve().parent` walk-up (~15 lines)

## Parent Review

- **TASK-REV-49AB** — Review of reseed + init (init_project_8) on clean graph
- **Report**: `.claude/reviews/TASK-REV-49AB-review-report.md`

## Predecessor Feature

- **FEAT-ISF** — Init Seeding Fixes (6/6 tasks completed, validated effective)

## Subtasks

| ID | Task | Effort | Priority | Status |
|----|------|--------|----------|--------|
| TASK-FIX-b06f | Add "templates" to 180s timeout tier | 1/10 | High | Completed |
| TASK-FIX-bbbd | Return episode counts from _add_episodes | 2/10 | Medium | Completed |
| TASK-FIX-ec01 | Fix pattern examples path resolution | 2/10 | Medium | Completed |

## Execution

```bash
# All 3 can run in parallel (no file conflicts)
/task-work TASK-FIX-b06f
/task-work TASK-FIX-bbbd
/task-work TASK-FIX-ec01
```
