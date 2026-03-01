---
id: TASK-EVAL-005
title: Implement MetricsExtractor for evidence file parsing
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: in_review
created: 2026-03-01 00:00:00+00:00
priority: high
tags:
- eval-runner
- metrics
- evidence
complexity: 3
wave: 2
implementation_mode: task-work
dependencies:
- TASK-EVAL-001
autobuild_state:
  current_turn: 2
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4296
  base_branch: main
  started_at: '2026-03-01T14:35:18.896171'
  last_updated: '2026-03-01T14:49:11.926147'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Independent test verification failed:\n  Error detail:\ntests/eval/test_eval_agent_invoker.py::TestSDKInvocation::test_sdk_options_include_max_turns\
      \ FAILED [ 26%]\ntests/eval/test_eval_agent_invoker.py::TestEvalAgentError::test_eval_agent_error_is_exception\
      \ PASSED [ 27%]\ntests/eval/test_eval_agent_invoker.py::TestEvalAgentError::test_eval_agent_error_preserves_cause\
      \ PASSED [ 28%]\ntests/eval/test_input_resolver.py::TestTextSource::test_text_source_returns_text_directly\
      \ PASSED [ 30%]\ntests/eval/test_input_resolver.py::TestTextSource::test_text_source_preserves_multiline\
      \ PASSED [ 31%]\nResult:\nFAILED tests/eval/test_eval_agent_invoker.py::TestHeartbeatAndCleanup::test_cleanup_handler_installed\
      \ - AttributeError: <module 'guardkit.eval.agent_invoker' from '/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4296/guardkit/eval/agent_invoker.py'>\
      \ does not have the attribute '_import_sdk'\nFAILED tests/eval/test_eval_agent_invoker.py::TestSDKInvocation::test_invoke_calls_sdk_query\
      \ - AttributeError: <modu..."
    timestamp: '2026-03-01T14:35:18.896171'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-03-01T14:42:02.387913'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement MetricsExtractor for Evidence File Parsing

## Description

Implement the metrics extraction system that reads `.eval/evidence/` files from both arm workspaces and produces `ComparisonMetrics` with deltas.

## Acceptance Criteria

- [ ] `MetricsExtractor.extract(guardkit_ws, vanilla_ws) -> ComparisonMetrics`
- [ ] Reads `.eval/evidence/c1.txt` for assumptions count (`assumptions_surfaced=N`)
- [ ] Reads `.eval/evidence/c2.txt` for test coverage (`coverage=N%`)
- [ ] Reads `.eval/evidence/c3.txt` for lint violations (`violations=N`)
- [ ] Reads `.eval/evidence/c5.txt` for runnable status (`runnable=yes|no`)
- [ ] Evidence file format: `key=value` plain text (ASSUM-003 confirmed)
- [ ] Missing evidence files produce `-1` / "not measurable" — NOT errors
- [ ] `ComparisonMetrics.coverage_delta()` returns positive when GuardKit better
- [ ] `ComparisonMetrics.lint_delta()` returns negative when GuardKit better (fewer violations)
- [ ] `ComparisonMetrics.assumption_surfacing_delta()` returns positive when GuardKit surfaced more
- [ ] Both arms with identical metrics → all deltas are 0
- [ ] `ComparisonMetrics.to_graphiti_fields()` serializes deltas for Graphiti storage
- [ ] Unit tests for parsing, missing files, delta calculations, edge cases

## Technical Context

- Location: `guardkit/eval/metrics.py` (new module)
- Prototype reference: `docs/research/eval-runner/guardkit_vs_vanilla_runner.py` (MetricsExtractor, ArmMetrics, ComparisonMetrics)
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 7)
- Evidence convention: `docs/research/eval-runner/eval-runner-architecture.md` (Section 5.2)

## BDD Scenario Coverage

- Key example: Quantitative metrics extracted from both workspaces
- Boundary: Missing evidence files produce not-measurable metrics, not errors
- Boundary: Perfect tie produces weighted score of 0.5
- Key example: Comparison includes coverage delta, lint delta, assumption delta

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
