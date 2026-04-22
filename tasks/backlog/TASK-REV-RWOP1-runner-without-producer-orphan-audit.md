---
id: TASK-REV-RWOP1
title: Re-review TASK-AC-53445 under "runner without producer" lens — find other Step-10.5-like orphans in feature-plan/feature-spec/task-work specs
status: backlog
task_type: review
review_mode: architectural
review_depth: comprehensive
decision_required: true
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: high
complexity: 5
tags: [architecture-review, runner-without-producer, task-ac-53445, r1, r2]
related_to: TASK-REV-4D190
related_tasks:
  - TASK-REV-4D190
  - TASK-REV-AC53
  - TASK-AC-53445
  - TASK-FIX-7B2E
  - TASK-FIX-3C9D
parent_review: TASK-REV-4D190
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Re-review TASK-AC-53445 under "runner without producer" lens — find other Step-10.5-like orphans across feature-plan / feature-spec / task-work specs

## Problem Statement

[TASK-FIX-7B2E](.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md)
discovered that **Step 10.5 of [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md)**
— TASK-AC-53445's load-bearing AC-linter post-step — was documented
in command-spec prose but had no imperative callsite. The linter
module `ac_linter.py` existed and was unit-tested directly, so the
integration tests went green even though `/feature-plan` never
invoked it at runtime. This is the **runner-without-producer**
anti-pattern (Graphiti: *"Design rule candidate: runner without
producer anti-pattern"*, seeded from TASK-REV-4D190).

[TASK-REV-AC53](tasks/backlog/TASK-REV-AC53-reaudit-task-ac-53445-for-orphan-runners.md)
is already queued to re-audit **TASK-AC-53445's delivery surface
specifically** — the files it touched. That task explicitly puts
other commands out of scope.

This task is the **complementary broader sweep**: apply the same
lens to the three command-spec files that most likely harbour
similar orphans, because they are the ones that carry long
procedural prose describing verifier/linter/oracle behaviour:

- [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md)
- [installer/core/commands/feature-spec.md](installer/core/commands/feature-spec.md)
- [installer/core/commands/task-work.md](installer/core/commands/task-work.md)

The goal is to find every step that *describes* an imperative
action ("Execute X", "Run Y", "Emit Z", "Invoke W") and verify
that a producer actually performs that action — either the command
runner itself, the installed executable under `~/.agentecflow/bin/`,
or a transitively-invoked script.

This must run **before the jarvis-cleared forge + study-tutor
cohort fires** (see TASK-REV-4D190 go/no-go). If more Step-10.5
orphans exist in `/feature-spec` (R2's adjacent surface) or
`/task-work` (where R2 oracle reads bdd_results), cohort evidence
will be contaminated exactly the way R1's was.

## Scope

### In-Scope

1. **Three command specs**, in full:
   - [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md)
   - [installer/core/commands/feature-spec.md](installer/core/commands/feature-spec.md)
   - [installer/core/commands/task-work.md](installer/core/commands/task-work.md)
2. For each numbered step / sub-step that **describes an
   imperative action** (verbs: Execute, Run, Invoke, Call, Emit,
   Write, Record, Gate, Block, Warn, Lint, Classify, Validate,
   Propagate, Persist):
   - Identify the claimed producer (script, module, function,
     slash-command-handler).
   - Grep the runtime surface (`guardkit/`, `~/.agentecflow/bin/`,
     installer scripts, shell wrappers) for a caller that is
     **not itself a test** and **not the module that defines it**.
   - Record: `wired` / `orphan` / `producer-ambiguous`.
3. For each `orphan` or `producer-ambiguous` finding: characterise
   the failure mode — would a green unit-test suite mask it? Would
   a cohort run surface it? Would the Coach see / not see it?
4. File the review report at
   `docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md`
   with:
   - One subsection per command-spec file
   - A verdict block per file: `clean` / `N orphans` / `needs-deeper-audit`
   - An overall verdict block: `safe-for-cohort` / `fix-before-cohort`
5. If orphans are found: file one remediation task per orphan
   (or a rollup if they collapse cleanly), cross-linked to this
   review and to the parent review
   [TASK-REV-4D190](tasks/in_review/TASK-REV-4D190-review-jarvis-first-autobuild-after-coach-updates.md).
6. Contribute back to the Graphiti design-rule candidate entry
   with concrete evidence of how often the pattern recurs —
   updates the `runner-without-producer` anti-pattern node with
   either confirmation (N additional instances) or refutation
   (pattern was a one-off).

### Out-of-Scope

- Fixing any orphan found (file separate remediation tasks).
- Re-doing TASK-REV-AC53's narrow re-audit of TASK-AC-53445's
  delivery files — that task stands.
- Generalising the runner-without-producer guard into a
  pre-commit lint rule across the repo — file separately if
  the evidence supports it.
- Re-reviewing every command spec in `installer/core/commands/`.
  Scope is strictly the three commands above; they are chosen
  because they are the **R1/R2 surface area** and because they
  carry the kind of long procedural prose most prone to producing
  orphan steps.

## Acceptance Criteria

- [ ] All three command-spec files walked step-by-step; every
      imperative action enumerated and tagged `wired` / `orphan` /
      `producer-ambiguous` with file:line evidence.
- [ ] For each `wired` finding: a caller file:line cited (not a
      test, not a self-reference).
- [ ] For each `orphan` finding: failure-mode characterisation
      included (would tests catch it? would Coach catch it? would
      a cohort run surface it?).
- [ ] Review report filed at
      `docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md`
      with per-file verdicts and an overall cohort go/no-go.
- [ ] If orphans found: remediation tasks filed, each cross-linked
      back to this review and to TASK-REV-4D190.
- [ ] Graphiti design-rule candidate updated with quantitative
      evidence: total imperative steps walked (N), orphans found
      (M), wiring-rate (N-M)/N per file and overall.
- [ ] Decision block recorded: does this change TASK-REV-4D190's
      go/no-go on forge + study-tutor cohort runs?

## Implementation Notes

- Audit frame: Graphiti node *"Design rule candidate: runner
  without producer anti-pattern"* (seeded from TASK-REV-4D190).
- Method is a **lens-application exercise**: apply the TASK-FIX-7B2E
  verification technique (grep for callers, not just definitions)
  to every imperative step in the three command specs.
- Expected finding distribution:
  - `/feature-plan`: R1 (Step 10.5) is the known orphan; audit
    checks whether other steps are similarly documented-but-unwired.
  - `/feature-spec`: R2 oracle-adjacent surface — high-interest
    because BDD oracle wiring is load-bearing for cohort evidence.
  - `/task-work`: longest spec, most procedural prose; most likely
    to harbour orphans if any exist.
- Scheduling priority: **before** forge + study-tutor cohort kicks
  off (TASK-COH-RUN1). If this audit surfaces additional orphans,
  cohort evidence will be compromised exactly the way R1's was.

## Related

- Parent review:
  [docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md](docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md)
  §R1 / Addendum A
- Sibling narrow-scope audit:
  [tasks/backlog/TASK-REV-AC53-reaudit-task-ac-53445-for-orphan-runners.md](tasks/backlog/TASK-REV-AC53-reaudit-task-ac-53445-for-orphan-runners.md)
- Verification that motivated this:
  [.claude/reviews/TASK-FIX-AC01-r1-wiring-verification.md](.claude/reviews/TASK-FIX-AC01-r1-wiring-verification.md)
- Task under re-review:
  [tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md](tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md)
- Parallel remediation (R1 orphan fix):
  [tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md](tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Downstream cohort run gated on this:
  [tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
- Design-rule candidate (Graphiti):
  *"Design rule candidate: runner without producer anti-pattern"*
  (group: `guardkit__project_decisions`)
