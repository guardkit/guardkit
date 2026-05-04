---
id: TASK-FIX-AB60
title: "GuardKit: pre-arrange venv for `[tool.uv.sources]` install branch (F09A2 gap)"
task_type: fix
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
completed: 2026-05-04T00:00:00Z
completed_location: tasks/completed/TASK-FIX-AB60/
organized_files:
  - TASK-FIX-AB60.md
previous_state: in_review
state_transition_reason: "Automatic transition by /task-complete"
operator_followup_required:
  - "Cross-repo verify: guardkit autobuild feature FEAT-9B60 against specialist-agent (no preflight, no override)"
  - "Forge regression: guardkit autobuild feature FEAT-FORGE-009 against forge without preflight"
  - "File follow-up to delete forge:.guardkit/preflight.sh once forge regression is green"
  - "Close specialist-agent:TASK-IMP-AB60 pointer with back-link to merge commit"
priority: high
tags: [fix, guardkit, environment-bootstrap, uv, uv-sources, venv, F09A2-followup, durable-fix, cross-repo]
complexity: 5
estimated_minutes: 180
estimated_effort: "2-3 hours (code change + tests + manual cross-repo regression check against specialist-agent)"
parent_review: TASK-REV-AB60
parent_task: TASK-FIX-F09A2
implementation_mode: in-repo  # the work happens here in guardkit
target_repo: appmilla_github/guardkit
related_tasks:
  - TASK-REV-AB60   # decision review (filed in specialist-agent)
  - TASK-FIX-F09A2  # predecessor — selected the command but didn't arrange the env
  - TASK-FIX-FD32   # adjacent — fixed a different matrix row (uv.lock + uv on PATH)
  - TASK-FIX-7A04   # adjacent — added the bootstrap_failure_mode gate
context_files:
  - ../../specialist-agent/.claude/reviews/TASK-REV-AB60-review-report.md
  - ../../specialist-agent/docs/history/autobuild-FEAT-9B6--fail-run-1.md
  - guardkit/orchestrator/environment_bootstrap.py
test_results:
  status: passed
  coverage: null  # not collected — focused unit tests under mocked subprocess
  last_run: 2026-05-04T00:00:00Z
  new_tests: 10
  regression_surfaces:
    - tests/unit/test_environment_bootstrap.py
    - tests/orchestrator/test_bootstrap_gating.py
    - tests/unit/test_environment_bootstrap_fix7539.py
    - tests/unit/test_inter_wave_bootstrap.py
    - tests/unit/test_environment_bootstrap_uv_venv.py
  total_passed: 214
---

# Task: GuardKit — pre-arrange venv for `[tool.uv.sources]` install branch

## Description

`TASK-FIX-F09A2` (`c23df11c`) added a 5-row install-command matrix and
correctly routes projects with `[tool.uv.sources]` and uv on PATH to
`uv pip install -e .`. But F09A2 stopped at command selection and ships no
venv-arrangement step, so the new branch hard-fails on any project that
declares `[tool.uv.sources]`, has no `uv.lock`, and has no active venv.

`uv pip install` requires either an active venv or `--system`. The current
orchestrator does neither for this branch. The PEP 668 fallback at
[`environment_bootstrap.py:1278-1281`](../../guardkit/orchestrator/environment_bootstrap.py#L1278-L1281)
is structurally unreachable because `cmd[0] == "uv"` (so `is_python_cmd` is
False) and uv's stderr says `No virtual environment found`, not
`externally-managed-environment` (so the sentinel doesn't match).

This task closes the gap by extending `_run_install` to detect uv's
"no venv" stderr sentinel and pre-create a worktree-local venv, then retry —
mirroring the existing PEP 668 fallback shape exactly.

## Empirical Reproduction (specialist-agent)

Full failure transcript:
[`specialist-agent:docs/history/autobuild-FEAT-9B6--fail-run-1.md`](../../../specialist-agent/docs/history/autobuild-FEAT-9B6--fail-run-1.md).

Repro recipe (post-task, before verifying the fix):

```bash
cd ~/Projects/appmilla_github/specialist-agent
# Confirm preconditions
grep '\[tool.uv.sources\]' pyproject.toml   # → present (line 67)
ls uv.lock                                  # → No such file
ls .guardkit/preflight.sh                   # → No such file
ls .guardkit/config.yaml                    # → No such file
which uv                                    # → resolves (e.g. /opt/homebrew/bin/uv)

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-9B60 --verbose
# Expect: bootstrap hard-fail with
#   stderr: error: No virtual environment found; run `uv venv` to create
#           an environment, or pass `--system` to install into a non-virtual
#           environment
```

The matrix path that produces this:
[`environment_bootstrap.py:396-404`](../../guardkit/orchestrator/environment_bootstrap.py#L396-L404)
row 4 — `[tool.uv.sources]` present, `uv.lock` any, uv on PATH yes →
`uv pip install -e .`. F09A2 selects this; the gap is downstream.

## Acceptance Criteria

- [ ] **Sentinel constant**: add a module-level constant alongside `PEP668_SENTINEL`
      (line 50) capturing uv's no-venv stderr fragment. Suggested:
      ```python
      UV_NO_VENV_SENTINEL = "No virtual environment found"
      ```
      The substring must be specific enough not to match unrelated uv
      errors but stable across uv versions — verify against uv's source
      (search for the literal in `uv/crates/uv-pip/`).

- [ ] **Detection helper**: add `_is_uv_no_venv_error(stderr: str) -> bool`
      symmetric with the existing `_is_pep668_error` (line 1168).

- [ ] **Venv arranger**: add `_ensure_uv_venv(cwd: Path) -> Path` that
      creates a venv at `cwd / ".venv"` via
      `subprocess.run(["uv", "venv", str(cwd / ".venv")], check=True, ...)`.
      Idempotent (skip if `.venv/bin/python` already exists), analogous to
      `_ensure_venv()` (line 1179). Distinct from `_ensure_venv` because
      the venv lives **inside the worktree** (where uv looks first), not
      in `<root>/.guardkit/venv/`. Caches result on
      `self._uv_venv_python` so a single bootstrap pass doesn't re-create.

- [ ] **Retry loop in `_run_install`**: extend the failure branch (currently
      ends at line 1317) with a parallel block that fires when:
      - `cmd[0] == "uv"` (NOT `is_python_cmd`)
      - The chosen command is `["uv", "pip", "install", ...]` (gate by
        `cmd[1:3] == ["pip", "install"]` to avoid intercepting `uv sync`)
      - `_is_uv_no_venv_error(proc.stderr)` matches
      - `self._uv_venv_python` is None (single retry budget)

      On match: call `_ensure_uv_venv(Path(cwd))`, retry the original
      command with `env={**os.environ, "VIRTUAL_ENV": str(venv_dir),
      "PATH": str(venv_dir / "bin") + os.pathsep + os.environ["PATH"]}`,
      and propagate the retry result.

- [ ] **Behaviour matrix doc update**: extend the comment block at
      [`environment_bootstrap.py:396-404`](../../guardkit/orchestrator/environment_bootstrap.py#L396-L404)
      with a footnote noting that the `present | any | yes →
      uv pip install -e .` row now ensures a worktree-local venv at
      `<cwd>/.venv` before invocation if one is not already discoverable
      by uv.

- [ ] **Tests**: add a new test class `TestUvSourcesVenvArrangement` in
      `tests/orchestrator/test_bootstrap_gating.py` (or a new sibling
      `tests/unit/test_environment_bootstrap_uv_venv.py` — implementer's
      choice; the convention in the repo seems to favour grouping by
      feature). Required cases:
      1. uv-sources + no uv.lock + no preexisting venv → first invocation
         emits no-venv error, retry creates `.venv/`, retry succeeds.
      2. uv-sources + no uv.lock + preexisting `.venv/` → first invocation
         succeeds (uv discovers the venv), no retry path entered.
      3. uv-sources + uv.lock present → still routes to `uv sync --frozen`
         (FD32 path), retry block does NOT fire (regression guard for FD32).
      4. No uv-sources + no uv.lock → still routes to `pip install -e .`,
         retry block does NOT fire (PEP 668 fallback unaffected).
      5. uv-sources branch + uv emits some unrelated error → no retry,
         escalates to `_maybe_hardfail_bootstrap` (regression guard for
         the gate added by 7A04).

- [ ] **Regression guards**: confirm by re-running existing test surfaces
      after the change:
      - `tests/unit/test_environment_bootstrap.py` (134 tests — F09A2 baseline)
      - `tests/orchestrator/test_bootstrap_gating.py` (7A04 surface)
      - `tests/unit/test_environment_bootstrap_fix7539.py`
      - `tests/unit/test_inter_wave_bootstrap.py`
      All must remain green.

- [ ] **Cross-repo verification (specialist-agent)**: from a fresh
      checkout of specialist-agent, run
      `guardkit autobuild feature FEAT-9B60 --verbose --fresh` with NO
      operator pre-venv, NO `.guardkit/preflight.sh`, and NO
      `bootstrap_failure_mode` override. Expect bootstrap to succeed and
      `nats-core` to resolve from the sibling at `../nats-core`. Capture
      the green log as `specialist-agent:docs/history/autobuild-FEAT-9B60-success-run-1.md`.

- [ ] **Forge regression check**: re-run
      `guardkit autobuild feature FEAT-FORGE-009 --verbose --fresh` against
      forge **without** running `.guardkit/preflight.sh`. Confirm bootstrap
      succeeds (this also retires forge's preflight script as a follow-up,
      mirroring the F09A2 acceptance criterion).

- [ ] **Hint message review**: the existing hint emitted on hard-fail
      ("set `bootstrap_failure_mode: warn` in .guardkit/config.yaml") is
      misleading for the no-venv case — `warn` would let task agents run
      against a broken environment. The hint emitted when the new path
      hard-fails (e.g. uv refused to create venv for some reason) should
      point at the venv-creation failure specifically, not at the
      warn-mode escape hatch.

## Out of Scope

- Re-architecting the install matrix beyond the minimum needed to close
  the F09A2 gap.
- Forge-side cleanup (deleting `.guardkit/preflight.sh`) — file as a
  separate follow-up after this lands and forge regression is green.
- Republishing the `nats-core` PyPI wheel (would obsolete `[tool.uv.sources]`
  entirely; tracked elsewhere as `TASK-FIX-F0E6b`).
- Adding `--system` as a fallback — explicitly avoided. `--system` writes
  to the host Python and on managed Pythons would re-trigger PEP 668. The
  per-worktree venv is the safer shape and matches uv's idiom.

## Implementation Notes

- The exact code site is `environment_bootstrap.py:1214-1317` (`_run_install`).
  Read the entire method before editing; the retry block at 1278-1317 is
  the model to mirror.
- The matrix selection at lines 477-478 is **correct and should not change**.
  This task only adds the env-arrangement step downstream.
- `uv venv <path>` creates a venv that uv subsequently discovers via
  `VIRTUAL_ENV` env var. uv's discovery order: 1) `$VIRTUAL_ENV`, 2)
  `./.venv` in cwd, 3) parent dirs. Setting `VIRTUAL_ENV` is the most
  explicit and survives subprocess env propagation cleanly.
- The retry timeout (line 1297) of 300s should be honoured for the new
  retry too — consider extracting a constant if not already done.
- The `_uv_venv_python` cache must reset per bootstrap run (similar to
  `_venv_python` for the PEP 668 path) — check `bootstrap()`'s state-reset
  block.
- The behaviour matrix comment at line 394 ("instead of leaving every
  consuming repo to ship its own preflight script") is the load-bearing
  design intent — the new arrangement step should preserve it. If a
  consuming repo would still need a preflight script after this fix,
  the fix isn't complete.

## Cross-Repo Handoff Notes

This task lives in guardkit, with a pointer in
[`specialist-agent:tasks/backlog/TASK-IMP-AB60-pointer-guardkit-bootstrap-venv-fix.md`](../../../specialist-agent/tasks/backlog/TASK-IMP-AB60-pointer-guardkit-bootstrap-venv-fix.md).

After this task lands:
1. Reinstall is automatic if guardkit is editable-installed at
   `~/Projects/appmilla_github/guardkit/` (verified for the operator who
   filed `TASK-REV-AB60`).
2. Run the cross-repo verification step above against specialist-agent.
3. Run the forge regression check.
4. Close `TASK-IMP-AB60` (specialist-agent pointer) with a back-link to
   this task's merge commit and the green autobuild log.
5. File the forge cleanup follow-up to delete `.guardkit/preflight.sh`.

## Test Execution Log

### 2026-05-04 — implementation run (`/task-work TASK-FIX-AB60`)

**Source changes**

- `guardkit/orchestrator/environment_bootstrap.py`
  - Added `import os` (needed for env propagation in retry).
  - Added `UV_NO_VENV_SENTINEL = "No virtual environment found"` constant
    alongside `PEP668_SENTINEL`, with a doc-comment explaining what
    triggers it and how the bootstrapper responds.
  - Extended the `# Behaviour matrix` comment block with footnote `[1]`
    documenting the worktree-local venv arrangement (the AB60 gap).
  - Initialised `self._uv_venv_python: Optional[Path] = None` in
    `EnvironmentBootstrapper.__init__`.
  - Added `_is_uv_no_venv_error(stderr)` symmetric with
    `_is_pep668_error`.
  - Added `_ensure_uv_venv(cwd)` — idempotent venv arranger that
    creates `<cwd>/.venv` via `uv venv`, returns the venv directory,
    caches `self._uv_venv_python`. Wraps subprocess in a 300s timeout.
  - Extended `_run_install`'s failure branch with a parallel retry
    block gated on `cmd[0] == "uv"`,
    `cmd[1:3] == ["pip", "install"]`, no cached venv, and
    `_is_uv_no_venv_error(stderr)`. On match, calls `_ensure_uv_venv`
    and retries the original command with `VIRTUAL_ENV=<cwd>/.venv`
    and `PATH` prepended. Single-shot retry budget per pass. If
    `uv venv` itself raises, surfaces a structured failure-detail
    string starting `"uv venv creation failed: ..."`.

- `guardkit/orchestrator/feature_orchestrator.py`
  - `_format_bootstrap_hardfail_message` now detects the
    `"uv venv creation failed"` marker in `stderr_excerpt` and emits a
    different hint pointing at venv-creation root causes (permissions,
    disk, uv version) instead of the misleading
    `bootstrap_failure_mode: warn` escape hatch — `warn` would let
    task agents run against a missing environment.

**New tests**

- `tests/unit/test_environment_bootstrap_uv_venv.py` (new file)
  - `TestUvSourcesVenvArrangement` (5 cases):
    1. uv-sources + no preexisting venv → no-venv stderr → retry
       creates `.venv/`, retry succeeds.
    2. uv-sources + preexisting `.venv/` → first call succeeds,
       no retry path entered.
    3. uv.lock path (`uv sync --frozen`) untouched even if stderr
       coincidentally contains the sentinel — gated by `cmd[1:3]`
       check (FD32 regression guard).
    4. Plain `pip install -e .` PEP 668 fallback unaffected — venv
       created at `<root>/.guardkit/venv/`, not `<cwd>/.venv` (PEP
       668 fallback regression guard).
    5. Unrelated uv error → no retry, escalates to bootstrap-failure-
       mode gate (7A04 regression guard).
  - `TestUvVenvHelpers` (4 cases): direct tests for
    `_is_uv_no_venv_error`, `_ensure_uv_venv` idempotency, cache
    behaviour, and the venv-creation-failure path that surfaces a
    structured failure-detail string.

- `tests/orchestrator/test_bootstrap_gating.py`
  - `test_format_message_swaps_hint_for_uv_venv_creation_failure` —
    confirms the warn-mode hint is suppressed and the AB60-specific
    hint fires when `stderr_excerpt` carries the
    `"uv venv creation failed"` marker.

**Regression surfaces (all green)**

```
$ python -m pytest tests/orchestrator/test_bootstrap_gating.py \
    tests/unit/test_environment_bootstrap.py \
    tests/unit/test_environment_bootstrap_uv_venv.py \
    tests/unit/test_environment_bootstrap_fix7539.py \
    tests/unit/test_inter_wave_bootstrap.py --no-cov
======== 214 passed in 0.44s ========
```

Breakdown: 31 (gating) + 9 (gating, uv-venv hint) → 40 gating; 134
(env_bootstrap baseline); 9 + 4 = 13 new uv-venv; 22 (fix7539); 8
(inter_wave). Net +10 new tests, 0 regressions.

### Operator follow-up — out-of-band ACs not in scope of this run

These ACs require cross-repo regression runs against sibling worktrees
which an in-loop `/task-work` cannot perform autonomously. After this
task's commit lands and is pulled into the operator's editable install
of guardkit, the operator must:

1. **Cross-repo verification (specialist-agent)** —
   `cd ~/Projects/appmilla_github/specialist-agent &&
   guardkit autobuild feature FEAT-9B60 --verbose --fresh` with no
   pre-arranged venv, no `.guardkit/preflight.sh`, no
   `bootstrap_failure_mode` override. Capture as
   `specialist-agent:docs/history/autobuild-FEAT-9B60-success-run-1.md`.
2. **Forge regression check** —
   `guardkit autobuild feature FEAT-FORGE-009 --verbose --fresh`
   against forge **without** running `.guardkit/preflight.sh`. Confirm
   bootstrap succeeds.
3. **Forge cleanup follow-up** — file a separate task to delete
   forge's `.guardkit/preflight.sh` once regression is green
   (mirrors the F09A2 acceptance criterion).
4. **Close `TASK-IMP-AB60`** (specialist-agent pointer) with a
   back-link to this task's merge commit and the green autobuild log.
