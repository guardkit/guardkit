# A deterministic verdict override must persist to disk, not just mutate the in-memory result

> **Source**: Seeded by TASK-FIX-COACHFG01 (commit `ae2e14041`, 2026-06-10).
> Pair with the Graphiti design-rule node *"signal_absent override must persist
> to disk for Layer-4"* under `guardkit__project_decisions`. Couples the
> [`absence-of-failure-is-not-success`](absence-of-failure-is-not-success.md)
> meta-frame with the Layer-4 late-approval taxonomy in
> [`harness-cancellation-contract.md`](harness-cancellation-contract.md).

## The rule

When a deterministic Coach guard overrides an `approve` verdict to `feedback`
in memory, it MUST also rewrite the on-disk `coach_turn_N.json` to match. The
in-memory override alone is **not** sufficient: a downstream reader that reads
the `decision` field straight off disk will otherwise resurrect the stale
`approve` the guard just rejected.

The concrete downstream reader is `feature_orchestrator._check_late_approval`
(Layer-4 late-approval reconciliation). Inside the `LATE_APPROVAL_GRACE_S`
window it re-reads `coach_turn_*.json` and, if it finds `decision == "approve"`,
reclassifies a `TimeoutError`'d task as `approved_late` with `success=True`.
An override that mutates only the returned `AgentInvocationResult.report` leaves
`approve` on disk and hands Layer-4 the ammunition to undo the guard.

Persistence failure must be **logged but non-blocking** — the in-memory override
has already rejected the turn, so a disk hiccup must never *unblock* it.

## Why this rule exists

TASK-FIX-COACHFG01 wired the absence-of-failure guard #6 (the
`INDEPENDENT-TEST ABSENT GUARD` in `_build_coach_prompt`) into deterministic
code. In FEAT-AOF run-19 the Coach's independent trust-but-verify pytest run
timed out (300s → `signal_absent = True`) yet the toolless-synthesis model
emitted `approve` anyway — a textbook false-green. The fix added
`AgentInvoker._reconcile_absent_independent_test_signal`
([`agent_invoker.py:5348`](../../guardkit/orchestrator/agent_invoker.py)),
called immediately after `_validate_coach_decision`
([`agent_invoker.py:2294`](../../guardkit/orchestrator/agent_invoker.py)), which
overrides `approve`→`feedback` whenever
`evidence_bundle.independent_tests.signal_absent is True`.

The **Layer-4 hardening** is the load-bearing part of this rule. The override
does not stop at mutating the `decision` dict; it also re-persists it:

```python
# agent_invoker.py:5447-5455
try:
    coach_output_path.write_text(json.dumps(decision, indent=2))
except OSError as exc:
    logger.warning(
        "TASK-FIX-COACHFG01: failed to re-persist overridden verdict "
        "to %s (%s); in-memory override still applies",
        coach_output_path, exc,
    )
```

Without that write, `_check_late_approval`
([`feature_orchestrator.py:3950`](../../guardkit/orchestrator/feature_orchestrator.py))
would `json.loads(latest.read_text()).get("decision")` and return the stale
`approve`; the wave-loop call site
([`feature_orchestrator.py:3071-3074`](../../guardkit/orchestrator/feature_orchestrator.py))
tests `if late_decision == "approve"` and would reclassify the task as
`approved_late` — silently defeating the very guard that just fired.

Prompt guard #6 was deliberately **kept** in `_build_coach_prompt` as cheap
defence-in-depth; the code override is now the load-bearing enforcement, and the
disk write is what makes the override survive Layer-4.

## Symptom

- A deterministic guard logs its `approve`→`feedback` override at WARNING, yet
  the task later shows up reclassified as `approved_late` / `success=True`.
- The turn's `coach_turn_N.json` on disk reads `"decision": "approve"` even
  though the returned `AgentInvocationResult.report` says `feedback`.
- A verdict-divergence between the wave summary (`approved_late`) and the
  in-memory Coach outcome (`feedback`) for a task whose Coach write landed
  inside `LATE_APPROVAL_GRACE_S` of the timer fire.

## Detection recipe

```bash
# 1. Every deterministic guard that mutates a loaded `decision` dict in place —
#    each is a candidate that must also re-persist to disk.
rg -n "_reconcile_absent_independent_test_signal|_apply_spec_gap_absent_guard|decision\[.decision.\] = .feedback." \
   guardkit/orchestrator/agent_invoker.py

# 2. Confirm the override re-persists coach_turn_N.json (absence = the disk half
#    is missing and Layer-4 can resurrect the stale approve).
rg -n "coach_output_path.write_text" guardkit/orchestrator/agent_invoker.py

# 3. The Layer-4 reader that reads `decision` straight off disk.
rg -n "read_text\(\)\).get\(.decision.\)|_check_late_approval" \
   guardkit/orchestrator/feature_orchestrator.py

# 4. Cross-check the meta-frame family.
rg "deterministic-verdict-override-must-persist|absence-of-failure|harness-cancellation" .claude/rules/
```

## Remediation

1. **Re-persist on every in-memory verdict override.** After flipping the
   `decision` dict, `coach_output_path.write_text(json.dumps(decision, ...))`.
   The natural seam is the same guard that performed the override.
2. **Fail-open on the write, fail-closed on the verdict.** Wrap the write in
   `try/except OSError`, log at WARNING, and continue — the in-memory override
   already rejects the turn, so a disk error must never unblock it.
3. **Any new deterministic verdict-override at the synthesis seam inherits this
   contract.** `_apply_spec_gap_absent_guard`
   ([`agent_invoker.py:5457`](../../guardkit/orchestrator/agent_invoker.py))
   already follows the same shape (it takes the same `coach_output_path` and
   re-persists). A new guard that mutates `decision` but skips the write is the
   regression.
4. **Keep the prompt-level guard as defence-in-depth, not the enforcement.**
   The LLM instruction is cheap and correct but advisory; the code override plus
   the disk write is the load-bearing pair.

## Grep-able signature (for next agent)

```bash
# Override + persist fingerprint (MUST MATCH; absence = the disk half is gone):
rg -n "coach_output_path.write_text" guardkit/orchestrator/agent_invoker.py   # -> 5448
rg -n "def _reconcile_absent_independent_test_signal" \
   guardkit/orchestrator/agent_invoker.py                                     # -> 5348

# Layer-4 disk-read fingerprint (why the persist is load-bearing):
rg -n "json.loads\(latest.read_text\(\)\).get\(.decision.\)" \
   guardkit/orchestrator/feature_orchestrator.py                             # -> 3992

# Reproducer that pins the on-disk flip:
rg -n "test_override_rewrites_coach_turn_file_on_disk" \
   tests/orchestrator/test_coach_independent_test_absent_guard.py            # -> 180

# Sibling-rule lookup:
rg "deterministic-verdict-override-must-persist|absence-of-failure|harness-cancellation" .claude/rules/
```

## When this rule triggers

- Before introducing a new deterministic Coach guard in `agent_invoker.py` that
  overrides a loaded `decision` dict at the post-synthesis seam.
- Before adding any orchestrator reader that reads a verdict field straight off
  `coach_turn_*.json` (a second Layer-4-style consumer widens the blast radius
  of a disk/memory divergence).
- During Phase 2.5 architectural review for anything touching
  `agent_invoker.invoke_coach` verdict reconciliation, `_check_late_approval`,
  or the `LATE_APPROVAL_GRACE_S` reconciliation window.
- During any diagnostic session investigating a Coach outcome that flipped from
  `feedback` back to `approved_late`.

## What it does NOT cover

- **The verdict-override logic itself.** *Whether* to override
  `approve`→`feedback` (the absent-signal decision) is
  [`absence-of-failure-is-not-success`](absence-of-failure-is-not-success.md)'s
  territory; this rule governs only that the override, once made, survives to
  disk.
- **`feedback` verdicts.** A `feedback` verdict already rejects the turn and is
  left untouched — there is nothing to re-persist.
- **Coach writing its own verdict file.** The Coach is read-only and does not
  write `coach_turn_N.json` (see
  [`feature-build-invariants.md`](feature-build-invariants.md)); the orchestrator
  parses and writes it. This rule is about the orchestrator's *override* of a
  file it has already written.
