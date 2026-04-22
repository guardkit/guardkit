---
id: TASK-REV-AC53
title: Re-review TASK-AC-53445 delivery for other "runner without producer" orphans
status: backlog
task_type: review
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: medium
complexity: 3
tags: [review, re-audit, runner-without-producer, ac-linter, task-ac-53445, design-rule]
parent_task: TASK-AC-53445
depends_on: []
---

# Task: Re-review TASK-AC-53445 for other Step-10.5-like orphans

## Problem Statement

TASK-FIX-7B2E verified that TASK-AC-53445's load-bearing post-step
(Step 10.5 of `installer/core/commands/feature-plan.md`) is documented
but not wired — the "runner without producer" anti-pattern. Since
TASK-AC-53445 was reviewed and accepted at the time with a green test
suite (the integration test calls `lint_plan_warnings` directly, so it
went green even though `/feature-plan` never invokes it), the review
lens used at delivery did not catch this class of bug.

Before R2 cohort runs (jarvis / forge / study-tutor) fire, re-audit
TASK-AC-53445's full delivery under the runner-without-producer lens
to check whether there are other Step-10.5-shaped orphans — sections
of spec prose that describe verifier behaviour but have no imperative
callsite in the same file's execution trace, and no matching invocation
from a producer script.

## Scope

### In-Scope

1. Walk every file touched by TASK-AC-53445 (see its Implementation
   Summary, lines 107-128 of the completed task file):
   - `guardkit/orchestrator/quality_gates/criteria_classifier.py`
   - `guardkit/orchestrator/quality_gates/ac_linter.py`
   - `installer/core/commands/feature-plan.md`
   - `tests/unit/test_criteria_classifier.py`
   - `tests/integration/feature_plan/test_ac_linter_warning_flow.py`
2. For each new function / module / spec-step added: grep the repo
   (including `~/.agentecflow/bin/` and any installer outputs) for a
   runtime caller that is NOT itself a test and NOT the module that
   defines it.
3. For each spec-step added: confirm it is referenced in an executable
   trace (an `Execute:` / `Run:` / `Call:` line, or transitively via a
   script that is itself invoked imperatively).
4. Record findings in a review report at
   `docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md`.
5. If additional orphans are found: file one remediation task per
   orphan (or a single rollup task if they collapse cleanly), linked
   back to this review and to TASK-AC-53445.

### Out-of-Scope

- Fixing the R1 orphan itself (already covered by TASK-FIX-3C9D).
- Generalising the runner-without-producer guard into a pre-commit /
  lint rule across the repo — file separately if worth doing.
- Re-reviewing unrelated commands (`/task-work`, `/feature-build`, etc.).
  Scope is strictly TASK-AC-53445's delivery surface.

## Acceptance Criteria

- [ ] All files touched by TASK-AC-53445 walked; findings enumerated
      per file.
- [ ] For each newly introduced callable: a runtime caller confirmed
      or the absence recorded.
- [ ] For each newly introduced spec step: imperative reachability
      confirmed or the absence recorded.
- [ ] Review report filed at
      `docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md` with a
      verdict block: clean / partially-orphaned (N findings) / further-audit-needed.
- [ ] If orphans found: remediation tasks filed and cross-linked.

## Implementation Notes

- The runner-without-producer pattern is captured in Graphiti as
  *"Design rule candidate: runner without producer anti-pattern"*
  (seeded from TASK-REV-4D190). Use it as the audit frame.
- This is a lens-application exercise, not new discovery. Expected
  finding is "R1 was the only orphan" — but confirm, don't assume.
- Low priority because TASK-FIX-3C9D closes the load-bearing orphan.
  Schedule before the jarvis/forge/study-tutor cohort kicks off so
  any other orphans are closed before cohort evidence starts landing.

## Related

- Verification that motivated this review:
  `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`
- Task under re-review:
  `tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
- Parallel remediation:
  `tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md`
- Design-rule candidate (Graphiti):
  *"Design rule candidate: runner without producer anti-pattern"*
- Parent review:
  `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` §R1 / Addendum A
