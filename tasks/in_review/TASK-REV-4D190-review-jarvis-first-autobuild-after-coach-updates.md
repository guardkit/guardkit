---
id: TASK-REV-4D190
title: Review first jarvis autobuild run (FEAT-JARVIS-001) post Coach updates
status: review_complete
task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: true
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: high
complexity: 0
tags: [autobuild, coach, review, jarvis, feat-jarvis-001, post-remediation, cohort-first, ac-linter, bdd-oracle, smoke-gates]
parent_review: TASK-REV-4D012
related_tasks:
  - TASK-AC-53445
  - TASK-BDD-E8954
  - TASK-SMK-F703A
review_results:
  mode: architectural
  depth: comprehensive
  decision: proceed-with-conditions
  findings_count: 6
  recommendations_count: 4
  first_pass_approval: 91
  tasks_completed: 11
  tasks_total: 11
  post_build_patches: 0
  r1_activated: unknown
  r2_activated: false
  r2_root_cause: pipeline-gap-no-tagging-command
  r3_activated: false
  report_path: docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md
  completed_at: 2026-04-22T00:00:00Z
  revision: 2
  follow_on_feature: FEAT-R2GP
  follow_on_tasks:
    - TASK-FIX-7B2E
    - TASK-BDD-JBKF
    - TASK-FP-LINK
    - TASK-FP-NDG1
    - TASK-FP-NDG2
    - TASK-COH-RUN1
  graphiti_episodes:
    - "Review findings: TASK-REV-4D190 (architectural) — jarvis first autobuild post-R1/R2/R3 (project_decisions)"
    - "Review outcome: TASK-REV-4D190 (task_outcomes)"
    - "Design rule candidate: runner without producer anti-pattern (project_decisions)"
    - "Cohort review methodology: activation vs regression-free (task_outcomes)"
    - "Decision: R2 activation linker lives in /feature-plan (project_decisions)"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review first jarvis autobuild run (FEAT-JARVIS-001) post Coach updates

## Problem Statement

FEAT-JARVIS-001 ("Project Scaffolding, Supervisor Skeleton & Session Lifecycle" — 11 tasks / 6 waves) is the **first cohort autobuild run** to execute after the R1–R3 remediations recommended by TASK-REV-4D012 landed:

- **R1 / TASK-AC-53445** — Assertable-AC linter in `/feature-plan` (warn-mode v1)
- **R2 / TASK-BDD-E8954** — BDD oracle wiring: `task-work` reads task-scoped `features/*.feature` and writes `bdd_results`
- **R3 / TASK-SMK-F703A** — Feature-level smoke gates between autobuild waves

TASK-REV-4D012 explicitly called for "jarvis first (smallest, shakes out regressions), then forge + study-tutor in parallel after jarvis clears cleanly". This review evaluates whether jarvis cleared cleanly, what the three remediations actually produced on a real run, and whether it is safe to proceed with forge + study-tutor.

## Scope

This is a **review / decision task**. No implementation. Output is a review report + recommendations + a go/no-go decision on the forge + study-tutor cohort runs.

### In-Scope

1. **Run outcome**: Did FEAT-JARVIS-001 complete? How many Player-Coach turns per task? First-pass approval rate vs the baseline comparison matrix from TASK-REV-4D012 (nats-core 100%, nats-infra 100%, specialist-agent 95%, ADF 92%, YTM 81%).
2. **R1 assessment — Assertable-AC linter**: Was the AC linter active during the `/feature-plan` that produced FEAT-JARVIS-001.yaml? Did it surface warnings? Were ACs in the resulting task files assertable (named test / shell command / file path) or did prose ACs slip through?
3. **R2 assessment — BDD oracle**: Were any task-scoped `features/*.feature` files present? Did `bdd_results` appear in `task_work_results.json` for any task? Did the three-state outcome model (pass / fail / **pending**) work as designed — or did pending scenarios cause false Coach rejections on the first jarvis run (the exact failure mode the three-state model was designed to avoid)?
4. **R3 assessment — Feature-level smoke gates**: Did `FEAT-JARVIS-001.yaml` carry a `smoke_gates` key? If yes, did it fire between waves? If no, does the 11-task / 6-wave scaffolding feature surface the class of composition bug that smoke gates are intended to catch?
5. **Post-autobuild triage**: Were any post-build patch tasks filed in the 24h after the run? Compare against the specialist-agent baseline of PEX-014..020 (6 patches within 36 hours) that motivated the whole remediation.
6. **Comparative analysis**: Against TASK-REV-4D012's success-vs-struggle matrix, where does jarvis land?
7. **Go/no-go for forge + study-tutor**: Based on the above, is the cohort safe to continue in parallel, or should remediation precede further runs?

### Out-of-Scope

- Changes to any of R1/R2/R3 implementations (if defects are found, file separate follow-on tasks).
- The content of what FEAT-JARVIS-001 actually built (the jarvis supervisor / session lifecycle code itself — that's a jarvis concern, not a GuardKit concern).
- Forge or study-tutor runs (they haven't happened yet; decision about them is an output, not an input).

## Source Material to Analyse

### Jarvis-side artefacts (primary)

- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/reviews/phase-1/autobuild-FEAT-JARVIS-001.md` — run log / review document (2,081 lines; contains the full `guardkit autobuild feature` invocation output and any retrospective observations captured during/after the run).
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/events.jsonl` — turn-by-turn event stream.
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/review-summary.md` — Coach's auto-generated summary.
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/TASK-J001-001/` through `.../TASK-J001-011/` — per-task Player/Coach turn JSONs and `task_work_results.json` (11 directories).
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/features/FEAT-JARVIS-001.yaml` — feature plan output, including `smoke_gates` key if R3 is configured.
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/features/` (if present) — `.feature` files to assess R2 activation.
- `/Users/richardwoollcott/Projects/appmilla_github/jarvis/tasks/backlog/feat-jarvis-001/` or equivalent — task markdown with AC phrasing to assess R1.
- Any post-run patch tasks in `/Users/richardwoollcott/Projects/appmilla_github/jarvis/tasks/*/` filed after the autobuild completed.

### GuardKit-side reference (for cross-checking intended behaviour)

- `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` — parent review with the baseline matrix and R1/R2/R3 acceptance criteria.
- `installer/core/agents/autobuild-coach.md` — Coach spec with the `bdd_results` gate (should match jarvis's `~/.agentecflow/agents/autobuild-coach.md`).
- `installer/core/agents/task-manager-ext.md` — TDD/BDD mode docs (section added during the cleanup after TASK-REV-4D012).

## Deliverables

1. **Review Report** — `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md`
   - Executive summary (1 page, decision-ready — **go / no-go** for forge + study-tutor).
   - Run outcome section: tasks succeeded / turns per task / first-pass rate / total wall time.
   - **Per-remediation section (R1, R2, R3)**: for each — activation evidence (did it fire?), effect on the run (did it help / did it misfire?), and comparison to its predicted behaviour in TASK-REV-4D012.
   - Comparison matrix row for jarvis inserted into TASK-REV-4D012's success-vs-struggle format.
   - Post-autobuild patch triage: count, categories, and whether any are pre-Coach-approval-blind (the exact pattern the remediations were meant to prevent).
   - Surprises: anything that happened on the run that the review didn't predict (positive or negative).

2. **Go/no-go recommendation** for forge + study-tutor cohort runs, with criteria.

3. **(If needed) Follow-on task list** — draft `/task-create` commands for any remediation gaps surfaced by the run.

## Acceptance Criteria

- [ ] All 11 per-task `coach_turn_*.json` files analysed; first-pass approval rate computed.
- [ ] R1 activation evidence cited: did the AC linter fire during `/feature-plan`? (yes/no + file:line if yes).
- [ ] R2 activation evidence cited: did `bdd_results` appear in any `task_work_results.json`? If yes, did the three-state pass/fail/pending model behave correctly? (grep `task_work_results.json` files for `"bdd_results"`).
- [ ] R3 activation evidence cited: does `FEAT-JARVIS-001.yaml` contain `smoke_gates`? If yes, did it fire? If no, why was it absent?
- [ ] Jarvis row added to the TASK-REV-4D012 success-vs-struggle matrix.
- [ ] Post-autobuild patch count documented (0 patches = clean; ≥1 patch requires categorisation).
- [ ] Review answers: *"Did the jarvis run clear cleanly enough to proceed with forge + study-tutor in parallel?"* with explicit criteria used for the decision.
- [ ] Review answers: *"Did any of R1/R2/R3 misfire?"* (false warning, blocked good work, misleading output) — with evidence.
- [ ] Decision checkpoint presented: [A]ccept / [R]evise / [I]mplement follow-on remediations / [C]ancel cohort.
- [ ] Parent review TASK-REV-4D012 linked in the report's "Related" section; this review explicitly documents whether its predictions held.

## Non-Goals / Guardrails

- **No changes to R1/R2/R3 implementations** in this task. If defects found, file follow-on tasks.
- **No forge / study-tutor runs** initiated by this review. The output is a decision *about* them, not the runs themselves.
- **Do not re-litigate TASK-REV-4D012.** This review tests its predictions, not its reasoning.
- **Do not overclaim success if the run was clean.** A clean run on an 11-task scaffolding feature does not prove R1/R2/R3 work at scale; it proves they don't regress on the smallest cohort member. State that limit explicitly in the go/no-go.

## Suggested Review Modes

Run with `/task-review TASK-REV-4D190 --mode=architectural --depth=comprehensive --capture-knowledge`. Architectural-reviewer plus (if needed) qa-tester for the per-task turn analysis.

## Context / Why Now

- FEAT-JARVIS-001 is the **first** cohort run after the Coach remediations landed.
- TASK-REV-4D012's explicit sequencing was jarvis → forge + study-tutor (parallel). Forge and study-tutor are waiting on this review's go/no-go.
- R1/R2/R3 have **never been exercised on a real feature** before this run. Defect surface is unknown.
- Timing is critical: forge and study-tutor were described in TASK-REV-4D012 as ready for parallel execution "after jarvis clears cleanly" — delay increases with every day jarvis sits un-analysed.

## Related

- Parent review: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`
- R1 task: `tasks/backlog/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
- R2 task: `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md` (already completed per git log)
- R3 task: `tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md` (already completed per git log)
- Jarvis run log: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/reviews/phase-1/autobuild-FEAT-JARVIS-001.md`
- Jarvis autobuild state: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/`
- Graphiti episode (from parent review): *"Review-gate hole: AutoBuild 13/13 green + e2e broken"* — is this pattern still reproducible post-R1/R2/R3?
