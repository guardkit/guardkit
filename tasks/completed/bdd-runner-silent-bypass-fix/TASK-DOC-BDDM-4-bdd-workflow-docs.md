---
id: TASK-DOC-BDDM-4
title: 'Document pytest-bdd prerequisite in BDD workflow guide + amend feature-spec wording (R5)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
completed: '2026-04-25T00:00:00Z'
completed_location: tasks/completed/bdd-runner-silent-bypass-fix/
priority: medium
complexity: 2
task_type: documentation
tags: [bdd, docs, prerequisites]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 1
conductor_workspace: bdd-fix-wave1-3
depends_on: []
previous_state: backlog
state_transition_reason: 'task-work direct-mode docs edits applied; /task-complete invoked by user'
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Document pytest-bdd prerequisite (R5)

## Description

[docs/guides/bdd-workflow-for-agentic-systems.md](../../../docs/guides/bdd-workflow-for-agentic-systems.md) mentions `pytest-bdd` as a framework choice (line 91) and as an install command (line 501-502), but does NOT explicitly state that adding `pytest-bdd` to the project's `pyproject.toml` is a runtime prerequisite for the AutoBuild R2 BDD oracle to fire. A reader who follows the guide can author feature files without ever discovering this requirement.

[installer/core/commands/feature-spec.md:491-493](../../../installer/core/commands/feature-spec.md#L491-L493) reads "if `pytest-bdd` is installable" — implying the runner does an install probe, when in fact it does an import probe.

## Acceptance Criteria

- [x] Add a "Runtime Prerequisites" subsection to `docs/guides/bdd-workflow-for-agentic-systems.md` immediately after the existing "Prerequisites" section (line 54), explicitly stating: "The R2 BDD oracle requires `pytest-bdd` to be declared in the project's `pyproject.toml` (or installed in the worktree env via another mechanism). Without it, AutoBuild will surface a `pytest_bdd_not_importable` Coach-blocking failure for any task with tagged scenarios."
- [x] Add a canonical-example snippet pointing to forge's `pyproject.toml:34` (`"pytest-bdd>=8.1,<9"`).
- [x] Amend `installer/core/commands/feature-spec.md:491-493`: change "if `pytest-bdd` is **installable**" to "if `pytest-bdd` is declared in the project's `pyproject.toml` (or otherwise installed in the worktree env)".
- [x] Mention TASK-FIX-BDDM-1 + TASK-FIX-BDDM-2 as the enforcement mechanism (the docs are the *third* line of defence after the in-loop blocker and the preflight error).

## Implementation Notes

**Direct mode** — small docs change, no test infrastructure needed. Manual review by user before merge.

**Wording priorities:**
1. State the requirement plainly (no hedging, no "if you're using BDD" — the requirement applies as soon as any `.feature` file gets a `@task:` tag).
2. Give the exact dependency string a user can paste.
3. Cross-reference TASK-FIX-BDDM-1 + TASK-FIX-BDDM-2 so a future reader can trace why the requirement is enforced.

## Notes

- See review report §F.5 for R5 details and §E for the rationale on why this is a should_fix not a must_fix (R1 + R3 already enforce; docs are belt-and-braces).
