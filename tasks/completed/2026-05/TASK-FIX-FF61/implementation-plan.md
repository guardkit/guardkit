# Implementation Plan — TASK-FIX-FF61

**Mode:** TDD
**Intensity:** strict
**Complexity:** 7/10
**Generated:** 2026-05-06

## Goal

Make the autobuild bootstrap step physically incapable of writing the
worktree's editable `_editable_impl_*.pth` line into the *parent*
project's `.venv`, by:

1. Eagerly creating a worktree-local `.venv` before any Python install
   subprocess runs.
2. Stripping inherited `VIRTUAL_ENV` and exporting a worktree-local one
   on every Python install subprocess (first try AND retry, all three
   install paths).
3. Remapping pip-path `cmd[0]` to the worktree venv's python interpreter
   (existing logic at `environment_bootstrap.py:1567-1568`, exercised by
   eager venv creation).
4. Replacing the false-success block at `environment_bootstrap.py:1239-1249`
   with an invariant raise (`BootstrapEnvironmentLeakError`).
5. Updating the regression-encoding test invariant
   (`test_preexisting_venv_succeeds_without_retry`) and sibling tests to
   assert env shape, not just exit code.

## Files To Change

### Primary

| File | Change |
|---|---|
| `guardkit/orchestrator/environment_bootstrap.py` | **MODIFY**: add `BootstrapEnvironmentLeakError`, `_ensure_worktree_venv`, `_isolated_env`; eager venv creation in `bootstrap()`; env override in `_run_install` and `_run_single_command`; replace false-success block with invariant raise; update `__all__` exports. |

### Tests (new)

| File | Change |
|---|---|
| `tests/unit/test_environment_bootstrap_ffc6.py` | **NEW**: AC-009..AC-012 regression suite. ~250 LOC. |

### Tests (existing — env-shape audit)

| File | Change |
|---|---|
| `tests/unit/test_environment_bootstrap_uv_venv.py` | **MODIFY**: AC-013 — update `test_preexisting_venv_succeeds_without_retry` to assert env shape; AC-014 — add `env=` shape assertions to `test_run_install_*` tests in this file. |
| `tests/unit/test_environment_bootstrap.py` | **MODIFY**: AC-014 — add `env=` shape assertions to `test_run_install_*` and `test_bootstrap_*` tests for Python manifests; AC-015..AC-018 don't-break audit (PEP 668, AB60, FD32, F09A2). |
| `tests/orchestrator/test_coach_verification.py` (or sibling) | **NEW or MODIFY**: AC-019 — assert `_resolve_venv_python` accepts explicit `<worktree>/.venv/bin/python`. |

## Phase Order (TDD)

### Wave A — RED (failing tests)

1. **AC-007** — Add `BootstrapEnvironmentLeakError` exception class to
   `environment_bootstrap.py` (no-op without raise; needed for tests to
   import). One-liner.
2. Create `tests/unit/test_environment_bootstrap_ffc6.py`:
   - **AC-009** `test_no_leak_when_VIRTUAL_ENV_inherited` (uv pip path).
   - **AC-010** `test_no_leak_when_sys_executable_is_parent_venv` (pip path).
   - **AC-011** `test_no_leak_when_uv_sync_path` (uv sync path).
   - **AC-012** `test_invariant_fails_when_install_lands_outside_worktree`.
3. **AC-013** Update `test_preexisting_venv_succeeds_without_retry` to
   assert env shape; remove the `mock_run.call_count == 1` assertion if
   it conflicts with eager venv creation (replace with no-leak check).
4. **AC-014** Audit pass — add `env=` shape assertions to sibling
   `test_run_install_*` and `test_bootstrap_*` tests for Python
   manifests.
5. **AC-019** Add new test in `test_coach_verification.py` asserting
   that `_resolve_venv_python` returns `<worktree>/.venv/bin/python`
   when passed as explicit param and the file exists.
6. **AC-020** Add a fixture/test simulating A7B6's extras config and
   asserting isolation holds (extras land in worktree venv).

**Verify**: All new and updated tests FAIL against current `main`.

### Wave B — GREEN (implementation)

7. **AC-001** Add `_ensure_worktree_venv(worktree: Path) -> Path`
   helper. Prefer `uv venv` if uv on PATH; fall back to
   `python -m venv`. Idempotent. Returns the python interpreter path.
8. **AC-002** Add `_isolated_env(worktree_venv: Path) -> Dict[str, str]`
   helper. Strip inherited `VIRTUAL_ENV` first, then set
   `VIRTUAL_ENV=str(worktree_venv)` and prepend `<worktree_venv>/bin`
   to `PATH`.
9. **AC-003** In `bootstrap()`, call `_ensure_worktree_venv(self._root)`
   eagerly when `any(m.stack == "python" for m in manifests)`, BEFORE
   the install loop runs. Cache result on `self._venv_python`. Place
   AFTER the saved-state recovery check at line 1146-1154 and BEFORE
   the install loop at line 1156.
10. **AC-004** In `_run_install`, pass
    `env=self._isolated_env(self._venv_python.parent.parent)` to **every**
    `subprocess.run` for Python install commands (`manifest.stack ==
    "python"` AND `self._venv_python is not None`). Apply to first-try
    call (line 1577-1584) AND PEP 668 retry (line 1608-1614). The
    AB60 retry at line 1664-1685 already does the right thing — preserve
    its env construction but route through `_isolated_env` for
    consistency. Non-Python commands inherit env unchanged.
11. **AC-004** (cont) In `_run_single_command`, same pattern: when
    `cmd[0] == sys.executable` (the only Python signal in this method;
    see line 257), pass `env=self._isolated_env(...)`.
12. **AC-005** No code change needed — the existing remap at line
    1567-1568 already swaps `cmd[0]` to `self._venv_python` when set.
    AC-003 sets it eagerly so the remap covers the first-try call too.
13. **AC-006** Replace false-success block at line 1239-1249 with
    invariant raise (`BootstrapEnvironmentLeakError`). Spec:
    ```python
    if (
        overall_success
        and any(m.stack == "python" for m in manifests)
        and self._venv_python is not None
        and not str(self._venv_python).startswith(str(self._root))
    ):
        raise BootstrapEnvironmentLeakError(
            f"Python install completed but interpreter "
            f"{self._venv_python} is outside worktree {self._root}. "
            f"Refusing to claim success — this would silently corrupt "
            f"the parent venv. See "
            f".claude/reviews/TASK-REV-FFC6-review-report.md."
        )
    ```
14. **AC-008** `BootstrapResult.venv_python` already populated from
    `self._venv_python` at line 1267. Eager creation guarantees it is
    set on every successful Python bootstrap. PEP 668 path remains
    orthogonal (`<worktree>/.guardkit/venv/...`); both paths satisfy
    the invariant `str(self._venv_python).startswith(str(self._root))`.
15. Update `__all__` to export `BootstrapEnvironmentLeakError`.

**Verify**: All Wave A tests now PASS.

### Wave C — Don't-break (AC-015..AC-020)

16. **AC-015** PEP 668 retry test — direct `_run_install` call doesn't
    go through `bootstrap()` so eager creation doesn't fire;
    `self._venv_python` is None on first call. PEP 668 stderr triggers
    `_ensure_venv()` (preserved), creating `<root>/.guardkit/venv/`,
    retry succeeds. Add `env=` to first call assertion (no-op since
    `self._venv_python` is None at that moment); add `env=` shape
    assertion to the retry call.
17. **AC-016** AB60 retry test — same reasoning. The retry already
    constructs env locally; preserve its assertion shape.
18. **AC-017** FD32 routing — uv sync test continues to bypass AB60
    retry because `cmd[1:3] != ["pip", "install"]`. With eager venv
    creation in `bootstrap()` (NOT `_run_install`), the test calling
    `_run_install` directly is unaffected.
19. **AC-018** F09A2 detection — `UvSourcesRequireUvError` raised at
    detection time (before `bootstrap()` runs), entirely orthogonal.
20. **AC-019** Coach test — `_resolve_venv_python` already handles
    explicit param (line 43-46). Add a test that explicitly passes
    `<worktree>/.venv/bin/python` to capture the FFC6-introduced path.
21. **AC-020** A7B6 extras simulation — add a fixture-based test
    constructing a manifest with `install_command =
    [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]` and
    asserting isolation (cmd[0] swap + env override).

**Verify**: Full bootstrap test suite passes.

### Wave D — Phase 5 review

22. Code review pass.
23. Phase 5.5 plan audit (strict: 0% LOC variance threshold, 0% file
    count variance — no surprises permitted).

## Estimates

- LOC: ~600 (impl: ~150, new tests: ~250, test updates: ~200)
- Files: 5 (1 modify primary, 1 new test, 2 modify tests, 1 new/modify coach test)
- Duration: 90-120 minutes
- Complexity: 7/10

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Mock-shape brittleness in existing tests when eager venv creation adds a subprocess.run call. | Eager creation lives in `bootstrap()`, NOT `_run_install`. Tests calling `_run_install` directly are unaffected. Tests calling `bootstrap()` get one extra `subprocess.run` (eager venv creation) — accept the count change. |
| `_isolated_env` breaks tests that mock `subprocess.run` and don't expect `env=` kwarg. | Tests use kwarg-aware patterns; `mock_run.call_args.kwargs["env"]` works. New behavior is additive — existing assertions on cmd/cwd unchanged. |
| `uv venv` failing on systems without uv when eager creation is invoked. | Fallback to `python -m venv` per AC-001. Both produce a working venv with `bin/python`. |
| Breaking the AB60 retry path (which already passes env). | Refactor AB60 to use `_isolated_env` helper for consistency, but preserve the `[uv pip install -e .]` retry shape exactly. Existing AB60 tests serve as the regression guard. |
| Saved-state recovery sets `self._venv_python` from previous run pointing at parent venv (state-file leak). | After recovery (line 1147-1154), the eager creation branch (AC-003) checks if `self._venv_python` is None OR not under `self._root`, and re-creates if so. Belt-and-braces. |

## Architectural Notes

- **SOLID**: Single new helper class methods, single responsibility each.
- **DRY**: Consolidate env construction in `_isolated_env`; AB60 retry
  refactored to use it.
- **YAGNI**: No new abstractions for "future stack venvs" — Python only.
- **Layer 2/3 explicitly out of scope** per task description.

## Knowledge Graph Capture (post-completion)

Per task description:
- Node: "bootstrap subprocess must pass explicit `env=` with worktree-local `VIRTUAL_ENV`"
- Node: "tests that mock `subprocess.run` must assert `env=` shape, not just exit code"
- Edges to: existing nodes for `namespace-hygiene` and `absence-of-failure-is-not-success`.
