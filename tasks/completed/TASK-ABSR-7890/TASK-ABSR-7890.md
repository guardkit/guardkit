---
id: TASK-ABSR-7890
title: Investigate why Player tests passed when Coach independent test failed on the same broken bootstrap
status: completed
task_type: review
review_mode: diagnostic
review_depth: standard
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
completed: 2026-04-27T00:00:00Z
priority: high
tags: [autobuild, coach, player, test-execution, investigation]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: direct
wave: 1
conductor_workspace: autobuild-stall-resilience-wave1-player-coach-divergence
complexity: 3
depends_on: []
previous_state: in_review
completed_location: tasks/completed/TASK-ABSR-7890/
report_path: .claude/reviews/TASK-ABSR-7890-report.md
organized_files:
  - TASK-ABSR-7890.md
graphiti_captured:
  - group: guardkit__task_outcomes
    episode: "Task Completion: TASK-ABSR-7890"
  - group: guardkit__project_decisions
    episode: "Decision: TASK-ABSR-7890 — Player↔Coach interpreter divergence is structural, not incidental"
---

# TASK-ABSR-7890 — Investigate why Player tests passed when Coach independent test failed on the same broken bootstrap

## Description

In FEAT-J004-702C / TASK-J004-004, the Coach decision JSON ([coach_turn_1.json](../../../../jarvis/.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-004/coach_turn_1.json)) recorded:

```
quality_gates.all_gates_passed = true   (tests=true, coverage=true, arch=true, audit=true)
independent_tests.tests_passed  = false  (AssertionError: import jarvis regressed)
```

Both signals come from the same broken-bootstrap worktree. The Player's tests passed; the Coach's independent re-run of the same test command failed. This is either:
- A real environmental divergence between Player and Coach test execution (different interpreters, different cwd, different env vars), OR
- The Player's tests didn't actually exercise `import jarvis` (different test selection, partial run, cached imports), OR
- The Player's test runner returned a successful exit code without running the failing test (collection error swallowed).

This investigation is **review-only** — it produces a diagnostic report at `.claude/reviews/TASK-ABSR-7890-report.md`. Any code changes that emerge become separate follow-up tasks.

The result is important for TASK-ABSR-2468 (R3 — Coach env-class conditional approval), which assumes Player gates passing is a meaningful signal of correctness. If Player tests are systematically more permissive than Coach independent tests, that assumption needs revisiting.

## Acceptance Criteria

- [ ] Read `.guardkit/autobuild/TASK-J004-004/player_turn_*.json` and `task_work_results.json` from the failing run worktree.
- [ ] Identify exactly which pytest command Player ran (test files, markers, `-k` filters), and compare against the Coach independent test command (`pytest tests/test_config_settings.py tests/test_phase2_dependencies.py tests/test_phase4_dependencies.py tests/test_routing_history_schema_smoke.py -v --tb=short`).
- [ ] Identify the Python interpreter used by Player (likely the bundled Claude Code CLI's Python, per [autobuild log lines](../../../../jarvis/docs/history/autobuild-FEAT-J004-702C-history.md) `subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude`) and compare against the Coach interpreter (`sys.executable` per [coach_validator.py:1797](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L1797)).
- [ ] Determine whether `tests/test_phase2_dependencies.py::TestPhase1ImportSurfaceStillWorks::test_jarvis_package_imports` was run by Player. If yes, why did it pass? If no, why was it excluded?
- [ ] Document findings in `.claude/reviews/TASK-ABSR-7890-report.md` with the same structure as TASK-REV-FA04's report (executive summary, findings with file:line evidence, recommendations).
- [ ] If a real divergence is identified (e.g. Player and Coach use different interpreters by design), document the architectural rationale and whether it should remain.
- [ ] If Player gates are systematically more permissive than Coach (e.g. lower bar for "tests passed"), file a follow-up TASK to either align them or document the asymmetry as intentional.

## Implementation Notes

- Investigation only — do not modify any source files.
- The failing-run worktree is preserved at `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/worktrees/FEAT-J004-702C/`. All evidence is there.
- Cross-reference [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F7 (where this question was first surfaced).

## Out of Scope

- Implementing any changes that this investigation might suggest — those become follow-up tasks.
- Reviewing other features' Player↔Coach divergence patterns (this is a single-incident investigation).

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F7, §R6
- Failing run artefacts: `jarvis/.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-004/`
