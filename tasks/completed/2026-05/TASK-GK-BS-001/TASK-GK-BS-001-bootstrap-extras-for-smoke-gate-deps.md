---
id: TASK-GK-BS-001
title: Bootstrap install must support extras so smoke-gate test deps are available
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
completed: 2026-05-07T00:00:00Z
completed_location: tasks/completed/2026-05/TASK-GK-BS-001/
previous_state: in_review
state_transition_reason: "All 10 ACs satisfied; ruff clean on new test file + main env_bootstrap; 26/26 new tests pass; only preexisting regressions remain in adjacent suites"
priority: high
priority_band: P1
task_type: feature
parent_review: TASK-REV-PEBR-002
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md
parent_feature_folder: autobuild-feat-pebr-failure-recovery-rev2
related_tasks:
  - TASK-GK-CV-001
  - TASK-GK-PA-002
  - TASK-GK-COACH-001
  - TASK-FRR-PEB-FM-002
  - TASK-REV-PEBR-002
implementation_mode: task-work
wave: 2
complexity: 4
estimated_minutes: 90
dependencies: []
tags:
  - autobuild
  - environment-bootstrap
  - smoke-gates
  - pyproject-extras
  - feat-pebr
  - bug-d
  - P1
test_results:
  status: pass
  coverage: null  # not measured for this task — test suite asserts call-shape, not coverage
  last_run: 2026-05-07T00:00:00Z
  new_tests_added: 26
  new_tests_passing: 26
  preexisting_failures_unchanged: true
---

# Task: Bootstrap install must support extras so smoke-gate test deps are available

## Description

Discovered during FEAT-PEBR autobuild **run-3** (2026-05-07): after
the rev-2 fixes (TASK-GK-CV-001, TASK-GK-PA-002, TASK-GK-COACH-001,
TASK-FRR-PEB-FM-002) all landed and TASK-FRR-PEB-003 + -004 approved
cleanly, the **smoke gate after Wave 4 failed at the module-import
boundary**:

```
✗ Smoke gate failed after wave 4 (exit=1, expected=0)
stderr:
  /Users/richardwoollcott/Projects/appmilla_github/forge/.guardkit/worktrees/
  FEAT-PEBR/.venv/bin/python: No module named pytest
```

**Root cause** (verified end-to-end):

1. `environment_bootstrap._resolve_python_pyproject_install_command`
   ([`guardkit/orchestrator/environment_bootstrap.py:680-728`](../../../guardkit/orchestrator/environment_bootstrap.py))
   hard-codes the install command as `["uv","pip","install","-e","."]`
   (or the pip equivalent). **There is no parameter to pass
   PEP 621 extras.**
2. Forge's `pyproject.toml` declares pytest, pytest-bdd, pytest-asyncio
   under `[project.optional-dependencies].dev` (intentionally — they
   are test-only dependencies, not production runtime deps). Without
   `[dev]` in the install command, those packages are not installed
   in the worktree's `.venv`.
3. The smoke-gate command for FEAT-PEBR is `PYTHONPATH=src python -m
   pytest tests/bdd -m smoke -x` — runs strictly via the worktree
   venv's interpreter ([`autobuild-FEAT-PEBR-failed-run-3.md` line 560](../../../forge/docs/history/autobuild-FEAT-PEBR-failed-run-3.md)).
   No `python -m pytest` fallback to a system pytest — the venv either
   has it or doesn't.
4. Coach's per-task tests passed every turn because Coach has a
   subprocess-fallback (we saw it fire in run-2 log line 211: *"SDK
   test execution failed (error_class=Exception), falling back to
   subprocess."*). The smoke-gate runner has no such fallback.
5. Feature yaml (`.guardkit/features/FEAT-PEBR.yaml`) has a
   `smoke_gates` block but no schema field for `bootstrap_extras`
   or similar — there is no operator-facing knob today.

**Why this is a guardkit bug, not a forge config error**:

Forge's pyproject is correct: pytest belongs under `[dev]`, not
under base `dependencies`. The autobuild orchestrator is the entity
that "knows" pytest is going to be needed (because it loaded the
feature yaml's `smoke_gates` block declaring a `python -m pytest`
command). The bootstrap step must close the gap between
"declared smoke-gate command" and "venv that can run that command".

The classic structural fix is for the bootstrap to install with the
declared test extras whenever smoke gates are configured. Two
plausible designs are detailed under "Implementation notes" below.

**Manual workaround in use today** (not a fix):

```bash
cd <worktree>
uv pip install -e ".[dev]"
```

This is sufficient for `--resume` because the worktree venv is
preserved across resumes, but the install is **lost on `--fresh`**
because bootstrap re-runs without extras. Therefore every `--fresh`
or new feature with smoke gates re-trips this bug.

## Acceptance Criteria

- [ ] **AC-1 — Feature yaml schema accepts `bootstrap_extras`.**
  `feature_loader.load(feature_yaml_path)` accepts an optional
  top-level `bootstrap_extras: List[str]` field, validated as a
  list of strings (each must be a valid PEP 621 extra name —
  `^[A-Za-z0-9._-]+$`). Document the field in the feature yaml
  schema docs.
- [ ] **AC-2 — Bootstrap install honours `bootstrap_extras`.**
  When `bootstrap_extras` is non-empty,
  `_resolve_python_pyproject_install_command` produces:
  - For `uv pip install`: `["uv", "pip", "install", "-e", ".[dev,test]"]`
    (or the equivalent comma-joined extras).
  - For `pip install`: `[sys.executable, "-m", "pip", "install",
    "-e", ".[dev,test]"]`.
  - For `uv sync --frozen`: log a warning and **skip** extras
    (uv.lock is already a frozen lockfile; extras are baked at lock
    time, not at install time). Document this caveat.
- [ ] **AC-3 — Smoke-gate-aware auto-detection (default-on).** When
  `bootstrap_extras` is **not** declared but the feature yaml's
  `smoke_gates.command` contains the literal `pytest` (case-insensitive
  word boundary), the bootstrap auto-includes `[dev]` (the
  PEP-621-conventional name for test extras). If `[dev]` is not
  defined in the project's pyproject, fall back to `[test]`. If
  neither is defined, log a warning naming both candidates and
  proceed without extras (current behaviour). This makes the bug
  self-healing for any feature with a pytest smoke gate, without
  requiring a per-feature config change.
- [ ] **AC-4 — Repro test using FEAT-PEBR run-3 fixture.** Add
  `tests/unit/orchestrator/test_environment_bootstrap_extras.py`
  with class `TestSmokeGateExtraDetection`:
  - Fixture: a feature yaml declaring smoke-gate command
    `python -m pytest tests/bdd -m smoke` and a project
    `pyproject.toml` with
    `[project.optional-dependencies].dev = ["pytest"]`.
  - Expected: `_resolve_python_pyproject_install_command(...)`
    returns a command containing `.[dev]`.
  - Today: returns `.` (no extras) — must FAIL on `main` and PASS
    after the fix.
- [ ] **AC-5 — Explicit `bootstrap_extras` overrides auto-detection.**
  When a feature yaml has both an explicit `bootstrap_extras: [test,
  integration]` AND a pytest smoke command, the explicit list wins
  and `[dev]` is NOT auto-added (operator-declared takes precedence).
- [ ] **AC-6 — Negative test: no extras when neither declared nor
  inferred.** A feature yaml with `bootstrap_extras: []` (or
  unset) AND no smoke gate (or a smoke gate that doesn't reference
  pytest, e.g. `bash scripts/integration.sh`) → install command is
  unchanged from today (no extras).
- [ ] **AC-7 — End-to-end test through the bootstrap call.**
  Mock `subprocess.run` and verify the actual install command line
  matches the expected `[..., "-e", ".[dev]"]` shape when feature
  yaml declares smoke gates.
- [ ] **AC-8 — Regression: existing bootstrap test suite stays
  green.** All tests under
  `tests/orchestrator/test_environment_bootstrap*.py`,
  `tests/unit/test_environment_bootstrap.py` continue to pass.
- [ ] **AC-9 — All modified files pass project-configured lint/format
  checks** (ruff). New test file passes cleanly.
- [ ] **AC-10 — Documentation.** Update the feature yaml schema docs
  (search guardkit for the canonical schema doc — likely
  `docs/internals/feature-yaml-schema.md` or similar) to describe
  `bootstrap_extras`. Note the auto-detection rule (AC-3) and the
  `uv sync --frozen` caveat (AC-2 final bullet).

## Out of Scope

- **`uv sync --frozen` extras at lock time.** When a project has a
  `uv.lock`, extras are baked into the lock — adding extras at
  install time would conflict with the lockfile. AC-2 documents
  this caveat; do not attempt to override the lock.
- **Stack auto-detection beyond Python.** Node/Go/Rust analogues
  (e.g. dev dependencies in `package.json`) can be a follow-up;
  scope this task to Python pyproject.
- **Resolving the smoke-gate failure for FEAT-PEBR run-3.** That is
  unblocked manually by `uv pip install -e ".[dev]"` in the
  preserved worktree. This task only addresses the structural gap
  for future runs and other features.

## Files to Create

- `tests/unit/orchestrator/test_environment_bootstrap_extras.py`
- `tests/fixtures/bootstrap_extras_feature/` (small feature yaml +
  pyproject pair for AC-4 / AC-5 fixtures)

## Files to Modify

- `guardkit/orchestrator/environment_bootstrap.py` (the
  `_resolve_python_pyproject_install_command` function at lines
  680-728; add an `extras: Sequence[str]` parameter; update the
  command builder to append `.[ext1,ext2]` when non-empty)
- `guardkit/orchestrator/feature_orchestrator.py` (or wherever the
  feature yaml is loaded and passed to bootstrap) — thread
  `feature.bootstrap_extras` through to the bootstrap call site.
- `guardkit/orchestrator/feature_loader.py` (or equivalent) — accept
  and validate the new `bootstrap_extras` field; implement the AC-3
  auto-detection rule.
- A schema doc — search for the canonical feature-yaml schema doc
  in `docs/` and update.

## Implementation notes

### Recommended approach

**Step 1: Plumb the field**

Add to the feature yaml dataclass / pydantic model:

```python
bootstrap_extras: List[str] = field(default_factory=list)
```

Validate in the loader:

```python
if "bootstrap_extras" in raw:
    extras = raw["bootstrap_extras"]
    if not isinstance(extras, list):
        raise FeatureValidationError("bootstrap_extras must be a list")
    for e in extras:
        if not re.match(r"^[A-Za-z0-9._-]+$", e):
            raise FeatureValidationError(f"invalid extra name: {e!r}")
    feature.bootstrap_extras = extras
```

**Step 2: Auto-detect from smoke-gate command (AC-3)**

In `feature_loader` (post-validation):

```python
if not feature.bootstrap_extras and feature.smoke_gates:
    cmd = feature.smoke_gates.get("command", "")
    if re.search(r"\bpytest\b", cmd, re.IGNORECASE):
        # Probe pyproject for the canonical extra name
        pyproject = _load_pyproject(feature.project_root)
        extras = pyproject.get("project", {}).get("optional-dependencies", {})
        for candidate in ("dev", "test"):
            if candidate in extras:
                feature.bootstrap_extras = [candidate]
                logger.info(
                    "Auto-detected smoke-gate pytest dep; "
                    "adding [%s] to bootstrap_extras", candidate,
                )
                break
        else:
            logger.warning(
                "Smoke gate references pytest but pyproject declares "
                "neither [dev] nor [test] extras. Smoke gate may fail "
                "with 'No module named pytest'. Either add a [dev] or "
                "[test] extra, or set bootstrap_extras: [yourname] "
                "explicitly."
            )
```

**Step 3: Build the command with extras**

In `_resolve_python_pyproject_install_command(directory, pyproject_path,
extras: Sequence[str] = ())`:

```python
target = "."
if extras:
    target = f".[{','.join(sorted(set(extras)))}]"

if has_uv_sources:
    return ["uv", "pip", "install", "-e", target]

if has_uv_lock and uv_available:
    if extras:
        logger.warning(
            "%s declares uv.lock; extras=%s ignored at install time. "
            "Add extras at lock time via `uv lock --extra %s`.",
            directory, list(extras), ",".join(sorted(set(extras))),
        )
    return ["uv", "sync", "--frozen"]

# pip path:
return [sys.executable, "-m", "pip", "install", "-e", target]
```

**Step 4: Thread through the call chain**

Find the caller of `_resolve_python_pyproject_install_command` (likely
in `ProjectEnvironmentDetector` or `_run_install`) and add an
`extras` parameter that defaults to `()`. Plumb up to wherever the
feature object is available.

### Why feature-yaml-only and not auto-from-pyproject

It's tempting to *always* install all `[project.optional-dependencies]`,
but that would:

1. Pull in provider integrations the user hasn't asked for (e.g.
   forge's `[providers]` extra installs `langchain-openai` and
   `langchain-google-genai` by default — that's intentional opt-in).
2. Inflate install time and disk for features that don't need them.
3. Mask declaration errors (e.g. test deps in `[providers]`).

The smoke-gate-driven auto-detection (AC-3) is conservative: it only
fires when there's evidence the test deps are needed.

### Regression risk

- New `bootstrap_extras` field is additive; existing feature yamls
  without the field behave unchanged unless AC-3 auto-detection
  fires. Tests for AC-6 (negative case) cover this.
- Auto-detection (AC-3) could surprise operators on existing features
  with a pytest smoke gate. Mitigation: log the auto-add at INFO
  level so it's visible in the run log; existing fixtures must
  declare the expected install command in the test (AC-4 / AC-7
  already do this).
- `uv sync --frozen` interaction is non-trivial (extras are
  lock-baked). AC-2's warning + skip is the safe default; document
  the lock-time alternative.

## Test requirements

- Unit tests in `test_environment_bootstrap_extras.py` per ACs 4-7.
- Mock-based subprocess test for AC-7 (verify command line shape).
- Negative-case fixture for AC-6.
- Regression suite for existing bootstrap tests must stay green
  (AC-8).

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/unit/orchestrator/test_environment_bootstrap_extras.py -x -v
PYTHONPATH=. python -m pytest tests/orchestrator/ tests/unit/test_environment_bootstrap.py -x
ruff check guardkit/orchestrator/environment_bootstrap.py guardkit/orchestrator/feature_loader.py tests/unit/orchestrator/test_environment_bootstrap_extras.py
```
