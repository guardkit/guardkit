---
id: TASK-EVAL-008
title: Create CLI command, workspace templates, and EVAL-007 brief
task_type: scaffolding
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: in_review
created: 2026-03-01 00:00:00+00:00
priority: high
tags:
- eval-runner
- cli
- templates
- brief
complexity: 4
wave: 4
implementation_mode: task-work
dependencies:
- TASK-EVAL-007
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4296
  base_branch: main
  started_at: '2026-03-01T15:24:05.319993'
  last_updated: '2026-03-01T15:32:13.454121'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-01T15:24:05.319993'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Create CLI Command, Workspace Templates, and EVAL-007 Brief

## Description

Create the CLI entry point (`guardkit eval run BRIEF.yaml`), the workspace templates for both arms, and the canonical EVAL-007 example brief.

## Acceptance Criteria

- [ ] `guardkit eval run <brief.yaml>` CLI command runs a single eval from YAML file
- [ ] CLI uses Click group pattern consistent with `guardkit/cli/autobuild.py`
- [ ] CLI displays progress output: workspace provisioning, arm status, metrics, judge result
- [ ] CLI exit code: 0 for PASSED, 1 for FAILED, 2 for ESCALATED, 3 for ERROR
- [ ] `workspaces/guardkit-project/` template has `CLAUDE.md`, `.guardkit/commands/`, `pyproject.toml`, sample codebase
- [ ] `workspaces/plain-project/` template has same codebase, `pyproject.toml` ONLY — no `CLAUDE.md`, no `.guardkit/`
- [ ] `plain-project` is verifiably `guardkit-project` minus GuardKit config (automated sync possible)
- [ ] Both templates have installable Python project (`pip install -e .` works)
- [ ] `briefs/EVAL-007-guardkit-vs-vanilla-youtube.yaml` matches canonical schema from architecture doc
- [ ] CLI supports `--dry-run` flag to validate brief without running agents
- [ ] Unit tests for CLI argument parsing, brief validation, template verification

## Technical Context

- CLI location: `guardkit/cli/eval.py` (new module, register in `guardkit/cli/main.py`)
- Templates location: `guardkit/eval/workspaces/` (or configurable via env var)
- Brief location: `guardkit/eval/briefs/` (git versioned)
- Reference CLI pattern: `guardkit/cli/autobuild.py`
- Example brief: `docs/research/eval-runner/EVAL-007-guardkit-vs-vanilla-youtube.yaml`
- Design reference: `docs/research/eval-runner/eval-runner-architecture.md` (Section 7)

## BDD Scenario Coverage

- Key example: End-to-end eval with text input completes
- Key example: Workspaces provisioned independently from respective templates
- Edge case: Eval runner dispatches guardkit_vs_vanilla to specialised runner
- Negative: Nonexistent workspace template → warning + blank workspace fallback

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
