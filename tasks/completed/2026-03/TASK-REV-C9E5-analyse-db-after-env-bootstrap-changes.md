---
id: TASK-REV-C9E5
title: Analyse DB failure after environment bootstrap implementation
status: review_complete
task_type: review
review_mode: architectural
created: 2025-06-07T00:00:00Z
updated: 2026-02-18T00:00:00Z
review_results:
  mode: architectural
  depth: comprehensive
  score: 62
  findings_count: 9
  recommendations_count: 5
  revision: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-C9E5-review-report.md
priority: high
tags: [autobuild, environment-bootstrap, root-cause-analysis, hatchling]
complexity: 5
parent_review: TASK-REV-4D57
parent_feature: environment-bootstrap
evidence_file: docs/reviews/autobuild-fixes/db_failed_after_env_changes.md
related_tasks:
  - TASK-BOOT-E3C0
  - TASK-BOOT-3CAF
  - TASK-BOOT-43DE
  - TASK-BOOT-214B
  - TASK-BOOT-6D85
  - TASK-BOOT-F9C4
  - TASK-BOOT-7369
implementation_tasks:
  - TASK-BOOT-B032
  - TASK-BOOT-F632
  - TASK-BOOT-0F53
  - TASK-BOOT-754A
  - TASK-BOOT-99A5
implementation_subfolder: tasks/backlog/boot-wave2/
---

# Task: Analyse DB failure after environment bootstrap implementation

## Description

Analyse the autobuild output from a re-run of FEAT-BA28 (PostgreSQL Database Integration) after the environment-bootstrap tasks (TASK-BOOT-*) were implemented. The evidence file is at `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`.

This is a follow-up to TASK-REV-4D57 which identified the missing environment bootstrap phase as the root cause of TASK-DB-003's `UNRECOVERABLE_STALL`. The bootstrap was implemented per the 7 tasks in `tasks/backlog/environment-bootstrap/`, but the re-run still fails.

## Evidence Summary

Key observations from the evidence file (859 lines of verbose autobuild output):

### What was implemented (working)
1. **Bootstrap phase fires** (line 32): `Bootstrapping environment: python` — TASK-BOOT-E3C0 integrated
2. **Inter-wave bootstrap fires** (line 373): Re-detection between waves — TASK-BOOT-3CAF integrated
3. **Classification upgraded** (lines 639, 703, 765): `confidence=high` — TASK-BOOT-F9C4 implemented
4. **Bootstrap partial reporting** (lines 104, 444): `Environment bootstrap partial: 0/1 succeeded`

### What failed (new issues)
1. **Wrong Python executable** (line 33): Bootstrap uses `/usr/local/bin/python3` instead of `sys.executable` (the framework Python at `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14`). This contradicts the design spec in TASK-BOOT-E3C0 which explicitly requires `sys.executable`.
2. **Hatchling build error** (lines 34-100): `pip install -e .` fails with `ValueError: Unable to determine which files to ship inside the wheel` because no directory matches the project name `fastapi_health_app`. This is a greenfield project where Wave 1 creates `pyproject.toml` but not the matching package directory.
3. **TASK-DB-003 still stalls** (line 779): `UNRECOVERABLE_STALL` after 3 identical Coach turns despite `confidence=high` classification.
4. **Conditional approval path not triggered**: Despite `confidence=high`, the conditional approval fallback does not appear to fire.

## Review Scope

### Primary Questions

1. **Why does bootstrap use `/usr/local/bin/python3` instead of `sys.executable`?**
   - Was TASK-BOOT-E3C0's `sys.executable` requirement not implemented correctly?
   - Or does `sys.executable` resolve to `/usr/local/bin/python3` in the orchestrator context?

2. **Is `pip install -e .` the right strategy for greenfield projects?**
   - Wave 1 creates `pyproject.toml` with hatchling backend but the package directory doesn't exist yet
   - Should bootstrap detect incomplete project structure and skip/defer?
   - Should bootstrap use `pip install -r requirements.txt` as fallback when editable install fails?

3. **Why doesn't conditional approval fire despite `confidence=high`?**
   - What are ALL the conditions required for conditional approval?
   - Which condition is not met? (`requires_infrastructure`? `_docker_available`? quality gates?)
   - Was TASK-BOOT-214B (`requires_infrastructure` in FEAT-BA28) implemented?
   - Was TASK-BOOT-6D85 (`_docker_available` wiring) implemented?

4. **What is the correct recovery path for hatchling greenfield projects?**
   - Should bootstrap fall back to `pip install` (non-editable) on editable install failure?
   - Should bootstrap install individual packages from `[project.dependencies]` directly?
   - Should bootstrap skip entirely for projects with no package directory?

### Secondary Questions

5. **Are all 7 BOOT tasks reflected in the evidence?** Verify which tasks were actually implemented vs planned.
6. **Does the inter-wave bootstrap add value here?** It fires (line 373) but fails with the same error — is this expected for the greenfield timing gap?
7. **What is the diagnostic logging output?** Was TASK-BOOT-7369 implemented? Is DEBUG output visible?

## Acceptance Criteria

- [ ] Root cause of bootstrap failure identified with evidence
- [ ] `sys.executable` vs `/usr/local/bin/python3` discrepancy explained
- [ ] Conditional approval path traced — identify which condition blocks it
- [ ] Each BOOT task's implementation status verified against evidence
- [ ] Recommendations for fixing the bootstrap failure
- [ ] Recommendations for greenfield project editable install strategy

## Source Files

- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
- Bootstrap implementation: `guardkit/orchestrator/environment_bootstrap.py`
- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Feature orchestrator: `guardkit/orchestrator/feature_orchestrator.py`
- AutoBuild orchestrator: `guardkit/orchestrator/autobuild.py`
- FEAT-BA28 definition: `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml`
- Parent review report: `.claude/reviews/TASK-REV-4D57-review-report.md`
- Implementation tasks: `tasks/backlog/environment-bootstrap/`
