---
id: TASK-CLN-FB61
title: "forge cleanup: retire .guardkit/preflight.sh after AB60 + AB61"
task_type: cleanup
status: backlog
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: medium
tags: [cleanup, forge, cross-repo, AB61-followup, AB60-followup, preflight]
complexity: 2
estimated_minutes: 30
estimated_effort: "30min (delete script + audit runbook references + verify autobuild on forge)"
parent_task: TASK-FIX-AB61
implementation_mode: cross-repo
target_repo: appmilla_github/forge
related_tasks:
  - TASK-FIX-AB61  # uv-sources symlink coordination — obsoletes the second half of preflight.sh
  - TASK-FIX-AB60  # uv venv arrangement — obsoletes the first half of preflight.sh
  - TASK-FIX-F09A1 # the original forge preflight.sh
context_files:
  - ../../forge/.guardkit/preflight.sh
  - ../../guardkit/tasks/completed/2026-05/TASK-FIX-AB61-uv-sources-worktree-symlink-coordination.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: forge — retire `.guardkit/preflight.sh`

## Description

`forge:.guardkit/preflight.sh` was introduced in TASK-FIX-F09A1 to do
two pieces of work that guardkit could not yet do autonomously:

1. **Create a worktree-local `.venv`** so `uv pip install -e .` could
   honour `[tool.uv.sources]` overrides. Obsoleted by **TASK-FIX-AB60**
   (guardkit now detects the no-venv stderr sentinel and runs
   `uv venv` automatically).

2. **Pre-create sibling-source symlinks** (e.g. for `nats-core`) so uv
   could resolve path-typed sources from the worktree. Obsoleted by
   **TASK-FIX-AB61** (guardkit now parses `[tool.uv.sources]` and
   pre-creates the bridging symlinks autonomously).

After AB61's helper-level cross-repo verification confirmed correct
emission against forge's actual `pyproject.toml`, the script is fully
vestigial. Keeping it carries two risks: (a) operators forget it
exists and waste time debugging "why didn't my preflight run?", (b)
its presence implies guardkit can't handle forge's bootstrap shape,
which is no longer true.

## Acceptance Criteria

- [ ] **Delete `.guardkit/preflight.sh`** from the forge repo. Single
      `git rm`. Commit message references TASK-CLN-FB61 and AB60+AB61.

- [ ] **Audit forge runbook + docs** for any references to the
      preflight script. Likely sites:
      - `forge/README.md`
      - `forge/docs/*.md` (any bootstrap / quickstart guide)
      - `forge/.guardkit/config.yaml` (if it pinned the script)
      Remove or rewrite each reference. The replacement framing is
      "guardkit handles bootstrap autonomously after AB60 + AB61."

- [ ] **Verify autobuild still works** on forge: pick any current
      feature in `forge:.guardkit/features/`, run
      `guardkit autobuild feature <FEAT-XXX> --verbose --fresh` from a
      fresh checkout. Confirm:
      1. No preflight prompt or invocation in the log.
      2. AB61's `creating uv-sources symlink` INFO line fires (post-
         operator-nit log-level bump on `feature_orchestrator.py:1282`).
      3. AB60's venv-arrangement retry fires if uv reports no venv.
      4. Bootstrap reaches success and the feature's tasks execute.

- [ ] **Close `TASK-FIX-F09A1`** in forge once this task lands —
      F09A1's deliverable is now retired by upstream guardkit fixes.

## Out of Scope

- Re-running guardkit's own AB61 verification — already passed at
  helper level.
- Touching forge's pyproject.toml itself — preflight.sh deletion does
  not require it.
- Auditing any OTHER consuming repo's preflight scripts (specialist-
  agent's stop-gap symlink was filesystem-only, not a script;
  jarvis has no preflight).

## Why a Separate Task

The cleanup is in forge, not guardkit, so it lives in forge's own
worktree branch and CI. AB61 itself only added the upstream code that
makes this cleanup possible — the deletion-side work belongs here.
