---
id: TASK-REV-E719
title: Analyse AutoBuild Run 3 UNRECOVERABLE_STALL on TASK-SFT-001 Post Pipeline Fix
task_type: review
status: review_complete
review_results:
  mode: debugging
  depth: deep
  findings_count: 3
  recommendations_count: 3
  report_path: .claude/reviews/TASK-REV-E719-review-report.md
  completed_at: 2026-02-15T23:30:00Z
created: 2026-02-15T23:00:00Z
updated: 2026-02-15T23:00:00Z
priority: high
tags: [autobuild, coach-validator, criteria-matching, feedback-stall, debugging]
complexity: 5
decision_required: true
related_tasks: [TASK-SFT-001, TASK-REV-F133, TASK-FIX-PIPELINE-DATA-LOSS]
related_feature: FEAT-AC1A
---

# Analyse AutoBuild Run 3 UNRECOVERABLE_STALL on TASK-SFT-001 Post Pipeline Fix

## Context

AutoBuild run 3 (`docs/reviews/autobuild-fixes/run_3.md`) was executed after implementing the TASK-FIX-PIPELINE-DATA-LOSS fixes (5 fixes to the Player→Coach data pipeline in `agent_invoker.py`). The pipeline fixes successfully resolved the data loss — completion_promises are now recovered (6 promises per turn) and requirements_addressed are populated (9-11 per turn). However, TASK-SFT-001 still fails with `UNRECOVERABLE_STALL` after 3 turns.

**Improvement over Run 2**: The pipeline data loss is fixed — Coach now sees data (6/10 criteria verified = 60%) instead of 0/10. But 4 criteria remain persistently unmet across all 3 turns, causing identical feedback and triggering the feedback stall detector.

**TASK-SFT-002** (documentation task): Succeeded in 3 turns (approved).

**Feature result**: FAILED — 1/11 tasks completed, 1 failed, 9 not attempted (stop_on_failure=True).

## Observed Failure Pattern

### Symptom: Persistent 4 Unmet Criteria (same 4 every turn)

The Coach consistently rejects the same 4 acceptance criteria across all 3 turns:

1. **`pytest.ini` or `pyproject.toml` registers `@pytest.mark.seam` marker**
2. **`tests/seam/` tests are discovered and run by `pytest tests/seam/`**
3. **Existing tests in `tests/integration/test_system_plan_seams.py` and `tests/integration/test_planning_module_seams.py` are NOT moved (migration is a separate task)**
4. **`tests/fixtures/minimal-spec.md` fixture file created for system-plan seam tests**

### Key Diagnostic Lines

```
Turn 1: Criteria Progress: 6/10 verified (criteria: 6 verified, 4 rejected, 0 pending)
Turn 2: Criteria Progress: 6/10 verified (criteria: 6 verified, 4 rejected, 0 pending)
Turn 3: Criteria Progress: 6/10 verified (criteria: 6 verified, 4 rejected, 0 pending)
```

```
WARNING: Feedback stall: identical feedback (sig=fec0ab4a) for 3 turns with 6 criteria passing
ERROR: Feedback stall detected for TASK-SFT-001: identical feedback for 3 consecutive turns with 0% criteria progress
```

### Pipeline Fix Verification (Working)

The TASK-FIX-PIPELINE-DATA-LOSS fixes are confirmed working:
- `Recovered 6 completion_promises from agent-written player report` — Fix 2 ✓
- `Recovered 10-11 requirements_addressed from agent-written player report` — Fix 2 ✓
- `Updated task_work_results.json with enriched data` — Fix 3 ✓
- `Git detection added: 3 modified, 1-22 created files` — Fix 4 ✓
- `ToolUseBlock Write input keys: ['file_path', 'content']` — Fix 1 diagnostic ✓
- No `"**"` spurious entries observed in logs — Fix 4 ✓

### Player Activity Per Turn

- **Turn 1**: 5 files created, 3 modified, 34 SDK turns, 33 tool calls, 0 tests (failing)
- **Turn 2**: 1 file created, 3 modified, 0 tests (failing)
- **Turn 3**: 1 file created, 3 modified, 0 tests (passing)

### Notable: `AC-007` and `AC-008` Have No Promises

```
AC-007: No completion promise for AC-007
AC-008: No completion promise for AC-008
```

The Player's 6 completion_promises only cover 6 of the 10 acceptance criteria. The remaining 4 (which happen to be the 4 failing ones) have no matching promise, so Coach falls through to text matching for those criteria — and text matching rejects them.

## Root Cause Hypotheses

### H1: Coach text matching is too strict for these specific criteria

The 4 failing criteria contain:
- **File path references** in backticks (e.g., `tests/fixtures/minimal-spec.md`)
- **Negative assertions** ("are NOT moved")
- **Command-line references** (`pytest tests/seam/`)
- **Multi-concept requirements** (marker registration in `pytest.ini` OR `pyproject.toml`)

The Coach's `_match_by_text()` may fail to match these against the Player's `requirements_addressed` entries because:
- The Player's wording differs from the exact AC text
- Negative assertions ("NOT moved") may not have a clear positive match in requirements_addressed
- OR conditions in criteria may not be handled

### H2: Player only generates 6 completion_promises but task has 10 criteria

The Player's execution protocol instructs it to write `completion_promises` for each AC. But the Player consistently writes only 6, leaving 4 without promises. This could be:
- The Player's SDK session exhausting turns before writing all promises
- The execution protocol not clearly enumerating all 10 criteria
- The Player bundling some criteria into combined promises

### H3: Stall detector threshold is too aggressive for partial progress

The stall detector triggers on "identical feedback for 3 consecutive turns with 0% criteria progress." But criteria progress IS at 60% (6/10) — it's just static. The "0% criteria progress" in the error message refers to the DELTA between turns (no improvement), not the absolute level. The stall detector may need to distinguish between "zero progress from zero" (run 2) and "significant progress but stuck on specific criteria" (run 3).

### H4: Criterion #5 ("tests NOT moved") is unverifiable by the Coach

The negative assertion "Existing tests... are NOT moved" requires verifying that files still exist at their original locations. The Coach's promise/text matching cannot verify negative conditions — it can only verify things the Player claims to have done. The Player has no mechanism to claim "I did NOT do X."

### H5: Criterion #4 (`tests/fixtures/minimal-spec.md`) IS being created but not matched

Turn 1 shows the file in the files_created list (line 168): `/Users/.../tests/fixtures/minimal-spec.md`. The Player created the file, but the Coach's text matching doesn't connect "file created" to "criterion met" for this specific AC.

## Acceptance Criteria

- [ ] Determine why Coach text matching fails for the 4 specific criteria
- [ ] Determine why the Player only generates 6 of 10 completion_promises
- [ ] Evaluate whether the stall detector should differentiate "stuck at 60%" from "stuck at 0%"
- [ ] Review Coach handling of negative assertions in acceptance criteria
- [ ] Propose fix(es) with specific code changes
- [ ] Assess impact on other scaffolding/non-code tasks in FEAT-AC1A

## Files to Investigate

- `docs/reviews/autobuild-fixes/run_3.md` — Full run 3 log
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_match_by_text()`, `_match_by_promises()`, criteria verification logic
- `guardkit/orchestrator/autobuild.py` — Stall detection, criteria progress tracking, feedback signature calculation
- `guardkit/orchestrator/agent_invoker.py` — Player report creation (post-TASK-FIX-PIPELINE-DATA-LOSS), execution protocol content
- `.guardkit/worktrees/FEAT-AC1A/.guardkit/autobuild/TASK-SFT-001/` — Player/Coach turn JSON files (if preserved)
- `tasks/backlog/seam-first-testing/TASK-SFT-001-scaffolding.md` — Task definition with acceptance criteria
- `.claude/reviews/TASK-REV-F133-review-report.md` — Previous review findings
- `tasks/completed/TASK-FIX-PIPELINE-DATA-LOSS/TASK-FIX-PIPELINE-DATA-LOSS.md` — Pipeline fix specification

## Prior Art

| Run | Root Cause | Fix Applied | Result |
|-----|-----------|-------------|--------|
| Run 2 | Player→Coach data pipeline loses all data (empty `requirements_met`, no `completion_promises`) | TASK-FIX-PIPELINE-DATA-LOSS: 5 fixes to `agent_invoker.py` | Data pipeline fixed, 6/10 criteria now pass |
| Run 3 | 4 specific criteria persistently unmet despite Player work | **This review** | TBD |

## Suggested Workflow

```bash
/task-review TASK-REV-E719 --mode=debugging --depth=deep
```
