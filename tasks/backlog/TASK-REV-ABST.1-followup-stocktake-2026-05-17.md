---
id: TASK-REV-ABST.1
title: Follow-up stocktake review on 2026-05-17 — score TASK-REV-ABST falsifiers and pick Continue/Hold/Pivot
status: backlog
created: 2026-05-10T18:50:00Z
updated: 2026-05-10T18:50:00Z
priority: high
tags: [review, followup, narrow-recommendation, falsifier-evaluation, deferred-2026-05-17]
parent_review: TASK-REV-ABST
parent_task: TASK-REV-ABST
task_type: review
decision_required: true
complexity: 5
review_mode: architectural
review_depth: quick
not_actionable_until: 2026-05-17
depends_on:
  - TASK-FREEZE-ABST
  - TASK-OBS-ABST
  - TASK-RETIRE-AC
  - TASK-DEMOTE-PA
---

# Task: 2026-05-17 follow-up stocktake — falsifier evaluation

> **Why this exists**: TASK-REV-ABST recommended **Narrow** with a 7-day
> freeze and a re-measurement deadline of 2026-05-17. This task is the
> formal re-measurement. Its job is to score the falsifiers in TASK-REV-ABST
> §8.2 against the data the freeze week has surfaced and pick exactly one
> outcome: **Promote-to-Continue**, **Hold-Narrow**, or **Escalate-to-Pivot**.
>
> **Do not start before 2026-05-17.** The whole point of the freeze is that
> the data only becomes available after it ends.

## Description

This is a `/task-review --mode=architectural --depth=quick` against the
existing TASK-REV-ABST evidence base, augmented with whatever the freeze week
has surfaced. The review is shallower than the original (depth=quick rather
than depth=thorough) because:

- The trajectory analysis (§2 of TASK-REV-ABST) does not need re-running —
  the freeze guarantees no new commits in the window.
- The gate-by-gate matrix (§4) only needs updates for any gate retired by
  TASK-RETIRE-AC or demoted by TASK-DEMOTE-PA.
- The doom-loop test (§6) gets a one-week extension (W19 → W20).
- The recommendation (§8) is a re-pick, not a re-derivation.

The follow-up's primary input is **TASK-OBS-ABST's metric snapshot** for the
2026-05-11→2026-05-17 window. Without that snapshot, this task degrades to
"manual filename census" — the same approach as the original review §3,
which the operator and reviewer agreed was too coarse. So if TASK-OBS-ABST
hasn't completed by 2026-05-17, escalate to the operator before proceeding.

## Acceptance criteria

### AC-001 — Eligibility check
**WHEN** the operator starts this task, **THE SYSTEM SHALL** verify:
- Today's date is on or after 2026-05-17.
- TASK-OBS-ABST has produced a metric snapshot covering 2026-05-11→2026-05-17.
- TASK-FREEZE-ABST held — no NEW_GATE commits to the frozen paths during the
  window (verify via `git log --since=2026-05-11 --until=2026-05-17`).
- TASK-RETIRE-AC has produced an audit report (decision recorded — keep or
  retire).

**IF** TASK-OBS-ABST is incomplete, **THE SYSTEM SHALL** abort and escalate to
the operator. **IF** the freeze did not hold (a NEW_GATE commit exists in the
window), **THE SYSTEM SHALL** flag the violation in the report and
proceed — the analysis is still valid, but the freeze-as-process needs review
in §process-falsifier.

### AC-002 — Score the four falsifiers
**THE SYSTEM SHALL** evaluate each of the four falsifiers from
`.claude/reviews/TASK-REV-ABST-review-report.md` §8.2:

| Falsifier | Source | Verdict |
|---|---|---|
| POSITIVE-1: ≥3 consumer-repo features pass cleanly on first-turn during the freeze | TASK-OBS-ABST snapshot `first_pass_pass` per repo for the freeze week | fired / not-fired / insufficient-evidence |
| POSITIVE-2: No new framework FP incident filed during the freeze | TASK-OBS-ABST snapshot `framework_fp_incidents` for the freeze week | fired / not-fired / insufficient-evidence |
| NEGATIVE-1: A new framework FP class filed (i.e. a class not yet documented in `.claude/rules/`) | Inventory of any new `.claude/rules/*-is-not-*.md` or sibling pattern files added in the window | fired / not-fired |
| NEGATIVE-2: Any consumer-repo feature stalls for ≥5 turns on identical Coach feedback signature with all production-code gates green | TASK-OBS-ABST snapshot `multi_retry_stuck` plus a coach-turn-JSON pass for identical-signature detection | fired / not-fired |

Note: under the operator-deadline constraint, POSITIVE-1 is **opportunistic**.
If the operator did not run any consumer-repo autobuilds during the freeze
(likely, given DDD South West + Kaggle Hackathon deadlines), POSITIVE-1 is
*insufficient-evidence*, not *not-fired*. Document the distinction.

### AC-003 — Doom-loop test extension (W19 → W20)
**THE SYSTEM SHALL** repeat the §6 doom-loop test for W20 (2026-05-12 to
2026-05-18). Count new failure-classes seeded as design rules (new files in
`.claude/rules/` matching the *-is-not-* / sibling-pattern shape, or new
Graphiti episodes in `guardkit__project_decisions` referencing a new meta-
class).

- **W20 ≤ 1 new class**: trajectory is converging (debug-cycle-end behaviour).
- **W20 = 2 new classes**: ambiguous — weight against W19's count.
- **W20 ≥ 3 new classes**: rising — supports doom-loop hypothesis.

### AC-004 — Pick exactly one outcome
**THE SYSTEM SHALL** pick exactly one of:

- **Promote-to-Continue**: POSITIVE-1 fired (or insufficient-evidence under
  deadline) AND POSITIVE-2 fired AND no NEGATIVE fired AND W20 ≤ 1 new class.
  Lift the freeze; remove the freeze pointer from CLAUDE.md; mark the
  trajectory closed.

- **Hold-Narrow**: ambiguous outcome (POSITIVE-1 insufficient-evidence AND
  POSITIVE-2 fired AND no NEGATIVE fired AND W20 ≤ 2). Extend the freeze to
  2026-05-24 and schedule TASK-REV-ABST.2.

- **Escalate-to-Pivot**: any NEGATIVE fired OR W20 ≥ 3 new classes. File
  TASK-REV-PIVOT (deterministic-Coach keep/retire decision, follow-up to
  TASK-REV-0414). Hold the freeze in place pending pivot review outcome.

### AC-005 — Anti-bias check
**THE SYSTEM SHALL** explicitly consider the counter-hypothesis to whatever
verdict AC-004 picks. If picking Continue, spend a section on "what would I
expect to see if Narrow should have held / escalated to Pivot" and check
whether that signal is present. Same for Hold and Pivot. This guards against
operator-confirmation bias on the convenient outcome.

### AC-006 — Update CLAUDE.md and freeze record
**WHEN** the verdict is Continue, **THE SYSTEM SHALL** remove the freeze
pointer from `CLAUDE.md` (per TASK-FREEZE-ABST AC-003) and update
`.claude/state/gate-freeze-2026-05-17.md` with a final-status line: "Freeze
ended 2026-05-17. Outcome: Continue. See TASK-REV-ABST.1 follow-up report."

**WHEN** the verdict is Hold, **THE SYSTEM SHALL** extend the freeze record's
end date to 2026-05-24 and update CLAUDE.md accordingly.

**WHEN** the verdict is Pivot, **THE SYSTEM SHALL** keep the freeze in place
pending TASK-REV-PIVOT outcome and document the escalation.

### AC-007 — Follow-up report persisted
**THE SYSTEM SHALL** write
`.claude/reviews/TASK-REV-ABST.1-followup-report.md` containing:
- Eligibility-check results (AC-001).
- Falsifier scoring (AC-002).
- Doom-loop W20 extension (AC-003).
- Verdict (AC-004).
- Anti-bias check (AC-005).
- Updated headline next-task list (any deferred → fired tasks; new TASK-REV-
  PIVOT if escalating).

### AC-008 — Decision checkpoint
**THE SYSTEM SHALL** present an `[A]ccept / [R]evise / [I]mplement / [C]ancel`
decision checkpoint to the operator with the verdict and the headline next-
task list. Same shape as TASK-REV-ABST §10.

## Implementation notes

- This is **not** a fresh review. Re-use the TASK-REV-ABST evidence base for
  everything that hasn't changed (timeline, gate-by-gate matrix). Update only
  what the freeze week's data informs.
- The follow-up report should be substantially shorter than the original
  (target 1500-2500 words vs the original's ~6000). The original did the
  hard analysis; this just scores against falsifiers.
- If TASK-OBS-ABST is not yet complete by 2026-05-17 morning, do *not* run
  this task with degraded data — escalate. The whole point of the metric is
  that the follow-up is data-grounded, not vibes-grounded.

## Files to read

- `.claude/reviews/TASK-REV-ABST-review-report.md` (full re-read of §8 + §6)
- `.claude/observability/run-success-snapshot-2026-05-1{0,7}.json` (start +
  end of freeze window — diff is the headline)
- `.claude/state/TASK-RETIRE-AC-audit-*.md`
- `.claude/state/TASK-DEMOTE-PA-audit-2026-05-17.md` (if produced)
- `.claude/state/gate-freeze-2026-05-17.md`
- `git log --since=2026-05-11 --until=2026-05-17` (freeze window)
- New files in `.claude/rules/` since 2026-05-10 (rule-rate signal)

## Files to modify

- `CLAUDE.md` (per AC-006 outcome)
- `.claude/state/gate-freeze-2026-05-17.md` (per AC-006 outcome)
- `tasks/backlog/TASK-REV-ABST-autobuild-bdd-verification-stocktake.md`
  frontmatter (`review_results.followup_outcome` field)

## Files to create

- `.claude/reviews/TASK-REV-ABST.1-followup-report.md`
- (Conditional, only if Pivot) `tasks/backlog/TASK-REV-PIVOT-deterministic-
  coach-keep-retire-decision.md`

## References

- Originating review: `.claude/reviews/TASK-REV-ABST-review-report.md`
- Falsifier definitions: same review §8.2
- Doom-loop test: same review §6
- Anti-bias methodology: same review §7
- TASK-REV-0414 — Option D origin (deterministic-Coach path); the candidate
  for Pivot review if NEGATIVE-1 or NEGATIVE-2 fires

## Dependencies

- **Blocks on**: TASK-FREEZE-ABST (freeze must have been declared and held)
- **Blocks on**: TASK-OBS-ABST (metric snapshot is the primary input)
- **Blocks on**: TASK-RETIRE-AC (assumption-confidence audit must be complete)
- **Soft dependency**: TASK-DEMOTE-PA (its outcome can be folded in if
  available, otherwise note it as still-pending)
- **Earliest start**: 2026-05-17

## Definition of done

- [ ] AC-001: preconditions verified or escalated
- [ ] AC-002: all four falsifiers scored
- [ ] AC-003: W20 doom-loop test run
- [ ] AC-004: exactly one verdict picked
- [ ] AC-005: anti-bias counter-hypothesis check documented
- [ ] AC-006: CLAUDE.md and freeze record updated per verdict
- [ ] AC-007: follow-up report at
  `.claude/reviews/TASK-REV-ABST.1-followup-report.md`
- [ ] AC-008: decision checkpoint presented to operator
- [ ] If verdict is Pivot: TASK-REV-PIVOT filed with concrete content (not
  just title)
- [ ] Task moved to `review_complete` with provenance fields populated
