---
id: TASK-REV-F6E1
title: "Analyse forge-run-6 failure; decide fix-class vs revert AutoBuild today"
status: completed
created: 2026-04-25T13:00:00Z
updated: 2026-04-25T14:55:00Z
completed: 2026-04-25T14:55:00Z
decision: accepted
decision_action: "User actioning F3c directly via coach_validator.py:657 edit; ~10 forge iterations to follow"
priority: critical
task_type: review
review_mode: decision
review_depth: standard
parent_review: TASK-REV-45750
parent_feature: FEAT-AB59
tags:
  - autobuild
  - critical-path
  - blocker
  - decision-point
  - F4A1-followup
  - revert-candidate
  - forge-run-6
related_to:
  - TASK-REV-45750
  - TASK-VAL-7C2E
  - TASK-REV-119C1
  - TASK-REV-F4A1
  - TASK-FIX-7A08
  - TASK-DIAG-F4A2
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  recommendation: implement_F3c
  recommendation_summary: "Demote agent_invocations_validation from blocker to feedback-enricher in coach_validator.py:657-738. Lets positions 2-4 (outcome gates + AC verification) run instead of being short-circuited by the process check."
  diagnostic_root_cause: "Process-check at coach_validator.py:720 short-circuits outcome gates and AC verification on violation. Wired 2 days ago in commit 7c14c01d (RWOP1.3.1). Single ordering decision is most of the pain."
  bisect_anchor: "Last green AutoBuild = nats-infrastructure FEAT-7B86 @ 2026-04-13 23:01"
  pivotal_commit: "7c14c01d (RWOP1.3.1, 2026-04-23 08:00) wired agent_invocations validator into producer; coach_validator.py:720 short-circuits on its violation"
  options_considered: [F1, F2, F2_prime, F3, F3c, F4_revert]
  iteration_plan: "14:30-15:30 implement F3c; then ~10 forge cycles of 30-40min each (~7.5h budget). Each run produces fresh AC-verification evidence in forge-run-N.md. Hard stop 22:00."
  out_of_scope_named: "Feature-level integration verification via QA-Tester agent invoking /task-review and /task-work — the real answer to '80% complete'. Filed for calmer-waters planning AFTER today's F3c iteration evidence informs its design."
  report_path: docs/reviews/forge-run-6-fix-or-revert/TASK-REV-F6E1-decision-report.md
  revisions:
    v1:
      timestamp: 2026-04-25T14:05:00Z
      recommendation: implement_F2_prime
      superseded_reason: "Timeline error (3-4 days not 3 weeks); user wants real fix today not tactical bypass; missed the gate-ordering short-circuit diagnostic"
    v2:
      timestamp: 2026-04-25T14:30:00Z
      recommendation: implement_F3c
      superseded_reason: "Test-run cycle math wrong (30-40min not 90min); didn't anchor that AutoBuild has been solid for weeks; missed the named 'integration via QA-Tester agent' future workstream"
    v3:
      timestamp: 2026-04-25T14:50:00Z
      recommendation: implement_F3c
      iteration_capacity: "~10 forge cycles available, not 3"
      reframing: "AutoBuild solid for weeks; recent BDD-AC bridge work landed an over-eager process gate that blocks its own AC verification pipeline; F3c unblocks small well-scoped feature; future integration/e2e gap addressed by separate QA-Tester agent workstream (out of scope today)"
  completed_at: 2026-04-25T14:50:00Z
---

# Task: Analyse forge-run-6 failure; decide fix-class vs revert AutoBuild today

## Hard constraint (user-imposed)

**Deadline: 23:00 today (2026-04-25).** Window opens at 13:15 = **~9 h 45 m
total** from review start to either a working AutoBuild or a clean revert.
AutoBuild is now blocking all other development work. The user has
explicitly framed this as a binary decision window — sustained debugging
is no longer affordable. The review must end with one of:

- **[I]mplement** — a fix-class with ETA + buffer that fits inside the
  remaining window (after this review consumes its own time-box).
- **[R]evert** — roll AutoBuild back to the last known working state
  (likely pre-FEAT-AB59, pre-TASK-FIX-7A08, or whatever bisect
  identifies) and freeze further AutoBuild changes until a calmer
  review window.
- **[A]ccept** — only if the analysis reveals the failure is unrelated
  to AutoBuild and a much smaller external fix unblocks it.

**Time-budget arithmetic the review must respect**:
- Review itself: ≤60 min (tighter than the original 90 min — execution
  has more room now, so spend less on diagnosis).
- Implementation buffer: leave ≥2 h slack for "the fix didn't work,
  revert anyway".
- Live forge re-run cost: ~30-60 min if attempted as proof.
- Net implementation budget if [I]mplement is chosen: ~6-7 h, depending
  on how thorough the verification step is.

The user's mystification signal is also a finding: *"I'm a bit mystified
as to why this is proving quite so difficult if I'm honest."* This means
the cumulative debugging cost has crossed a threshold where pragmatic
revert-and-reassess may be the right call regardless of whether a clean
fix exists in code.

## Why this task exists

forge-FEAT-FORGE-002 was the acceptance target FEAT-AB59 was supposed to
unblock. forge-run-6 (the post-FEAT-AB59 live run, log at
`docs/reviews/bdd-acceptance-wired-up/forge-run-6.md`, 1575 lines) **still
failed** — but with a different signature than forge-run-3/5:

**Wave 2 result**: 0 / 3 tasks passed (TASK-NFI-003, TASK-NFI-006,
TASK-NFI-007 all failed with `unrecoverable_stall` after 3 turns each).

**The new failure mode**:

> *"Coach's agent-invocations gate rejected the Player's task-work
> results for 3 consecutive turns (**missing phases: ['3']**;
> co-fired stall sub-types: `context_pollution_stall_no_checkpoint`)."*

> *"(a) ensure the Player's system prompt mandates Task-tool invocation
> for the missing phases. Required specialists: **Phase 3: the
> stack-specific Phase-3 specialist (Implementation)**;
> (b) set `implementation_mode: direct` in the task frontmatter if the
> task's complexity does not warrant the specialist."*

(forge-run-6.md lines 1310–1325, 1410–1422, 1493–1505.)

**This is the same prompt-class fix-class that was already refuted by
TASK-FIX-7A08** (reverted across three commits). The Player LLM not
invoking the stack-specific Phase 3 specialist via the `Task` tool. The
Coach correctly flags it as a violation. AutoBuild correctly classifies
the stall as unrecoverable. The fix that was supposed to be structural
(orchestrator-side specialist invocation, FEAT-AB59) **only addressed
Phases 4 and 5**, not Phase 3.

## What the log positively confirms (the FEAT-AB59 fix DID land)

forge-run-6 contains **9 instances** of:

> `INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator
> specialist records into … task_work_results.json (merged=2,
> validation=violation)`

(forge-run-6.md lines 683, 755, 853, 951, 1046, 1171, 1254, 1354, 1437.)

This proves:
- **FEAT-AB59 wiring is firing on every non-direct task** ✅
- **`_inject_specialist_records_into_task_work_results` runs in
  production** ✅
- The merged ledger shows `merged=2` (Phase 4 and Phase 5 records were
  injected with `source: "orchestrator"`) ✅
- TASK-VAL-7C2E's stub-SDK gate has a real-SDK corroboration in the wild
  (this is the live-SDK confirmation that was missing from
  TASK-REV-45750 — ironically delivered by a *failed* run rather than a
  canonical validation) ✅

**FEAT-AB59 works. The problem moved.**

The Phase 4/5 gate-credit problem that consumed the past three weeks is
now resolved at the structural level. The Phase 3 gate-credit problem is
the new bottleneck — and it's the *same shape* as the original Phase 4/5
problem (Player ignores Task-tool prompt instruction).

## Reasoning rigour required

This is the third reviewer-cycle on the same family of defects. The risk
is over-fitting a fix to forge-run-6 that doesn't generalise. The
reviewer MUST:

1. **State the meta-pattern explicitly**: every "Player must invoke a
   specialist via the Task tool" gate is **prompt-class-fragile**. We
   already proved this with TASK-FIX-7A08 (reverted). FEAT-AB59 fixed
   Phases 4 and 5 by removing the Player from the loop. Phase 3 is now
   the only remaining LLM-discretion gate, and it has the same failure
   mode for the same reason.

2. **Quantify the bisect cost**. What's the last AutoBuild commit that
   ran forge or jarvis green? If it predates FEAT-AB59, reverting loses
   the Phase 4/5 fix but unblocks development. If it predates other
   changes too (TASK-DIAG-F4A2, TASK-FIX-RWOP1.x, TASK-FIX-7A09,
   TASK-FIX-7A07, etc.), reverting loses more. Specifically check
   forge-run-1/2 logs to anchor "last green".

3. **Identify the cheapest possible fix-class**. Three candidates,
   re-scored against the 9 h 45 m window:
   - **F1 — Mirror FEAT-AB59 to Phase 3**: orchestrator-side invocation
     of the stack-specific Phase 3 specialist. Similar shape to
     OSI-001/004/005/006 — but Phase 3 has more variance (per-stack
     specialist routing, more allowed_tools, larger prompt context,
     and the Player still has to write the implementation either way,
     so "orchestrator runs the specialist alongside the Player" or
     "orchestrator runs it instead of the Player" is itself a design
     question). **Marginally feasible inside today's window** if scope
     is brutally tight (one stack only — Python/forge — defer the
     general fix), but high risk: the FEAT-AB59 build cycle was 4-5
     hours of focused work for two specialists in a more constrained
     design space. F1 today is the high-variance bet.
   - **F2 — Per-task `implementation_mode: direct` autodetection
     widening**: the stall message itself names this option:
     *"set `implementation_mode: direct` in the task frontmatter if the
     task's complexity does not warrant the specialist"*. The current
     auto-detect direct-mode threshold is `complexity ≤ 1`
     (`agent_invoker.py:_auto_detect_direct_mode`). Widening to
     ≤ 2 or ≤ 3, OR auto-detecting "no test scaffolding required"
     tasks as direct, could unblock the three forge Wave-2 tasks
     today. **ETA: 1-2 h**. Comfortably fits the window with full
     buffer for a verification forge re-run. Lower-variance bet than
     F1.
   - **F3 — Make the Phase 3 gate non-load-bearing**: change
     `agent_invocations_validation` so a missing Phase 3 marker
     downgrades to `warning` rather than `violation` when the
     implementation files were nonetheless created and tests pass.
     Coach falls back to evidence-based judgement. **ETA: 1-2 h**.
     Comfortably fits the window. Risk: introduces a quality-gate
     softening that may not be reversible — once the gate is "just a
     warning", deciding to harden it back later requires the same
     prompt-class reasoning that's failed three times already.
     Could be paired with F1 in a follow-up workstream.

4. **Honest revert scoring**. The user asked: *"why is this proving
   quite so difficult?"* The reviewer must answer that question with
   evidence (number of revisions in the past N weeks, fix-class
   genealogy, refuted-fix list). If the answer is "the prompt-class
   fix-class is fundamentally fragile and we've now hit the third
   variant of it", revert + freeze + plan a clean structural rewrite
   in calmer waters is a defensible call. **Do not anchor on "we just
   need one more fix"**.

5. **Bound the day**. Whichever path is recommended, it must fit in
   the remaining wall-clock (≤ ~6-7 h after this review's own
   time-box and a ~2 h buffer for "the fix didn't work, revert
   anyway"). No "small" fix that's actually a day-and-a-half. No
   "we'll just verify one more thing." If the recommended path slips
   past 21:00, the fallback is the pre-named revert candidate —
   the review must define that handoff explicitly so the user can
   pivot without re-deciding.

## Description

Read forge-run-6.md end-to-end. Cross-reference against the FEAT-AB59
deliverables (verified in TASK-REV-45750), the TASK-FIX-7A08 revert
history, and the agent_invocations gate logic. Produce a decision
report that ends with one of [I]mplement-X / [R]evert-to-Y /
[A]ccept-because-Z, where each option has explicit ETA, risk, and
post-decision next step. The user picks the path. Execution of that
path is OUT OF SCOPE for this review — file as a follow-up task with
a clear handoff.

### Scope (in)

1. **Read evidence**:
   - `docs/reviews/bdd-acceptance-wired-up/forge-run-6.md` (full log,
     1575 lines)
   - `docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md`
     (the post-FEAT-AB59 review that said wiring was sound)
   - `docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md` (the
     diagnostic that motivated FEAT-AB59 in the first place — confirm
     the problem genuinely shifted vs. recurring)
   - The three failing task files: `TASK-NFI-003`, `TASK-NFI-006`,
     `TASK-NFI-007` (in
     `.guardkit/worktrees/FEAT-FORGE-002/tasks/backlog/` if preserved)
   - `task_work_results.json` for each of the three failing tasks
     (worktree path quoted in the log) — confirm
     `agent_invocations_validation.missing_phases == ["3"]` and
     orchestrator-injected Phase 4/5 records are present
   - Git log for AutoBuild-touching files since the last green
     forge/jarvis run; identify candidate revert points

2. **Quantify the meta-pattern**:
   - List every commit in the past N weeks that addressed a
     "Player ignores Task-tool prompt for Phase X" failure.
   - For each, note: shipped → reverted? still in tree?
   - State whether Phase 3 stochastic delegation has the same
     prompt-class fingerprint as Phase 4/5 had (forge-run-3/5
     analyses) — yes/no/with caveat.

3. **Score the three fix-classes** (F1, F2, F3) plus revert (F4):
   - ETA bound (hours, against the 23:00 deadline)
   - Probability the forge Wave 2 unblocks
   - Risk of regressing things that currently work
   - Reversibility if it doesn't help
   - Whether it survives the next failure variant
   - **Pivot wall-clock**: at what time-of-day should the user
     abandon this option and fall back to revert? (e.g. "if F2 isn't
     verifiably green by 20:30, revert at 21:00".)

4. **Identify the bootstrap nuisance**: forge-run-6.md lines 46-48 show
   `nats-core` dependency resolution failed during environment
   bootstrap (PEP-668 venv install error). Lines 207, 272 show SDK
   exit-code-1 errors from coach_validator early in the run. Determine
   whether either of these is a contributing factor or a noisy
   side-issue. **One paragraph max** — do not let this consume the
   review.

5. **Produce a decision recommendation** with all four options scored
   and one recommended. Time-box your reasoning: this review must end
   in ≤60 minutes of reviewer wall-clock so the user has 8+ hours
   remaining to execute and verify.

### Scope (out)

- **Implementing any of F1/F2/F3/F4**. This is a review, not a fix.
  Execution is the user's call after seeing the recommendation.
- **Re-running forge or jarvis**. forge-run-6 is the data; another live
  run before the decision is more spend in the same hole.
- **Re-debating FEAT-AB59 architecture**. It's verified-correct;
  TASK-REV-45750 closed that question. Phase 4/5 are demonstrably
  unblocked.
- **Long-form post-mortem of the past three weeks**. One paragraph in
  the report is enough; the deeper retro can happen after the
  immediate blocker is resolved.

### Acceptance criteria

- [ ] AC-001: forge-run-6.md fully read; the three stalled tasks'
      `missing_phases: ["3"]` signature is confirmed end-to-end (Coach
      stall classification → orchestrator unrecoverable detection →
      task-work_results.json gate block).
- [ ] AC-002: A timeline of the relevant fix-classes is produced
      (TASK-FIX-7A08 lifecycle, FEAT-AB59 lifecycle, this-Phase-3
      lifecycle), making the meta-pattern visible at a glance.
- [ ] AC-003: A bisect candidate is named: the most-recent commit
      before which AutoBuild was last seen running forge/jarvis green
      end-to-end, with a one-line diff-summary of what would be lost
      by reverting to it.
- [ ] AC-004: Each of F1/F2/F3/F4 is scored on the four axes (ETA,
      unblock probability, regression risk, reversibility), in a
      single table.
- [ ] AC-005: The report's last section is a single decision
      recommendation with one paragraph of justification. The
      recommendation must answer the user's "why is this proving so
      difficult?" question honestly.
- [ ] AC-006: A handoff follow-up task is named for whichever option is
      recommended (e.g.
      `TASK-FIX-<hash>: Widen direct-mode autodetection to complexity ≤ 3`
      or `TASK-REVERT-<hash>: Pin AutoBuild to commit <sha> until
      structural Phase 3 fix lands`). Just the title + 3-line scope —
      detailed task creation is part of the handoff.
- [ ] AC-007: Report saved at
      `docs/reviews/forge-run-6-fix-or-revert/TASK-REV-F6E1-decision-report.md`.

## Implementation Notes

- **Treat reviewer time as the most expensive resource right now.** Do
  not boil the ocean. The deliverable is a decision. The user is tired,
  the budget is gone, the day is half over.
- **Be willing to recommend revert.** The "we just need one more fix"
  pattern has now produced TASK-FIX-7A08 (reverted), FEAT-AB59
  (works for Phase 4/5, not Phase 3), and now this. A third
  prompt-class iteration in the same defect family is a strong signal
  that the cheap-fix shelf is empty. If the review concludes revert,
  say so plainly. The user explicitly authorised it.
- **Revert ≠ failure.** A clean revert that unblocks the rest of the
  team while a structural Phase 3 fix is planned in calm waters is a
  better outcome than another failed live run today.
- **The meta-question** *"why is this proving so difficult?"* deserves
  an honest answer, even if the answer is uncomfortable: the
  prompt-class fix-class is fundamentally fragile, and every
  "the Player should invoke X via Task tool" gate is one stochastic
  LLM choice away from the same failure. If that's the conclusion,
  the structural answer is to keep extending FEAT-AB59 until no gate
  depends on Player tool-use discretion — but that's a
  separate workstream, not this afternoon.

## References

- **Live failure log**:
  `docs/reviews/bdd-acceptance-wired-up/forge-run-6.md`
- **Recent prior review (FEAT-AB59 verification)**:
  `docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md`
- **The diagnostic that motivated FEAT-AB59**:
  `docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md`
- **FEAT-AB59 design review**:
  `docs/reviews/orchestrator-side-specialist-invocation/TASK-REV-119C1-review-report.md`
- **Refuted prompt-class fix lifecycle** (read for genealogy):
  commits `7f8f14ba`, `86688fc6`, `9d304ed9`, `d58b91a1`, `a8789317`
  (TASK-FIX-7A08 land + revert)
- **The seven OSI commits** (FEAT-AB59 implementation, all green in
  TASK-REV-45750 review): `f62047b3`, `a0c08fb8`, `810cdc88`, `753cba8f`,
  `355e439d`, `73a12c00`
- **agent_invocations gate logic**:
  `guardkit/orchestrator/agent_invoker.py:5562-5848`
  (`_compute_agent_invocations_validation`,
  `_inject_specialist_records_into_task_work_results`)
- **Direct-mode autodetect** (relevant to fix-class F2):
  `guardkit/orchestrator/agent_invoker.py:_auto_detect_direct_mode`
- **Stall classification**:
  `guardkit/orchestrator/autobuild.py` —
  `coach_agent_invocations_stall`,
  `context_pollution_stall_no_checkpoint`
- **FEAT-AB59 task folder** (provenance):
  `tasks/backlog/orchestrator-side-specialist-invocation/`
- **Pending validation task** (now stale — partially superseded by
  this run's incidental live-SDK evidence):
  `tasks/backlog/TASK-VAL-7C2E-live-sdk-canonical-validation-feat-ab59.md`

## Notes

- Priority `critical`. Same priority as TASK-REV-45750, same
  blocker class.
- Review depth `standard`, not `comprehensive`: the user has hours, not
  days (deadline 23:00 today, ~9 h 45 m total window). Do not produce
  a 500-line report. Aim for ≤200 lines.
- This review's deliverable is **a decision under time pressure**, not
  an architectural treatise. Optimise for "user can act in 10 minutes
  of reading."
- Per `/task-create` automatic detection rules, this is a `review`
  task — the system suggests `/task-review`. That is the correct
  command — do not invoke `/task-work` on this task.
- After this review's decision is acted on (whichever path), file the
  longer "fix-class fragility retrospective" as a separate
  non-urgent task for the calmer-waters review.
