# Implementation Plan — TASK-FIX-FF62

**Mode:** TDD
**Intensity:** strict
**Complexity:** 4/10 (medium; strict overrides to maximum rigor)
**Generated:** 2026-05-06
**Parent review:** TASK-REV-FFC6 (Recommendation R2 — Layer 3)
**Depends on:** TASK-FIX-FF61 (✅ completed, in commit `87936e56` and prior)

## Goal

Add a defense-in-depth boundary check to the `/feature-complete` worktree-cleanup flow that:

1. Scans known parent venv roots for editable `_editable_impl_*.pth` files referencing the worktree about to be removed.
2. Emits a one-line warning per leak with a copy-pasteable repair command.
3. **Never aborts cleanup** — it is read-only, warning-only, informational.
4. Stays silent when no leaks are present (the steady state after FF61).

This is the [absence-of-failure-is-not-success rule](../../../.claude/rules/absence-of-failure-is-not-success.md) applied to FF61: even though FF61 makes parent-venv leaks impossible at write time, an independent verification at the cleanup boundary is the prescribed remediation pattern. It also rescues users with pre-existing leaks from before FF61 landed.

## Files To Change

### Primary (NEW)

| File | Change | LOC est. |
|---|---|---|
| `guardkit/worktrees/pth_leak_scanner.py` | **NEW**: `find_pth_leaks(repo_root, worktree_path) -> list[tuple[Path, str]]` (scanner) and `warn_pth_leaks(repo_root, worktree_path, console=None) -> int` (presenter). Pure stdlib. Read-only. Never raises. | ~110 |

### Wiring (MODIFY)

| File | Change | LOC est. |
|---|---|---|
| `guardkit/worktrees/__init__.py` | Re-export `find_pth_leaks` and `warn_pth_leaks` for ergonomic import. | ~3 |
| `guardkit/orchestrator/feature_orchestrator.py` | Call `warn_pth_leaks(repo_root=self.repo_root, worktree_path=worktree_path, console=console)` in `_clean_state` (`:1716`) **before** `self._worktree_manager.cleanup(...)` (`:1727`). Wrapped in `try/except` so the scanner can never abort cleanup even if the implementation panics. | ~8 |

### Tests (NEW)

| File | Change | LOC est. |
|---|---|---|
| `tests/unit/test_pth_leak_scanner.py` | **NEW**: AC-005..AC-009 (5 unit tests for `find_pth_leaks`) + smoke tests for `warn_pth_leaks` output shape. | ~210 |
| `tests/orchestrator/test_feature_orchestrator_pth_warning.py` | **NEW**: AC-010, AC-011, AC-012 — integration tests against `_clean_state`. Uses real tmp_path repo, real `.venv` directory layout, fake worktree path, mocked `WorktreeManager.cleanup` (so we don't actually `git worktree remove` in tests). | ~180 |

**Total est. LOC:** ~510 lines (110 prod + 400 test).

## Acceptance Criteria → Tests Mapping

| AC | Test (file::function) | Target |
|---|---|---|
| AC-001 | covered transitively by AC-005..AC-009 | `find_pth_leaks` signature + behavior |
| AC-002 | `test_feature_orchestrator_pth_warning::test_warns_before_cleanup_runs` | Wiring + ordering |
| AC-003 | `test_pth_leak_scanner::test_returns_empty_when_clean` + `test_feature_orchestrator_pth_warning::test_silent_when_no_leaks` | Silent steady state |
| AC-004 | `test_pth_leak_scanner::test_handles_missing_repo_root` (None / nonexistent) | Defensive boundary |
| AC-005 | `test_pth_leak_scanner::test_find_pth_leaks_detects_worktree_reference` | Detection happy path |
| AC-006 | `test_pth_leak_scanner::test_find_pth_leaks_returns_empty_when_clean` | False-positive guard |
| AC-007 | `test_pth_leak_scanner::test_find_pth_leaks_handles_missing_venv_dir` | Missing-venv tolerance |
| AC-008 | `test_pth_leak_scanner::test_find_pth_leaks_handles_unreadable_pth` | Permission tolerance |
| AC-009 | `test_pth_leak_scanner::test_find_pth_leaks_does_not_follow_symlinks` | Symlink containment |
| AC-010 | `test_feature_orchestrator_pth_warning::test_warns_but_does_not_abort` | Integration: warn + cleanup runs |
| AC-011 | `test_feature_orchestrator_pth_warning::test_silent_when_no_leaks` | Integration: silent steady state |
| AC-012 | `test_feature_orchestrator_pth_warning::test_no_python_venv_no_warning` | No-Python project |
| AC-013 | covered by existing `_clean_state` behavior + `test_warns_before_cleanup_runs` ordering | `--force` semantics intact |
| AC-014 | implicit (scanner imports only `pathlib`/`os`); enforced by reading the scanner module's import section in code review | No new deps |

## Phase Order (TDD)

### Wave A — RED (failing tests first)

1. **Create scanner module skeleton**: empty `find_pth_leaks` returning a hardcoded `[]`, empty `warn_pth_leaks` returning `0`. Just enough for the test file to import.
2. **Write `tests/unit/test_pth_leak_scanner.py`** with all 5 AC unit tests + 2 `warn_pth_leaks` output tests.
3. **Write `tests/orchestrator/test_feature_orchestrator_pth_warning.py`** with 3 integration tests.
4. **Verify**: `pytest tests/unit/test_pth_leak_scanner.py tests/orchestrator/test_feature_orchestrator_pth_warning.py -v` shows 10 failures (or skeleton-passing-trivially-but-asserting-wrong-shape — both are RED).

### Wave B — GREEN (minimum implementation)

5. **Implement `find_pth_leaks`**:
   - Iterate `[".venv", ".guardkit/venv"]` scan roots under `repo_root`.
   - For each, glob `lib/python*/site-packages/_editable_impl_*.pth`.
   - Skip the root entirely if it is a symlink (use `Path.is_symlink()`).
   - For each `.pth` file: read text (catch `OSError`), check if `str(worktree_path)` appears as substring in any line. If so, record `(pth_file, matching_line)`.
   - Return aggregated list.
6. **Implement `warn_pth_leaks`**:
   - Call `find_pth_leaks`.
   - For each leak, emit a 3-line warning block (warning header, file path, repair hint) via `console.print(..., style="yellow")` if console provided, else `print(..., file=sys.stderr)`.
   - DEBUG-log when zero leaks found and exit silently.
   - Wrap the entire body in `try/except Exception` that DEBUG-logs and returns `0` (so a buggy scanner never breaks the cleanup boundary).
7. **Wire into `feature_orchestrator._clean_state`** before the `cleanup(...)` call. Wrap in its own `try/except` for double safety.
8. **Re-export from `guardkit/worktrees/__init__.py`**.
9. **Verify**: re-run pytest — all 10 tests pass.

### Wave C — REFACTOR

10. Extract magic strings (scan roots, glob pattern, repair-hint template) into module-level constants for easy future extension.
11. Add module docstring with rationale citation to `absence-of-failure-is-not-success.md`.
12. Re-run pytest to confirm refactor preserves green state.

## External Dependencies

**None.** Scanner uses only `pathlib`, `os`, `sys`, `logging` from stdlib. AC-014 requires zero new dependencies.

## Risks

| Severity | Risk | Mitigation |
|---|---|---|
| 🟢 LOW | Scanner reads `.pth` files that contain unreadable bytes, raising `UnicodeDecodeError`. | Wrap `Path.read_text()` in `try/except (OSError, UnicodeDecodeError)`; skip the file silently. Covered by AC-008. |
| 🟢 LOW | Glob `lib/python*/site-packages/` matches multiple Python versions in same venv (e.g., upgrade left both `python3.13` and `python3.14`). | Iterating multiple matches is correct behavior — emit one warning per matched `.pth` regardless of Python version. No special handling needed. |
| 🟢 LOW | `worktree_path` is a relative path; `.pth` lines are absolute. | Resolve `worktree_path` to absolute via `.resolve()` before substring match. |
| 🟢 LOW | Future scan roots (Conda, asdf) get added without a corresponding test. | Out-of-scope per task description. Constants make future extension trivial. |
| 🟡 MEDIUM | The scanner runs in `_clean_state` BEFORE cleanup, but `_clean_state` is also invoked during *resume*-with-refresh flows, not just `/feature-complete`. This means the warning surfaces in places the operator may not expect. | Acceptable — surfacing leaks in any cleanup path is *more* defense-in-depth, not less. The warning text is unambiguous about what is happening. |

## Estimated Duration

**45–60 minutes** in strict TDD mode:
- 10m: write tests (Wave A)
- 20m: implement scanner + wiring (Wave B)
- 10m: refactor + final test pass (Wave C)
- 10m: Phase 5 review + Phase 5.5 audit

## Test Strategy

- **Unit tests** use `tmp_path` fixtures with real directory hierarchies. No mocking of `pathlib` itself. Only mock `WorktreeManager.cleanup` in the integration tests so we don't actually run `git worktree remove`.
- **Symlink test (AC-009)** uses `Path.symlink_to()`. On platforms where symlinks aren't supported (Windows without admin), the test is `pytest.skip`-ped.
- **Permission test (AC-008)** uses `chmod 0o000` on the `.pth` file via `os.chmod`. Includes a `try/finally` that restores `0o644` so cleanup works.
- **Integration tests** construct a fake `Worktree` dataclass and a `WorktreeManager` mock whose `cleanup` is a `MagicMock`. Then call `_clean_state` directly with a feature whose `execution.worktree_path` matches the tmp_path layout. Assert (a) console captured the warning (or didn't), (b) `cleanup` was called with `force=True`.

## Plan Audit Targets (Phase 5.5)

For strict intensity (0% variance allowed):

- **Files**: 4 expected (1 NEW prod, 1 MODIFY init, 1 MODIFY orchestrator, 2 NEW test files = 5 actually). **Target: 5 files.**
- **External deps**: 0 added. **Target: 0.**
- **LOC**: ~510 ± 0%. **Target: 460–560 LOC.**
- **Duration**: 45–60 min ± 10%. **Target: 41–66 min.**

Any deviation flagged for review per strict-mode 0% LOC variance threshold.
