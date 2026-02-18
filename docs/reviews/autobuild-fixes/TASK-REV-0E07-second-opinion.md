# TASK-REV-0E07 Second Opinion: Definitive Root Cause Analysis

**Date:** 2026-02-18  
**Reviewed by:** Claude (Second Opinion)  
**Subject:** TASK-DB-003 UNRECOVERABLE_STALL — psycopg2 ModuleNotFoundError  
**Verdict:** Review is partially correct on symptom identification but **misdiagnoses the root cause** and proposes a fix that **cannot work** as specified.

---

## Executive Summary

TASK-DB-003 stalled at turn 6 because the Coach's independent test verification consistently fails with `ModuleNotFoundError: No module named 'psycopg2'`. The review correctly identified that the error occurs at test collection time when SQLAlchemy attempts to load a database driver. However, the review incorrectly concluded that `asyncpg` is not installed in the test environment and proposed adding a `bootstrap_packages` field to the feature YAML — a field that does not exist in the schema.

**The actual root cause is a dialect mismatch in `docker_fixtures.py`.** The Coach's infrastructure setup exports `DATABASE_URL=postgresql://...` without the `+asyncpg` dialect suffix. When SQLAlchemy's `create_async_engine()` receives this URL at module import time, it attempts to load the `psycopg2` dialect (the default for plain `postgresql://` URLs) rather than `asyncpg`, causing the import failure.

---

## Evidence Chain

### 1. Bootstrap Successfully Installs asyncpg

From the AutoBuild logs:

```
⚙ Bootstrapping environment: python
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /usr/local/bin/python3 -m pip install asyncpg>=0.29.0
✓ Environment bootstrapped: python
```

Bootstrap runs before Wave 2 begins. `asyncpg` is installed to `/usr/local/bin/python3` — the same interpreter used by the Coach for test execution. **The review's premise that asyncpg is missing from the environment is incorrect.**

### 2. Coach Uses Correct Python Interpreter

From `coach_validator.py` lines 1280–1290:

```python
if test_cmd.startswith("pytest"):
    parts = test_cmd.split()
    cmd = [sys.executable, "-m", "pytest"] + parts[1:]
    result = subprocess.run(cmd, ...)
```

The Coach invokes `sys.executable -m pytest`, which runs pytest under the same Python that has asyncpg installed. **There is no interpreter mismatch** for the test subprocess itself.

### 3. The Smoking Gun: DATABASE_URL Without Dialect

From `docker_fixtures.py` line 26:

```python
DOCKER_FIXTURES: Dict[str, Dict[str, object]] = {
    "postgresql": {
        ...
        "env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},
    },
}
```

From the AutoBuild logs:

```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Set DATABASE_URL=postgresql://postgres:test@localhost:5433/test
```

The URL uses `postgresql://` — not `postgresql+asyncpg://`.

### 4. SQLAlchemy Dialect Resolution Behaviour

When `create_async_engine("postgresql://...")` is called:

1. SQLAlchemy parses the URL scheme `postgresql`
2. The default driver for `postgresql` is `psycopg2` (synchronous)
3. SQLAlchemy attempts to import `psycopg2`
4. `psycopg2` is not installed → `ModuleNotFoundError`
5. **It never attempts `asyncpg`** because the URL doesn't specify `+asyncpg`

The correct URL for async SQLAlchemy is `postgresql+asyncpg://...`, which explicitly tells SQLAlchemy to use the asyncpg driver.

### 5. Error Trace Confirms Dialect Issue

From the Coach's test output:

```
ModuleNotFoundError: No module named 'psycopg2'
```

This error occurs at collection time (~0.7–0.9s) when pytest imports the application module, which triggers `create_async_engine(settings.DATABASE_URL)` at module scope. The URL from the environment is `postgresql://...`, so SQLAlchemy tries psycopg2.

---

## Why the Review's Proposed Fix Cannot Work

The review recommends:

> Add `asyncpg` and `aiosqlite` to FEAT-BA28 bootstrap packages:
> ```yaml
> bootstrap_packages:
>   - asyncpg>=0.29.0
>   - aiosqlite>=0.19.0
> ```

This fails for three independent reasons:

1. **`bootstrap_packages` does not exist** in the feature YAML schema. The schema supports fields like `name`, `description`, `stack`, `infrastructure`, `acceptance_criteria`, etc. — but not `bootstrap_packages`. Adding this field would be silently ignored.

2. **asyncpg is already installed.** The existing bootstrap mechanism (via `ProjectEnvironmentDetector` + `EnvironmentBootstrapper`) correctly detects `asyncpg>=0.29.0` from the generated `pyproject.toml` and installs it before Wave 2 begins. Installing it again would be a no-op.

3. **The problem is not missing packages — it's the wrong URL dialect.** Even with asyncpg installed correctly, SQLAlchemy will not use it unless the connection URL specifies `+asyncpg` as the dialect.

---

## Correct Fix

### Primary Fix: Update `docker_fixtures.py`

**File:** `guardkit/orchestrator/docker_fixtures.py`  
**Change:** Update the PostgreSQL `env_export` to include the `+asyncpg` dialect suffix.

```python
# Before (line 26)
"env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},

# After
"env_export": {"DATABASE_URL": "postgresql+asyncpg://postgres:test@localhost:5433/test"},
```

### Test Updates Required

**File:** `tests/unit/test_docker_fixtures.py`

Two assertions need updating:

```python
# test_get_env_exports_postgresql_contains_database_url (line ~105)
# Before:
assert exports["DATABASE_URL"].startswith("postgresql://")
# After:
assert exports["DATABASE_URL"].startswith("postgresql+asyncpg://")

# test_start_infrastructure_containers_sets_env_vars (line ~140)
# Before:
assert os.environ["DATABASE_URL"].startswith("postgresql://")
# After:
assert os.environ["DATABASE_URL"].startswith("postgresql+asyncpg://")
```

### Risk Assessment

**Risk:** Future synchronous PostgreSQL tasks (using `psycopg2` or `psycopg`) would fail if they rely on the same `DATABASE_URL` environment variable, since `postgresql+asyncpg://` forces the asyncpg driver.

**Mitigation:** All current AutoBuild templates use async SQLAlchemy with asyncpg. If synchronous support is needed later, add a `postgresql-sync` fixture variant:

```python
"postgresql-sync": {
    ...
    "env_export": {"DATABASE_URL": "postgresql://postgres:test@localhost:5433/test"},
},
```

### Alternative: Dialect-Agnostic Fix

A more defensive approach would have the Coach detect the Player's database driver from the generated `pyproject.toml` and set the dialect suffix accordingly. This is more robust but adds complexity that isn't justified until synchronous PostgreSQL tasks exist. The simple fix above is correct for the current state.

---

## Prior Fix Tasks Assessment

| Task | Status | Effective? |
|------|--------|-----------|
| TASK-FIX-A7F1 | ✅ Implemented | Yes — removed psycopg2 from `_KNOWN_SERVICE_CLIENT_LIBS` |
| TASK-FIX-AE7E | ✅ Implemented | Partially — accumulates peak criteria for stall detection only |
| TASK-FIX-70F3 | ✅ Implemented | Yes — cumulative diff fallback works |
| TASK-FIX-4415 | ⚠️ Implemented | No — tells Player to "remove psycopg2 import" but Player has no such import |

None of these address the actual root cause. TASK-FIX-4415 is particularly misleading — it blames the Player for an import that doesn't exist in Player code. The import attempt comes from SQLAlchemy's internal dialect resolution, triggered by the Coach's `DATABASE_URL` configuration.

---

## Recommendations

1. **Implement the `docker_fixtures.py` fix immediately.** This is a one-line change plus two test assertion updates. It unblocks all async PostgreSQL AutoBuild tasks, not just TASK-DB-003.

2. **Re-run TASK-DB-003 after the fix** to verify the stall is resolved. The Player's implementation code was correct — only the test environment was misconfigured.

3. **Close TASK-FIX-4415 as ineffective.** Its guidance to "remove psycopg2 import" is based on a misdiagnosis and cannot help the Player.

4. **Consider adding dialect detection** to the Coach's infrastructure setup as a future enhancement, allowing automatic selection of `+asyncpg`, `+psycopg`, or plain `postgresql://` based on the project's declared dependencies.
