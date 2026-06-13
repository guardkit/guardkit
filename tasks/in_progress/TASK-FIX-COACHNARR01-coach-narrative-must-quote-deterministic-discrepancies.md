---
id: TASK-FIX-COACHNARR01
title: Coach feedback must quote deterministic discrepancy records verbatim, not paraphrase them
task_type: feature
status: backlog
created: 2026-06-12T19:50:00Z
priority: high
tags: [autobuild, coach, feedback-quality, b-min, honesty]
complexity: 4
---

# Task: Coach narrative misattribution of deterministic discrepancies

## Problem (observed FEAT-C332 run 2, TASK-QAWE-002, 2026-06-12)

The deterministic honesty gate found a REAL discrepancy (the Player claimed
test runs while the test-orchestrator specialist had hung — see
TASK-FIX-SPECVIOL01). But the Coach's B-min synthesis **invented a wrong
explanation** in the rationale and feedback:

> "The Player claimed to have run tests in files
> (`tests/orchestrator/test_coach_evidence_bundle.py` and
> `tests/unit/orchestrator/quality_gates/test_coach_validator.py`) that do
> not exist on disk."

Both files exist — they are pre-existing, tracked repo files present in
every checkpoint. The Player received the feedback "Ensure all claimed test
files exist" — unactionable, since they do — and burned turn 2 (and the
task budget) failing to act on a hallucinated cause. The verdict
*direction* was right both turns; the *explanation* was fabricated.

Context: Phase-A gather had degraded to B-min synthesis (the known
`gemma4:26b` recursion-limit failure, tracked as TASK-PERF-COACHGATHER01),
so the toolless synthesis model narrated discrepancy records it could not
inspect.

## Fix direction

Feedback derived from deterministic checks must carry the deterministic
record VERBATIM, not an LLM paraphrase:

1. When honesty (or any deterministic gate) produces discrepancies, render
   the structured fields (`category`, `claimed`, `actual`, `severity`,
   paths) directly into the feedback issue `description`/`details` —
   template-formatted, not synthesized.
2. The LLM synthesis may ADD context but must not REPLACE the record; if
   the rationale contradicts the deterministic record (e.g. names a
   category or path not present in any discrepancy), prefer the record.
3. Consider a post-synthesis consistency check: every file path the
   rationale claims "does not exist" must appear in an actual
   `file_existence`-class discrepancy; otherwise strip/correct the claim.

## Acceptance criteria

- [ ] AC-001: feedback issues for deterministic discrepancies embed the
      structured record fields verbatim (category, claimed vs actual).
- [ ] AC-002: a synthesis rationale that names a cause absent from the
      deterministic records is corrected or flagged, not shipped to the
      Player as-is.
- [ ] AC-003: regression test using the FEAT-C332 run-2 records: the
      rendered feedback must NOT contain a "does not exist on disk" claim
      for a path with no file_existence discrepancy.

## Evidence

- Verdicts with the fabricated narrative:
  `.guardkit/autobuild/FEAT-C332-run2-artifacts-TASK-QAWE-002/coach_turn_{1,2}.json`
- Run log: `.guardkit/autobuild/FEAT-C332-run2-stdout.log`
- Disk truth: both named test files exist in every FEAT-C332 checkpoint and
  on main (`git log` shows history to TASK-HMIG-008R / earlier).
- Related: TASK-PERF-COACHGATHER01 (Phase-A always degrades to B-min);
  TASK-FIX-SPECVIOL01 (the underlying discrepancy's real cause).
