---
id: TASK-AB-NULLEVID01
title: Deterministic approve→feedback override when evidence gathering is incomplete
status: backlog
created: 2026-07-04T09:31:00Z
priority: high
tags: [autobuild, coach, evidence-bundle, null-evidence, deterministic-override, false-green]
complexity: 4
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Deterministic approve→feedback override when evidence gathering is incomplete

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 7 (R4 gap 3 —
FEAT-SMP-002 / TASK-SMP2-07, the "null-evidence-approve" gap).

When the Coach's evidence gathering aborts early (`partial_honesty_abort`),
the returned bundle has everything downstream `None`
(`coach_validator.py:2803-2816`) and **never sets `signal_absent`** — so the
deterministic backstop `_reconcile_absent_independent_test_signal`
explicitly no-ops (`agent_invoker.py:5400-5404`). The only thing standing
between a null-evidence turn and `approve` is **prompt guard #5**
(`agent_invoker.py:3468-3475`) — an advisory LLM instruction, which is
exactly the shape `structural-defence-beats-prompt-instruction` forbids for
a gating invariant.

On SMP2-07 turn 2, evidence gathering *did* re-run (the approve was enabled
by R4 gaps 1+2, tracked in TASK-AB-BDDAUTHOR01), but gap 3 is **live for any
task whose turn-2 follows a null-evidence turn**.

Fix: a deterministic code override `approve→feedback` whenever the evidence
bundle's `gathering_status != "complete"`, shaped **exactly** like
`_reconcile_absent_independent_test_signal` — including the
`coach_turn_N.json` re-persist, so Layer-4 late-approval reconciliation
cannot resurrect the stale `approve` off disk.

Secondary (may split out if regression care demands): the "no non-glue tests
found → synthetic `tests_passed=True, command='skipped'`" fallback
(`coach_validator.py:4616-4623`) manufactures a pass-shaped result from an
absent oracle; consider making it `signal_absent=True` instead — but this
interacts with guard #6 / the absent-signal backstop and needs its own
regression analysis.

## Acceptance Criteria

- [ ] AC-001: A deterministic guard in `AgentInvoker` overrides an LLM-Coach
      `approve` to `feedback` whenever the evidence bundle's
      `gathering_status != "complete"`. The override is code, not prompt —
      prompt guard #5 remains as defence-in-depth only.
- [ ] AC-002: The override is shaped like
      `_reconcile_absent_independent_test_signal`: called immediately after
      verdict validation at the post-synthesis seam, logs at WARNING, and
      emits an actionable feedback issue naming the incomplete gathering
      status as the reason.
- [ ] AC-003: The override **re-persists the flipped verdict to
      `coach_turn_N.json`** (fail-open on the write: `try/except OSError`,
      WARNING log, in-memory override still applies) — so
      `_check_late_approval` cannot read a stale `approve` off disk.
- [ ] AC-004: The guard runs in every Coach path that can produce an
      `approve` from a null-evidence bundle (deterministic and LLM-synthesis
      paths alike).
- [ ] AC-005: A `feedback` verdict is left untouched (nothing to override);
      a complete bundle (`gathering_status == "complete"`) is left
      untouched.
- [ ] AC-006: A task that yields null-evidence turns forever terminates via
      `max_turns` with `success=False`, never `approve` (no
      false-green-by-non-termination; the override converts the turn to
      feedback, it does not extend budgets).
- [ ] AC-007: Regression tests: (a) null-evidence approve → feedback with
      on-disk `coach_turn_N.json` flipped (mirror
      `test_override_rewrites_coach_turn_file_on_disk`); (b) complete-bundle
      approve untouched; (c) disk-write failure does not unblock the turn.
- [ ] AC-008: The existing `signal_absent` backstop
      (`_reconcile_absent_independent_test_signal`) is NOT disarmed or
      bypassed — both guards coexist; regression fingerprints for it still
      match.

## Implementation Notes

File:line anchors from the xref (§3 R4 gap 3, §5 item 7):

- `guardkit/orchestrator/quality_gates/coach_validator.py:2803-2816` —
  `partial_honesty_abort` bundle: everything downstream `None`,
  `signal_absent` never set (the hole).
- `guardkit/orchestrator/agent_invoker.py:5400-5404` — the existing
  absent-signal backstop explicitly no-ops on this bundle shape.
- `guardkit/orchestrator/agent_invoker.py:3468-3475` — prompt guard #5 (the
  advisory instruction currently doing the gating; keep as defence-in-depth).
- Shape template: `_reconcile_absent_independent_test_signal`
  (`agent_invoker.py:5348+`) including its `coach_output_path.write_text`
  re-persist (`agent_invoker.py:5447-5455`) and its call-site right after
  `_validate_coach_decision`.
- Layer-4 reader that makes the persist load-bearing:
  `feature_orchestrator._check_late_approval` (reads `decision` straight off
  `coach_turn_*.json`).
- Secondary surface: `coach_validator.py:4616-4623` — the synthetic
  `tests_passed=True, command='skipped'` fallback (pass-shaped result from
  an absent oracle; candidate for `signal_absent=True`, needs guard-#6
  regression care).

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Deterministic overrides re-persist to disk**
  (`.claude/rules/deterministic-verdict-override-must-persist-to-disk.md`):
  the in-memory flip alone is defeated by Layer-4 late-approval
  reconciliation reading `coach_turn_N.json`. Fail-open on the write,
  fail-closed on the verdict.
- **Structural defence beats a prompt instruction**
  (`.claude/rules/structural-defence-beats-prompt-instruction.md`): prompt
  guard #5 is the advisory layer; this task adds the load-bearing structural
  bound. Keep the prompt guard as cheap defence-in-depth, do not treat it as
  enforcement.
- **Tri-state stays tri-state** (§6): `None` evidence stays `None` through
  every layer (`.claude/rules/absence-must-survive-every-reconciliation-layer.md`,
  `.claude/rules/absence-of-failure-is-not-success.md`). The override must
  not coerce the bundle's `None` fields into explicit `False` — it flips the
  *verdict* on the grounds of absent evidence; it does not fabricate a
  ran-and-failed signal (no contribution to the consecutive-failure stall
  tally; `cp.tests_passed is False` at `worktree_checkpoints.py:738` remains
  the only thing that counts).
- **Both Coach paths, deterministically** (§6; direct-mode precedent
  `.claude/rules/direct-mode-relaxed-gates-require-positive-evidence.md`):
  a Coach path that skips the guard re-opens the false-green. Coach stays
  read-only — the orchestrator writes/rewrites `coach_turn_N.json`.
- **Do NOT disarm the false-green backstop**: `signal_absent=True` remains
  the sole precondition for `_reconcile_absent_independent_test_signal`;
  this guard is additive (covers `gathering_status != "complete"`), not a
  replacement.
- **Bound non-termination** (per
  `absence-must-survive-every-reconciliation-layer.md` remediation item 7):
  perpetual null-evidence must end at `max_turns` with `success=False`.
