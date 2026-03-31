---
id: TASK-REV-F133
title: Investigate AutoBuild UNRECOVERABLE_STALL on TASK-SFT-001 (Run 2)
task_type: review
status: review_complete
created: 2026-02-15T20:00:00Z
updated: 2026-02-15T21:00:00Z
review_results:
  mode: debugging
  depth: deep
  score: 95
  findings_count: 1
  recommendations_count: 3
  decision: implement
  root_cause: H1_confirmed
  report_path: .claude/reviews/TASK-REV-F133-review-report.md
  implementation_task: TASK-FIX-PIPELINE-DATA-LOSS
priority: high
tags: [autobuild, stall-detection, coach-validator, debugging]
complexity: 5
decision_required: true
related_tasks: [TASK-SFT-001]
related_feature: FEAT-AC1A
---

# Investigate AutoBuild UNRECOVERABLE_STALL on TASK-SFT-001 (Run 2)

## Context

AutoBuild run 2 (`docs/reviews/autobuild-fixes/run_2.md`) failed with `UNRECOVERABLE_STALL` on TASK-SFT-001 (scaffolding task) after 3 turns. TASK-SFT-002 (documentation) succeeded in 2 turns.

Feature: FEAT-AC1A (Seam-First Testing Strategy)
Result: 1/11 tasks completed, 1 failed, 9 not attempted (stop_on_failure=True)

## Observed Failure Pattern

### Symptom: Feedback Stall (identical feedback signature for 3 turns)
- **Turn 1**: Player creates 5 files, modifies 4 — Coach says 0/10 criteria met
- **Turn 2**: Player creates 1 file, modifies 2 — Coach says 0/10 criteria met (identical feedback)
- **Turn 3**: Player creates 1 file, modifies 3 — Coach says 0/10 criteria met (identical feedback)
- **Result**: `feedback_stall` → `UNRECOVERABLE_STALL` (sig=bbaba24c repeated 3x)

### Key Diagnostic Lines
```
WARNING: Criteria verification 0/10 - diagnostic dump
WARNING:   requirements_met: []
WARNING:   matching_strategy: text
WARNING:   _synthetic: False
```

The Coach's `_match_by_text()` found **zero matches** because `requirements_met` from the Player's `task_work_results.json` was an **empty list** — despite the Player successfully creating the expected files.

### Contrast: TASK-SFT-002 Succeeded
- Turn 1: Coach verified 6/11 criteria (60%) — `requirements_met` was populated
- Turn 2: Coach verified remaining criteria → approved

## Root Cause Hypotheses

### H1: Player task-work delegation doesn't populate `requirements_met` for scaffolding tasks
The Player uses `implementation_mode: task-work` which delegates to Claude Code's `/task-work` command. The `task_work_results.json` may not include `requirements_met` entries when the task type is `scaffolding` (no tests to run, no code logic to validate). The Coach then falls through to text matching against an empty list → 0/10.

### H2: Coach text matching is too strict for scaffolding criteria
The acceptance criteria contain multi-line/nested items (e.g., fixtures list with sub-bullets). The `_match_by_text()` normalization may not handle nested criteria like:
```
- `tests/seam/conftest.py` provides shared fixtures:
  - `graphiti_mock_client` — AsyncMock...
  - `cli_runner` — Click CliRunner...
```

### H3: Quality gate profile for `scaffolding` task type is misconfigured
The Coach uses `quality_gate_profile` for task type `scaffolding` — it skips tests (`tests_required=False`) and independent verification. But it still requires `requirements_met` to match criteria, which scaffolding tasks may not produce.

### H4: FalkorDB event loop errors degraded context
Multiple `Event loop is closed` and `asyncio.locks.Lock bound to different event loop` errors suggest Graphiti context was unavailable. The Player may have lacked context about what criteria format the Coach expects.

## Acceptance Criteria

- [ ] Identify the root cause of empty `requirements_met` in TASK-SFT-001's Player output
- [ ] Determine why TASK-SFT-002 populated `requirements_met` but TASK-SFT-001 did not
- [ ] Review `coach_validator.py` text matching logic for scaffolding task handling
- [ ] Propose fix(es) with specific code changes
- [ ] Assess whether this affects other scaffolding/non-code tasks in the feature

## Files to Investigate

- `docs/reviews/autobuild-fixes/run_2.md` — Full run log
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Coach validation logic (`_match_by_text`, criteria verification)
- `guardkit/orchestrator/autobuild.py` — Stall detection, criteria progress tracking
- `guardkit/orchestrator/agent_invoker.py` — Player report creation, `task_work_results.json` generation
- `.guardkit/worktrees/FEAT-AC1A/.guardkit/autobuild/TASK-SFT-001/` — Player/Coach turn JSON files (if preserved)
- `tasks/backlog/seam-first-testing/TASK-SFT-001-scaffolding.md` — Task definition with acceptance criteria

## Suggested Workflow

```bash
/task-review TASK-REV-F133 --mode=debugging --depth=deep
```
