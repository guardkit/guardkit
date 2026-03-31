---
id: TASK-REV-4D57
title: Analyse DB task outcome after infra-aware AutoBuild changes
status: review_complete
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, player-coach, infrastructure-failure, infra-aware, review]
task_type: review
complexity: 4
parent_review: TASK-REV-BA4B
related_tasks: [TASK-INFR-6D4F, TASK-INFR-1670, TASK-INFR-5922, TASK-INFR-24DB]
review_results:
  mode: architectural
  depth: comprehensive
  revision: 3
  score: 30
  findings_count: 6
  recommendations_count: 7
  decision: implement
  root_cause: "AutoBuild has no environment bootstrap phase — _setup_phase() creates worktree but never installs project dependencies. No inter-wave hook to detect new manifests."
  previous_root_cause_corrected: "SDK subprocess environment mismatch was WRONG — SDK passes {**os.environ} correctly"
  report_path: .claude/reviews/TASK-REV-4D57-review-report.md
  completed_at: 2026-02-17T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse DB task outcome after infra-aware AutoBuild changes

## Description

Following the implementation of the infra-aware AutoBuild feature (tasks/backlog/infra-aware-autobuild/), a re-run of FEAT-BA28 (PostgreSQL Database Integration) was performed with `--max-turns 10 --fresh`. This review analyses the output to determine:

1. Which FEAT-INFRA changes are working correctly
2. Why TASK-DB-003 still stalls (it does — `UNRECOVERABLE_STALL` after 3 turns)
3. What gaps remain and what needs to be fixed

## Evidence

Full autobuild output: `docs/reviews/autobuild-fixes/db_after_infra_aware_changes.md`

### What worked

- **TASK-DB-001** (scaffolding): APPROVED in 1 turn (unchanged from before — scaffolding skips tests)
- **TASK-DB-002** (scaffolding): APPROVED in 1 turn (parallel with TASK-DB-003)
- **Tiered classification**: The log shows `classification=infrastructure, confidence=ambiguous` — the tiered pattern split (TASK-INFR-1670) is working. The classification correctly distinguishes high-confidence from ambiguous patterns.

### What failed

- **TASK-DB-003**: Still `UNRECOVERABLE_STALL` after 3 turns, identical to the pre-fix behaviour
- **Classification returns `ambiguous`**, not `high` — this means the test failure involves `ImportError`/`ModuleNotFoundError` (for psycopg2 or similar), not `ConnectionRefusedError`
- **Conditional approval (TASK-INFR-24DB) did not trigger** because it requires `confidence=high`, and the classification returned `ambiguous`
- **Docker test fixtures (TASK-INFR-5922) did not activate** — Docker Desktop was confirmed running on the host machine, yet no Docker-related log lines are visible in the output. This means the fixture code either wasn't wired in, wasn't triggered, or `requires_infrastructure` wasn't propagated correctly

### Key log lines

- Line 359: `WARNING: Independent test verification failed for TASK-DB-003 (classification=infrastructure, confidence=ambiguous)`
- Line 421: Same pattern repeats turn 2 — `confidence=ambiguous`
- Line 480: Same pattern repeats turn 3 — `confidence=ambiguous`
- Line 491: `ERROR: Feedback stall detected for TASK-DB-003: identical feedback with no criteria progress`
- Line 507: `Status: UNRECOVERABLE_STALL`

### Pattern

```
Turn 1: Player implements → Coach tests → fails (infrastructure, ambiguous) → feedback
Turn 2: Player adjusts   → Coach tests → fails (infrastructure, ambiguous) → feedback
Turn 3: Player adjusts   → Coach tests → fails (infrastructure, ambiguous) → STALL DETECTED
```

## Acceptance Criteria

- [ ] Determine the actual test failure output for TASK-DB-003 — is it `ModuleNotFoundError: No module named 'psycopg2'` or `ConnectionRefusedError`?
- [ ] If `ModuleNotFoundError`, analyse why the psycopg2/asyncpg pattern in `_INFRA_HIGH_CONFIDENCE` didn't match (the string "psycopg2" IS in the high-confidence list — did the actual error message use a different format?)
- [ ] Check whether `requires_infrastructure` was declared in the FEAT-BA28 feature YAML and propagated to TASK-DB-003 frontmatter
- [ ] Check whether Docker test fixtures (TASK-INFR-5922) were attempted — Docker Desktop was confirmed running, so determine why fixtures weren't activated. Did the execution protocol include the infrastructure setup section?
- [ ] Determine why Docker fixtures were not used despite Docker being available — was the fixture code not wired into the Coach validator? Was `requires_infrastructure` not propagated to the task dict? Was the Docker availability check not implemented?
- [ ] Assess whether the conditional approval fallback (TASK-INFR-24DB) logic is correctly wired — is `_docker_available` being set in the task dict?
- [ ] Recommend specific fixes for each gap identified
- [ ] Determine if `psycopg2` / `asyncpg` patterns should be moved to high-confidence (they currently ARE in the list — so why is confidence `ambiguous`?)

## Review Focus Areas

### 1. Classification confidence discrepancy

The `_INFRA_HIGH_CONFIDENCE` list includes `"psycopg2"`, `"psycopg"`, and `"asyncpg"`. If the test failure output contains `ModuleNotFoundError: No module named 'psycopg2'`, the high-confidence check should match on `"psycopg2"` BEFORE the ambiguous check matches on `"ModuleNotFoundError"`.

Possible explanations:
- The classification code checks ambiguous patterns first (ordering bug)
- The actual error message doesn't contain any high-confidence pattern
- The error message uses a different module name (e.g., `asyncpg` vs `psycopg2`)

### 2. Docker test fixture activation

**Docker Desktop was confirmed running** on the host machine during this test run. Despite this, no Docker-related log lines appear in the output. The investigation should focus on the wiring gaps:
- Was `requires_infrastructure` declared in FEAT-BA28.yaml and propagated to TASK-DB-003 frontmatter?
- Did the Coach validator code include the Docker availability check (`shutil.which("docker")` or similar)?
- Did the Coach attempt to start containers before running tests? If not, is `run_independent_tests()` missing the container lifecycle code?
- Did the Player receive infrastructure setup instructions in the execution protocol?
- Was the `_docker_available` flag set correctly in the task dict passed to CoachValidator?

### 3. Conditional approval wiring

Since Docker Desktop WAS available, the conditional approval fallback (designed for when Docker is unavailable) should NOT have been the active path. The primary path — Docker test fixtures — should have activated instead. The conditional approval fallback would only be relevant if Docker fixture startup failed at runtime.

However, since neither path activated, the investigation should determine:
- Did the Docker fixture path fail silently?
- Or was it never reached because `requires_infrastructure` wasn't in the task dict?
- The `ambiguous` confidence classification is a secondary issue — if Docker fixtures had worked, classification confidence wouldn't matter (tests would pass against real PostgreSQL)

### 4. Player behaviour across turns

Note the Player's output degradation:
- Turn 1: 12 files created, 3 modified, 1 test passing
- Turn 2: 4 files created, 3 modified, 0 tests passing
- Turn 3: 2 files created, 4 modified, 0 tests passing

The Player created a `docker-compose.yml` in TASK-DB-001 (line 100). Did the Player attempt to use Docker in TASK-DB-003? Why did tests go from 1 passing to 0?

## Key Files to Review

### Primary
- `docs/reviews/autobuild-fixes/db_after_infra_aware_changes.md` - Full autobuild output
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Classification logic, conditional approval path
- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` - Check for infrastructure setup section

### Feature YAML (in guardkit-examples/fastapi)
- `.guardkit/features/FEAT-BA28.yaml` - Check for `requires_infrastructure` on TASK-DB-003

### Coach decisions (in worktree, if still available)
- `.guardkit/autobuild/TASK-DB-003/coach_turn_1.json` - Full Coach decision including raw test output
- `.guardkit/autobuild/TASK-DB-003/coach_turn_2.json`
- `.guardkit/autobuild/TASK-DB-003/coach_turn_3.json`

## Implementation Notes

Review task — analysis and gap identification only. The goal is to understand exactly why TASK-DB-003 still fails after the FEAT-INFRA implementation and produce targeted fix recommendations.

There are likely two independent issues:

1. **Primary (Docker fixtures not activating)**: Docker Desktop was running but no containers were started. This suggests the Docker fixture code (TASK-INFR-5922) either wasn't fully wired into the Coach validator, or `requires_infrastructure` wasn't propagated through the task dict, so the fixture path was never reached.

2. **Secondary (Classification confidence)**: The `_classify_test_failure` method may be checking ambiguous patterns before high-confidence patterns (ordering bug), or the actual test output doesn't contain any high-confidence pattern string. This is relevant for the conditional approval fallback but is secondary to fixing the Docker fixture path.

## Test Execution Log
[Automatically populated by /task-work]
