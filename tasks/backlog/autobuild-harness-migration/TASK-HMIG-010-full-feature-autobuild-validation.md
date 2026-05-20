---
id: TASK-HMIG-010
title: Full feature autobuild end-to-end validation under LangGraph
status: backlog
task_type: validation
created: 2026-05-19T20:30:00Z
updated: 2026-05-19T20:30:00Z
priority: critical
complexity: 5
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
parallel_group: 3B
implementation_mode: task-work
intensity: standard
effort_hours: 8
depends_on:
  - TASK-HMIG-009   # canary must pass first; this is the larger-scale follow-up
falsifier: "A representative 3-task feature (target: FEAT-PEBR-style structure, ≥3 tasks across ≥2 waves) completes under GUARDKIT_HARNESS=langgraph with ≥80% of tasks passing on first attempt (matches LangGraph fleet baseline; comfortably exceeds the SDK baseline). Any task that fails first-pass must succeed on --resume; non-recoverable failures fail the falsifier and trigger Wave 4 cutover-halt."
tags:
  - autobuild
  - validation
  - feature-build
  - langgraph-migration
---

# Task: Full feature autobuild end-to-end validation

## Description

Wave 3's second task. After TASK-HMIG-009 confirms the LangGraph harness on
isolated canary tasks, run a full multi-task feature autobuild under
`GUARDKIT_HARNESS=langgraph` to validate the end-to-end orchestration —
multi-wave execution, parallel groups, feature-complete merge, Coach gating
across multiple tasks, etc. The canary tasks tested the harness; this test
tests the orchestration around the harness.

## Acceptance Criteria

- [ ] AC-001: Target feature selected and recorded in
      `.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`. Selection criteria:
      ≥3 tasks, ≥2 waves, includes a BDD-gated task, includes a task with non-trivial state-bridge transitions, total estimated effort ≤8h orchestrator-time.
- [ ] AC-002: Feature run end-to-end with `GUARDKIT_HARNESS=langgraph` via
      `guardkit autobuild feature FEAT-XXX`.
- [ ] AC-003: Per-task outcome recorded in
      `.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`:
      `task_id`, `wave`, `parallel_group`, `coach_decision`, `turns_used`, `first_pass_success`, `resume_used`, `wall_clock_seconds`, `notes`.
- [ ] AC-004: First-pass-success rate computed and compared to the canary
      baseline from TASK-HMIG-009. Significant divergence (>10pp drop) is a
      red flag and must be investigated before Wave 4.
- [ ] AC-005: Any first-pass failure → `--resume` retry; resume outcome
      recorded; analysis of why first-pass failed and whether the retry was
      successful.
- [ ] AC-006: Any non-recoverable failure documented with root-cause analysis
      in `docs/state/TASK-REV-HMIG/feature-run-incidents.md`. A non-recoverable failure means: Coach rejection that survives 3 task-work attempts, orchestrator crash, state-bridge corruption, or any failure the operator cannot resolve without code edits to the harness itself.
- [ ] AC-007: Feature-complete merge attempted. The merge succeeds (no
      conflict, no broken downstream consumer) — this exercises the
      `WorktreeManager` + `feature_complete` paths which are substrate-agnostic
      but must continue to work under LangGraph.
- [ ] AC-008: Falsifier evaluation:
  - If ≥80% first-pass-success AND no non-recoverable failure: proceed to Wave 4 cutover.
  - If <80% first-pass-success OR any non-recoverable failure: halt cutover. Escalate to operator with the incidents document.
- [ ] AC-009: Result analysis appended to
      `docs/state/TASK-REV-HMIG/feature-run-analysis.md` (separate from
      canary-analysis.md for clarity).

## Implementation Notes

- The "target feature" should be a real feature the operator wants built — this
  is a validation run AND a feature delivery. Don't synthesise a feature; pick
  one already in backlog that fits the selection criteria.
- Schedule for D-9 → D-7 so that result analysis informs the D-7 cutover-flip
  decision.
- If the feature's tasks have failures unrelated to the substrate (e.g.,
  pre-existing bugs in the orchestrator), distinguish those in the analysis
  — they don't fail the falsifier.
- TASK-HMIG-009's results gate this task. If canary fails the 75% threshold,
  this task does not run.

## References

- Review §7.3 — Wave 3 sequencing
- Review §11 — Falsifier for the central recommendation
- Review §5.10 — Cross-repo failure-rate asymmetry (80-90% LangGraph fleet baseline)
- TASK-HMIG-009 result artifacts

## Notes

Wave 4 cutover hinges on this task's outcome. If both TASK-HMIG-009 and
TASK-HMIG-010 pass their falsifiers, the cutover flip at D-7 is a
configuration change with high confidence. If either fails, the cutover-flip
PR should be held until the issue is resolved or the falsifier explicitly
relaxed by the operator with a recorded rationale.
