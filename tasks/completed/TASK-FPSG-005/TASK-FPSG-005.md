---
id: TASK-FPSG-005
title: "FeatureLoader._parse_feature: pre-flight smoke-gate paths at load time (L4 — defense-in-depth)"
status: completed
created: 2026-05-02T13:30:00Z
updated: 2026-05-02T14:45:00Z
completed: 2026-05-02T14:45:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FPSG-005/
priority: high
task_type: enhancement
implementation_mode: task-work
tags:
  - feature-loader
  - smoke-gate
  - pre-flight
  - defense-in-depth
  - cross-repo-followup
  - feature-plan-smoke-gate-validation
complexity: 4
estimated_minutes: 90
parent_review: appmilla_github/forge/TASK-REV-DEA8
parent_feature: feature-plan-smoke-gate-validation
wave: 2
dependencies: []  # shares parse_positional_paths with TASK-FPSG-002
---

# Task: `_parse_feature` — pre-flight smoke-gate paths at load time

## Description

The runtime safety net. Even if all of L3a/b/c/d slip through (e.g.
the YAML is hand-edited after `/feature-plan` finishes), this layer
catches a stale `tests/cli`-style path **before any wave starts**.

Today, `guardkit/orchestrator/feature_loader.py:645-654` parses
`smoke_gates` via Pydantic but does not verify path existence:

```python
smoke_gates_data = data.get("smoke_gates")
smoke_gates: Optional[SmokeGates] = None
if smoke_gates_data is not None:
    try:
        smoke_gates = SmokeGates.model_validate(smoke_gates_data)
    except ValidationError as e:
        raise SchemaValidationError(
            f"Invalid smoke_gates configuration:\n{e}"
        )
```

This task adds a path-existence check immediately after
`SmokeGates.model_validate`, gated on the feature's repo root.

## Acceptance Criteria

- [ ] **New helper** `_validate_smoke_gates_paths(smoke_gates: SmokeGates,
      repo_root: Path) -> None` in `feature_loader.py`.
      - Calls `parse_positional_paths(smoke_gates.command)` (shared
        with TASK-FPSG-002 / TASK-FPSG-004).
      - For each path, checks `(repo_root / path).exists()`.
      - On any miss, raises `SmokeGatePathError(SchemaValidationError)`
        with a clear message including the missing path, the repo
        root, and the discovered test roots.
- [ ] **Wired into `_parse_feature`** at line 645-654 area, after
      `SmokeGates.model_validate` and inside the same `try` block (so
      load-time failures surface uniformly).
- [ ] **Run-2 transcript signature** — when this is wired, a feature
      YAML with `tests/cli` should produce, before any wave starts:
      ```
      ✗ Pre-flight validation failed: smoke_gates.command references
        non-existent path: tests/cli (repo root: /Users/.../forge)
        Available test roots: tests/forge, tests/integration, ...
      ```
      In contrast to today's behaviour, where the orchestrator
      bootstraps the worktree, runs Wave 1 (~17 min), THEN fails on
      the smoke gate.
- [ ] **Repo root resolution** — the validator must use the **same
      `cwd`** that `run_smoke_gate` will use at execution time.
      Mismatched paths between load-time validation and run-time
      execution would create false positives. Inspect
      `feature_orchestrator.py:1953` (`run_smoke_gate(...)` invocation)
      to confirm the cwd.
- [ ] **No regression in existing feature-load tests** — smoke-free
      features and well-formed features still load cleanly.

## Test Requirements

- [ ] Unit test
      `tests/unit/orchestrator/test_feature_loader_smoke_gate_paths.py`:
      - tmp_path repo + fixture YAML with `tests/cli` (missing) →
        `_parse_feature` raises `SmokeGatePathError`; message includes
        `tests/cli`, the repo root, and the available roots.
      - Same fixture with `tests/forge` (existing) → `_parse_feature`
        succeeds.
      - Fixture with no `smoke_gates` block → `_parse_feature`
        succeeds.
      - Fixture with non-pytest `smoke_gates.command` (e.g.
        `python3 .guardkit/smoke/foo.py`) → succeeds (parser returns
        `[]`).
- [ ] Regression test ensuring the run-2-style failure mode is
      caught at load time, not runtime.

## Implementation Notes

- This is purely **additive** — no existing behaviour changes for
  features with valid smoke_gates or no smoke_gates.
- Error message must be **byte-identical** to TASK-FPSG-002's
  `--validate-smoke-gates` mode and TASK-FPSG-004's `feature validate`
  output. One source of truth for the message string.
- Consider extracting the message-formatting helper alongside the
  shared parser, e.g.:
  ```python
  def format_smoke_gate_path_error(missing: list[str], repo_root: Path) -> str: ...
  ```
- **Out of scope**: do NOT extend the exit-5 carve-out at
  `smoke_gates.py:212-214` to also cover exit 4. Promoting exit 4 to
  soft-warn would silently mask path typos (rejected as L5 in the
  parent review — see TASK-REV-DEA8 §F9).

## Files

- `guardkit/orchestrator/feature_loader.py` — primary edit
- `guardkit/orchestrator/smoke_gates.py` (or `lib/pytest_argv.py`) —
  shared parser + message formatter
- `tests/unit/orchestrator/test_feature_loader_smoke_gate_paths.py` — new

## Implementation Summary

L4 of the four-layer smoke-gate validation chain landed: a stale
`tests/cli`-style path now fails at `FeatureLoader.load_feature` time,
before the orchestrator bootstraps a worktree or runs Wave 1. The
canonical worst-case (DEA8 run-2) cost ~17 min on Wave 1 before
surfacing the smoke-gate path miss; this layer reduces that to seconds.

**Approach**

- **New shared module `guardkit/lib/pytest_argv.py`** — single source of
  truth for `parse_positional_paths(command)` and
  `format_smoke_gate_path_error(missing, repo_root, available_roots)`.
  Sibling tasks TASK-FPSG-002 (validator mode) and TASK-FPSG-004
  (`feature validate` wrapper) import the same helpers, so all three
  layers emit byte-identical wording for the same defect.
- **Parser** uses `shlex.split` per line, locates the first
  `pytest`/`*/pytest` token, then walks argv: skips flag-with-value
  pairs (`-k EXPR`, `--rootdir DIR`, etc.) and `--key=value` forms,
  stops at `--`. Non-pytest commands return `[]` so the validator is a
  no-op for custom smoke scripts.
- **`SmokeGatePathError(SchemaValidationError)`** — distinct class so
  triage can tell a path-existence miss apart from a Pydantic schema
  violation, but inheritance keeps existing `except
  SchemaValidationError` / `FeatureParseError` handlers working.
- **`FeatureLoader._validate_smoke_gates_paths(smoke_gates, repo_root)`**
  wired into `_parse_feature` immediately after `SmokeGates.model_validate`.
  Threaded `repo_root: Optional[Path]` through `_parse_feature`'s
  signature; default `None` skips path validation for in-memory parses
  (tests, etc.). `load_feature` now passes its `repo_root` through.
- Reuses `installer/core/commands/lib/smoke_gates_nudge.discover_test_roots`
  for the "Available test roots" line in the error message — same
  sorting, same `_TEST_ROOT_SKIP_NAMES` filter as the authoring-time
  banner.

**`cwd` invariant**

`run_smoke_gate` runs with `cwd=Path(worktree.path)` at execution time,
but the worktree is a git checkout of `repo_root` — the same source
tree, so `tests/<x>/` exists in both or neither. Validating at load
time against `repo_root` is therefore equivalent to validating against
the worktree path; no false-positive risk.

**Test surface**

- `tests/unit/orchestrator/test_feature_loader_smoke_gate_paths.py`
  pins all four AC scenarios (missing path raises, existing path
  succeeds, no `smoke_gates` block succeeds, non-pytest command
  succeeds), the multi-line block-scalar case (`set -e\npytest …`),
  the multi-positional partial-miss case, the `SchemaValidationError`
  inheritance contract, and the run-2-style failure-mode regression
  (failure surfaces at `load_feature`, not at `run_smoke_gate`).
- `tests/unit/models/test_feature_yaml_schema.py::test_smoke_gates_after_wave_int`
  was updated to materialize the referenced path on disk — the only
  pre-existing test that referenced a non-real pytest positional under
  tmp_path. No other regressions across orchestrator/feature-loader/
  smoke-gates/schema suites (285/285).

## Notes

**Lessons**

1. **Import-graph hygiene paid off.** `discover_test_roots` already
   lived in `installer/core/commands/lib/smoke_gates_nudge.py`; reusing
   it kept the "Available test roots" wording consistent across the
   nudge banner (authoring-time) and the validator error
   (load-time/runtime). Future smoke-gate validators should reach for
   the same helper rather than re-implementing the walk.
2. **Optional `repo_root` parameter chosen over a separate "validated"
   loader method.** Threading `repo_root: Optional[Path] = None`
   through `_parse_feature` keeps a single parse path; callers without
   repo context (in-memory parses) get the old behaviour for free.
   Kept the change additive — no caller had to change signature except
   the one production call site inside `load_feature`.
3. **Parser kept conservative.** Pytest has dozens of flags; the
   parser only special-cases the ones that demonstrably consume their
   next token (`-k`, `-m`, `--rootdir`, etc.). Unknown flags are
   treated as no-value, which means a future flag could in theory eat
   a positional. Acceptable because the failure mode is "validator
   misses a real path" → falls through to runtime smoke gate
   (existing pre-FPSG-005 behaviour). Worst case is regressing to the
   old experience, never blocking valid features.

**Related ADRs / parent review**

- Parent review: `appmilla_github/forge/TASK-REV-DEA8` (defines the
  four-layer L3a/b/c/d + L4 chain).
- Sibling tasks: TASK-FPSG-002 (L3b, `--validate-smoke-gates` mode),
  TASK-FPSG-003 (L3c, `discover_test_roots` grounding — already
  landed), TASK-FPSG-004 (L3d, `feature validate` wrapper).
- Out-of-scope by parent review: extending the exit-5 carve-out at
  `smoke_gates.py:212-214` to cover exit 4 (rejected as L5 — would
  silently mask path typos).
