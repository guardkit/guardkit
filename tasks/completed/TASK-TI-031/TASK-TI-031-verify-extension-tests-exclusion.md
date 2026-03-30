---
id: TASK-TI-031
title: Verify extension tests excluded from user installation
status: completed
created: 2026-03-30T12:00:00Z
updated: 2026-03-30T14:00:00Z
completed: 2026-03-30T14:00:00Z
priority: low
tags: [template, tests, extends, installation]
task_type: implementation
complexity: 3
parent_review: TASK-REV-4F71
feature_id: FEAT-TI
implementation_mode: task-work
wave: 5
depends_on:
  - TASK-TI-027
---

# Task: Verify Extension Tests Excluded from User Installation

## Description

The extension template bundles 4 test files inside `langchain-deepagents-weighted-evaluation/tests/`. These are *template development tests* (validating scaffold code), not *user project tests*. When installed via the extends mechanism, these files would be copied into the user's project, potentially confusing their test suite.

## Finding Reference

TASK-REV-4F71, Finding F4 (LOW severity).

## What to Do

1. Verify what happens when `guardkit init langchain-deepagents-weighted-evaluation` is run:
   - Does the `tests/` directory from the extension get copied to the user project?
   - If yes, proceed to step 2
   - If no (already excluded), document the exclusion mechanism and close
2. If tests ARE copied, choose one approach:
   - Option A (preferred): Add an exclusion rule to `_apply_single_template()` in `guardkit/cli/init.py` that skips `tests/` directories from template installation
   - Option B: Move the extension tests from `installer/core/templates/langchain-deepagents-weighted-evaluation/tests/` to `tests/templates/langchain-deepagents-weighted-evaluation/` alongside the existing base template tests
3. Ensure the moved/excluded tests still run in CI

## Acceptance Criteria

- [x] Extension test files do NOT end up in user projects after `guardkit init`
- [x] Extension tests still run and pass in the GuardKit development environment
- [x] Documented which approach was taken

## Resolution

**Result: Already excluded by design. No code changes needed.**

### Verification Summary

Both init mechanisms (Python CLI and shell script) use an **allowlist-based copy strategy** that only copies specific file types. The `tests/` directory is never in the allowlist.

#### Python CLI (`guardkit/cli/init.py`, `_apply_single_template()` lines 886-972)

Copies ONLY:
- `agents/*.md` → `.claude/agents/`
- `.claude/rules/**/*.md` → `.claude/rules/`
- `CLAUDE.md` / `.claude/CLAUDE.md`
- `manifest.json` → `.claude/manifest.json`

#### Shell script (`installer/scripts/init-project.sh`, `copy_template_files()` lines 261-390)

Copies ONLY:
- `CLAUDE.md` / `.claude/CLAUDE.md`
- `agents/*.md` (excluding `-ext.md`)
- `templates/` → `.claude/templates/`
- `docs/patterns/` and `docs/reference/`
- `.claude/rules/`
- Root-level `*.md` and `*.json` files

#### Extension tests run in CI

The 4 test files remain at `installer/core/templates/langchain-deepagents-weighted-evaluation/tests/` and are collected by pytest (182 test items total including these). They run as part of the standard `pytest` invocation from the repo root.
