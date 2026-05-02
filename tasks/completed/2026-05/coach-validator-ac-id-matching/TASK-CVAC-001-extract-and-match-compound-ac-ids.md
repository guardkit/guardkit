---
id: TASK-CVAC-001
title: "Coach validator: extract compound/markdown-bold AC IDs and match against Player's natural-label promises"
status: completed
created: 2026-05-02T13:30:00Z
updated: 2026-05-02T16:45:00Z
completed: 2026-05-02T16:45:00Z
completed_location: tasks/completed/2026-05/coach-validator-ac-id-matching/
previous_state: in_review
state_transition_reason: "All 7 acceptance criteria met; 27 new tests + 461 existing coach_validator tests passing (488/488)"
priority: high
task_type: fix
implementation_mode: task-work
tags:
  - coach-validator
  - acceptance-criteria
  - player-coach-contract
  - cross-repo-followup
  - coach-validator-ac-id-matching
complexity: 4
estimated_minutes: 90
parent_review: appmilla_github/forge/TASK-REV-DEA8  # sibling diagnosis from same session
parent_incident: appmilla_github/study-tutor FEAT-FD32 Run 1 (2026-05-02)
parent_feature: coach-validator-ac-id-matching
wave: 1
dependencies: []
---

# Task: Coach validator — extract compound + markdown-bold AC IDs

## Description

`guardkit/orchestrator/quality_gates/coach_validator.py` has a
Player/Coach contract mismatch on acceptance-criterion identifiers.
Coach **always** generates IDs by index (`AC-{i+1:03d}` →
`AC-001`...`AC-NNN`), regardless of any ID present in the AC
markdown. Player emits promises using the natural label from the
markdown (e.g. `AC-LOAD-01`, `AC-AUTH-03`). Lookups never match.

The failure mode is silent: Coach reports "Criteria verification
0/8" with the diagnostic `No completion promise for AC-001`, the
orchestrator interprets the identical 0/8 across turns as a
"feedback stall," and exits "unrecoverable_stall" — even when
implementation, tests, and coverage are all correct.

**Reproducer (study-tutor FEAT-FD32 Run 1):**
[autobuild-feature-FEAT-FD32-failure-run-1-history.md](../../../../study-tutor/docs/history/autobuild-feature-FEAT-FD32-failure-run-1-history.md).
TASK-GR-LOAD turn 4 logged `Independent tests passed in 0.9s`,
`AC-001: No completion promise for AC-001` ×8, `Feedback stall
detected ... Exiting loop early`. Player's promises that turn:
`criterion_id: 'AC-LOAD-01'`...`'AC-LOAD-08'` (history line 584).

## Acceptance Criteria

- [x] **AC-CVAC-01** — A new helper
      `_extract_ac_id(cleaned: str) -> tuple[str, Optional[str]]`
      (or extension of `_clean_criterion_text`) recognises and
      extracts AC IDs in all four formats:
      1. `**AC-LOAD-01** — text`     (markdown bold + compound + em-dash)
      2. `**AC-001** — text`         (markdown bold + simple + em-dash)
      3. `AC-LOAD-01: text`          (compound + colon, no bold)
      4. `AC-001: text`              (simple + colon, no bold — existing format)
      Plus separator variants: `:`, `—` (em-dash, U+2014), `-`
      (hyphen). Returns `(cleaned_text_without_id, extracted_id)`.
      If no ID matches, returns `(cleaned_text, None)`.
- [x] **AC-CVAC-02** — All three callsites that currently assign
      `criterion_id = f"AC-{i+1:03d}"`
      ([line 2878](../../../guardkit/guardkit/orchestrator/quality_gates/coach_validator.py#L2878),
      [line 3120](../../../guardkit/guardkit/orchestrator/quality_gates/coach_validator.py#L3120),
      [line 3327](../../../guardkit/guardkit/orchestrator/quality_gates/coach_validator.py#L3327))
      now read:
      ```python
      criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"
      ```
      so labelled ACs use their natural label and unlabelled ACs
      keep the index-based fallback (backwards compatible).
- [x] **AC-CVAC-03** — `_validate_via_promises` builds
      `promise_map` keyed by the same canonicalisation rule as
      `criterion_id`, so naturally-labelled promises
      (`AC-LOAD-01`) hit naturally-labelled criteria
      (`AC-LOAD-01`) without surprises.
- [x] **AC-CVAC-04** — `acceptance_criteria_status` written into
      `turn_state_turn_N.json` uses the same IDs (so debugging logs
      remain coherent — currently they show
      `"AC-001": "rejected"` even when the markdown labels are
      `AC-LOAD-NN`, which is misleading; see
      [study-tutor turn_state_turn_4.json](../../../../study-tutor/.guardkit/worktrees/FEAT-FD32/.guardkit/autobuild/TASK-GR-LOAD/turn_state_turn_4.json)).
- [x] **AC-CVAC-05** — Unit tests assert the extraction +
      matching round-trip against four fixture criteria (one per
      format) plus an unlabelled control.
- [x] **AC-CVAC-06** — Integration test reproduces the
      study-tutor FEAT-FD32 stall: a fixture markdown with eight
      `**AC-LOAD-NN**` ACs + a Player report with eight matching
      `AC-LOAD-NN` promises must produce `criteria_met=8,
      all_criteria_met=True` (today: `0, False`).
- [x] **AC-CVAC-07** — Backwards-compat test: a fixture markdown
      with no AC IDs at all (just `- [ ] description text`) plus
      a Player report with `criterion_id: "AC-001"`...`"AC-008"`
      promises must continue to match (the index-based fallback
      preserves prior behaviour).

## Test Requirements

- [ ] Unit test
      `tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py`
      — covers AC-CVAC-01 (extraction) + AC-CVAC-05 (round-trip).
- [ ] Integration test
      `tests/integration/orchestrator/test_coach_validator_compound_ids.py`
      — covers AC-CVAC-06 (study-tutor reproducer) + AC-CVAC-07
      (backwards-compat).
- [ ] Existing `_validate_via_promises` tests continue to pass.
- [ ] Existing `_clean_criterion_text` tests continue to pass
      (extension is additive; cleaned-text return value unchanged).

## Implementation Notes

### Suggested regex

```python
import re

# Captures: bold markers (optional), AC ID (compound or simple),
# separator (colon / em-dash / hyphen), trailing whitespace.
_AC_ID_PATTERN = re.compile(
    r'^(?P<bold_open>\*\*)?'           # optional **
    r'(?P<id>AC(?:-[A-Z0-9]+)+)'        # AC- followed by 1+ dash-separated alphanumeric segments
    r'(?P=bold_open)?'                  # matching ** if opened (uses backreference via group name)
    r'\s*[:—\-]\s*',                    # separator: colon, em-dash, or hyphen
    re.UNICODE,
)
```

⚠️ Python regex doesn't support `(?P=name)` as conditional in this
shape directly — use a callable strip:

```python
def _extract_ac_id(cleaned: str) -> tuple[str, Optional[str]]:
    """
    Extract AC ID from cleaned criterion text.

    Returns (text_without_id_prefix, extracted_id_or_none).
    """
    # Try markdown-bold-wrapped IDs first (more specific)
    m = re.match(
        r'^\*\*(AC(?:-[A-Z0-9]+)+)\*\*\s*[:—\-]\s*', cleaned,
    )
    if m:
        return cleaned[m.end():], m.group(1)

    # Then plain compound or simple IDs with explicit separator
    m = re.match(
        r'^(AC(?:-[A-Z0-9]+)+)\s*[:—\-]\s*', cleaned,
    )
    if m:
        return cleaned[m.end():], m.group(1)

    return cleaned, None
```

Cover edge cases:
- `AC-001:` → simple, colon → `("text", "AC-001")`
- `**AC-LOAD-01** — text` → bold + compound + em-dash →
  `("text", "AC-LOAD-01")`
- `**AC-LOAD-01: text` (unmatched bold) → conservative: don't match,
  return `(input, None)` to avoid silently mangling input.
- Plain prose like `**AC-LOAD-01** is implemented` (no separator) →
  no match, return `(input, None)`.

### Backwards compatibility

Existing tasks with index-style IDs (`AC-001:`) keep working
unchanged — the existing `^AC-\d+:\s*` regex remains a special
case of the new `AC(?:-[A-Z0-9]+)+` pattern. The change is purely
additive; only the **extracted-id** result is new.

### Caller-side change

Today's three callsites that hard-code `f"AC-{i+1:03d}"`:

1. `_validate_via_promises` — line 2878
2. (callsite at line 3120 — review for context)
3. (callsite at line 3327 — review for context)

Each becomes:

```python
extracted_ids: list[Optional[str]] = [
    _extract_ac_id(text)[1] for text in raw_criterion_texts
]
# ... then in the loop:
criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"
```

So the index-based fallback only kicks in when no ID is extractable
— preserving today's behaviour for unlabelled ACs.

### Diagnostic-log fix (AC-CVAC-04)

`turn_state_turn_N.json::acceptance_criteria_status` is currently
written keyed by the index-based IDs:

```json
"acceptance_criteria_status": {
    "AC-001": "rejected",
    "AC-002": "rejected",
    ...
}
```

After this fix, that dict should be keyed by the extracted IDs
(falling back to AC-NNN when missing) so a developer reading the
turn-state file can correlate the rejection back to the markdown
without having to count line numbers.

### Why this is more than a parser bug

The parser's `^AC-\d+:` regex is a leaky abstraction that
permeates Coach's whole verification pipeline. Coach's prompt
(elsewhere in the codebase) likely also tells the LLM "use AC-NNN
IDs" or similar — but Player tasks (especially those generated by
`/feature-plan` or `/task-create`) freely use compound IDs. The fix
makes Coach **adapt to what's in the markdown** instead of forcing
authors into a narrow canonical format.

## Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — primary edit
- `tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py` — new
- `tests/integration/orchestrator/test_coach_validator_compound_ids.py` — new

## Cross-Repo Provenance

- **Discovered**: study-tutor FEAT-FD32 Run 1, 2026-05-02 — TASK-GR-LOAD
  stalled after 4 turns despite passing 59/59 tests.
- **Sibling diagnosis**: forge TASK-REV-DEA8 (same session) discovered
  the parallel `/feature-plan` smoke-gate emission bug (now captured
  in `feature-plan-smoke-gate-validation/`).
- **Workaround applied**: `appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml`
  was hand-edited 2026-05-02 to mark TASK-GR-LOAD `status: completed`
  / `final_decision: approved`, allowing `--resume` to proceed to
  Wave 2. The workaround documents this task as the proper fix.

## Implementation Summary

Added a static helper `CoachValidator._extract_ac_id` that recognises
all four documented AC ID formats (markdown-bold + compound, markdown-
bold + simple, plain compound + colon, plain simple + colon) and
accepts ``:``, ``—`` (em-dash, U+2014), and ``-`` (hyphen) separators.
The three callsites in `coach_validator.py` that previously generated
`criterion_id = f"AC-{i+1:03d}"` (`_match_by_promises` line 2878,
`_match_by_text` line 3120, `_build_all_unmet` line 3327) now read
`criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"` — the natural
label is preferred, the index-based fallback preserves backwards
compatibility with unlabelled criteria. AC-CVAC-04 (`acceptance_criteria_status`
in `turn_state_turn_N.json` keyed by extracted IDs) is satisfied
transitively because the orchestrator builds that dict from
`criteria_results[].criterion_id`.

### Approach

`_extract_ac_id` is conservative on edge cases by design:

- Requires a paired closing `**` for the bold form (no silent
  mangling of unmatched bold markers).
- Requires an explicit separator (`:` / `—` / `-`) so prose mentions
  of an AC ID without a separator do not match.
- Uppercase-only ID body (matches the markdown convention used across
  the project; lowercase variants are not matched).

The helper is additive — `_strip_criterion_prefix` is unchanged, so
all existing tests continue to pass without modification.

### Test Results

- New unit tests: 22 in `tests/unit/orchestrator/quality_gates/test_ac_id_extraction.py`
  (4 formats, edge cases, round-trip, integration with `_strip_criterion_prefix`).
- New integration tests: 5 in `tests/integration/orchestrator/test_coach_validator_compound_ids.py`
  (FEAT-FD32 reproducer, backwards-compat, mixed formats, diagnostic-label correctness).
- Full coach_validator suite: **488/488 passing** in 204s — no regressions.

### Lessons

- **Producer/consumer ID contracts must be enforced symmetrically.**
  Coach generated IDs unilaterally by index regardless of any label
  in the source markdown, while Player promises preserved the markdown
  label. Either the producer (Player) had to lose information by
  re-keying to indices, or the consumer (Coach) had to read the IDs
  off the markdown. Reading wins because it preserves semantic info
  and is what authors expect.
- **Silent-stall failure modes deserve named error categories.** The
  FEAT-FD32 incident burned 44 minutes of SDK budget with the
  orchestrator reporting "feedback stall" / "unrecoverable_stall"
  on a contract-mismatch root cause. A clearer category
  (`criterion_id_lookup_miss_rate=100%`) would have surfaced this
  in turn 2, not turn 4.
- **Sibling failure surfaces from the same root cause.** TASK-REV-DEA8
  discovered the parallel `/feature-plan` smoke-gate emission bug
  in the same session. Both stem from "permissive producer / strict
  consumer with no mediator" — the seam between guardkit's emission
  side and validation side has insufficient invariants.
