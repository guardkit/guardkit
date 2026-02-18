---
id: TASK-REV-CB30
title: Analyse DB failure after boot-wave2 implementation
status: completed
task_type: review
review_mode: architectural
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T14:00:00Z
review_results:
  mode: architectural
  depth: comprehensive
  score: 78
  findings_count: 6
  recommendations_count: 3
  revision: 2
  root_cause: "Dual-Python PATH resolution — bootstrap installs to Framework Python, SDK Bash resolves to Homebrew pytest"
  actual_error: "ModuleNotFoundError: No module named 'sqlalchemy'"
  decision: implement
  report_path: .claude/reviews/TASK-REV-CB30-review-report.md
  implemented:
    - R5_option_b: "Force subprocess for infrastructure-dependent tasks"
    - R6: "Escalate conditional approval log to logger.info"
    - R7: "Add interpreter consistency diagnostic"
  tests_passed: true
  test_results: "508 passed, 76 skipped, 0 failures"
priority: high
tags: [autobuild, environment-bootstrap, root-cause-analysis, docker, conditional-approval]
complexity: 5
parent_review: TASK-REV-C9E5
parent_feature: environment-bootstrap
evidence_file: docs/reviews/autobuild-fixes/db_fails_after_yet_more_fixes.md
related_tasks:
  - TASK-BOOT-B032
  - TASK-BOOT-F632
  - TASK-BOOT-0F53
  - TASK-BOOT-754A
  - TASK-BOOT-99A5
  - TASK-REV-C9E5
---

# Task: Analyse DB failure after boot-wave2 implementation

## Description

Analyse the autobuild output from a re-run of FEAT-BA28 (PostgreSQL Database Integration) after the boot-wave2 tasks (TASK-BOOT-{B032, F632, 0F53, 754A, 99A5}) were implemented. The evidence file is at `docs/reviews/autobuild-fixes/db_fails_after_yet_more_fixes.md`.

This is a follow-up to TASK-REV-C9E5 which identified two root causes: (1) `requires_infrastructure` propagation gap and (2) install-before-ready pattern. The boot-wave2 tasks were implemented per `tasks/backlog/boot-wave2/`, and both R1 and R2 fixes are visibly working in the new evidence. However, TASK-DB-003 still stalls with UNRECOVERABLE_STALL.

## Evidence Summary

Key observations from the evidence file (671 lines of verbose autobuild output):

### What is now working (boot-wave2 fixes confirmed)
1. **R2 (dependency-only install)**: Individual `dep-install` commands run at lines 32-35 (initial) and lines 169-175 (inter-wave). The inter-wave bootstrap picks up sqlalchemy, asyncpg, alembic — dependencies that were missing in the previous run.
2. **R1 (propagation fix)**: Docker lifecycle now fires! Line 314: `Starting Docker container for service: postgresql`. Line 315: `Set DATABASE_URL=postgresql://postgres:test@localhost:5433/test`. This was completely absent in the previous evidence.
3. **TASK-DB-001**: APPROVED in 1 turn (lines 140-149)
4. **TASK-DB-002**: APPROVED in 2 turns (lines 526-538)
5. **Quality gates pass**: Line 312: `ALL_PASSED=True` for TASK-DB-003

### What still fails (new issues or persisting issues)
1. **Docker starts but tests still fail**: Line 318: `SDK independent tests failed in 6.6s`. Docker container starts (line 314) and DATABASE_URL is set (line 315), but tests fail within 6.6 seconds. Possible causes: (a) readiness check timing — `pg_isready` loop may not complete before tests run, (b) SDK subprocess may not inherit `DATABASE_URL` from `os.environ`, (c) test code may use different connection parameters.
2. **Conditional approval STILL doesn't fire**: Despite `classification=infrastructure, confidence=high` (line 320), the stall persists. Docker is now available and `requires_infrastructure` should be propagated. If R4 diagnostic logging was deployed, the `conditional_approval check` log should be visible — but it's not. Either R4 wasn't deployed, or it's at DEBUG level and filtered out, or one of the 5 conditions still evaluates False.
3. **TASK-DB-003 stalls again**: Lines 591-592: `Feedback stall: identical feedback (sig=f229025b) for 3 turns with 0 criteria passing`. Same pattern as before but with a different signature hash (f229025b vs 7e914c9e), suggesting the feedback content changed slightly.
4. **Docker container stopped after each test**: Lines 319, 459, 580: `Stopping Docker container: guardkit-test-pg`. The container is stopped after each Coach validation turn, meaning it's re-created each turn. This is correct behaviour but means the readiness check runs 3 times.

## Review Scope

### Primary Questions

1. **Why do tests fail despite Docker running and DATABASE_URL set?**
   - Does the SDK subprocess inherit `os.environ` (where `DATABASE_URL` is set at line 315)?
   - Is the PostgreSQL container ready when tests start? Is `pg_isready` completing?
   - Do the test files use `DATABASE_URL` from the environment, or do they hardcode connection parameters?
   - Is there a port conflict (5433 non-standard port)?

2. **Why doesn't conditional approval fire despite Docker running?**
   - If R1 is deployed, `requires_infrastructure` should now be `[postgresql]` in the task dict
   - If R4 diagnostic logging is deployed, the condition values should be logged
   - Is `_docker_available` returning True? (Docker IS available since containers start)
   - Is `all_gates_passed` True? (Evidence shows `ALL_PASSED=True` at line 312)
   - Which of the 5 conditions is blocking?

3. **What is the actual test error?**
   - The coach_turn_1.json / coach_turn_2.json / coach_turn_3.json files would show the exact test output
   - Is it `ConnectionRefusedError`? `OperationalError`? Something else?
   - Does the error change between turns (suggesting Docker state changes)?

4. **Was R4 (diagnostic logging) deployed?**
   - No `conditional_approval check` line visible in 671 lines of output
   - Was TASK-BOOT-754A implemented? At what log level?
   - Is GUARDKIT_LOG_LEVEL=DEBUG set? (Line 1 shows it IS set)

### Secondary Questions

5. **Does the DATABASE_URL port match the Docker fixture?** The fixture uses port 5433 (non-standard). Does the Player-created code use port 5433 or default 5432?
6. **Is the readiness check blocking?** `until docker exec guardkit-test-pg pg_isready; do sleep 1; done` — does this complete before tests run?
7. **Are the boot-wave2 tasks all implemented?** Verify which tasks were actually deployed vs planned.

## Acceptance Criteria

- [ ] Root cause of test failure identified with evidence (exact error from test output)
- [ ] Conditional approval path traced — identify which condition blocks it (or confirm it fires and something else fails)
- [ ] DATABASE_URL propagation verified: os.environ → SDK subprocess → test process
- [ ] Docker readiness check timing verified
- [ ] Each boot-wave2 task's deployment status verified against evidence
- [ ] Recommendations for fixing the remaining failure

## Source Files

- Evidence: `docs/reviews/autobuild-fixes/db_fails_after_yet_more_fixes.md`
- Bootstrap implementation: `guardkit/orchestrator/environment_bootstrap.py`
- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Feature orchestrator: `guardkit/orchestrator/feature_orchestrator.py`
- AutoBuild orchestrator: `guardkit/orchestrator/autobuild.py`
- Docker fixtures: `guardkit/orchestrator/docker_fixtures.py`
- FEAT-BA28 definition: `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml`
- Previous review report: `.claude/reviews/TASK-REV-C9E5-review-report.md`
- Implementation tasks: `tasks/backlog/boot-wave2/`
