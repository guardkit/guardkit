---
id: TASK-DOC-CKPTABSF01
title: Document the checkpoint-layer false-red as an instance of absence-of-failure-is-not-success
status: completed
task_type: documentation
created: 2026-06-14T13:00:00Z
updated: 2026-06-14T14:45:00Z
completed: 2026-06-14T14:45:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-DOC-CKPTABSF01/
state_transition_reason: "Docs-only task complete; all ACs verified"
priority: medium
complexity: 2
related: [TASK-FIX-CKPTTESTRED01, TASK-AB-FIX-INVAB1, TASK-DOC-1B4D]
implementation_mode: task-work
tags: [docs, rules, absence-of-failure, checkpoints, false-red, knowledge-capture]
---

# Task: Document the checkpoint-layer false-red instance in the absence-of-failure rule

## Why this task exists

TASK-FIX-CKPTTESTRED01 (commit `c6b5e7d9`, 2026-06-14) fixed a fourth,
previously-undocumented instance of the absence-of-failure meta-class: the
checkpoint pollution detector reading an **absent** test signal
(`tests_run`/`tests_passed` = `None`, or the LLM-Coach report lacking
`validation_results.quality_gates`) as a **negative** one (tests failed),
producing a false-red `unrecoverable_stall`.

The fix landed code + a Graphiti `guardkit__project_decisions` node
("checkpoint test signal is tri-state (absent is UNKNOWN not failure)"), but
the canonical rule file
[`.claude/rules/absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md)
was **not** updated to enumerate this instance. The rule's own "Prior art" /
instances list is how the *next* agent discovers the pattern; leaving a landed
instance out of it is itself a "Graphiti/rules-didn't-capture-it" failure (the
exact failure mode `stack-plugin-architecture.md` warns about).

This is a docs-only follow-up: record the instance so the family stays
self-documenting and greppable.

## Scope

1. **Update `.claude/rules/absence-of-failure-is-not-success.md`:**
   - Add TASK-FIX-CKPTTESTRED01 to the recurrence list ("Why this rule
     exists") as the checkpoint-layer, false-red instance (2026-06-14,
     FEAT-9DDE run 5).
   - Add a "Prior art" / sibling-rule cross-reference noting the
     checkpoint layer (`worktree_checkpoints.py` `should_rollback` +
     `autobuild.py` `_extract_tests_passed`) now treats an absent test
     signal as tri-state UNKNOWN, excluded from the consecutive-failure
     tally.
   - Add the grep-able fingerprint for the new instance, e.g.:
     `rg -n "cp.tests_passed is False" guardkit/orchestrator/worktree_checkpoints.py`
     and `rg -n "Optional\[bool\]" guardkit/orchestrator/autobuild.py` near
     `_extract_tests_passed`.
2. **Cross-link the inverse/family rules** that already list each other so
   the new instance appears consistently in all of:
   `path-string-mismatch-is-not-dishonesty.md`,
   `harness-cancellation-contract.md`,
   `evidence-boundary-narrower-than-write-surface.md` (only where they
   enumerate the absence-of-failure instance set — do not bloat them).
3. **Note the supersession**: the rule text should record that
   TASK-FIX-CKPTTESTRED01 supersedes TASK-FIX-64EE's `None → False`
   coercion *for the absent-signal case only* (a genuine ran-and-failed
   `False` still stalls).

## Acceptance Criteria

- [x] `.claude/rules/absence-of-failure-is-not-success.md` lists
      TASK-FIX-CKPTTESTRED01 as the checkpoint-layer, false-red instance,
      with date (2026-06-14), origin (FEAT-9DDE run 5), and fix commit
      (`c6b5e7d9`). — instance 4 in "Why this rule exists" + Prior-art bullet.
- [x] The rule includes a grep-able fingerprint for the new instance that
      actually matches the committed code (`cp.tests_passed is False` in
      `worktree_checkpoints.py`; tri-state `_extract_tests_passed` in
      `autobuild.py`). — added to "Grep-able signature"; both `rg` commands
      verified to return hits against the committed tree.
- [x] The supersession of TASK-FIX-64EE's `None → False` coercion (absent
      case only) is stated in the rule. — stated in instance 4 and the
      Prior-art bullet ("a genuine ran-and-failed `False` still stalls").
- [x] No code changes (documentation/rules only); no existing rule's grep
      signatures are broken by the edit. — only the rule `.md` was edited;
      existing `rg` signatures were appended-to, not modified. (The
      `autobuild.py` working-tree change present in this checkout belongs to
      the separate in-flight TASK-AB-CKPTGATE01 and was NOT touched by this
      task.)

## Evidence
- Landed fix: commit `c6b5e7d9` (TASK-FIX-CKPTTESTRED01); task at
  `tasks/completed/TASK-FIX-CKPTTESTRED01/TASK-FIX-CKPTTESTRED01.md`.
- Graphiti node (already written): `guardkit__project_decisions` —
  "Decision: TASK-FIX-CKPTTESTRED01 - checkpoint test signal is tri-state
  (absent is UNKNOWN not failure)".
- Run-5 evidence: `docs/retro/run5-evidence/`,
  `.guardkit/autobuild/FEAT-9DDE-run5-stdout.log`.
