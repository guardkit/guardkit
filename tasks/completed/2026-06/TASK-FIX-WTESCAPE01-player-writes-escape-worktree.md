---
id: TASK-FIX-WTESCAPE01
title: Player file writes escape the worktree via absolute paths (LangGraph filesystem backend not path-confined)
task_type: feature
status: completed
created: 2026-06-12T20:05:00Z
updated: 2026-06-13T00:00:00Z
completed: 2026-06-13T00:00:00Z
completed_location: tasks/completed/2026-06/TASK-FIX-WTESCAPE01-player-writes-escape-worktree.md
priority: high
tags: [autobuild, langgraph, harness, sandbox, worktree, evidence-boundary]
complexity: 5
---

# Task: Worktree escape — Player writes landed in the host repo

## Problem (observed FEAT-C332 run 2, 2026-06-12)

During run 2, the autobuild Player **modified files in the MAIN guardkit
repo** while supposedly confined to the feature worktree. Host-repo mtimes
fall squarely inside Player turn windows:

| Host-repo file (MAIN, not worktree)             | mtime (local) | Player window           |
|---|---|---|
| `guardkit/orchestrator/quality_gates/coach_evidence.py`  | 17:20:02 | QAWE-002 turn 2 (17:14–17:56) |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | 17:22:09 | QAWE-002 turn 2 |
| `guardkit/orchestrator/agent_invoker.py`                 | 17:22:45 | QAWE-002 turn 2 |
| `tasks/backlog/qa-wiring-evidence/TASK-QAWE-002-*.md`    | 18:04:28 | QAWE-003 turn 1 start |

The stray content was an early draft of the QAWE-002/003 work (a
`spec_gap.deselected_files` shape that never shipped) — i.e. the Player
wrote some edits to ABSOLUTE host-repo paths and others to worktree
paths. Likely vector: the task context (scope doc §"Files referenced (all
absolute)") hands the Player absolute `/home/.../guardkit/...` paths and
the deepagents filesystem backend (Write/Edit/Read) honours absolute paths
outside the backend root. `build_autobuild_backend(cwd)` confines the
SHELL cwd, not the file tools.

The strays sat uncommitted in main until found by manual `git status`
review; they were archived to
`.guardkit/autobuild/FEAT-C332-run2-worktree-escape-evidence/*.diff` and
reverted (the authoritative implementations live on `autobuild/FEAT-C332`).

## Why this is worse than a hygiene issue

1. **Host-repo corruption**: a parallel/long autobuild run silently mutates
   the operator's main checkout; a `git add -A` in an unrelated commit
   could merge unreviewed Player output.
2. **Evidence-boundary poisoning, both directions**: the escaped writes
   are invisible to the worktree-scoped git diff, so the Player's honest
   "I modified coach_evidence.py" claim shows as "not present in git
   status" → honesty discrepancies (this contributed to run 2's
   `partial_honesty_abort` spiral, alongside TASK-FIX-SPECVIOL01).
   Sibling of TASK-AB-XREPOEV01 — same evidence-boundary meta-class,
   inverse direction (there: legitimate sibling-repo writes invisible;
   here: illegitimate out-of-tree writes possible AND invisible).

## Fix direction

1. **Confine the file tools, not just the shell**: the LangGraph/deepagents
   filesystem backend must reject (or worktree-rebase) absolute paths that
   resolve outside the backend root. Symlink-aware (`Path.resolve()` before
   the containment check; note `.guardkit/worktrees/guardkitfactory` is an
   intentional symlink — decide policy explicitly rather than implicitly).
2. **Stop feeding absolute host paths into Player context** where
   avoidable: scope docs/task files should reference worktree-relative
   paths; the prompt assembly could rewrite known host-repo absolute
   prefixes to worktree paths.
3. **Detection backstop**: after each turn, the orchestrator can cheaply
   `git status --porcelain` the HOST repo and WARN on new modifications
   appearing during a Player window (defence-in-depth, catches whatever
   slips through confinement).

## Acceptance criteria

- [x] AC-001: a Player Write/Edit to an absolute path outside the worktree
      root is rejected (tool error) or rebased into the worktree —
      reproduced by a regression test against the backend.
      → **Rejected** (not rebased — rebasing is the doubly-nested-path
      NOVMODE failure in reverse). `PathConfinedBackend` in
      `guardkitfactory/src/guardkitfactory/harness/backend_config.py`
      confines `write`/`awrite`/`edit`/`aedit` via `Path.resolve()` +
      `is_relative_to(allowed_root)`. Tests: `TestWriteConfinement`
      (absolute write/edit, relative `../` traversal, in-worktree symlink
      smuggle, async variants; NOVMODE-preservation positives).
- [x] AC-002: the guardkitfactory symlink policy is explicit (allowed or
      blocked) and tested.
      → **Allowed**, narrowly: a sibling symlink literally named
      `guardkitfactory` in `worktree.parent` (the intentional
      `.guardkit/worktrees/guardkitfactory` convention; cross-repo tasks —
      TASK-AB-XREPOEV01 lineage — legitimately write through it). Any other
      sibling symlink is rejected. Plus explicit `extra_write_roots=`
      parameter on `build_autobuild_backend`. Tests: `TestSymlinkPolicy`.
- [x] AC-003: host-repo `git status` is clean after a full autobuild turn
      whose prompt contains absolute host-repo paths (integration test or
      recorded fixture).
      → Recorded-fixture form: `TestHostRepoStaysClean` builds a real host
      git repo + nested worktree, replays the FEAT-C332 run-2 escape shapes
      (edit tracked host file, write new host file, both via absolute
      paths), asserts tool errors AND `git status --porcelain` empty.
- [x] AC-004: escaped-write attempts surface in the turn log (WARNING) so
      operators see confinement doing work.
      → Every rejection logs `WARNING` on
      `guardkitfactory.harness.backend_config` ("AutoBuild write
      confinement: rejected …"). Test: `TestEscapeObservability`.

## Outcome (2026-06-12)

Implemented in **guardkitfactory** (sibling repo):
`PathConfinedBackend` delegating wrapper (same pattern as
`TruncatingBackend`) wired as the always-on composite default in
`build_autobuild_backend`. The permissions-middleware route was not
viable (DeepAgents declined execute-capable-backend permissions, #2894 —
see `permissions.py` NOPERMS docstring).

**Two latent defects found and fixed en route** (both pre-existing on the
Coach-gather path, surfaced by the new wrapper):

1. `CompositeBackend.execute` gates on
   `isinstance(default, SandboxBackendProtocol)` — an ABC, so
   `__getattr__`-delegating wrappers failed it and `execute` raised
   `NotImplementedError` whenever `max_tool_result_chars` was set (latent
   since TASK-PERF-COACHSYNTH). Fixed via
   `SandboxBackendProtocol.register(...)` for both wrappers + regression
   test `test_wrapped_default_still_passes_composite_execute_gate`.
2. `TruncatingBackend.execute(*args, **kwargs)` hid the `timeout` name
   from `execute_accepts_timeout`'s class-level signature introspection,
   silently dropping per-call timeout overrides. Fixed with explicit
   `timeout` parameter + regression test
   `test_execute_honours_per_call_timeout_override_when_gather_capped`.

guardkit-side: only `tests/orchestrator/harness/test_selector.py` shape
assertion updated (composite default is now the confinement wrapper;
`LocalShellBackend` at `default._inner`). The confinement claim at
`selector.py:363` is now true for file tools.

Tests: guardkitfactory 205 passed / 8 skipped (pre-existing NOVMODE/NOPERMS
skips); guardkit `tests/orchestrator/harness/` 104 passed / 3 skipped.
Plan: `docs/state/TASK-FIX-WTESCAPE01/implementation_plan.md`.

## Follow-ups (explicitly NOT done — fix-direction items 2 and 3)

- Orchestrator-side host-repo `git status --porcelain` backstop after each
  Player turn (defence-in-depth; the task's "can", not a "must").
- Prompt-assembly rewriting of absolute host-repo path prefixes to
  worktree-relative ones in scope docs / task context.
- SDK-harness equivalent confinement (defect observed on LangGraph only;
  SDK harness has `cwd=worktree` + `acceptEdits`, same theoretical gap).

## Evidence

- Stray diffs: `.guardkit/autobuild/FEAT-C332-run2-worktree-escape-evidence/`
- Run log: `.guardkit/autobuild/FEAT-C332-run2-stdout.log`
- Backend constructor contract: `select_harness(langgraph)` requires
  `cwd=` "so guardkitfactory.harness.build_autobuild_backend(cwd) can build
  a path-confined LocalShellBackend" (`guardkit/orchestrator/harness/selector.py:363`)
  — the confinement claim this defect falsifies for file tools.
- Siblings: TASK-AB-XREPOEV01 (evidence boundary, inverse direction);
  TASK-FIX-SPECVIOL01 (the honesty spiral this fed).
