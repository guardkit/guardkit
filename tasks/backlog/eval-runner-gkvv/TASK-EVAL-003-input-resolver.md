---
id: TASK-EVAL-003
title: "Implement InputResolver for text, file, and linear ticket sources"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, input-resolution, linear]
complexity: 3
wave: 1
implementation_mode: task-work
dependencies:
  - TASK-EVAL-001
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
