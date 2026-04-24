---
id: TASK-FIX-7A02
title: Classify player_invocation_stall vs coach_feedback_stall at AutoBuild summary layer
status: backlog
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T12:55:00Z
priority: high
tags: [autobuild, stall-classification, diagnostics, orchestrator]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 2
conductor_workspace: autobuild-sdk-stall-resilience-w2-1
complexity: 5
depends_on:
  - TASK-FIX-7A01
---

# Task: Classify player-invocation stalls distinctly at the final-summary layer

## Description

Address review TASK-REV-E4F5 finding **F3** and **F4**. When the Player fails
3+ turns at the SDK layer before producing any work, AutoBuild's final summary
currently emits `Suggested action: Review task_type classification and
acceptance criteria` — a misdiagnosis. The task is fine; the Player never ran.

The orchestrator already captures every signal needed:
- `player_result.error` is non-None on every SDK failure
- synthetic reports carry `"_synthetic": True` and
  `recovery_metadata.detection_method ∈ {"player_report","git_test_detection","git_only","test_only"}`
- `implementation_notes` embeds the `original_error` string

…but the final-summary hint block (in `guardkit/orchestrator/autobuild.py`
≈ lines 4538–4561) inspects only Coach-feedback text for the substring
`"SDK API error"`. In FEAT-FORGE-002 Coach's feedback is the AC-miss list
(because the synthetic report fails every AC), so the SDK-hint branch misses
and we fall through to the task-blaming generic hint.

Prior art: TASK-REV-8A08 (FEAT-486D / TASK-AD-004) is the same class of defect,
which makes this the second incident — a structural fix is justified.

## Acceptance Criteria

- [ ] New decision label `player_invocation_stall` (or equivalent constant)
      distinct from `unrecoverable_stall` / `coach_feedback_stall`.
- [ ] At end-of-loop, when all N recent turns (N = stall-threshold, currently 3)
      have `player_result.error is not None` **OR** the synthetic report's
      `recovery_metadata.detection_method` indicates Player never produced a real
      report, the orchestrator emits:
      - decision label `player_invocation_stall`
      - summary hint: _"Player failed {N}× at the SDK layer before producing
        any work. Underlying error (turn 1): <quoted first-turn error>.
        Suggested checks: (a) `claude` is logged in on this host, (b)
        `pip show claude-agent-sdk` matches the working environment."_
      - final-summary table annotation flagging all Player-error rows.
- [ ] Existing `"SDK API error"`-string branch retained **only** as a fallback
      path — the new signal-based branch takes precedence.
- [ ] Coach-rejection stall (identical feedback, real Player report, 0/N criteria
      passing) continues to emit the existing `"Review task_type classification..."`
      hint unchanged.
- [ ] Unit tests covering all three branches:
      1. 3× Player SDK error → `player_invocation_stall`
      2. 3× "SDK API error" in Coach feedback text → existing fallback hint
         (keeps TASK-REV-8A08's diagnostic working)
      3. 3× real Coach rejection with 0/N → `coach_feedback_stall` / task-blaming hint
- [ ] Replaying the two saved transcripts
      (`docs/reviews/bdd-acceptance-wired-up/forge-run-[1-2].md`) through a unit
      fixture produces `player_invocation_stall` rather than the current
      misattribution (assert in an integration-style test, if tractable).

## Files

- `guardkit/orchestrator/autobuild.py` (final-summary / stall-hint block
  ≈ lines 4538–4561; stall detector ≈ 3238–3318 for label integration)
- `guardkit/orchestrator/` — stall-decision constants (likely an enum or
  module-level string set); grep for existing `unrecoverable_stall` definition.
- `tests/orchestrator/test_stall_classification.py` (new or extend existing
  stall tests).

## Implementation Notes

- **Do not** change the stall-detection threshold or timing — this task only
  changes *how the stall is labeled and summarized*, not when it fires.
- The synthetic-report marker `"_synthetic": True` is the single cleanest
  source-of-truth that the Player never produced a real report. Prefer it
  over string-matching on error messages.
- Preserve all existing log lines (WARNING/ERROR) that downstream tooling may
  parse; add new ones rather than retargeting old ones.

## Notes

- Cross-link: findings F3+F4 + recommendation R2 in TASK-REV-E4F5.
- Depends on TASK-FIX-7A01 because R1 touches the same file
  (`autobuild.py` startup-log region vs. final-summary region) and Wave 1
  merges cleanly first; W2 rebases on top.
- This task does **not** attempt to classify streaming-internal SDK errors
  — that's TASK-FIX-7A03's concern. Here we only improve the *summary*
  decision when stalls are already declared by the existing detector.
