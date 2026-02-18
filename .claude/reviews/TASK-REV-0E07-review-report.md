# Review Report: TASK-REV-0E07 (Revision 2)

**Mode**: Architectural Review
**Depth**: Comprehensive
**Date**: 2026-02-18
**Reviewer**: Claude (architectural-reviewer + second opinion)
**Evidence**: `docs/reviews/autobuild-fixes/db_another_fail.md` + all 6 coach/player turn JSON artifacts + `docker_fixtures.py` source

---

## Executive Summary

After reading all 6 coach turn JSON files and verifying the evidence chain, the root cause of the UNRECOVERABLE_STALL is **definitively identified**:

> **`docker_fixtures.py` exports `DATABASE_URL=postgresql://...` without the `+asyncpg` dialect suffix. When SQLAlchemy's `create_async_engine()` receives this URL at module import time during pytest collection, it defaults to loading `psycopg2` (the synchronous PostgreSQL driver), which is not installed. The fix is a single-line change in `docker_fixtures.py`.**

Initial review revision (Revision 1) correctly identified the error symptom and collection-time nature, but misdiagnosed the root cause as "asyncpg not installed in the subprocess environment." This was wrong: the bootstrap logs show asyncpg IS installed before Wave 2, and the Coach subprocess uses the same Python (`/usr/local/bin/python3 -m pytest`). The correct cause is a dialect mismatch in the URL exported by the Docker fixture.

**Fix**: Change one line in `guardkit/orchestrator/docker_fixtures.py` and update two test assertions. This unblocks all async PostgreSQL AutoBuild tasks.

---

## Section 1: Fix Task Status Verification

### TASK-FIX-A7F1 — Remove psycopg2 from `_KNOWN_SERVICE_CLIENT_LIBS`
**Status: WORKING ✅**

`_KNOWN_SERVICE_CLIENT_LIBS` contains `["asyncpg", "pymongo", "redis", "psycopg"]` — `psycopg2` is correctly absent. Classification correctly returns `("code", "high")` for the `ModuleNotFoundError: No module named 'psycopg2'` error.

**Effect**: Correct classification, but unhelpful feedback because the classification blames code when the actual cause is an environment configuration bug in GuardKit itself (docker_fixtures.py).

### TASK-FIX-AE7E — Cross-turn criteria memory
**Status: IMPLEMENTED, SCOPE-LIMITED ✅**

Confirmed in `autobuild.py:1664–1666`: accumulates `_max_criteria_passed` for stall detection only. Not a fix for criteria staying at 0/6 — criteria verification is skipped entirely when independent tests fail with `("code", "high")`.

**Why criteria remain 0/6**: Coach skips `_validate_requirements()` when the independent test fails. Since tests fail every turn, criteria are never evaluated.

### TASK-FIX-70F3 — Accumulate test files across turns
**Status: WORKING ✅**

Turns 2, 5, 6: cumulative diff fallback finds 2 test files. Turns 1, 4: primary path finds 1 file from `task_work_results`. Inconsistency is benign (see Section 4). Fix confirmed working.

### TASK-FIX-4415 — Specific feedback for psycopg2 in asyncpg projects
**Status: IMPLEMENTED BUT COUNTERPRODUCTIVE ⚠️**

The feedback message "Remove `import psycopg2` from your code" is wrong for this scenario. The Player has no `import psycopg2` statement. The error originates from SQLAlchemy's internal dialect resolution triggered by a URL exported by GuardKit itself. The message actively misdirects the Player, causing 6 turns of fruitless searching.

---

## Section 2: Actual Test Error (Definitive)

From all 6 coach turn JSON files — error is identical across every turn:

```
==================================== ERRORS ====================================
__________________ ERROR collecting tests/users/test_users.py __________________
ModuleNotFoundError: No module named 'psycopg2'
ERROR tests/users/test_users.py
1 error in 0.32s
```

**Duration**: ~0.7–0.9 seconds — collection-time failure, zero test execution.

### Root Cause Evidence Chain

**Step 1**: Bootstrap installs asyncpg before Wave 2:
```
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /usr/local/bin/python3 -m pip install asyncpg>=0.29.0
✓ Environment bootstrapped: python
```
asyncpg IS installed in `/usr/local/bin/python3`. This disproves the Revision 1 hypothesis.

**Step 2**: Coach subprocess uses the same Python:
```python
# coach_validator.py
cmd = [sys.executable, "-m", "pytest"] + parts[1:]
```
No interpreter mismatch.

**Step 3**: The smoking gun — `docker_fixtures.py` line 30:
```python
"env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},
```

**Step 4**: Coach sets this URL as environment variable:
```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Set DATABASE_URL=postgresql://postgres:test@localhost:5433/test
```

**Step 5**: When pytest collects `tests/users/test_users.py`, it loads `tests/conftest.py` which imports `src.main` → `src.db.session`. The module-level call is:
```python
engine = create_async_engine(str(settings.DATABASE_URL), ...)
```

`settings.DATABASE_URL` now reads `postgresql://...` from `os.environ` (set by the Coach). SQLAlchemy's dialect resolution for `postgresql://` (without `+asyncpg`) defaults to `psycopg2`. `psycopg2` is not installed → `ModuleNotFoundError`.

**Summary**: asyncpg is installed, the right Python is used, and the test is correctly written. GuardKit's own infrastructure setup injects the wrong URL scheme, causing SQLAlchemy to load the wrong driver.

---

## Section 3: Turn 3 Coverage Failure

Turn 3: `coverage_met=False`, `line_coverage=47.0`, `branch_coverage=0` — quality gate failed before independent test verification.

**Cause**: Perspective reset at turn 3 cleared the Player's state. The Player rebuilt code without sufficient test coverage. The coverage gate failed first, so the Coach returned feedback before reaching independent tests. This is a one-off from the perspective reset, not systemic.

---

## Section 4: Inconsistent Test File Detection (1 vs 2 Files)

| Turn | Files | Path |
|------|-------|------|
| 1 | 1 (`tests/users/test_users.py`) | `task_work_results` primary |
| 2 | 2 (+ `tests/db/test_migrations.py`) | Cumulative diff fallback |
| 3 | N/A | Coverage gate failed first |
| 4 | 1 | `task_work_results` primary |
| 5 | 2 | Cumulative diff fallback |
| 6 | 2 | Cumulative diff fallback |

On turns where the Player didn't modify a test file, the cumulative diff fallback finds both test files in the task history. Both commands produce the same error (`test_users.py` fails at collection), so the inconsistency has no effect on the outcome. Fix TASK-FIX-70F3 is working correctly.

---

## Section 5: Why Stall Took 6 Turns (Not 4)

Stall threshold is 3 consecutive identical feedback signatures.

- Turn 1: psycopg2 feedback (sig A) — 1st
- Turn 2: psycopg2 feedback (sig A) — 2nd
- Turn 3: coverage feedback (sig B) — **resets counter**
- Turn 4: psycopg2 feedback (sig A) — 1st again
- Turn 5: psycopg2 feedback (sig A) — 2nd
- Turn 6: psycopg2 feedback (sig A) — 3rd → **UNRECOVERABLE_STALL**

Turn 3's different failure broke the streak, requiring 6 turns instead of 4. Correct stall detection behavior.

---

## Definitive Fix

### Fix 1 — `docker_fixtures.py` (CRITICAL, one line)

**File**: `guardkit/orchestrator/docker_fixtures.py` line 30

```python
# Before:
"env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},

# After:
"env_export": {"DATABASE_URL": "postgresql+asyncpg://postgres:test@localhost:5433/test"},
```

This is the complete fix. No YAML schema changes, no environment changes, no Player code changes.

### Fix 2 — `tests/unit/test_docker_fixtures.py` (2 assertions)

```python
# test_get_env_exports_postgresql_contains_database_url (~line 144):
assert exports["DATABASE_URL"].startswith("postgresql+asyncpg://")

# test_start_infrastructure_containers_sets_env_vars (~line 303):
assert os.environ["DATABASE_URL"].startswith("postgresql+asyncpg://")
```

### Risk Assessment

**Risk**: Future synchronous PostgreSQL tasks (`psycopg2`/`psycopg` driver) would need a different URL. **Mitigation**: Add a `postgresql-sync` fixture variant when needed. All current templates use async SQLAlchemy.

### Future Enhancement (Optional)

Auto-detect the correct dialect from `pyproject.toml`/`requirements.txt` dependencies and set `+asyncpg` or `+psycopg` accordingly. Not urgent — all current templates use asyncpg.

---

## Acceptance Criteria Verification

- [x] Actual test error identified: `ModuleNotFoundError: No module named 'psycopg2'` at collection time — SQLAlchemy tries psycopg2 because `DATABASE_URL` lacks `+asyncpg` dialect
- [x] Implementation status of all four fix tasks verified (Section 1)
- [x] Root cause of `coverage threshold not met` on turn 3: perspective reset → Player wrote insufficient tests
- [x] Root cause of inconsistent test file detection: primary vs cumulative diff path; benign
- [x] Root cause of criteria 0/6: Coach skips criteria verification when independent tests fail with `("code", "high")`; not a regression — expected behavior
- [x] Definitive fix: change `postgresql://` to `postgresql+asyncpg://` in `docker_fixtures.py`
- [x] Prior fix task status documented

---

## Report Metadata

```yaml
report_path: .claude/reviews/TASK-REV-0E07-review-report.md
task_id: TASK-REV-0E07
mode: architectural
depth: comprehensive
revision: 2
findings_count: 7
recommendations_count: 3
decision: implement
primary_fix_file: guardkit/orchestrator/docker_fixtures.py
completed_at: 2026-02-18T18:30:00Z
```
