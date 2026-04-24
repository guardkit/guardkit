---
id: TASK-FIX-7A07
title: Classify coach_agent_invocations_stall and refine recovery feedback
status: in_progress
created: 2026-04-24T14:00:00Z
updated: 2026-04-24T17:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
priority: high
tags: [autobuild, stall-classification, coach-validation, agent-invocations-gate, diagnostics, summary-renderer]
parent_review: TASK-REV-JMBP
feature_id: FEAT-7A00
implementation_mode: task-work
wave: 2
conductor_workspace: autobuild-sdk-stall-resilience-w2-3
complexity: 5
depends_on:
  - TASK-FIX-7A02
---

# Task: Classify coach_agent_invocations stalls distinctly and make the recovery feedback actionable

## Description

Address review **TASK-REV-JMBP** (jarvis FEAT-J002 MacBook Pro run) Workstream D — decision **D1**.
This task is the symmetric sibling of TASK-FIX-7A02.

TASK-FIX-7A02 handles the "Player never ran at the SDK layer" stall (`player_invocation_stall`).
The jarvis FEAT-J002 run on MBP (2026-04-24) surfaced the **opposite** failure mode: the Player
*did* run successfully on every turn (53–92 files created per turn, 25/25 tests passing for
TASK-J002-008), but the **Coach agent-invocations gate** (wired in TASK-FIX-RWOP1.3.1) rejected
the Player's results for 3+ consecutive turns with an identical signature. The feedback-stall
detector fired correctly, but the final-summary hint still routed to the generic task-blaming
default (`"Review task_type classification and acceptance criteria"`).

Forensic findings from TASK-REV-JMBP (see [docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md](../../../docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md)):

1. **Bimodal routing is the core differentiator.** Every Wave-2 task that approved ran with
   `implementation_mode: direct` (agent-invocations gate bypassed). The two that failed ran in
   default task-work mode, which *requires* 3 sub-agent invocations (specialist + test-orchestrator
   + code-reviewer) per `get_expected_phase_list("implement-only")`.
2. **The Player's own producer-side validator flags the violation.** `agent_invoker.py:5406
   _compute_agent_invocations_validation` runs `validate_agent_invocations(tracker, workflow_mode)`
   and persists the verdict under `task_work_results.agent_invocations_validation.status:
   "violation"`. Coach reads this (`coach_validator.py:645-685`) and faithfully returns a
   feedback decision. The gate itself is correct.
3. **Recovery is closed by the current feedback text.** The Coach's feedback — "task-work results
   claim phases were completed without matching agent invocations. Missing phases: 4, 5" — is
   semantically right but operationally useless: the Player re-enters the turn with no primer on
   *which specific sub-agent to invoke via the Task tool* and repeats the same inline-pytest
   pattern. Hence identical feedback signatures for 3 turns → unrecoverable_stall.
4. **Secondary issue — md5 normalisation robustness.** `autobuild._is_feedback_stalled` collapses
   feedback to an md5 signature. The current normaliser does not sort `missing_phases` before
   hashing, so a hypothetical Player that reorders phase keys in its `phases` dict could produce
   two textually-different-but-semantically-identical feedback strings and miss the stall (latent).

## Acceptance Criteria

- [ ] **AC-1 — new stall classifier branch.** Add a new `decision_label =
      "coach_agent_invocations_stall"` to the existing classifier framework introduced by
      TASK-FIX-7A02. Fires when: all N recent turns (`N == stall_threshold`, currently 3) have
      `turn_record.coach_result.issues[0].category == "agent_invocations_violation"`
      (OR equivalent schema-stable predicate — see Implementation Notes for the resilient check).
- [ ] **AC-2 — summary-hint renderer update.** In `autobuild._render_unrecoverable_stall_summary`
      (currently `autobuild.py:4538-4561`), add a new branch *before* the generic fallback:
      when decision_label == `coach_agent_invocations_stall`, emit:

      > "Coach's agent-invocations gate rejected the Player's task-work results for {N} consecutive
      > turns (missing phases: {sorted missing_phases}; expected {expected_phases}, actual
      > {actual_invocations}). The Player appears to have completed the work inline without
      > invoking the required sub-agents via the Task tool. Inspect
      > `.guardkit/autobuild/{task_id}/task_work_results.json → agent_invocations_validation`.
      > Remediation options: (a) ensure the Player's system prompt mandates Task-tool invocation
      > for Phase 4 (test-orchestrator) and Phase 5 (code-reviewer) — see TASK-FIX-7A08;
      > (b) set `implementation_mode: direct` in the task frontmatter if the task's complexity
      > does not warrant the specialist pipeline."

- [ ] **AC-3 — enriched Coach feedback in the gate itself.** In `coach_validator.py:658-685`
      (`agent_invocations_violation` issue construction), enrich the `description` field to cite
      the **specific sub-agent names** the Player should invoke — not just phase numbers. Derive
      the stack-specific Phase-3 specialist from the existing stack-profile detection
      (`agent_invoker` / project-profile code; grep for `stack_profile` and `phase_3_specialist`).
      The new description should read (example for Python stack):

      > "Task-work produced a report with {actual_invocations} of {expected_phases} required
      > agent invocations. Missing phases: {missing_phases_with_names}.
      > Invoke these agents via the Task tool before re-emitting the report:
      > - Phase 3: `python-api-specialist` (or the detected Phase-3 specialist for this stack)
      > - Phase 4: `test-orchestrator`
      > - Phase 5: `code-reviewer`"

      Render the list filtered to *only the missing phases*, not the entire 3–5 set.

- [ ] **AC-4 — per-task stall sub-type in `review-summary.md`.** In the feature-level review-summary
      renderer (grep for where the "Per-Task Outcomes" table is produced), replace the generic
      `unrecoverable_stall` label in the `Decision` column with the classifier output, e.g.:

      ```
      | TASK-J002-008 | 2 | 6 | FAILED | coach_agent_invocations_stall | … |
      | TASK-J002-013 | 2 | 3 | FAILED | coach_agent_invocations_stall + context_pollution | … |
      ```

      When multiple exit paths co-fire (as in J002-013 — feedback-stall *plus* context-pollution),
      emit both separated by `+`. Maintain backward compatibility with downstream consumers of the
      summary by keeping the legacy `unrecoverable_stall` token as the top-level decision field
      and introducing a new `decision_subtype` alongside.

- [ ] **AC-5 — md5-signature normalisation robustness.** Update
      `autobuild._normalize_feedback_for_stall` (line ~3234) so that for feedback where
      `issues[0].category == "agent_invocations_violation"`, the normaliser **sorts
      `missing_phases` lexicographically** before folding into the hash input. Add a regression
      test using a fixture with two turns whose Coach feedback differs only by missing_phases
      ordering; both must produce identical md5 signatures.

- [ ] **AC-6 — `mixed_partial_failure` feature-level verdict.** In the feature-level summary
      renderer, introduce a new top-line verdict branch: when ≥ 50% of observed tasks approved
      AND ≥ 1 task exited `unrecoverable_stall` AND ≥ 1 task exited before waves completed
      (preempted under `stop_on_failure: True`), emit `MIXED_PARTIAL_FAILURE` in place of
      `FAILED`, accompanied by a headline like "14 of 16 observed tasks approved; 2 stalled;
      7 preempted under stop_on_failure". Keep the overall exit code non-zero (this is still
      a failure — the verdict is about clarity, not about success).

- [ ] **AC-7 — unit tests covering all branches.**
      1. 3× identical `agent_invocations_violation` feedback → decision_label
         `coach_agent_invocations_stall`, new hint emitted.
      2. 3× identical `agent_invocations_violation` feedback with reordered `missing_phases`
         across turns → still classified as stall (AC-5 regression test).
      3. Co-fire case: 3× `agent_invocations_violation` + 3× `test_count=0` checkpoints (as in
         J002-013) → decision_subtype contains both stall labels, review-summary reflects both.
      4. Existing TASK-FIX-7A02 `player_invocation_stall` case still classifies correctly
         (no cross-branch regression).
      5. Enriched Coach feedback (AC-3) — assert the issue `description` contains each missing
         phase's specialist agent name for a representative stack profile.
      6. Feature-level mixed_partial_failure branch (AC-6) — 14/16 approve + 2 stall fixture
         produces the new verdict.

- [ ] **AC-8 — Graphiti seeding.** In the Phase-5 `capture_review_to_graphiti` path (or equivalent
      outcome-persistence hook for the autobuild feature-level finish), when the
      `coach_agent_invocations_stall` label is emitted, persist a fact to
      `guardkit__project_decisions` describing the classification. One-episode-per-feature-run is
      sufficient — do not spam. See `.claude/rules/graphiti-knowledge-graph.md` for group-id
      conventions and the review's Graphiti preamble §"Knowledge-graph remediation
      recommendations" for the episode shape.

- [ ] **AC-9 — replay the jarvis-FEAT002-run-1 evidence as an integration test.** Using the
      preserved `task_work_results.json` + `coach_turn_{5,6}.json` artefacts from the jarvis
      worktree (copy minimal fixture versions into `tests/fixtures/`; do *not* reference the
      external jarvis path), assert that the new classifier produces
      `coach_agent_invocations_stall` rather than the current misattribution.

## Files (expected touch list)

- `guardkit/orchestrator/autobuild.py` — classifier framework hook (≈ `_render_unrecoverable_stall_summary`
  at 4538–4561; stall-detector at 3237–3318 for label integration; feedback-normalisation
  at 3234; feature-level summary renderer for AC-4 and AC-6).
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `agent_invocations_violation` issue
  construction at 658–685 for AC-3 (enriched description).
- `guardkit/orchestrator/agent_invoker.py` — read-only reference; may need a helper exported from
  the stack-profile module to name the Phase-3 specialist.
- `tests/orchestrator/test_stall_classification.py` — extend (if created by 7A02) or new.
- `tests/fixtures/jarvis_feat_j002_replay/` — anonymised/minimised replay fixture for AC-9.
- `installer/core/commands/lib/agent_invocation_validator.py` — **no changes** (the validator
  itself is correct; this task is entirely about classification & feedback rendering).

## Implementation Notes

- **Do not change gate semantics.** The Coach's gate at `coach_validator.py:645-685` correctly
  enforces the Player's producer-side self-verdict. This task does not relax the gate, does not
  add outcome-evidence substitution (option β from the review), and does not introduce a
  task_type profile for `expected_phases` (option γ). Those are deferred to TASK-FIX-7A08
  (proposed, not yet filed) and beyond.
- **Classifier hook placement.** Prefer a single `classify_stall(turn_history,
  checkpoint_history) -> StallClassification` function that all three call sites
  (summary renderer, review-summary-per-task, Graphiti seeding) consume. Avoid duplicating the
  pattern-matching logic across sites.
- **Schema-stable predicate for AC-1.** The preferred predicate is
  `turn_record.coach_result.report.get("issues", [{}])[0].get("category") == "agent_invocations_violation"`
  — walking into the Coach-result report shape. Verify the shape against `coach_turn_6.json`
  in the preserved jarvis worktree; do not match on feedback-text substrings (too brittle).
- **Stack-profile detection (AC-3).** Grep the repo for the existing stack-detection layer —
  TASK-FIX-7A01's pyproject.toml / requirements.txt changes touched neighbouring code. The Phase-3
  specialist name is derived per-project (`python-api-specialist`, `react-typescript-specialist`,
  `dotnet-specialist`, etc.). If that detection is unavailable, fall back to emitting "the
  stack-specific Phase-3 specialist" without naming it — do not hardcode.
- **md5 normalisation (AC-5).** Normalise list-valued fields (`missing_phases`, etc.) before
  hashing by:
    1. extracting the `details` dict
    2. for any list value, replacing it with `sorted(value)`
    3. re-serialising in a canonical form (e.g. `json.dumps(details, sort_keys=True)`)
    4. concatenating with the feedback text before md5.
- **Co-fire handling (AC-4).** Two stall classes fire independently:
  `coach_agent_invocations_stall` (from feedback-stall detector, `autobuild.py:1995`) and
  `context_pollution_stall_no_checkpoint` (from context-pollution exit, `autobuild.py:1982-1988`).
  Both can fire for the same task. The review-summary and Graphiti episode should reflect both.
- **`MIXED_PARTIAL_FAILURE` verdict (AC-6).** This is a cosmetic/clarity improvement to the
  top-line verdict, not a behavioural change. The feature's exit status should remain non-zero
  (this IS still a failure); the verdict name just communicates the shape. Do not let AC-6
  bloat into resume-semantics work — that's explicitly out of scope (see Notes below).
- **Dependency on TASK-FIX-7A02.** This task depends on 7A02's classifier framework. If the 7A02
  implementation chose a different framework shape than anticipated, revisit AC-1's
  `decision_label` naming and integration approach to compose with that shape rather than
  re-inventing it.

## Out of Scope (explicitly)

The following are intentionally deferred and should NOT be absorbed into this task:

- **Player prompt structural change** to mandate sub-agent invocation via the Task tool. This is a
  larger architectural change affecting every task-work-mode run across all projects and requires
  its own review + feature-spec pass. Proposed follow-on: **TASK-FIX-7A08** (not yet filed).
  This task produces *better feedback* so a Player prompt change is unblocked and has a clear
  target; it does not itself fix the Player's invocation habits.
- **Resume semantics** for partially-failed feature runs (`--resume` + `--retry-stalled` /
  `--skip-stalled`). Raised as Workstream F.2 in TASK-REV-JMBP but file separately; not
  appropriate to fold into AC-6.
- **Relaxing the agent-invocations gate** (option β from the review). Explicitly rejected —
  would require an ADR and a trust-model review.
- **Task-type profile for `expected_phases`** (option γ). Deferred — file as its own task if
  pursued.

## Counterfactual

Had this task's AC-1/AC-2 landed before 2026-04-24, the jarvis FEAT-J002 run on MBP would have
failed in exactly the same way (the gate itself fires independently of this task's changes), but
the **final summary hint** would have been actionable: it would have named the specific sub-agents
to invoke or pointed the user at `implementation_mode: direct` as a fix. That alone might have
saved the diagnostic round-trip that generated TASK-REV-JMBP.

## Related

- **Parent review**: [TASK-REV-JMBP](../../in_review/TASK-REV-JMBP-analyse-jarvis-FEAT-J002-autobuild-failure-on-macbook-pro.md)
  — Workstream D decision D1, Workstream F AC-4/AC-6 recommendations.
- **Sibling task (symmetric)**: [TASK-FIX-7A02](./TASK-FIX-7A02-player-invocation-stall-classification.md)
  — `player_invocation_stall` classification. This task composes with 7A02's classifier framework.
- **Companion artefact**: Graphiti preamble at
  [docs/reviews/TASK-REV-JMBP-graphiti-preamble.md](../../../docs/reviews/TASK-REV-JMBP-graphiti-preamble.md).
- **Prior validator wiring**: [TASK-FIX-RWOP1.3.1](../../completed/2026-04/TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md)
  — folded `validate_agent_invocations` into the producer path. This task's ACs build on that fix.
- **Preserved forensic evidence**:
  `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J002/.guardkit/autobuild/TASK-J002-{008,013}/`
  — `task_work_results.json`, `coach_turn_{5,6}.json`, `checkpoints.json`. Consume via
  minimised fixture under `tests/fixtures/` per AC-9.
