---
id: TASK-QAV-003
title: "L3 runtime coverage gate \u2014 zero-execution authored public surface"
task_type: feature
parent_review: TASK-REV-QAVG
feature_id: FEAT-10AC
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-QAV-002
priority: high
consumer_context:
- task: TASK-QAV-002
  consumes: coverage
  framework: CoachEvidenceBundle sibling field
  driver: guardkit.orchestrator.quality_gates.coach_evidence
  format_note: Optional[Dict]; None = gate did not run; positive status + findings:[]
    = real clean verdict
status: completed
updated: '2026-07-04T21:56:00'
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC
  base_branch: main
  started_at: '2026-07-04T21:20:49.534717'
  last_updated: '2026-07-04T21:44:07.440649'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-04T21:20:49.534717'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: L3 runtime coverage gate

## Description

Populate the `coverage` bundle field: run the worktree test suite under
coverage measurement and flag every **authored public symbol** with **zero
real execution** — tests green over code no test ever entered. This closes
the "green over dead code" half the syntactic L1 probes cannot see.

Execution is stack-plugin territory
(`.claude/rules/stack-plugin-architecture.md`): day one is Python via
`pytest --cov` (coverage.py JSON/XML report) using the worktree venv
interpreter the Coach already uses for independent tests; any other stack —
or any coverage-tool failure — degrades to an **absent** signal, never a pass
and never a block. Symbol extraction (which lines belong to which authored
public symbol) reuses the factory tree-sitter symbol queries — do NOT write a
second parser.

## Acceptance Criteria

- [ ] **AC-1 (positive):** a fixture worktree whose tests pass but never
  execute an authored public function yields one `coverage` finding
  `{file, symbol, lineno, executed_lines: 0, severity:"warning",
  pattern:"ZERO_EXECUTION"}` with a positive run status.
- [ ] **AC-2 (control):** an authored public function executed at least once
  yields no finding; a fully-covered fixture yields `findings:[]` with a
  positive status (real clean verdict, distinct from `None`).
- [ ] **AC-3 (zero-execution only):** no percentage threshold — a symbol with
  any executed line is not flagged (v0 policy, ASSUM-002).
- [ ] **AC-4 (absent-signal safety):** coverage tool missing / run error /
  non-python stack → `coverage` is `None` or carries a non-positive status;
  it never counts as a pass and never blocks the turn on its own; the absent
  signal survives serialization to `task_work_results`/checkpoint unchanged.
- [ ] **AC-5 (scope):** only FEATURE / REFACTOR / INTEGRATION task types run
  the gate; only the turn's authored set is examined (never peer files).
- [ ] **AC-6 (advisory only):** coverage findings surface as `should_fix`
  Coach feedback; they never deterministically override an approve in v0.
- [ ] **AC-7 (behavioural check, dogfood):** an integration test runs the real
  pytest-under-coverage path over a fixture worktree (no mocked coverage
  report) and asserts the finding appears in the rendered evidence bundle.
- [ ] **AC-8:** existing suites green; all modified files pass
  project-configured lint/format checks with zero errors.

## Test Requirements

Unit tests for report-parsing + symbol mapping; the AC-7 integration test
exercising the real runner. Pin the absent-signal branches explicitly
(tool-missing, run-error, unsupported-stack).

## Implementation Notes

- Reuse the independent-test execution machinery (worktree venv interpreter,
  timeout discipline) rather than a new subprocess layer; a coverage run that
  times out is a **runner** outcome for this gate — treat it as absent, not
  ran-and-failed (the gate measures the tests, not the deliverable; contrast
  ASSUM-005 for L4).
- Coverage source of truth: `coverage.py` JSON report (`--cov-report=json`)
  keyed by file + executed line numbers, intersected with the factory
  symbol-extent extents for authored files.
- Do not conflate with the existing line/branch thresholds in the quality
  gates — this gate is per-symbol reachability, not aggregate percentage.
