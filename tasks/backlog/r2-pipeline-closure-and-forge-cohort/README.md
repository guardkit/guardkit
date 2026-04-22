# FEAT-R2GP — Close R2 activation pipeline gap & run forge + study-tutor cohort

**Source:** TASK-REV-4D190 (architectural review of first jarvis autobuild after Coach R1–R3 remediations landed).

## Problem in one paragraph

The first post-remediation autobuild cohort run (FEAT-JARVIS-001) completed cleanly — 11/11 tasks, 91% first-pass, 0 post-run patches. But none of R1/R2/R3 actually activated: R1 produced no observable output (unknown if wired), R2 did not fire because no scenarios carry `@task:<TASK-ID>` tags, and R3 did not fire because the feature YAML had no `smoke_gates:` key. The run validated the "zero regression" design of the remediations, but validated zero percent of their behavioural surface. The R2 gap is the deepest: no command in the pipeline currently writes task tags — `/feature-spec` can't (task IDs don't exist at spec time), `/feature-plan` creates tasks but doesn't rewrite the `.feature`, and TASK-BDD-E8954 explicitly deferred the emission step.

## Solution approach

1. **Close the R2 pipeline gap** by adding an LLM-assisted scenario-to-task linking step to `/feature-plan` that rewrites `.feature` files with `@task:<TASK-ID>` tags after task creation (**TASK-FP-LINK**, the core architectural fix).
2. **Add interim nudges** so authors can't silently ship features with missing activation artefacts (**TASK-FP-NDG1** for R2, **TASK-FP-NDG2** for R3).
3. **Verify R1 is actually wired** (**TASK-FIX-7B2E**) — silence-on-assertable-ACs is the same observational shape as not-wired, and we can't tell without forcing the issue.
4. **Retroactively activate R2 on jarvis** (**TASK-BDD-JBKF**) to get one real-code data point that the runner works end-to-end, including the three-state pass/fail/pending model.
5. **Run forge + study-tutor cohort** (**TASK-COH-RUN1**) with all three remediations verified active before autobuild starts — the first run that will actually exercise R1/R2/R3 against a composition-risk surface.

## Subtasks

| ID | Title | Wave | Mode | Complexity | Priority |
|---|---|---|---|---:|---|
| TASK-FIX-7B2E | Verify R1 (AC linter) wiring in `/feature-plan` | 1 | task-work | 2 | high |
| TASK-BDD-JBKF | Backfill R2 on jarvis feature file | 1 | task-work | 3 | high |
| TASK-FP-NDG1 | `/feature-plan` nudge for missing `@task:` tags (R2) | 1 | direct | 2 | medium |
| TASK-FP-NDG2 | `/feature-plan` nudge for missing `smoke_gates:` (R3) | 1 | direct | 2 | medium |
| TASK-FP-LINK | Implement R2 linking step in `/feature-plan` | 2 | task-work | 7 | **high** (core fix) |
| TASK-COH-RUN1 | Fire forge + study-tutor cohort runs | 3 | task-work | 5 | high |

Total: 6 tasks, 3 waves.

## Execution plan

- **Wave 1** (parallel, 4 tasks): AC01, JBKF, NDG1, NDG2. All independent investigations or small ergonomics additions. Can run in four Conductor workspaces simultaneously.
- **Wave 2** (1 task): FP-LINK. Depends on JBKF's evidence of the runner's actual behaviour on real code (informs the scenario-matching heuristic), and is the heaviest task by far (complexity 7).
- **Wave 3** (1 task): COH-RUN1. Depends on all of Wave 1 + Wave 2. This is the gate that finally tests whether R1/R2/R3 work when activated.

## Success definition

FEAT-R2GP is complete when forge and study-tutor autobuild cohorts have run with R1/R2/R3 *demonstrably active* (pre-flight grep confirms tags + smoke-gates; post-run `bdd_results` present; smoke gate events observed in `events.jsonl`), and a comparative report vs jarvis + specialist-agent has been produced. Whether the cohorts pass or fail is secondary — the point is we finally have real data on the remediations.

## Related

- **Parent review:** [TASK-REV-4D190](../../../docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md)
- **Predecessor review:** [TASK-REV-4D012](../../../docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md)
- **R1/R2/R3 task trail:** TASK-AC-53445 (R1), TASK-BDD-E8954 (R2), TASK-SMK-F703A (R3)
