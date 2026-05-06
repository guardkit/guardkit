---
id: TASK-FIX-FF61
title: "Bootstrap worktree-venv isolation across all three install paths"
status: backlog
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-FFC6
feature_id: FEAT-FFC6
implementation_mode: task-work
wave: 1
complexity: 7
tags: [autobuild, environment-bootstrap, venv-isolation, regression-fix, ffc3-bug-4]
related_tasks: [TASK-REV-FFC6, TASK-FIX-FF62, TASK-FIX-A7B6, TASK-FIX-AB60, TASK-FIX-F09A2, TASK-FIX-7A05]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Bootstrap worktree-venv isolation across all three install paths

## Description

Implements **Recommendation R1** (eager worktree-local venv with explicit env isolation) and **R3** (test invariant fix) from [TASK-REV-FFC6 review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md).

The autobuild's `environment_bootstrap` step writes the worktree's path into the parent project's `.venv` editable `.pth` file because every install subprocess inherits `os.environ` (including `$VIRTUAL_ENV`) and, on the pip path, uses `sys.executable` (which may itself be the parent venv's python). After worktree teardown, the parent venv holds dangling pointers that break Claude Desktop MCPs, IDE language servers, and any other process using that venv.

The review surfaced **three** independent leak paths:
1. `["uv", "pip", "install", "-e", "."]` — leaks via inherited `$VIRTUAL_ENV`
2. `["uv", "sync", "--frozen"]` — leaks via inherited `$VIRTUAL_ENV` (project mode)
3. `[sys.executable, "-m", "pip", "install", "-e", "."]` — leaks via `sys.executable`'s `sys.prefix`, **independent of `$VIRTUAL_ENV`**

…and a **test-suite defense-in-depth failure**: the existing test `test_preexisting_venv_succeeds_without_retry` actively encodes the leak as expected behaviour. This task fixes both the implementation and the test invariant.

## Context

- **Affected file (primary):** [`guardkit/orchestrator/environment_bootstrap.py`](../../../guardkit/orchestrator/environment_bootstrap.py)
- **Affected files (test):** [`tests/unit/test_environment_bootstrap.py`](../../../tests/unit/test_environment_bootstrap.py), [`tests/unit/test_environment_bootstrap_uv_venv.py`](../../../tests/unit/test_environment_bootstrap_uv_venv.py)
- **Downstream consumer (no change required):** [`guardkit/orchestrator/coach_verification.py:29-57`](../../../guardkit/orchestrator/coach_verification.py#L29-L57) `_resolve_venv_python` already handles explicit interpreter paths.
- **Existing-pattern template:** the retry block at [environment_bootstrap.py:1664-1671](../../../guardkit/orchestrator/environment_bootstrap.py#L1664-L1671) demonstrates the correct env-isolation pattern for retries — this task generalizes it to first-try call sites.

## Acceptance Criteria

### Implementation

- [ ] **AC-001:** Add `_ensure_worktree_venv(worktree: Path) -> Path` helper that creates `<worktree>/.venv` (via `uv venv` if uv is on PATH, else `python -m venv`). Idempotent. May rename existing `_ensure_uv_venv` if cleaner.
- [ ] **AC-002:** Add `_isolated_env(worktree_venv: Path) -> Dict[str, str]` helper that returns `os.environ` with **inherited `VIRTUAL_ENV` stripped**, then `VIRTUAL_ENV` and `PATH` set to point at the worktree venv. The strip-then-set order matters — do not rely solely on `{**os.environ, "VIRTUAL_ENV": ...}` semantics.
- [ ] **AC-003:** In `bootstrap()`, call `_ensure_worktree_venv` eagerly **before** the install loop runs, gated on `any(m.stack == "python" for m in manifests)`. Cache the resulting interpreter on `self._venv_python`.
- [ ] **AC-004:** In `_run_install` and `_run_single_command`, pass `env=self._isolated_env(self._venv_python.parent.parent)` to **every** `subprocess.run` for Python install commands — first try AND retry. Non-Python commands (`npm`, `dotnet`, `cargo`, …) inherit env unchanged.
- [ ] **AC-005:** For pip-path install commands (`cmd[0] in (sys.executable, str(self._venv_python), ...)`), replace `cmd[0]` with `str(self._venv_python)` (the worktree venv's python) BEFORE `subprocess.run`. The existing remap at [line 1567-1568](../../../guardkit/orchestrator/environment_bootstrap.py#L1567-L1568) already does this when `self._venv_python` is set; AC-003 sets it eagerly so the remap covers the first-try call too.
- [ ] **AC-006:** Replace the false-success block at [line 1239-1249](../../../guardkit/orchestrator/environment_bootstrap.py#L1239-L1249) with an invariant raise:
  ```python
  if (
      overall_success
      and any(m.stack == "python" for m in manifests)
      and self._venv_python is not None
      and not str(self._venv_python).startswith(str(self._root))
  ):
      raise BootstrapEnvironmentLeakError(
          f"Python install completed but interpreter {self._venv_python} "
          f"is outside worktree {self._root}. Refusing to claim success."
      )
  ```
- [ ] **AC-007:** Add `BootstrapEnvironmentLeakError(RuntimeError)` exception class with a docstring referencing this task and the review report.
- [ ] **AC-008:** `BootstrapResult.venv_python` is set to `<worktree>/.venv/bin/python` on every successful Python bootstrap. Existing PEP 668 path (`<worktree>/.guardkit/venv/`) remains unchanged — its trigger and behaviour are orthogonal.

### Regression tests (must fail BEFORE this task lands; pass AFTER)

- [ ] **AC-009:** `test_no_leak_when_VIRTUAL_ENV_inherited` — sets `monkeypatch.setenv("VIRTUAL_ENV", "<parent>/.venv")`, runs bootstrap, asserts every captured `subprocess.run(env=...)` has `VIRTUAL_ENV` pointing at `<worktree>/.venv` (NOT the parent path).
- [ ] **AC-010:** `test_no_leak_when_sys_executable_is_parent_venv` — uses pip-path install command (no `[tool.uv.sources]`, no `uv.lock`); asserts the captured `cmd[0]` is `<worktree>/.venv/bin/python`, NOT `sys.executable`.
- [ ] **AC-011:** `test_no_leak_when_uv_sync_path` — uses `uv sync --frozen` install command (uv.lock present); asserts the captured `env["VIRTUAL_ENV"]` is worktree-local even when `monkeypatch.setenv("VIRTUAL_ENV", parent_venv)` is set.
- [ ] **AC-012:** `test_invariant_fails_when_install_lands_outside_worktree` — directly mocks `_run_install` to leave `self._venv_python` pointing at a path outside `self._root`; asserts `bootstrap()` raises `BootstrapEnvironmentLeakError`.

### Test invariant fix (R3)

- [ ] **AC-013:** Update [`test_preexisting_venv_succeeds_without_retry`](../../../tests/unit/test_environment_bootstrap_uv_venv.py#L160-L180) to assert `mock_run.call_args.kwargs["env"]["VIRTUAL_ENV"] == str(tmp_path / ".venv")`. Remove the `mock_run.call_count == 1` assertion if it conflicts with eager venv creation; replace with a check that no `_editable_impl_*.pth` is written outside the worktree.
- [ ] **AC-014:** Audit and update sibling tests in the same file (`test_run_install_*`) and in [`test_environment_bootstrap.py`](../../../tests/unit/test_environment_bootstrap.py) (`test_run_install_*`, `test_bootstrap_*`) — add `env=` shape assertions to any test that calls `_run_install` or `_run_single_command` for a Python manifest. List the changed tests in the PR description.

### Don't-break invariants

- [ ] **AC-015:** PEP 668 retry path at [test_environment_bootstrap.py:1677](../../../tests/unit/test_environment_bootstrap.py#L1677) (`test_run_install_pep668_creates_venv_and_retries`) continues to pass without modification of its core invariants. The `<worktree>/.guardkit/venv/` path is preserved as a separate fallback for the externally-managed Python case.
- [ ] **AC-016:** AB60 retry path at [test_environment_bootstrap_uv_venv.py:118](../../../tests/unit/test_environment_bootstrap_uv_venv.py#L118) (`test_no_venv_error_triggers_retry_that_creates_venv_and_succeeds`) continues to pass; the retry is now redundant with eager creation but the code path remains valid for any uv version that fails the eager creation.
- [ ] **AC-017:** FD32 routing at [test_environment_bootstrap_uv_venv.py:182](../../../tests/unit/test_environment_bootstrap_uv_venv.py#L182) (`test_uv_sync_lockfile_path_does_not_enter_retry`) continues to pass.
- [ ] **AC-018:** F09A2 detection (`UvSourcesRequireUvError` when `[tool.uv.sources]` declared without uv on PATH) continues to fire correctly.
- [ ] **AC-019:** Coach pytest interpreter resolution at [coach_verification.py:29-57](../../../guardkit/orchestrator/coach_verification.py#L29-L57) continues to find the venv: previously via `<worktree>/.guardkit/venv/bin/python`; now ALSO via `BootstrapResult.venv_python` set to `<worktree>/.venv/bin/python`. Add a unit test for the new path.
- [ ] **AC-020:** TASK-FIX-A7B6 sequencing — when A7B6 lands later and changes the install command to include extras (`pip install -e ".[dev]"`), the FFC6 isolation MUST still apply (extras land in the worktree venv, not the parent). Add a test fixture that simulates A7B6's extras config and asserts isolation holds.

## Files Likely To Change

- `guardkit/orchestrator/environment_bootstrap.py` — primary; helper additions, eager venv creation, env override, invariant raise.
- `tests/unit/test_environment_bootstrap.py` — env-shape assertions added to existing `_run_install` / `_run_single_command` tests.
- `tests/unit/test_environment_bootstrap_uv_venv.py` — `test_preexisting_venv_succeeds_without_retry` updated; new tests AC-009 through AC-012 added.
- `tests/unit/test_environment_bootstrap_ffc6.py` (NEW) — top-level regression suite for the leak.
- `tests/orchestrator/test_coach_verification.py` (or sibling) — new test for AC-019.

## Out Of Scope

- Layer 2 (repoint parent venv at `/feature-complete`) — explicitly skipped per review.
- Layer 3 (detect-and-warn at finalization) — separate task TASK-FIX-FF62.
- Refactoring the broader bootstrap pipeline.
- Cross-template work (Node/.NET/Go/Rust/Flutter — leak-free per review F8).
- TASK-FIX-A7B6 extras feature — separate task; FFC6 must merge first to avoid conflict.

## Reproduction (manual, pre-fix)

```bash
# In a project with a parent .venv:
cd <parent>
source .venv/bin/activate
guardkit autobuild feature <any-feature>   # any feature with a Python pyproject.toml worktree
/feature-complete <feature-id>

# Verify the leak BEFORE this task lands:
cat .venv/lib/python*/site-packages/_editable_impl_*.pth
# Expected pre-fix: contains a path under <parent>/.guardkit/worktrees/
# Expected post-fix: file does not exist OR points only at <parent>/src
```

## References

- [TASK-REV-FFC6 review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md) — comprehensive depth, includes C4 + 6 sequence diagrams. Read Sequence Diagrams 1, 2, 3 (current bug paths) and 5 (Layer 1 fixed flow) before implementing.
- [.claude/rules/absence-of-failure-is-not-success.md](../../../.claude/rules/absence-of-failure-is-not-success.md) — the false-success block at line 1239 is a textbook instance of this rule.
- [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md) — parent venv is an externally-defined namespace.
- Original incident: `specialist-agent/docs/history/autobuild-FFC3-editable-install-leak-incident.md`

## Knowledge-Graph Capture (post-completion)

Seed under `guardkit__project_decisions`:
- Node: "bootstrap subprocess must pass explicit `env=` with worktree-local `VIRTUAL_ENV`"
- Node: "tests that mock `subprocess.run` must assert `env=` shape, not just exit code"
- Edges to: existing nodes for `namespace-hygiene` and `absence-of-failure-is-not-success`.
