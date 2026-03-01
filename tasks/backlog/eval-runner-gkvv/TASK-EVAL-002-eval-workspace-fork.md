---
id: TASK-EVAL-002
title: "Implement EvalWorkspace fork support for A/B comparison"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, workspace, isolation]
complexity: 4
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Implement EvalWorkspace Fork Support for A/B Comparison

## Description

Implement workspace provisioning with fork support for the guardkit_vs_vanilla eval type. Two independent workspaces must be created from different templates — one with GuardKit configuration (CLAUDE.md, .guardkit/) and one without.

## Acceptance Criteria

- [ ] `EvalWorkspace.create(template_name)` provisions a temp directory from a template
- [ ] `EvalWorkspace.create_forked_pair(eval_id, guardkit_template, vanilla_template) -> tuple[ForkedWorkspace, ForkedWorkspace]`
- [ ] Each returned workspace is an independent temp directory with no shared state
- [ ] GuardKit workspace seeded from `guardkit_template` (contains CLAUDE.md and .guardkit/)
- [ ] Vanilla workspace seeded from `vanilla_template` (same codebase, NO CLAUDE.md, NO .guardkit/)
- [ ] Both workspaces have `.eval/evidence/` directory created automatically
- [ ] `ForkedWorkspace.write_input(text) -> Path` writes `input.txt` to workspace root
- [ ] `EvalWorkspace.teardown()` removes workspace temp directory
- [ ] Vanilla workspace isolation verified: no `CLAUDE.md` anywhere, no `.guardkit/` anywhere, `guardkit` not importable
- [ ] Existing `EvalWorkspace.create()` / `teardown()` behaviour unchanged for non-fork use
- [ ] Unit tests for workspace provisioning, forking, isolation verification, teardown

## Technical Context

- Location: `guardkit/eval/workspace.py` (new module)
- Prototype reference: `docs/research/eval-runner/eval_workspace.py`
- Design reference: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 4)
- Templates directory: `eval-runner/workspaces/` (guardkit-project, plain-project)

## BDD Scenario Coverage

- Key example: Workspaces provisioned independently from respective templates
- Key example: Both arms receive identical input text
- Edge case: Vanilla workspace does not contain any GuardKit configuration
- Edge case: Vanilla arm creating GuardKit config detected in post-run inspection
- Negative: Brief referencing nonexistent template → warning + blank workspace fallback

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
