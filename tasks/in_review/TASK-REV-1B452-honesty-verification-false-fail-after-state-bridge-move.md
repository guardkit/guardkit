---
id: TASK-REV-1B452
title: "Review: Honesty verification false-fails when state-bridge moves task files mid-turn"
status: review_complete
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
priority: high
task_type: review
tags: [autobuild, coach, honesty-verification, state-bridge, false-fail, absence-of-failure]
complexity: 0
review_results:
  mode: architectural
  depth: standard
  revision: 2
  score: 64
  findings_count: 6
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-1B452-review-report.md
  feature_id: FEAT-1B452
  follow_on_tasks:
    - TASK-FIX-1B4A  # Layer 1 — canonical-path resolution
    - TASK-FIX-1B4C  # Layer 3' — filter orchestrator-induced ghosts
    - TASK-FIX-1B4B  # Layer 2 — demote single discrepancy
    - TASK-DOC-1B4D  # sibling rule
  deferred_tasks:
    - TASK-FIX-1B452-D  # Coach Override (revisit after 2-4 weeks)
  sibling_tasks:
    - TASK-REV-7E3F1  # Bug 2 review (pre-existing): _record_honesty AttributeError on None payload
    - TASK-FIX-7E3F   # Bug 2+3 fix (pre-existing, in_progress): _record_honesty regression + observability
  completed_at: 2026-05-06T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review: Honesty verification false-fails when state-bridge moves task files mid-turn

## Description

During the FEAT-FFC3 Wave 3 autobuild on 2026-05-06, a complete and correct
Player turn (28 minutes, 25 SDK turns, 26 passing tests, 16 ACs covered) was
marked `error` and dragged the entire feature run to `FAILED`. Production code
was correct on disk; the framework rejected it on a bookkeeping technicality.

**Root mechanism (as documented in the incident report):**

1. `guardkit.tasks.state_bridge` moves the task markdown from
   `tasks/backlog/TASK-FFC3-005-...md` to `tasks/design_approved/...md` at
   the start of the task's first turn.
2. The Player reads the (already-moved) task spec, whose frontmatter and
   prose still quote the old `tasks/backlog/...` path.
3. The Player completes its work and lists the old `tasks/backlog/...` path
   under `files_modified` in its self-report.
4. `coach_validator` honesty verification does **exact-path string matching**
   against disk, sees `File does not exist`, raises a `must_fix` honesty
   issue, and **short-circuits gate evaluation** before any of the 16
   acceptance criteria are evaluated.
5. `criteria_verification` and `acceptance_criteria_verification` come back
   empty. Verdict: `feedback` → turn 2 retry → SDK exit 1 → final `error`.

This task analyzes the failure, scopes the fix, and produces an
implementation breakdown. Implementation is out of scope (a follow-on
`/task-work` task is expected if the review concludes a fix is warranted).

## Context

**Incident report (load-bearing reference):**
[autobuild-FFC3-honesty-path-mismatch-incident.md](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/history/autobuild-FFC3-honesty-path-mismatch-incident.md)

**Companion evidence (in the specialist-agent repo, not this one):**
- Raw autobuild log: `specialist-agent/docs/history/autobuild-FFC3-failed-overall-history.md`
- Coach JSON: `.guardkit/worktrees/FEAT-FFC3/.guardkit/autobuild/TASK-FFC3-005/coach_turn_1.json`

**Affected GuardKit components (in this repo):**
- `guardkit/orchestrator/quality_gates/coach_validator.py` (honesty verification step,
  short-circuit logic)
- `guardkit/orchestrator/quality_gates/coach_verification.py` (CoachVerifier — the
  on-disk verifier wired in by TASK-AB-FIX-INVAB1)
- `guardkit/tasks/state_bridge.py` (the component that moves task files
  mid-turn)
- Player prompt assembly path (whichever module injects the task spec into
  the Player system prompt — to be confirmed during review)

**Related prior art (must be reviewed for consistency, not duplicated):**
- `.claude/rules/absence-of-failure-is-not-success.md` — the meta-rule that
  governs Coach gates that misread zero-cardinality oracle results. **This
  defect is the inverse shape**: not a false-green from absent evidence, but
  a false-red from path-string mismatch. Review must articulate the
  relationship between the two and decide whether one rule covers both or
  whether a sibling rule is needed.
- TASK-AB-FIX-INVAB1 (commit `b9a45694`) — wired `CoachVerifier` into the
  deterministic Coach path. The honesty verification that fired here is
  almost certainly that verifier. Review must identify exactly which call
  site short-circuits the gate and why.
- TASK-REV-0414 — origin of the Option D delegation pattern that introduced
  the deterministic Coach. The short-circuit-on-honesty behaviour was
  presumably designed for content-hash mismatches and over-applied to
  path-string mismatches.

## Review Scope

**Focus**: All three layers proposed in the incident report, in priority
order:

1. **Layer 1 (load-bearing)**: Identity-based honesty matching. Resolve
   `files_modified` claims through state-bridge canonical paths keyed on
   task ID, not raw path-string equality. Pseudocode in the incident report
   §"Recommended fix" §1.

2. **Layer 2 (robustness)**: Don't short-circuit the entire 16-AC gate on a
   single path-only honesty discrepancy. Demote single path-only
   discrepancies from `must_fix` to `feedback`; reserve hard short-circuit
   for content-hash mismatches or multiple discrepancies.

3. **Layer 3 (preventative)**: Inject the post-move canonical path into the
   Player's prompt context at turn start, so the Player quotes the correct
   path in its self-report. Defer-able if Layer 1 lands.

**Trade-off priority**: Correctness (no more false-fails) over throughput.
The incident wasted ~28 minutes of SDK time and one full retry budget; the
manual recovery (flipping the YAML status to `completed`) bypassed the
gate entirely, which is itself a hazard.

**Out of scope:**
- Changes to the SDK exit-1 crash on turn 2 — that's a separate
  transient-recovery defect, tracked elsewhere if at all.
- Broader rework of the state-bridge mid-turn semantics (e.g., "should we
  even be moving the file mid-turn?"). The review may recommend this as a
  follow-up but should not block on it.
- Implementation. This is a `/task-review` task; implementation is a
  follow-on `/task-work` task if the review approves a fix.

## Acceptance Criteria

- [ ] **AC-1**: Failure mechanism confirmed against the running code.
  Identify the exact `coach_validator` call site that short-circuits gate
  evaluation on a `must_fix` honesty issue. Cite file + line.
- [ ] **AC-2**: Identify the exact honesty-verification logic that performs
  path-string equality against `files_modified` claims. Confirm it is
  `CoachVerifier` (TASK-AB-FIX-INVAB1) or, if not, identify what is.
- [ ] **AC-3**: Confirm or refute that `state_bridge` exposes (or could
  cheaply expose) a `canonical_path_for(task_id)` lookup. If not, scope
  the change.
- [ ] **AC-4**: Articulate the relationship to
  `.claude/rules/absence-of-failure-is-not-success.md`. Decide: does the
  existing rule cover this defect, does it need an inverse-shape sibling,
  or is the existing rule the wrong frame?
- [ ] **AC-5**: Decide whether Layer 2 (don't short-circuit) is a separable
  defect from Layer 1. If yes, propose two follow-on tasks; if no, justify
  the bundling.
- [ ] **AC-6**: Produce an implementation task breakdown for whichever
  layers the review approves. Each subtask should be independently
  implementable and testable. Include parallelisation hints where
  applicable.
- [ ] **AC-7**: Specify the regression test shape: simulate a state-bridge
  move during turn 1, run a fixture Player that emits the old path in its
  self-report, assert Coach evaluates the 16 ACs rather than
  short-circuiting. Indicate where this test should live (which test
  module under `tests/`).
- [ ] **AC-8**: Risk assessment per layer. What does each fix break if
  done wrong? Layer 1's biggest risk is masking genuine Player honesty
  violations (claim path X, actually wrote path Y); the review must
  address this directly.
- [ ] **AC-9**: Decide on the manual-recovery hazard: should the YAML-flip
  workaround used for FEAT-FFC3 be supported, deprecated, or replaced
  with an in-product Coach override? This is adjacent but should be
  flagged.

## Review Mode

Recommended: `/task-review TASK-REV-1B452 --mode=architectural --depth=standard`

The defect spans the Coach gate semantics, the state-bridge contract, and
the Player prompt assembly. Architectural mode is appropriate; deep mode
is overkill given the clear reproduction.

## Notes

- This is a **review task only**. Do not start implementing. After
  review, the [I]mplement decision will create the follow-on task.
- The Graphiti design-rule node *"absence-of-failure-is-not-success"*
  exists under `guardkit__project_decisions`. If the review concludes a
  sibling rule is needed for the false-red shape, propose the node name
  and content; do not write the rule in this task.
- Manual workaround already applied to FEAT-FFC3: TASK-FFC3-005 status
  flipped to `completed` in `.guardkit/features/FEAT-FFC3.yaml` to
  unblock Wave 4. The production code is correct and committed to the
  worktree on branch `autobuild/FEAT-FFC3`. The reviewer should not need
  to re-run the autobuild to reproduce — the artifact JSON is preserved.
