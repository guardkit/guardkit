---
id: TASK-FIX-F09A2
title: "GuardKit: detect [tool.uv.sources] and prefer `uv pip install -e .` when uv is on PATH"
status: in_review
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
previous_state: in_progress
state_transition_reason: "All quality gates passed — implementation + 7 new tests + doc"
priority: medium
task_type: fix
tags: [fix, guardkit, environment-bootstrap, uv-sources, cross-repo, F09A-followup, durable-fix]
complexity: 5
estimated_minutes: 180
estimated_effort: "3-4 hours (cross-repo: code change + tests + uv installation in CI/dev image)"
parent_review: TASK-REV-F09A
parent_task: TASK-FIX-F09A1
implementation_mode: cross-repo  # work happens in appmilla_github/guardkit, not forge
target_repo: appmilla_github/guardkit
related_tasks:
  - TASK-REV-F09A   # decision review that produced this task
  - TASK-FIX-F09A1  # forge-side ship-now fix that this task makes obsolete
context_files:
  - .claude/reviews/TASK-REV-F09A-review-report.md
  - ../../appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py
test_results:
  status: passing
  coverage: "TestPyprojectUvSourcesDetection: 7/7; full test_environment_bootstrap.py: 134/134"
  last_run: 2026-04-30T00:00:00Z
---

# Task: GuardKit — detect `[tool.uv.sources]` and prefer `uv pip install -e .` when uv is on PATH

## Description

Layer 2 of the layered fix recommended by `TASK-REV-F09A`'s decision review.
This task is a **cross-repo handoff**: the work happens in
`~/Projects/appmilla_github/guardkit/`, not in forge. Filed in forge's
backlog for traceability with `TASK-REV-F09A` and `TASK-FIX-F09A1`,
mirroring the convention established by `TASK-FIX-F0E6b`.

### Why this matters

GuardKit's `environment_bootstrap` currently constructs its install command
as a hardcoded
`[sys.executable, "-m", "pip", "install", "-e", "."]` at
[`environment_bootstrap.py:546,557`](../../../appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L546).
`pip` does not honour `[tool.uv.sources]`, so any project that uses the
sibling-source override (forge, jarvis today; an unknown number of future
projects) hits a structural Phase-1 bootstrap failure. The forge-side
workaround in `TASK-FIX-F09A1` (`.guardkit/preflight.sh` that pre-installs
the sibling dep via plain pip) ships today, but it puts operator burden on
every consuming repo.

This task removes that burden by teaching GuardKit's bootstrap to **prefer
`uv pip install -e .`** when the project's pyproject declares
`[tool.uv.sources]` (or a `uv.lock` is present) **and** `uv` is on the
caller's `PATH`.

## Acceptance Criteria

- [ ] **Detection**: `environment_bootstrap.py` parses pyproject.toml when
      a Python manifest is detected and checks for the presence of
      `[tool.uv.sources]` (and/or `uv.lock` adjacent to pyproject).

- [ ] **Behaviour matrix**:

  | pyproject `[tool.uv.sources]` | `uv.lock` present | `uv` on PATH | Install command chosen |
  |-------------------------------|-------------------|--------------|------------------------|
  | absent                        | absent            | any          | `python -m pip install -e .` (unchanged) |
  | absent                        | present           | yes          | `uv pip sync uv.lock` (full lockfile fidelity) |
  | absent                        | present           | no           | `python -m pip install -e .` (unchanged) + warning |
  | present                       | any               | yes          | `uv pip install -e .` |
  | present                       | any               | no           | **Hard-fail** with actionable error: "this project declares `[tool.uv.sources]` but `uv` is not on PATH; install uv (https://astral.sh/uv) or remove the `[tool.uv.sources]` block from pyproject.toml" |

- [ ] **Backwards compatibility**: projects with neither
      `[tool.uv.sources]` nor `uv.lock` see **no behaviour change**. The
      existing `pip install -e .` path is preserved exactly.

- [ ] **Symlink coordination**: GuardKit's worktree-creation step (already
      copies task files into the worktree per `_setup_phase`) should also
      ensure the canonical sibling-source symlink layout works from inside
      the worktree. Two acceptable approaches:
      (a) Document a guardkit-side hook that lets consuming repos
          contribute pre-bootstrap fixups (would also enable forge to
          drop `.guardkit/preflight.sh`); or
      (b) Document the operator-side requirement and leave the symlink to
          consuming-repo preflight scripts.
      Implementer's choice; either is acceptable, but pick one and
      document it in `guardkit/docs/`.

- [ ] **Tests**: add unit tests covering all 5 rows of the behaviour matrix
      using `tmp_path` fixtures with synthetic pyproject.toml content.
      Mock `shutil.which("uv")` to control the "uv on PATH" axis. The
      existing test layout in
      `appmilla_github/guardkit/tests/orchestrator/` is the target home.

- [ ] **PEP 668 fallback path**: the venv-fallback retry (transcript
      lines 36-37) must use the **same uv detection** so the second
      attempt also benefits. Otherwise we'd resolve correctly on the host
      attempt and fail on the venv retry.

- [ ] **CI update**: GuardKit's CI (and dev image / contributor docs) must
      install `uv` so the new branch of behaviour can be tested. Document
      `pip install uv` (or equivalent) as a required dev/CI dep.

- [ ] **Forge regression check**: once shipped, re-run
      `guardkit autobuild feature FEAT-FORGE-009 --verbose --fresh` against
      forge **without** running `.guardkit/preflight.sh`. Confirm
      bootstrap succeeds. (This unblocks the eventual deletion of the
      preflight script.)

- [ ] **Forge cleanup follow-up**: open a forge-side cleanup task to
      remove `.guardkit/preflight.sh` and the runbook pre-step note once
      this task is verified green in forge's autobuild. (Preflight script
      can stay around for a transition window — it's idempotent, so
      running it under the new uv-aware bootstrap is harmless.)

## Out of Scope

- Republishing the `nats-core` wheel (TASK-FIX-F0E6b).
- Removing forge's `[tool.uv.sources]` block (depends on F0E6b).
- Re-architecting GuardKit's environment bootstrap beyond the minimum
  needed to honour `[tool.uv.sources]` / `uv.lock`.

## Implementation Notes

- The exact code site is `environment_bootstrap.py:535-560` (the
  manifest-to-`DetectedManifest` factory block — see the lines that build
  `install_command=[sys.executable, "-m", "pip", "install", "-e", "."]`
  for both `poetry.lock` and `pyproject.toml`).
- `tomllib` is already imported in this file's `_python_pyproject_is_complete`
  helper (line 181) — reuse the same parser for the
  `[tool.uv.sources]` detection rather than re-importing.
- The "uv on PATH" check should use `shutil.which("uv")` (return `None`
  when uv isn't installed) — easy to mock in tests.
- An alternative implementation: only detect `[tool.uv.sources]` and
  swap to `uv pip install -e .`; leave full `uv pip sync uv.lock` for a
  later task. Acceptable scope reduction if maintainer prefers a smaller
  PR — call it out in the PR description.
- See the empirical reproductions in
  `.claude/reviews/TASK-REV-F09A-review-report.md` (Reproductions A & B)
  for the exact failure / success transcript that should remain
  reproducible after this fix lands.
- The hint that orchestrator already emits
  ("set `bootstrap_failure_mode: warn`") should be **revised** as part of
  this task: when the new error-message branch fires (uv-sources declared
  but uv missing), the hint should point at the missing-uv condition,
  not at the warn-mode escape hatch. Warn-mode is the wrong fix for an
  install-system mismatch.

## Cross-Repo Handoff Notes

This task is **filed in the forge backlog** (matching TASK-FIX-F0E6b's
pattern) but the implementation work happens in `appmilla_github/guardkit/`.
The handoff path:

1. Forge owner reviews and approves this task description.
2. Either the forge owner mirrors this task into
   `appmilla_github/guardkit/tasks/backlog/` and tackles it directly, or
   it's handed off to whoever owns guardkit's `environment_bootstrap`.
3. Once the guardkit PR lands, return here to mark the forge-side
   regression check (penultimate acceptance bullet) green and to file
   the forge-side cleanup follow-up.

## Test Execution Log

### 2026-04-30 — `/task-work TASK-FIX-F09A2`

- New test class `TestPyprojectUvSourcesDetection` covering all 5 matrix
  rows (plus a uv-sources + uv.lock variant and a PEP-668 inheritance
  check): 7/7 passing.
- Full `tests/unit/test_environment_bootstrap.py` suite: 134/134 passing.
- Related bootstrap test surfaces (`tests/orchestrator/test_bootstrap_gating.py`,
  `tests/unit/test_environment_bootstrap_fix7539.py`,
  `tests/unit/test_inter_wave_bootstrap.py`): 70/70 passing.
- Broader orchestrator + bootstrap surfaces (961 tests excluding pre-existing
  failures in `test_visual_comparator.py` — needs scikit-image/pillow — and
  `test_design_context_integration.py` — pre-existing, unrelated): all green.
- Forge regression check (penultimate AC bullet) and forge cleanup
  follow-up (final AC bullet) are deferred to forge-side: re-run
  `guardkit autobuild feature FEAT-FORGE-009 --verbose --fresh` against
  forge **without** running `.guardkit/preflight.sh` to confirm the new
  bootstrap resolves `[tool.uv.sources]` natively, then file the cleanup
  task to remove the preflight script + runbook note.

### Implementation summary

- `guardkit/orchestrator/environment_bootstrap.py`: added
  `UvSourcesRequireUvError`, `_uv_on_path`, `_pyproject_has_uv_sources`,
  `_resolve_python_pyproject_install_command`. Wired the resolver into
  `ProjectEnvironmentDetector._scan_directory` for the `pyproject.toml`
  branch only — `poetry.lock` and `requirements.txt` paths are unchanged
  (those layouts don't use uv-sources).
- `guardkit/orchestrator/feature_orchestrator.py`: catches
  `UvSourcesRequireUvError` from `detector.detect()` and re-raises as
  `FeatureOrchestrationError` so it propagates as a hard-fail before any
  pip work runs (rather than being swallowed by the generic
  `except Exception` that falls through to a warning + `return None`).
  The actionable error message lives in the exception itself (mentions
  the file, the install URL for uv, and the option to remove the block);
  it intentionally does **not** mention `bootstrap_failure_mode: warn` —
  warn-mode is the wrong escape hatch for an install-system mismatch.
- `tests/unit/test_environment_bootstrap.py`: new
  `TestPyprojectUvSourcesDetection` class (7 tests, monkeypatch on
  `shutil.which`).
- `docs/guides/uv-sources-bootstrap.md`: new doc covering the matrix,
  the option-(b) symlink coordination decision (consuming repos own
  preflight scripts, GuardKit does not provide a hook API), the CI
  requirement to install uv, and the forge migration path for
  retiring `.guardkit/preflight.sh`.
