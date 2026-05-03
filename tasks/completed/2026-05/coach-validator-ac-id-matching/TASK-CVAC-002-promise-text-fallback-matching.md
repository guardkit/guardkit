---
id: TASK-CVAC-002
title: "Coach validator: match Player promises by extracted criterion_text ID when criterion_id lookup fails (TASK-CVAC-001 follow-up)"
status: completed
created: 2026-05-03T08:30:00Z
updated: 2026-05-03T09:05:00Z
completed: 2026-05-03T09:05:00Z
previous_state: in_review
completed_location: tasks/completed/2026-05/coach-validator-ac-id-matching/
state_transition_reason: "All 6 ACs satisfied; 13 new tests + 22 CVAC-001 tests + full quality_gates suite (77/77) green"
priority: high
task_type: fix
implementation_mode: task-work
tags:
  - coach-validator
  - acceptance-criteria
  - player-coach-contract
  - cross-repo-followup
complexity: 3
estimated_minutes: 60
parent_task: TASK-CVAC-001
related_incident: appmilla_github/study-tutor FEAT-FD32 Run 4 — TASK-GR-SEED stalled 5/5 turns at 0/8 verified despite TASK-CVAC-001 being live
---

# Task: Coach validator — match promises by criterion_text fallback

## Description

TASK-CVAC-001 fixed Coach to extract natural-label AC IDs (`AC-LOAD-01`,
`AC-SEED-01`, etc.) from the task markdown so it could match Player's
natural-label promises. That fix shipped in commit `5192fc60` and is
proven by FEAT-FD32 / TASK-GR-SMOK passing on retry.

But the contract has **two halves**, and only one was fixed. The
inverse failure mode is now reproducible:

- **Coach**: extracts `criterion_id = 'AC-SEED-01'` from `**AC-SEED-01** — text` (TASK-CVAC-001).
- **Player**: emits `criterion_id: 'AC-001'` (index-based zero-padded
  fallback) for the same criterion. Player's `criterion_text` field
  contains the natural label (`AC-SEED-01** — text`) but the lookup
  key it sets is index-based.
- `promise_map.get('AC-SEED-01')` → `None` → 0/N verified → feedback
  stall.

This was lottery-luck before TASK-CVAC-001 (Coach used index, Player
sometimes guessed compound, sometimes index). After CVAC-001 the
lottery just inverted: Coach uses compound, Player still sometimes
emits index. Either way, the fundamental issue is **Player and Coach
agree on naming by accident, not by contract**.

This task adds a robustness layer on the Coach side that doesn't
require changing Player's prompt: when looking up a promise by
`criterion_id` returns `None`, also try looking up by the AC ID
**extracted from the promise's own `criterion_text`** field. This
makes Coach robust to either Player naming convention.

**Real-world reproducer**:
[appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-after-raising-floor-history.md](../../../study-tutor/docs/history/autobuild-FEAT-FD32-failed-after-raising-floor-history.md)
(line 333) shows Player's promise dump:

```
{'criterion_id': 'AC-001',
 'criterion_text': 'AC-SEED-01** — `python scripts/seed_student_model.py` runs successfully against...',
 'status': 'complete',
 'evidence': 'File-existence verified: ...'}
```

Coach extracted `AC-SEED-01` from the markdown (correct) but
`promise_map['AC-SEED-01']` returned `None` (the promise is keyed
under `AC-001`). With the proposed fix, Coach would also try
`_extract_ac_id(promise['criterion_text'])` → `'AC-SEED-01'`, find a
hit, and approve.

## Acceptance Criteria

- [ ] **AC-CVAC-2-01** — `_validate_via_promises` builds `promise_map`
      with **two keys per promise** (when the criterion_text yields a
      different ID than the criterion_id):
      ```python
      for p in completion_promises:
          cid = p.get("criterion_id") or p.get("ac_id", "")
          if cid:
              promise_map[cid] = p
          # NEW: also key by extracted-from-text ID (TASK-CVAC-002)
          text_id = None
          if p.get("criterion_text"):
              _, text_id = self._extract_ac_id(
                  self._strip_criterion_prefix(p["criterion_text"])
              )
          if text_id and text_id != cid:
              promise_map.setdefault(text_id, p)
      ```
      `setdefault` ensures the explicit `criterion_id` wins if both
      keys are present (no behaviour change for promises that already
      use the extracted ID directly).

- [ ] **AC-CVAC-2-02** — When the lookup at line 2893
      (`promise_map.get(criterion_id)`) succeeds via the fallback key,
      the diagnostic logger emits a DEBUG line so operators can see
      the contract divergence:
      ```
      DEBUG  AC-SEED-01: matched via criterion_text fallback (
              promise.criterion_id='AC-001',
              extracted_text_id='AC-SEED-01')
      ```
      Useful for tracking which features have Player/Coach contract
      drift — over time this pinpoints which Player-prompt versions
      are still emitting index-based IDs.

- [ ] **AC-CVAC-2-03** — Round-trip test for the FEAT-FD32 reproducer:
      a fixture markdown with `**AC-SEED-01** — text` paired with a
      promise dict `{'criterion_id': 'AC-001', 'criterion_text':
      'AC-SEED-01** — text', 'status': 'complete', ...}` must produce
      `criteria_met=1, all_criteria_met=True`. Today this returns
      `0, False` and stalls.

- [ ] **AC-CVAC-2-04** — Backwards-compat tests still green:
      promises that already use the extracted ID directly
      (e.g. `criterion_id: 'AC-SEED-01'`) match exactly as before.
      No regression in TASK-CVAC-001's existing 22-test suite.

- [ ] **AC-CVAC-2-05** — Edge case: promise with `criterion_text=None`
      or an unparseable `criterion_text` (no AC ID extractable) does
      NOT raise; the fallback is silently skipped and the existing
      `criterion_id`-only lookup behaviour applies.

- [ ] **AC-CVAC-2-06** — Order-stability test: when both Player and
      Coach use the same naming convention (the post-CVAC-001 happy
      path), the fallback is a no-op. Verified by asserting that
      `len(promise_map) == len(completion_promises)` for the
      naturally-aligned case.

## Test Requirements

- [ ] Extend
      `tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py`
      (or add a new
      `tests/unit/orchestrator/quality_gates/test_promise_text_fallback.py`)
      with the AC-CVAC-2-03 reproducer + AC-CVAC-2-04/05/06 cases.
- [ ] Integration test against the verbatim FEAT-FD32 promise shape
      (lifted from the diagnostic dump) asserting Coach approves.
- [ ] Existing TASK-CVAC-001 tests (22 currently green) all still pass.

## Implementation Notes

### Why fix Coach not Player

Three reasons:

1. **Single point of change.** Coach is one module; Player's
   promise-emission logic is spread across the inline implement
   protocol, the task-work prompt, and SDK Claude's own
   interpretation of "what should `criterion_id` be?". Fixing Coach
   centralises the robustness.

2. **Backwards compatibility.** Older Player runs (before any
   prompt-side fix) keep working without re-running them. The
   `tasks_completed` and `criteria_results` they wrote remain valid
   after Coach's matcher learns to read them.

3. **Defence in depth.** Even if Player's prompt is later updated to
   always use natural labels, the fallback is a cheap insurance against
   future Player drift (different SDK version, different model, new
   `criterion_id` convention).

### Why `setdefault`, not unconditional assignment

If a Player promise has `criterion_id: 'AC-FOO-01'` AND its
`criterion_text` extracts to `AC-FOO-01`, both keys point to the same
promise — fine. If the two diverge (the FEAT-FD32 case), the explicit
`criterion_id` should still win in case Player meant something
specific. `setdefault` only adds the text-extracted key when it's not
already present, so explicit assignments take priority.

### Out of scope

- **Player-side prompt update.** A separate ticket could update
  Player's task-work prompt / inline implement protocol to always emit
  natural-label `criterion_id` matching the markdown. That's
  complementary to this fix, not a substitute. File as TASK-CVAC-003
  if/when prioritised.
- **Fuzzy text matching.** The existing `_extract_keywords` /
  fuzzy infrastructure could match by criterion_text similarity even
  when no AC ID is extractable. That's a bigger semantic change with
  false-positive risk. Defer until the simpler fallback is proven
  insufficient.
- **Diagnostic-log changes** beyond AC-CVAC-2-02 — the existing
  `acceptance_criteria_status` write path in
  `autobuild.py:4243-4247` reads `result.criterion_id`, which now
  contains the matched ID (whether direct or fallback). No additional
  change needed there.

## Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — primary edit
  - Modify `_validate_via_promises` (around line 2882-2886).
  - Mirror the same pattern in `_match_by_promises` if used elsewhere
    in the codebase (search for `promise_map` builders).
- `tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py` — extend
  OR `tests/unit/orchestrator/quality_gates/test_promise_text_fallback.py` — new

## Cross-Repo Provenance

- **Parent fix**: TASK-CVAC-001 (commit 5192fc60, 2026-05-02 15:10) —
  Coach extracts compound + markdown-bold AC IDs. Now in
  `tasks/completed/2026-05/coach-validator-ac-id-matching/`.
- **Discovered**: study-tutor FEAT-FD32 Run 4, 2026-05-03 — TASK-GR-SEED
  stalled 5/5 turns despite parser fix being live. Diagnosis traced
  to Player still emitting index-based `criterion_id` while Coach now
  expects natural labels.
- **Workaround applied**: `appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml`
  was hand-edited 2026-05-03 to mark TASK-GR-SEED `status: completed`
  / `final_decision: approved`, allowing `--resume` to proceed to
  Wave 5. The seed-script execution itself was deferred to operator
  follow-up because TASK-GR-SEED's runtime ACs (live FalkorDB writes,
  MCP queries, wall-clock measurement) are inherently outside what
  Player can verify — that's a task-design issue separate from this
  fix, captured in the YAML's manual-completion comment block.
