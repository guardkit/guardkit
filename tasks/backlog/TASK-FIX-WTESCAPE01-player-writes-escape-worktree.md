---
id: TASK-FIX-WTESCAPE01
title: Player file writes escape the worktree via absolute paths (LangGraph filesystem backend not path-confined)
task_type: feature
status: backlog
created: 2026-06-12T20:05:00Z
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

- [ ] AC-001: a Player Write/Edit to an absolute path outside the worktree
      root is rejected (tool error) or rebased into the worktree —
      reproduced by a regression test against the backend.
- [ ] AC-002: the guardkitfactory symlink policy is explicit (allowed or
      blocked) and tested.
- [ ] AC-003: host-repo `git status` is clean after a full autobuild turn
      whose prompt contains absolute host-repo paths (integration test or
      recorded fixture).
- [ ] AC-004: escaped-write attempts surface in the turn log (WARNING) so
      operators see confinement doing work.

## Evidence

- Stray diffs: `.guardkit/autobuild/FEAT-C332-run2-worktree-escape-evidence/`
- Run log: `.guardkit/autobuild/FEAT-C332-run2-stdout.log`
- Backend constructor contract: `select_harness(langgraph)` requires
  `cwd=` "so guardkitfactory.harness.build_autobuild_backend(cwd) can build
  a path-confined LocalShellBackend" (`guardkit/orchestrator/harness/selector.py:363`)
  — the confinement claim this defect falsifies for file tools.
- Siblings: TASK-AB-XREPOEV01 (evidence boundary, inverse direction);
  TASK-FIX-SPECVIOL01 (the honesty spiral this fed).
