---
id: TASK-EVAL-003
title: Implement InputResolver for text, file, and linear ticket sources
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: in_review
created: 2026-03-01 00:00:00+00:00
priority: high
tags:
- eval-runner
- input-resolution
- linear
complexity: 3
wave: 1
implementation_mode: task-work
dependencies:
- TASK-EVAL-001
autobuild_state:
  current_turn: 2
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4296
  base_branch: main
  started_at: '2026-03-01T14:35:18.897709'
  last_updated: '2026-03-01T14:49:27.456545'
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
      \ does not have the attribute 'query'\nFAILED tests/eval/test_eval_agent_invoker.py::TestSDKInvocation::test_invoke_calls_sdk_query\
      \ - AttributeError: <module 'gu..."
    timestamp: '2026-03-01T14:35:18.897709'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-03-01T14:39:37.713306'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement InputResolver for Text, File, and Linear Ticket Sources

## Description

Implement the input resolution system that loads eval input from multiple sources (text, file, Linear ticket) and distributes it identically to both arm workspaces.

## Acceptance Criteria

- [ ] `InputResolver.resolve(brief) -> str` returns raw input text
- [ ] `source: text` — returns `brief.input.text` directly
- [ ] `source: file` — reads and returns content from `brief.input.file_path`
- [ ] `source: linear_ticket` — fetches ticket title + description via web fetch, normalizes to plain text
- [ ] Empty text field with `source: text` raises `InputResolutionError` with clear message
- [ ] Missing file with `source: file` raises `InputResolutionError` including the missing path
- [ ] Unreachable Linear ticket raises `InputResolutionError` suggesting `source: text` fallback
- [ ] Unknown source type raises `InputResolutionError` listing valid sources (text, file, linear_ticket)
- [ ] Resolved text is identical for both arms — no summarization or paraphrasing
- [ ] Unit tests for all source types, error cases, and edge cases

## Technical Context

- Location: `guardkit/eval/input_resolver.py` (new module)
- Prototype reference: `docs/research/eval-runner/guardkit_vs_vanilla_runner.py` (InputResolver class)
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 5.3)
- Uses `httpx` for Linear ticket web fetch (already a dependency)

## BDD Scenario Coverage

- Key example: Both arms receive identical input text
- Negative: Unknown input source "database" → InputResolutionError
- Negative: Empty text field → InputResolutionError
- Negative: Nonexistent file path → InputResolutionError
- Negative: Unreachable Linear ticket → InputResolutionError with fallback suggestion

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
