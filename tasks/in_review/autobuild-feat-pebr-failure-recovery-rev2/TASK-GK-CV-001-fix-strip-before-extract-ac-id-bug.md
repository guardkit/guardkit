---
id: TASK-GK-CV-001
title: Fix _strip_criterion_prefix stripping AC ID before _extract_ac_id can extract it
status: in_review
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
previous_state: in_progress
state_transition_reason: "All 7 ACs satisfied; 453/453 regression tests pass; ruff clean on new file"
priority: high
priority_band: P0
task_type: feature
parent_review: TASK-REV-PEBR-002
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md
parent_feature_folder: autobuild-feat-pebr-failure-recovery-rev2
related_tasks:
  - TASK-GK-CR-001
  - TASK-FRR-PEB-FM-002
  - TASK-REV-PEBR-002
implementation_mode: task-work
wave: 1
complexity: 4
estimated_minutes: 75
dependencies: []
tags:
  - autobuild
  - coach-evaluator
  - ac-matching
  - regression-fix
  - feat-pebr
  - bug-b
  - P0
test_results:
  status: passed
  total: 453
  passed: 453
  failed: 0
  new_tests_added: 6
  coverage: not_measured_for_this_change
  last_run: 2026-05-07T00:00:00Z
implementation_summary:
  files_modified:
    - guardkit/orchestrator/quality_gates/coach_validator.py
    - tests/unit/test_coach_validator_fuzzy.py
    - tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py
  files_created:
    - tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py
  approach: simple_delete
  notes: |
    Removed lines 3243-3246 of coach_validator.py (the AC-NNN strip block).
    Updated 4 unit tests in test_coach_validator_fuzzy.py and 1 test in
    test_ac_id_extraction.py that locked in the buggy behavior — they now
    assert the new correct contract (AC labels preserved by
    _strip_criterion_prefix; consumed by _extract_ac_id).
    Pre-existing ruff errors on coach_validator.py and the 2 modified test
    files are unchanged (9 errors before, 9 errors after; 0 new errors).
    AC-6 tested via _match_by_promises directly (mirrors compound_ids
    integration test pattern); full validate() invocation deferred — flagged
    for reviewer.
---

# Task: Fix _strip_criterion_prefix stripping AC ID before _extract_ac_id can extract it

## Description

`CoachValidator._strip_criterion_prefix`
([`guardkit/orchestrator/quality_gates/coach_validator.py:3203-3248`](../../../guardkit/orchestrator/quality_gates/coach_validator.py))
strips `^AC-\d+:\s*` from the criterion text **before**
`_extract_ac_id`
([`coach_validator.py:3251-3307`](../../../guardkit/orchestrator/quality_gates/coach_validator.py))
runs. The extractor's regex
`^(AC(?:-[A-Z0-9]+)+)\s*[:—\-]\s*` is *designed* to consume that
prefix — but the strip step has already removed it, so the extractor
sees text with no AC label, returns `None`, and the caller falls
back to building lookup keys via `f"AC-{i+1:03d}"` (zero-padded).

**Fingerprint** (from FEAT-PEBR run-2 turn 1):

- Player produces `criterion_id="AC-1"` and
  `criterion_text="src/forge/lifecycle_bridge/translation.py exposes a..."`
  (no leading `AC-N:` prefix in `criterion_text` because the Player
  reports the AC text without re-prefixing).
- Coach reads `acceptance_criteria` from task body
  (`AC-1: \`src/forge/lifecycle_bridge/translation.py\` exposes a`),
  passes through `_strip_criterion_prefix` which strips `AC-1: ` →
  `\`src/forge/lifecycle_bridge/translation.py\` exposes a`.
- `_extract_ac_id` regex doesn't match → returns `None`.
- `extracted_ids[0] = None` →
  `criterion_id = f"AC-{1:03d}" = "AC-001"`.
- `promise_map.get("AC-001")` → MISS (Player put it under `"AC-1"`).
- Result: `"No completion promise for AC-001"`,
  `criteria_met = 0/7`, even though the Player provided 7 valid
  promises.

**Empirical repro** (validates the regex behaviour):

```python
>>> import re
>>> # _strip_criterion_prefix line 3244
>>> ac_match = re.match(r'^AC-\d+:\s*', 'AC-1: src/forge/lifecycle_bridge/translation.py exposes a')
>>> ac_match.group()
'AC-1: '
>>> stripped = 'src/forge/lifecycle_bridge/translation.py exposes a'
>>> # _extract_ac_id line 3301-3303
>>> re.match(r'^(AC(?:-[A-Z0-9]+)+)\s*[:—\-]\s*', stripped)
None  # ← bug: extractor sees no AC ID because strip removed it
```

This is the **root cause of the 0 → 7 jump in `criteria_met`** in
FEAT-PEBR run-2 — Player adapts by turn 2 (switches to
`criterion_id="AC-001"` and prepends `AC-1:` to `criterion_text`),
the lookup hits, criteria_met flips. The 0 → 7 transition is what
defeats the stall extender (TASK-GK-COACH-001's surface).

This bug affects **every task in every feature** that uses
natural-label `AC-N:` formatting in its acceptance criteria
(which is the dominant convention across forge tasks). Players that
emit `criterion_id="AC-N"` always miss; Players that emit
`criterion_id="AC-NNN"` always hit. The Coach is forcing a specific
Player ID format without documenting it.

## Acceptance Criteria

- [ ] **AC-1 — Strip-before-extract reversed.** The
  `_strip_criterion_prefix` function no longer strips
  `^AC-\d+:\s*`. `_extract_ac_id` runs first against the
  bullet-stripped (but AC-prefix-preserved) text and consumes the
  AC label as designed.
- [ ] **AC-2 — Repro test fails on main, passes on fix.** Add
  `tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py`
  with class `TestNaturalLabelACMatching`:
  - Fixture: AC text `["AC-1: src/forge/foo.py exposes Bar"]`.
  - Player promise:
    `{"criterion_id": "AC-1", "criterion_text": "src/forge/foo.py exposes Bar", "status": "complete", "evidence": "..."}`.
  - Expected: `criteria_met == 1`,
    `criteria_results[0].criterion_id == "AC-1"`,
    `criteria_results[0].result == "verified"`.
  - This must FAIL on `main` (criteria_met=0) and PASS after the fix.
- [ ] **AC-3 — Zero-padded format still works.** Add a parallel test
  fixture with Player promise
  `{"criterion_id": "AC-001", "criterion_text": "AC-1: src/forge/foo.py exposes Bar", ...}`
  → must produce `criteria_met == 1` with the existing TASK-CVAC-002
  text-fallback path or directly via the extracted ID. Both formats
  must coexist.
- [ ] **AC-4 — Compound IDs still work.** Add fixture with AC text
  `["**AC-LOAD-01** — Frobnicate the widget"]` and Player promise
  `{"criterion_id": "AC-LOAD-01", "criterion_text": "Frobnicate the widget", ...}`.
  Must produce `criteria_met == 1`. Verifies `_extract_ac_id`'s bold-
  and em-dash forms still match.
- [ ] **AC-5 — Regression: existing test suite stays green.** All
  tests under `tests/unit/test_coach_validator.py`,
  `tests/unit/orchestrator/quality_gates/`, and
  `tests/integration/orchestrator/test_coach_validator_compound_ids.py`
  continue to pass. Document any pre-existing failures (cite by
  test name) so the reviewer can confirm they are unrelated.
- [ ] **AC-6 — End-to-end fixture using FEAT-PEBR run-2 signature.**
  Add an integration test that mirrors run-2's turn-1 inputs:
  - 7 ACs in natural-label form (`AC-1:` ... `AC-7:`).
  - 7 Player promises with `criterion_id="AC-N"` (not zero-padded).
  - All gates passing (mock plan_audit as `status: passed`).
  - Expected: `decision == "approve"`, `criteria_met == 7`,
    `all_criteria_met == True`. Today: `criteria_met == 0`.
- [ ] **AC-7 — All modified files pass project-configured
  lint/format checks** (ruff). Add the new test file to ruff's
  scope; new test file must report zero errors.

## Out of Scope

- Bug A (qualified prose paths) — covered by TASK-GK-PA-002.
- Bug C (stall extender plateau) — covered by TASK-GK-COACH-001.
- Renaming `_scan_ac_for_missing_paths` (cosmetic).
- Touching the synthetic-report path
  (`synthetic_report.generate_file_existence_promises`) — it does not
  use this matching pipeline.

## Files to Create

- `tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py`

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` (lines
  3243-3246: remove or revise the `^AC-\d+:\s*` strip)

## Implementation notes

### The fix (recommended approach)

The cleanest fix is **delete lines 3243-3246** of `coach_validator.py`:

```python
# Strip AC-NNN: prefixes (e.g., "AC-001: Some text")
ac_match = re.match(r'^AC-\d+:\s*', cleaned)
if ac_match:
    cleaned = cleaned[ac_match.end():].strip()
```

The intent of this strip block is to normalise criterion text for
display / fuzzy matching. But the `_extract_ac_id` regex
(`^(AC(?:-[A-Z0-9]+)+)\s*[:—\-]\s*`) is already a superset — it
matches not just `AC-\d+:` but also `AC-LOAD-01:`,
`**AC-001** — `, etc., AND it captures the ID as group 1. Letting
`_extract_ac_id` run first preserves the strip semantics (caller
gets text with the prefix removed via `cleaned[m.end():]`) AND
records the extracted ID for downstream lookup.

After deleting the strip, verify:

1. `_strip_criterion_prefix` still handles checkbox and bullet
   prefixes (lines 3225-3241). Those are unrelated to AC IDs.
2. The single in-source caller of `_strip_criterion_prefix`
   (`_match_by_promises` at coach_validator.py:3075 and 3099) now
   sees the AC prefix preserved → passes to `_extract_ac_id` → works
   correctly.
3. There are no other callers of `_strip_criterion_prefix` that rely
   on the AC-ID strip behaviour. Audit with
   `grep -rn "_strip_criterion_prefix" guardkit/ tests/`.

### Alternative (if removing the strip breaks hidden callers)

If the audit in step 3 above turns up unexpected callers, an
alternative is to **change the call ordering** in `_match_by_promises`
(lines 3075-3077) so `_extract_ac_id` runs against the bullet-stripped
but AC-prefix-preserved text:

```python
extracted_ids: List[Optional[str]] = []
for criterion_text in acceptance_criteria:
    # Strip bullet/checkbox prefixes only (NOT AC-N:)
    bullet_stripped = self._strip_bullet_prefixes_only(criterion_text)
    _, extracted_id = self._extract_ac_id(bullet_stripped)
    extracted_ids.append(extracted_id)
```

Where `_strip_bullet_prefixes_only` is a new helper that contains
lines 3225-3241 of the current `_strip_criterion_prefix` but **not**
the AC-NNN block at 3243-3246. The simpler fix (delete) is preferred
when the audit allows it; this two-helper approach is the fallback.

### Why this is high leverage

This bug silently miscounts `criteria_met` on **turn 1 of every
task** in **every feature** that uses natural-label AC formatting
(the forge convention). With Bug A also present, the gate-fail
short-circuit hides the miscount from the operator. With Bug A
fixed, the miscount becomes operator-visible (turn 1 reports
`criteria_met=0` even though gates pass and the run approves on
later turns).

Fixing Bug B alone produces a partial unblock: run-2 would still
fail because Bug A's plan-audit gate fires; but with Bug B fixed,
the criteria-passed history would be `[7, 7, 7, 7, 7]` (no 0→N
transition) and the stall extender would correctly fire at turn 5
(Bug C's surface eliminated as a side effect).

## Test requirements

- Unit tests in
  `tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py`
  per ACs 2-4.
- Integration test (end-to-end CoachValidator with mocked plan_audit
  passing) per AC-6.
- Existing regression suites under
  `tests/unit/test_coach_validator.py`,
  `tests/unit/orchestrator/quality_gates/`,
  `tests/integration/orchestrator/test_coach_validator_compound_ids.py`
  must all continue to pass (AC-5).

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py -x -v
PYTHONPATH=. python -m pytest tests/unit/test_coach_validator.py tests/unit/orchestrator/quality_gates/ tests/integration/orchestrator/test_coach_validator_compound_ids.py -x
ruff check guardkit/orchestrator/quality_gates/coach_validator.py tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py
```
