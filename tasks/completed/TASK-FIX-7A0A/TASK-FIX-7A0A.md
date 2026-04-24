---
id: TASK-FIX-7A0A
title: CI lint — every hardcoded TASK-ID literal in orchestrator code resolves
status: completed
created: 2026-04-24T18:30:00Z
updated: 2026-04-24T19:25:00Z
completed: 2026-04-24T19:25:00Z
completed_location: tasks/completed/TASK-FIX-7A0A/
previous_state: in_review
state_transition_reason: "Task completed — lint test passes on clean repo, all ACs met"
priority: medium
task_type: implementation
tags: [ci, lint, task-id-references, hygiene, autobuild]
parent_review: TASK-REV-F3D7
feature_id: FEAT-F3D7
implementation_mode: direct
wave: 2
conductor_workspace: autobuild-sdk-stall-resilience-phase2-w2-1
complexity: 1
depends_on:
  - TASK-FIX-7A08
---

# Task: CI lint — every hardcoded TASK-ID literal in orchestrator code resolves

## Description

The forge-run-3 failure investigation (TASK-REV-F3D7) surfaced a dead
`TASK-FIX-7A08` reference hardcoded in two places — `autobuild.py:5078` and
`feature_orchestrator.py:1616` — pointing at a task that never existed. This
class of defect (runtime/advice text references an external artefact that was
promised but not filed) is cheap to prevent at CI time with a simple lint.

This task adds that lint. It depends on `TASK-FIX-7A08` existing (so that the
current live reference is valid — the lint's first CI run should pass).

## Acceptance Criteria

- [x] New test file `tests/rules/test_no_dead_task_id_references.py`:
  - Greps `guardkit/orchestrator/**/*.py` for the regex
    `TASK-(?:FIX|REV|DOC|POL|CFG|NFI|IMP|VER|SEC|E\d+|[A-Z]{2,4})-[A-Z0-9]{4}`
    (extend character class as needed — the IDs are hash-based per
    `.claude/rules/hash-based-ids.md`).
  - For each match, asserts the referenced task ID exists as a file matching
    `tasks/backlog/**/TASK-<id>-*.md`,
    `tasks/in_progress/**/TASK-<id>-*.md`,
    `tasks/in_review/**/TASK-<id>-*.md`,
    `tasks/completed/**/TASK-<id>-*.md`,
    `tasks/completed/**/TASK-<id>/*.md`, or
    `docs/state/TASK-<id>/*`.
  - Emits a readable failure listing `{file}:{line}` for every unresolved ID.
- [x] Test passes on a clean repo with 7A08 filed (verify both `autobuild.py:5078`
      and `feature_orchestrator.py:1616` resolve).
- [x] Test is included in the default `pytest` discovery (no special marker
      required) and runs in the standard CI path.
- [x] Documentation note added to `.claude/rules/hash-based-ids.md` (or a new
      sibling rule) briefly stating the lint exists and what it enforces.

## Implementation Notes

- **Keep it simple**: a single pytest module, no fancy infrastructure. Use
  `pathlib.Path.rglob('*.py')` to enumerate source files, a precompiled
  regex, and `pathlib.Path(tasks_root).rglob(f'TASK-{id}*')` to resolve.
- **False-positive avoidance**: do NOT match IDs inside string-literal
  blocks that are clearly examples/placeholders (e.g. the string
  `'TASK-XXX'` used for templating). A simple exclusion of `XXX`/`YYY`
  literal IDs and of IDs inside comments starting with `# example:` is
  enough.
- **Scope**: lint only orchestrator code (`guardkit/orchestrator/**/*.py`) for
  the first pass. Broadening to CLI / `guardkit/knowledge` / tests can be a
  separate follow-up if valuable — but the original incident was
  orchestrator-localised.
- **Direct mode rationale**: this is a single-file test with no cross-module
  ramifications. Specialist pipeline is overkill.

## Key References

- **Review report**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)
- **Live references today** (should both resolve after 7A08 lands):
  - `guardkit/orchestrator/autobuild.py:5078` — `"(see TASK-FIX-7A08). Required specialists:"`
  - `guardkit/orchestrator/feature_orchestrator.py:1616` — `"Task-tool invocation for the missing phases (TASK-FIX-7A08), "`
- **ID format rule**: `.claude/rules/hash-based-ids.md`
- **Graphiti seed** (to add post-completion): `guardkit__project_decisions` —
  *"Hardcoded task-ID references in orchestrator code are lint-checked in CI;
  any dead reference breaks the build"*
