# Feature: Coach validator AC-ID matching repair

**Feature slug**: `coach-validator-ac-id-matching`
**Sibling feature**: `feature-plan-smoke-gate-validation/` (same parent
review session, different defect surface)
**Cross-repo trigger**: study-tutor FEAT-FD32 autobuild Run 1 stalled
on TASK-GR-LOAD after 4 turns even though the implementation passed
59/59 unit tests at 95% coverage. Coach reported "Criteria
verification 0/8" because the AC parser couldn't match Player's
markdown-label promise IDs (`AC-LOAD-01`) against its own index-based
expected IDs (`AC-001`).
**Total estimate**: 1.5–2 hours (single subtask)
**Prerequisites**: none

## Problem Statement

`guardkit/orchestrator/quality_gates/coach_validator.py` has a
contract mismatch between Player and Coach for acceptance-criterion
identifiers:

1. **Coach's parser** (`_clean_criterion_text` at lines 2965-2992)
   strips `- [ ] ` markdown checkbox prefixes and tries to match
   `^AC-\d+:\s*`. It does not handle:
   - Markdown bold delimiters: `- [ ] **AC-LOAD-01** — text`
   - Compound AC IDs with sub-prefixes: `AC-LOAD-NN`, `AC-AUTH-NN`,
     `AC-DB-NN`, etc.
   - Em-dash (`—`) or hyphen (`-`) separators in place of `:`.

2. **Coach's matcher** (`_validate_via_promises` at lines 2867-2928)
   always generates `criterion_id` as `f"AC-{i+1:03d}"` by
   **index** (line 2878), regardless of any ID present in the AC
   text. So after parsing 8 ACs from the markdown, Coach expects
   promises keyed `AC-001`, `AC-002`, ..., `AC-008`.

3. **Player's promise emitter** uses the natural label from the AC
   text. For task TASK-GR-LOAD, that produced
   `criterion_id: 'AC-LOAD-01'`, ..., `'AC-LOAD-08'`.

4. **Result**: every `promise_map.get('AC-001')` lookup returns
   `None`. Coach reports 0/8 verified, every turn. After 4 identical
   feedback turns the orchestrator concludes "unrecoverable_stall"
   and exits — even though the implementation is correct, the tests
   pass, and Player's promises contain accurate file:line evidence
   for every AC.

**Real-world incident**: study-tutor FEAT-FD32 Run 1, 2026-05-02. 44
minutes of SDK budget burned, 4/5 tasks blocked, root cause was the
AC parser's regex. Diagnosis traced through:

- [study-tutor history line 573](../../../study-tutor/docs/history/autobuild-feature-FEAT-FD32-failure-run-1-history.md#L573) —
  `Independent tests passed in 0.9s` (Coach saw the tests pass).
- [study-tutor history line 597-598](../../../study-tutor/docs/history/autobuild-feature-FEAT-FD32-failure-run-1-history.md#L597) —
  `AC-001: No completion promise for AC-001` (the index-based
  fallback IDs).
- [study-tutor history line 584](../../../study-tutor/docs/history/autobuild-feature-FEAT-FD32-failure-run-1-history.md#L584) —
  Player's promises were keyed `AC-LOAD-01`, ..., `AC-LOAD-08`.

The implementation was correct; the contract was broken.

The forge FEAT-DEA8 review (TASK-REV-DEA8) discovered a sibling
class of issue in `/feature-plan` smoke-gate emission. Both stem
from the same family of root cause: **a guardkit producer/consumer
contract is permissive on one side and strict on the other, with
no mediator that flags the mismatch**. This task fixes the Coach
side; `feature-plan-smoke-gate-validation/` fixes the
generate-feature-yaml side.

## Solution Approach

A single, tightly-coupled fix in two adjacent code paths:

**Step 1 — Extract the AC ID from the parsed text.** Extend
`_clean_criterion_text` (or add a sibling `_extract_ac_id`) to
recognise:

- `**AC-LOAD-01**` (markdown bold + compound ID)
- `**AC-001**` (markdown bold + simple ID)
- `AC-LOAD-01:` (compound + colon)
- `AC-001:` (existing — must keep working)

Return both the cleaned text (no ID prefix) and the extracted ID
string (or `None` if no ID found).

**Step 2 — Use the extracted ID, not the index.** In
`_validate_via_promises` (line 2878) and the parallel callsites
(lines 3120, 3327), replace the unconditional
`criterion_id = f"AC-{i+1:03d}"` with:

```python
criterion_id = extracted_id_for_criterion[i] or f"AC-{i+1:03d}"
```

Index-based fallback preserves backwards-compatibility for tasks
that don't label their ACs.

**Step 3 — Round-trip parity test.** A new test asserts that for
every AC label format the parser accepts, Player's natural-label
promises match. Specifically: parse a fixture markdown with
`**AC-LOAD-01** — text`, assert the extracted criterion_id is
`AC-LOAD-01`, and assert that `promise_map['AC-LOAD-01']` resolves
in `_validate_via_promises`.

## Success Criteria

A reproduction fixture mirroring TASK-GR-LOAD's exact AC shape:

```markdown
## Acceptance Criteria

- [ ] **AC-LOAD-01** — Function `foo()` exists in `src/foo.py`.
- [ ] **AC-LOAD-02** — Tests in `tests/test_foo.py` cover all branches.
- [ ] **AC-LOAD-03** — Lint passes with zero errors.
```

…paired with a Player report containing:

```json
"completion_promises": [
  {"criterion_id": "AC-LOAD-01", "status": "complete", "evidence": "..."},
  {"criterion_id": "AC-LOAD-02", "status": "complete", "evidence": "..."},
  {"criterion_id": "AC-LOAD-03", "status": "complete", "evidence": "..."}
]
```

…must result in `_validate_via_promises` returning
`criteria_met=3, all_criteria_met=True`. Today it returns
`criteria_met=0, missing=3`.

## Out of Scope

- **Player-side promise normalisation.** Player should keep emitting
  natural labels; the fix is on Coach's side. Forcing Player to
  emit `AC-NNN` index-based IDs would lose semantic information.
- **AC text re-formatting in the task markdown.** Authors should
  continue using `**AC-LOAD-01** — text`; the parser should adapt.
- **Index-based fallback removal.** Tasks that don't label their
  ACs (legacy or unlabelled) must keep working — fall back to
  `AC-NNN`.

## Files

- `coach-validator-ac-id-matching/`
  - `README.md` (this file)
  - `TASK-CVAC-001-extract-and-match-compound-ac-ids.md`
