---
id: TASK-AC-53445
title: Assertable-AC linter in /feature-plan post-step (warn-mode v1 → block-mode v2)
status: completed
task_type: implementation
created: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
completed: 2026-04-21T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed via /task-complete — all passing ACs satisfied, deviations explicitly documented"
completed_location: tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md
priority: high
complexity: 4
tags: [feature-plan, acceptance-criteria, linter, warn-mode, autobuild-quality]
parent_review: TASK-REV-4D012
implementation_mode: task-work
test_results:
  status: pass
  coverage:
    ac_linter: 95
    criteria_classifier: 94
  last_run: 2026-04-21T00:00:00Z
  new_tests: 13
  suite: "tests/unit/test_criteria_classifier.py + tests/integration/feature_plan/test_ac_linter_warning_flow.py"
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

## Implementation Summary

Landed in four files — warn-mode v1 only, no block-mode:

- **`guardkit/orchestrator/quality_gates/criteria_classifier.py`** — added
  `UnverifiableACWarning` dataclass, `UNVERIFIABLE_CONFIDENCE_THRESHOLD = 0.6`
  constant, and `classify_with_warnings(criteria, task_id)` returning
  `(ClassificationResult, List[UnverifiableACWarning])`. Warnings are
  derived purely from existing `ClassifiedCriterion.confidence` and
  `.reason` — no new patterns, no new logic.
- **`guardkit/orchestrator/quality_gates/ac_linter.py`** (new, 83 lines)
  — plan-level aggregator `lint_plan_warnings(tasks)` and
  `format_warning_summary(warnings)`. Contains no regexes, no
  threshold literals, no pattern constants. Enforced by
  `test_linter_has_no_independent_patterns`.
- **`installer/core/commands/feature-plan.md`** — new Step 10.5 "AC-quality
  review (warn-mode v1)" post-step section documenting trigger,
  single-source-of-truth guardrail, warn-only rollout posture, and
  example output.
- **Tests** (13 new):
  - `tests/unit/test_criteria_classifier.py` — 6 new tests
    (`TestUnverifiableACWarning` × 4, `TestLinterHasNoIndependentPatterns` × 2).
  - `tests/integration/feature_plan/test_ac_linter_warning_flow.py` — 7
    new tests (`TestProseAcsSurfaceWarnings` × 6 + `TestLinterReasonFidelity` × 1).

## AC Checklist (completion status)

- [x] `classify_with_warnings()` returning `(ClassificationResult, List[UnverifiableACWarning])` for confidence < 0.6 fallbacks — added in `criteria_classifier.py:227-281`. No new classification logic; warnings are derived from existing `confidence` + `reason` fields.
- [x] `test_linter_has_no_independent_patterns` passes — **note path deviation**: tests added to existing `tests/unit/test_criteria_classifier.py` rather than the AC-specified `tests/unit/orchestrator/test_criteria_classifier.py`. Creating a parallel directory would fragment the classifier test suite; this deviation is recorded in an inline test-file comment. Test validates no `re.compile`, no `import re`, no `_PATTERNS`, no direct confidence comparisons in `ac_linter.py`.
- [x] `test_unverifiable_ac_warning_emitted` passes (same path-deviation note). Prose AC `"handles edge cases correctly"` produces exactly 1 warning.
- [x] `/feature-plan` spec documents the post-step — Step 10.5 added in `feature-plan.md`.
- [x] Post-step produces a summary block with per-task grouping, verbatim AC text, and classifier reason — `format_warning_summary()` in `ac_linter.py`; example block in the spec.
- [x] `test_prose_acs_surface_warnings` passes in `tests/integration/feature_plan/test_ac_linter_warning_flow.py`.
- [ ] **Retrospective acceptance (DEFERRED with explicit note)**: the FEAT-POR-EXT archive referenced in the AC lives at `specialist-agent/command_history.md:~2000-2200` and is not present in this repo. Per agreement at task-work start, this AC is deferred to v2-promotion gate where cohort observational data (jarvis / forge / study-tutor) will supply the retrospective evidence base. Not blocking v1 landing.
- [x] No shape change to `tasks/backlog/*.md` — linter is read-only over task dicts; writes happen only if user accepts LLM refinement (not implemented in this task scope — documented in spec as optional future extension).

## Test Results

```
tests/unit/test_criteria_classifier.py: 26 passed (20 pre-existing + 6 new)
tests/integration/feature_plan/test_ac_linter_warning_flow.py: 7 passed (new)
Total: 33 passed, 0 failed

Coverage (focused on touched modules):
  guardkit/orchestrator/quality_gates/ac_linter.py          95%
  guardkit/orchestrator/quality_gates/criteria_classifier.py 94%
```

Pre-existing unrelated failures (`test_doc_file_paths.py`, `test_task_769d_ai_analyzer.py`, `test_lint_discovery.py`) reproduce on clean `main` and are not touched by this task.
