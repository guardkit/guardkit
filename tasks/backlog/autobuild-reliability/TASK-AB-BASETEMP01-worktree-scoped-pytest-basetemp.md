---
id: TASK-AB-BASETEMP01
title: Worktree-scoped pytest --basetemp for orchestrator-run deterministic test executions
status: backlog
created: 2026-07-04T09:36:00Z
priority: low
tags: [autobuild, pytest, basetemp, isolation, concurrent-loops, coach]
complexity: 2
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Worktree-scoped pytest --basetemp for orchestrator-run deterministic test executions

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 16 (R1
operational lesson → small code).

Two concurrent autobuild loops on the same machine raced on the shared
`/tmp/pytest-of-<user>` pytest basetemp — the ABL-005 Coach died on it three
turns straight. pytest's default basetemp is per-user, not per-run, so any
two orchestrator-driven pytest invocations on one host can collide on
tmp-dir creation/cleanup and manufacture spurious reds that have nothing to
do with the code under test.

Fix: have the deterministic oracle pass a **per-invocation isolated**
`--basetemp` via the existing `pytest_argv` construction layer — one argv
addition, no new mechanism.

> **Design revision at implementation time (2026-07-04):** the basetemp lands
> under the SYSTEM temp dir (`tempfile.mkdtemp(prefix="guardkit-pytest-<context>-")`,
> cleaned up in a `finally`), NOT inside the worktree as first drafted. A
> worktree-local tmp dir would be swept into checkpoints — `.guardkit/` under
> a worktree is not gitignored and `worktree_checkpoints` stages the entire
> tree with `git add -A` — recreating the evidence-noise class TASK-FIX-EVBINST01
> fixed. AC-005 below is amended accordingly; AC-001/AC-006 "worktree-scoped"
> reads as "per-invocation isolated".

The sibling operational lessons from the same retro (one-loop-per-llama-swap;
monitors-must-terminate) stay as operator documentation, not code — this
task carries only the basetemp slice.

## Acceptance Criteria

- [ ] AC-001: Every orchestrator-constructed pytest invocation
      (deterministic Coach oracle / independent-test subprocess path) passes
      a `--basetemp` scoped under the task's worktree, so two concurrent
      loops on one host cannot share a basetemp.
- [ ] AC-002: The argv addition goes through the existing `pytest_argv`
      construction layer (single source of truth) — not duplicated at each
      call site.
- [ ] AC-003: A caller-supplied `--basetemp` already present in a configured
      command is not overridden (respect explicit operator config).
- [ ] AC-004: Test verdict semantics are unchanged — this is pure tmp-dir
      isolation. No change to pass/fail/absent classification, timeouts, or
      counts.
- [ ] AC-005 (amended, see design revision above): The basetemp directory
      lands under the SYSTEM temp dir with a per-invocation unique,
      context-labelled name, is removed best-effort in a `finally`, and is
      therefore structurally outside evidence collection (`git add -A`
      checkpoints can never sweep it).
- [ ] AC-006: Regression tests: (a) argv contains the worktree-scoped
      `--basetemp`; (b) explicit basetemp respected; (c) two simulated
      concurrent invocations get distinct basetemps.

## Implementation Notes

File:line anchors from the xref (§5 item 16):

- The existing `pytest_argv` construction layer used by the deterministic
  oracle (independent-test subprocess path in
  `guardkit/orchestrator/quality_gates/coach_validator.py`; the BDD runner's
  `_build_pytest_argv` in
  `guardkit/orchestrator/quality_gates/bdd_runner.py` is the sibling shape).
- Failure evidence: ABL-005 Coach died three turns straight on the shared
  `/tmp/pytest-of-<user>` race (R1 operational trace).
- Placement: under the feature worktree so cleanup is automatic; check
  `.gitignore`/checkpoint behaviour (`worktree_checkpoints.py:470-474`
  stages the entire tree with `git add -A`).

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Tri-state stays tri-state** (§6): a basetemp-related failure to create
  the directory must not fabricate a ran-and-failed verdict — if the oracle
  cannot run, that is an ABSENT signal
  (`.claude/rules/absence-must-survive-every-reconciliation-layer.md`);
  prefer fail-open (drop the flag, log) over failing the run on tmp-dir
  trouble.
- **Glue exclusion from independent tests stays** (§6; TASK-FIX-CC-BDD):
  touching `pytest_argv` construction must not disturb the BDD-glue
  exclusion from the Coach's independent pytest command
  (`coach_validator.py:6740-6822`).
- **Evidence boundary discipline**
  (`.claude/rules/evidence-boundary-narrower-than-write-surface.md` /
  `.claude/rules/path-string-mismatch-is-not-dishonesty.md`): the basetemp
  dir is orchestrator-induced filesystem noise — it must not leak into
  `files_modified` attribution or checkpoint contents where an honesty gate
  could read it as Player work.
- **Scope**: the one-loop-per-llama-swap and monitors-must-terminate lessons
  are operator doc (xref §5 item 16), NOT code in this task.
