---
id: TASK-AC-53445
title: Assertable-AC linter in /feature-plan post-step (warn-mode v1 → block-mode v2)
status: backlog
task_type: implementation
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
priority: high
complexity: 4
tags: [feature-plan, acceptance-criteria, linter, warn-mode, autobuild-quality]
parent_review: TASK-REV-4D012
implementation_mode: task-work
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Assertable-AC linter in /feature-plan post-step (warn-mode v1 → block-mode v2)

## Context

Follow-on from **TASK-REV-4D012** (AutoBuild Coach integration review). Report: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`, §6 R1.

The review's strongest-evidenced finding (F3 + F6): **acceptance-criterion phrasing is the load-bearing factor** separating smooth AutoBuild runs from painful ones. `criteria_classifier.py` already routes ACs to `FILE_CONTENT`, `COMMAND_EXECUTION`, or `MANUAL`. Prose ACs (`"handles edge cases correctly"`, `"backward-compatible defaults ensure no breakage"`) fall through to `MANUAL` and are silently skipped by Coach. There is no feedback loop that tells the planner its ACs are unverifiable.

## Problem Statement

`/feature-plan` generates ACs that may be prose-only and therefore unverifiable by the Coach. Today the planner has no signal that its output is weak; the problem surfaces 30+ tasks later as post-Coach-approval smoke failures.

## Scope

### In-Scope

1. Extend `guardkit/orchestrator/quality_gates/criteria_classifier.py:197–202` — the current 0.3-confidence `FILE_CONTENT` fallback — to emit a structured `UnverifiableACWarning` per criterion.
2. Add a `/feature-plan` post-step that:
   - Aggregates warnings across all generated tasks
   - Surfaces them to the user with a count and examples
   - Optionally prompts the LLM to refine ACs (v1: user-confirmed; v2: auto-iterating up to 2x)
3. **Rollout posture — critical:** v1 is **warn-only**. Planner continues to emit its output; user sees warnings and can rerun with refinements or proceed as-is. Graduating to block-mode is v2, **after** the jarvis/forge/study-tutor cohort has landed cleanly.

### Architectural guardrail — single source of truth

**The linter is a report-mode wrapper around `criteria_classifier.py`, not a second classifier.**

`criteria_classifier.py` already owns the AUTO vs MANUAL split (`COMMAND_EXECUTION` / `FILE_CONTENT` / `MANUAL` plus confidence score). The linter's job is to:

1. Call the existing classifier.
2. Aggregate its results across a plan.
3. Surface unverifiable cases to the user.

**Do not** introduce a second set of regex patterns, heuristics, or confidence thresholds in the linter layer. If the linter and the classifier ever disagree on whether an AC is assertable, that is a bug in whichever is newer — and the fix is to collapse them, not to reconcile. Keeping the classifier as the sole source of "is this AC verifiable?" is what makes v1→v2 promotion (warn → block) a one-line threshold change rather than a cross-file rewrite.

### v1 posture on classifier tuning — *defer hand-tuning until observational data arrives*

Warn-mode v1 deliberately exists to collect data on which prose phrasings show up in practice across jarvis / forge / study-tutor. **Resist hand-tuning the classifier's regex patterns before that data lands.** Block-mode v2 is when to draw the line; v1 is when to observe where the line should be drawn. A premature tweak to `_MANUAL_PATTERNS` or `_FILE_CONTENT_PATTERNS` will bias the v2 cut point.

### Out-of-Scope

- Changing any Coach logic. This is upstream of the Coach.
- Blocking behaviour in v1 (explicitly deferred to v2).
- TypeScript / .NET support for criteria_classifier (Python-only at launch; all three cohort repos are Python).

## Acceptance Criteria

- [ ] `criteria_classifier.py` exposes `classify_with_warnings()` returning `(ClassificationResult, List[UnverifiableACWarning])` where warnings are emitted for confidence < 0.6 fallbacks. **No new classification logic is added — warnings are derived purely from existing `ClassifiedCriterion.confidence` and `criterion_type`.**
- [ ] `tests/unit/orchestrator/test_criteria_classifier.py::test_linter_has_no_independent_patterns` passes — greps the linter module for regex / heuristic patterns and asserts it contains none beyond delegation to `classify_criterion()`.
- [ ] Test `tests/unit/orchestrator/test_criteria_classifier.py::test_unverifiable_ac_warning_emitted` passes, verifying a prose AC (`"handles edge cases correctly"`) produces exactly one warning.
- [ ] `/feature-plan` command spec (`installer/core/commands/feature-plan.md`) documents a new "AC-quality review" post-step section.
- [ ] Post-step produces a summary block visible in planner output listing each unverifiable AC with its owning task ID and suggested rewrites (if LLM refinement accepted).
- [ ] Test `tests/integration/feature_plan/test_ac_linter_warning_flow.py::test_prose_acs_surface_warnings` passes, verifying a planner run on a mocked feature description emits ≥1 warning without blocking.
- [ ] **Retrospective acceptance**: on a re-run of specialist-agent's FEAT-POR-EXT planning call (archived at `specialist-agent/command_history.md:~2000-2200`), at least 3 of the 6 post-patch bug classes (schema shape, stub semantic drift, `./output` path validation) have a corresponding warning-flagged AC in the revised plan output.
- [ ] No change to the shape of `tasks/backlog/*.md` files generated by `/feature-plan` beyond optional AC-rewrite content.

## Implementation Notes

- Start from `guardkit/orchestrator/quality_gates/criteria_classifier.py:197–202`. The fallback branch is where unverifiable ACs land today.
- The warning shape should include: `ac_text`, `task_id`, `reason`, `suggested_rewrite_hint` (optional).
- For the post-step refinement prompt, cap at 2 LLM roundtrips to avoid runaway cost; surface the diff clearly so the user sees what changed.
- v2 block-mode is **out of scope for this task** — a follow-up after cohort.

## Non-Goals / Guardrails

- **Do not add a frontmatter flag to opt-in.** The linter runs always; it's the v1 posture (warn) that's gentle, not the activation. A flag would re-create the YTM silent-exclusion failure mode in reverse.
- **Do not cascade into Coach prompt changes.** Coach reads `acceptance_criteria` as it does today; improvement comes from better inputs, not wider Coach scope.
- **Do not create a parallel classification path in the linter.** The linter delegates to `classify_criterion()`; it has no independent regexes, heuristics, or confidence thresholds of its own.
- **Do not pre-tune `criteria_classifier.py` patterns during v1.** Observational data from the cohort tells us where block-mode v2 should cut; changing the classifier before that arrives biases the cut point.

## Related

- Review report: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` §6 R1
- Source: `guardkit/orchestrator/quality_gates/criteria_classifier.py`
- Command spec: `installer/core/commands/feature-plan.md`
- Ships before: TASK-BDD-E8954, TASK-SMK-F703A (AC → BDD → SMK order)
- Cohort: enables confident firing of jarvis / forge / study-tutor AutoBuild runs
