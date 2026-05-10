---
id: TASK-REV-ABST
title: Autobuild stocktake — has the BDD-verification trajectory destroyed quality?
status: review_complete
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T18:00:00Z
priority: critical
tags: [review, autobuild, bdd, coach, honesty-verification, strategic-decision, rollback-candidate]
task_type: review
decision_required: true
complexity: 9
review_mode: architectural
review_depth: thorough
review_results:
  mode: architectural
  depth: thorough
  decision: narrow
  recommendation: "Narrow (Option B) — 7-day gate-stack freeze + re-measurement; deciding observation has not been made"
  follow_up_date: 2026-05-17
  falsifier_positive: "≥3 consumer-repo features pass cleanly on first-turn against guardkit@HEAD by 2026-05-17"
  falsifier_negative: "any new framework false-positive class filed in any consumer repo by 2026-05-17"
  fix_to_new_gate_ratio: "3.57:1 (25 fixes / 7 new gates since 2026-04-15)"
  first_pass_success_rate: "10% (2/21 features in sample window)"
  framework_fp_incidents_documented: 3
  rules_seeded: 4
  report_path: .claude/reviews/TASK-REV-ABST-review-report.md
---

# Task: Autobuild stocktake — has the BDD-verification trajectory destroyed quality?

> **This is a `/task-review` task, not a `/task-work` task.** Do not implement
> anything. The deliverable is an evidence-backed report and a strategic
> decision: **continue, narrow, or roll back** the BDD-verification +
> deterministic-Coach + honesty-verification track in autobuild.

## The user's framing (verbatim, for context)

> "since we implemented the changes for BDD verification it simply fails every
> run and every time we have to execute tasks to adapt the tasks in the feature
> and upstream task in guardkit — we need to ascertain if fundamentally it just
> doesn't work. Before these changes we had something that worked probably 95%
> of the time and are the changes actually even improving quality? Look at the
> docs/history folders in the repos jarvis/forge/study-tutor/specialist-agent/
> fleet-gateway and the review/git histories — nothing has worked since those
> changes. Are we getting to the end or are we just going to continue down this
> disappointing rabbit hole of failure after failure — time to take stock."

That framing is the hypothesis under test. The review must NOT presuppose it
is correct, and must NOT presuppose it is wrong. The review must produce an
evidence-backed verdict and a recommendation.

## The reviewer's job

Produce a **stocktake report** that answers, with cited evidence and quantified
metrics, the following questions in order. The report's audience is the
project owner, who needs to make a go/no-go/narrow decision today.

1. **What changed, and when?** Build a chronological timeline of the major
   autobuild-affecting landings since the last "things mostly worked" baseline
   the user is referring to. Span at minimum:
   - BDD oracle introduction and the FEAT-AB-FIX series (TASK-AB-001..AB-004,
     TASK-AB-FIX-INVAB1, TASK-FIX-1B4A/1B4B/1B4C, TASK-DOC-1B4D, TASK-FIX-7E3F,
     TASK-CVAC-001/002, TASK-FPTC-004, TASK-FPSG-001).
   - Honesty-verification wiring into the deterministic Coach path
     (`CoachVerifier` ↔ `CoachValidator` integration, FFC3 false-fail and
     fixes in `state_bridge` / `agent_invoker` union-merge).
   - Player-Coach feedback shape changes (criterion-id matching, AC extraction).
   - Pytest-bdd rollout (TASK-OPS-BDDM-* series) across consumer repos.
   - Per-task BDD glue contract (TASK-AB-004) and the `GUARDKIT_BDD_TASK_ID`
     env-var coupling.
   - Anything else surfaced by `git log` since the user's "95%" baseline.

   For each landing, capture: SHA, date, intent, the failure-class it was
   meant to close, and whether it introduced or revealed a new failure class.

2. **What is the actual current run-success rate?** Survey the consumer repos
   for empirical signal:
   - `jarvis/docs/history/`
   - `forge/docs/history/`
   - `study-tutor/docs/history/`
   - `specialist-agent/docs/history/`
   - `fleet-gateway/docs/history/`
   - `guardkit/.claude/reviews/` (own-dogfood reviews)
   - `guardkit/tasks/in_review/`, `tasks/in_progress/`, `tasks/completed/`,
     `tasks/blocked/` for autobuild-rerun / fix-up task density.

   Quantify (best effort with the evidence available, do not fabricate):
   - **Run outcomes** by week since the BDD-verification trajectory began:
     pass-on-first-turn, pass-after-N-turns, blocked, abandoned, rolled-back.
   - **Fix-up task density**: how many "adapt the upstream guardkit task" or
     "patch the feature task" tasks were spawned per autobuild run. The user's
     core complaint is *the rate of ad-hoc remediation*, not just final pass
     rate — measure both.
   - **Time-to-green** trend: hours/days from a feature's first run to a clean
     run, before vs after.
   - **What broke that previously worked**: enumerate consumer-repo features
     that completed cleanly pre-trajectory and now fail or stall. The
     fleet-gateway FEAT-FG-001 wave-2 race (per `bdd-per-task-glue.md`) is one
     known instance — find the others.

3. **Are the changes actually improving quality, or just adding gates?**
   This is the decisive question. For each gate that landed in the trajectory,
   classify it:
   - **Caught a real defect** that pre-trajectory autobuild would have shipped:
     concrete citation required (commit, before/after symptom, what the gate
     blocked).
   - **Caught nothing real, blocked turns spuriously**: false-fail evidence.
     The FFC3 incident (`path-string-mismatch-is-not-dishonesty.md`) is one
     known case; enumerate the rest.
   - **Caught nothing because it ran zero attempts**: false-green evidence
     (the `absence-of-failure-is-not-success.md` class). How often did the
     deterministic Coach approve on zero-cardinality counters?
   - **Net unknown / not enough signal**: be explicit when evidence is
     inconclusive.

   Build a 2x2 of {real-positives, false-positives, false-negatives,
   true-negatives} for each gate using the empirical evidence from question 2.
   The acceptable cost of a real-positive is "Player did one extra turn"; the
   cost of a false-positive is "the user wrote a fix-up task and re-ran". If
   the false-positive rate × cost exceeds the real-positive rate × benefit,
   the gate is destroying value.

4. **Where is the trajectory load-bearing vs incidental?** Distinguish:
   - **Load-bearing**: gates whose removal would let real defects ship
     (cite the defect class and where it would land).
   - **Incidental**: gates whose removal would only lose theoretical
     adversarial rigor with no measured defect-prevention benefit.
   - **Counter-productive**: gates that are net-negative once false-fail
     remediation cost is included.

   The Layer-3' filter (`state_bridge.orchestrator_induced_paths_for`),
   the Layer-1 canonical-path resolution in `_verify_files_exist`, and the
   Layer-2 demotion of single path-only discrepancies (TASK-FIX-1B4B) are
   each candidates for this analysis. So is the entire deterministic Coach
   path (Option D from TASK-REV-0414).

5. **Is the system at the end of a debug cycle, or in a doom loop?** The
   user's framing is "are we close to fixed or are we just stacking patches".
   Evidence to consider:
   - Are recent FEAT-AB-FIX landings closing distinct root causes (= debug
     cycle ending) or recurring instances of the same meta-class
     (= doom loop / wrong abstraction)?
   - Is the rate of new failure-classes per week declining, flat, or rising?
   - Are the existing rules (`absence-of-failure-is-not-success.md`,
     `path-string-mismatch-is-not-dishonesty.md`,
     `namespace-hygiene.md`, `bdd-per-task-glue.md`) generative — i.e. they
     prevented a recurrence — or descriptive — i.e. they only document
     what already happened?
   - Has any consumer-repo feature reached "clean autobuild → merge" in the
     last two weeks without a manual fix-up loop?

6. **What is the recommendation?** Pick exactly one of:
   - **A. Continue** — the gates are net-positive, the recent fixes are
     converging, give it N more days/turns and the run-success rate will
     return to ≥95%. State the leading indicator that would falsify this.
   - **B. Narrow** — keep the gates that have caught real defects, retire
     or demote the gates that are net false-positive generators. Specify
     which gates to retire/demote and the expected effect on each consumer
     repo. The Layer-2 demotion (single path-only → `should_fix`) is a
     proof-of-concept for narrowing; the question is which other gates
     deserve the same treatment.
   - **C. Roll back** — the trajectory is net-negative, revert to the
     pre-BDD-verification baseline (cite the SHA), and re-enter individual
     gates only with a measured defect-prevention case for each. State the
     migration path for consumer repos that have come to depend on the
     newer behaviour (e.g. the per-task BDD glue contract).
   - **D. Pivot** — the deterministic Coach path was a structural mistake
     (Option D from TASK-REV-0414), the LLM-Coach-with-tools path was
     correct, and the right move is to retire the deterministic path
     entirely. State the runtime/cost impact and the migration plan.

   Whichever option is chosen, the report MUST include:
   - The leading indicator(s) that would invalidate the recommendation.
   - The latest date by which a follow-up review should be scheduled.
   - The specific task(s) that should be created next, with their
     prefix/scope (NOT a full plan — just the headline).

## Acceptance criteria

- [ ] **AC-001 — Timeline.** A chronological table of every autobuild-affecting
      landing since the user's "95%" baseline, with SHA, date, intent, and
      observed effect (closed-defect / new-defect / no-change). Anchored in
      `git log` evidence; no speculation.
- [ ] **AC-002 — Empirical run-success metrics.** Quantified pass/fail/blocked
      counts and fix-up-task densities per consumer repo
      (jarvis, forge, study-tutor, specialist-agent, fleet-gateway) and for
      guardkit-self, sourced from `docs/history/`, `.claude/reviews/`, and
      task-folder state. Report sample sizes and confidence — if the data is
      thin, say so.
- [ ] **AC-003 — Gate-by-gate quality matrix.** Each gate landed in the
      trajectory classified as real-positive / false-positive /
      false-negative-by-zero-cardinality / true-negative, with at least one
      cited incident per non-empty cell.
- [ ] **AC-004 — Load-bearing audit.** Every gate marked load-bearing,
      incidental, or counter-productive, with the defect-class citation
      required for "load-bearing".
- [ ] **AC-005 — Doom-loop test.** Explicit answer to "is the rate of new
      failure-classes declining?" with the supporting weekly counts.
- [ ] **AC-006 — Recommendation.** Exactly one of {Continue, Narrow,
      Roll back, Pivot} chosen, with the falsifying leading indicator,
      follow-up date, and headline next-task list specified.
- [ ] **AC-007 — Honest acknowledgement of limits.** Sections of the report
      where evidence is missing or inconclusive are flagged as such, not
      papered over. Per `absence-of-failure-is-not-success.md`: "absence of
      negative signal in the dataset" is not "evidence the gate is working" —
      apply the same rule to the meta-review.
- [ ] **AC-008 — Pair the verdict with anti-bias check.** Before finalising
      the recommendation, the reviewer must explicitly consider the
      counter-hypothesis (i.e. if recommending "roll back", spend a section
      on "what would I expect to see if the trajectory IS working", and
      check whether that signal is present). This guards against
      confirmation of the user's stated framing.

## Scope — in

- **GuardKit autobuild orchestrator surface**: `guardkit/orchestrator/`
  (especially `agent_invoker.py`, `quality_gates/coach_validator.py`,
  `quality_gates/coach_verification.py`, `quality_gates/bdd_runner.py`,
  `tasks/state_bridge.py`).
- **BDD oracle and per-task glue contract**: the FEAT-AB-FIX series and
  the `bdd-per-task-glue.md` rule.
- **Honesty verification** (CoachVerifier + CoachValidator) and the
  deterministic Coach path (Option D from TASK-REV-0414).
- **Consumer repos as evidence sources only**: jarvis, forge, study-tutor,
  specialist-agent, fleet-gateway. The review reads their
  `docs/history/`, `.claude/reviews/`, and `tasks/` folders for run
  outcomes; it does NOT redesign their pipelines.
- **The four design rules already on disk**:
  `absence-of-failure-is-not-success.md`,
  `path-string-mismatch-is-not-dishonesty.md`,
  `namespace-hygiene.md`,
  `bdd-per-task-glue.md` — the review must assess whether these rules
  are themselves load-bearing or post-hoc rationalisation.

## Scope — out

- ❌ Implementing any change. This is `/task-review`, not `/task-work`.
- ❌ Re-architecting the consumer repos.
- ❌ Touching `installer/core/templates/` content (template hygiene is a
  separate review).
- ❌ Touching the Graphiti / FalkorDB / vLLM infrastructure surface
  (covered by other open tasks).
- ❌ Producing a full implementation plan for the chosen recommendation —
  the deliverable is the verdict + the headline next-task list, not the
  plan itself. A separate `/task-review --mode=plan` or `/feature-plan`
  invocation should follow.

## Inputs the reviewer should ingest

| Source | What to extract |
|---|---|
| `git log --oneline --since="2026-04-01"` (filter for autobuild/coach/bdd/honesty) | Trajectory timeline |
| `guardkit/.claude/reviews/TASK-REV-*.md` | Prior review verdicts and which ones held up |
| `guardkit/tasks/{backlog,in_progress,in_review,blocked,completed}/` | Fix-up task density by week |
| `jarvis/docs/history/`, `forge/docs/history/`, `study-tutor/docs/history/`, `specialist-agent/docs/history/`, `fleet-gateway/docs/history/` | Per-feature run outcomes, retry counts, abandonment events |
| `.claude/rules/absence-of-failure-is-not-success.md` | False-green class signature |
| `.claude/rules/path-string-mismatch-is-not-dishonesty.md` | False-red class signature |
| `.claude/rules/bdd-per-task-glue.md` | Per-task glue contract; FEAT-FG-001 wave-2 race instance |
| `.claude/rules/namespace-hygiene.md` | Sibling meta-class for confirmation |
| `tasks/in_progress/autobuild-bdd-oracle-fix/` (FEAT-AB-FIX) | Recent fix-up trajectory |

## Suggested review structure

1. **Executive summary** (one page, decision-first).
2. **Timeline of changes** (AC-001).
3. **Empirical run outcomes** (AC-002) — per-repo and aggregated.
4. **Gate-by-gate matrix** (AC-003, AC-004).
5. **Doom-loop vs debug-cycle test** (AC-005).
6. **Anti-bias section** (AC-008).
7. **Recommendation and falsifier** (AC-006).
8. **Headline next-task list** — IDs and titles only, no plans.
9. **Limits and unknowns** (AC-007).

## Decision points the reviewer must NOT skip

- **Don't pre-commit to the user's framing.** The user has stated a
  hypothesis ("these changes destroyed a 95% system"). The review's job
  is to test it, not to confirm it. A finding of "the hypothesis is
  wrong, the system is converging" is a valid and welcome outcome if
  the evidence supports it.
- **Don't pre-commit against the user's framing.** A finding of "the
  hypothesis is correct, roll back" is also valid if the evidence
  supports it. Adversarial-cooperation rules apply to the reviewer
  too: weigh both directions.
- **Distinguish "the gate is broken" from "the gate is correct, the
  Player is making real mistakes the user didn't see"**. Some of the
  user-perceived "fix-up tasks" may be the system correctly catching
  real defects that would otherwise have shipped. Quantify this
  separately from the false-positive count.

## Related rules and prior reviews

- `.claude/rules/absence-of-failure-is-not-success.md`
- `.claude/rules/path-string-mismatch-is-not-dishonesty.md`
- `.claude/rules/namespace-hygiene.md`
- `.claude/rules/bdd-per-task-glue.md`
- `.claude/reviews/TASK-REV-1B452-review-report.md` (FFC3 false-fail)
- `.claude/reviews/TASK-REV-0414-review-report.md` (Option D origin)
- `.claude/reviews/TASK-INV-AB1-review-report.md` (deterministic Coach
  honesty wiring)
- `tasks/in_progress/autobuild-bdd-oracle-fix/` (FEAT-AB-FIX)
- `tasks/completed/TASK-AB-FIX-INVAB1` and the TASK-FIX-1B4A/B/C trio

## Outputs

- **Primary**: `.claude/reviews/TASK-REV-ABST-review-report.md`
  containing all eight ACs.
- **Secondary**: a Graphiti capture under `guardkit__project_decisions`
  with the verdict, falsifier, and follow-up date — so the next agent
  picking up this thread does not have to re-read the whole report
  to know the disposition.
- **Tertiary (only if recommendation is Roll back / Narrow / Pivot)**:
  a headline list of follow-up task IDs + titles, NOT plans. Plans are
  scoped out — they belong to the follow-up `/feature-plan` or
  `/task-review --mode=plan` invocations.

## Test execution log

[Automatically populated by /task-review]
