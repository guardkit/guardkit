# Implementation Guide — FEAT-R2GP

Closes the R2 pipeline activation gap identified in TASK-REV-4D190 §Addendum A, then fires the forge + study-tutor autobuild cohorts with all three Coach remediations (R1/R2/R3) verified active.

## Ordering & dependencies

```
Wave 1 (parallel, no dependencies):
┌────────────────────────┐  ┌────────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  TASK-FIX-7B2E         │  │  TASK-BDD-JBKF         │  │  TASK-FP-NDG1    │  │  TASK-FP-NDG2    │
│  Verify R1 wiring      │  │  Backfill R2 on jarvis │  │  R2 nudge        │  │  R3 nudge        │
│  (cx 2, task-work)     │  │  (cx 3, task-work)     │  │  (cx 2, direct)  │  │  (cx 2, direct)  │
└───────────┬────────────┘  └───────────┬────────────┘  └──────────────────┘  └──────────────────┘
            │                           │
            │  R1 wiring answer         │  Runner behaviour data
            │                           │  (informs LINK heuristic)
            ▼                           ▼
Wave 2 (serial, blocks on JBKF):
                            ┌────────────────────────────────────────┐
                            │  TASK-FP-LINK                          │
                            │  R2 linking step in /feature-plan      │
                            │  (cx 7, task-work)                     │
                            │  • Gherkin parse + rewrite             │
                            │  • LLM scenario-to-task matching       │
                            │  • Idempotent, preserves formatting    │
                            └──────────────────┬─────────────────────┘
                                               │
                                               │  Auto-activation available
                                               ▼
Wave 3 (serial, blocks on all Wave 1 + 2):
                            ┌────────────────────────────────────────┐
                            │  TASK-COH-RUN1                         │
                            │  Forge + study-tutor cohort run        │
                            │  (cx 5, task-work)                     │
                            │  • Pre-flight verifies R1/R2/R3 active │
                            │  • Parallel execution of 2 features    │
                            │  • Combined review report              │
                            └────────────────────────────────────────┘
```

## Wave 1 — parallel, independent

Goal: get evidence + ergonomics in place before committing to the heavier LINK work.

- **TASK-FIX-7B2E** and **TASK-BDD-JBKF** are both evidence-gathering tasks. They can (and should) run simultaneously — they touch different remediations and share no code.
  - AC01 is fast: stand up a prose-AC fixture, run `/feature-plan`, look for warnings. <1 day.
  - JBKF is slightly slower because it touches the jarvis repo (temporary tags, pytest-bdd invocation), but straightforward. <1 day.
- **TASK-FP-NDG1** and **TASK-FP-NDG2** are twin nudge features. Implement together in a single `/feature-plan` code change — same file, same interaction point, one shared test harness. Treat as one implementation PR covering both task files. <1 day combined.

**Entry criterion:** none (all depend only on a clean `main`).

**Exit criterion:** AC01 has produced a "wired / not wired / partially wired" answer. JBKF has produced a BDDResult with confirmed three-state categorisation (or a defect report against TASK-BDD-E8954). Both nudges are in place and suppressible.

## Wave 2 — serial, blocks Wave 3

**TASK-FP-LINK** is the core architectural fix. Single highest-complexity task in this feature (cx 7). Key design considerations documented in the task file — summarised here for orchestration:

- **Parser:** use `gherkin-official` or `pytest-bdd`'s parser. Do not roll a regex.
- **Matcher:** LLM-assisted, with per-mapping confidence scores. Default threshold ~0.6; below threshold = leave untagged and report.
- **Rewrite safety:** parse → insert → atomic rename. Preserve all existing comments, tags, blank lines, formatting.
- **Idempotency:** re-running `/feature-plan` must not duplicate or shift tags.
- **Interactive vs non-interactive:** respect `--no-questions`. Interactive = per-mapping confirmation; non-interactive = auto-apply above threshold.

**Entry criterion:** TASK-BDD-JBKF complete (we want real evidence about R2 runner behaviour before designing the matching heuristic).

**Exit criterion:** all ACs pass, including: the FEAT-JARVIS-001 `.feature` file run through the linker with the J001-001..011 task list produces a tagging that matches TASK-BDD-JBKF's ground-truth subset.

## Wave 3 — serial, final gate

**TASK-COH-RUN1** is the payoff. First autobuild run where R1/R2/R3 are all confirmed active before the run starts.

- **Pre-flight is hard-gated.** If any pre-flight check fails, the cohort does not start; a targeted follow-on is filed against the failing remediation.
- **Parallel execution** of forge and study-tutor is the design (TASK-REV-4D012 §7). Do not fall back to sequential unless infra constraints (rate limits, FalkorDB throughput) force it.
- **Report is the deliverable,** not the cohort success. A cohort member failure *with R3 correctly blocking* is a success for this feature.

**Entry criterion:** all of Wave 1 and Wave 2 complete.

**Exit criterion:** `docs/reviews/TASK-COH-RUN1-forge-study-tutor-cohort-review.md` exists and answers the carry-over question: *did R3 catch a composition failure that per-task Coach missed?*

## Risk register

| Risk | Likelihood | Blast radius | Mitigation |
|---|---|---|---|
| TASK-FP-LINK matcher is too brittle (LLM picks wrong task for scenarios) | Medium | R2 activates on wrong task → false Coach rejection | Interactive confirmation + confidence threshold + idempotency (rerun with corrections) |
| AC01 reveals R1 is not wired | Low-Medium | Cohort run blocked on R1 remediation | File remediation task, assess whether COH-RUN1 proceeds with R2/R3 only and R1 deferred |
| JBKF reveals R2 runner has a defect (pending collapses into failed) | Low | P0 — TASK-BDD-E8954 needs a bug fix before COH-RUN1 | Halt pipeline, file bug, fix, re-run JBKF |
| `/feature-plan` rewrite breaks non-`/feature-spec`-generated `.feature` files | Medium | User's hand-edited scenarios corrupted | Idempotency tests + formatting-preservation tests + atomic write |
| Forge or study-tutor autobuild fails for reasons unrelated to R1/R2/R3 | Medium | Hard to separate "remediation bug" from "cohort-specific bug" | Use Graphiti groups consistent with jarvis; capture full run logs; compare to jarvis baseline |

## How to run — recommended sequence

```bash
# Wave 1 (four parallel workspaces)
/task-work TASK-FIX-7B2E
/task-work TASK-BDD-JBKF
/task-work TASK-FP-NDG1       # ship with NDG2
/task-work TASK-FP-NDG2       # ship with NDG1

# Wave 2 (after JBKF confirms runner behaviour)
/task-work TASK-FP-LINK

# Wave 3 (after all Wave 1 + 2 done)
/task-work TASK-COH-RUN1
```

## Definition of done (feature level)

- All 6 subtasks in COMPLETED state.
- `/feature-plan` has a working R2 linking step (auto-activation path), a working R2 nudge (fallback path), and a working R3 nudge.
- A verified BDDResult from jarvis exists (TASK-BDD-JBKF evidence file).
- R1 wiring status is documented.
- Forge and study-tutor cohort review report exists with baseline-matrix rows, per-remediation activation evidence, and an explicit answer on whether the PEX-014..020 "review-gate hole" pattern was closed.
