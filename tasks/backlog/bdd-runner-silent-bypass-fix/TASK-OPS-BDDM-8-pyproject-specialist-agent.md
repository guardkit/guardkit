---
id: TASK-OPS-BDDM-8
title: 'specialist-agent: add pytest-bdd to pyproject (advisory remediation)'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: medium
complexity: 1
task_type: bugfix
tags: [bdd, cross-repo-remediation, pytest-bdd]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 3
conductor_workspace: bdd-fix-wave3-specagent
depends_on: [TASK-FIX-BDDM-1]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/specialist-agent
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: specialist-agent — add pytest-bdd to pyproject

## Description

Audit (2026-04-25): specialist-agent has **21 `.feature` files** (largest BDD scaffold of any non-forge repo audited) but **zero `@task:` tags** and no `pytest-bdd`. Status: **advisory** — extensive BDD scope authored, no current silent-bypass risk, but proactive remediation is high-value here because the volume of feature files makes this repo a likely future tagging target.

## Acceptance Criteria

- [ ] Add `"pytest-bdd>=8.1,<9"` to `specialist-agent/pyproject.toml` test/dev dependencies.
- [ ] Reinstall.
- [ ] Verify `python -c "import pytest_bdd"` succeeds.
- [ ] Existing test suite still passes.
- [ ] Add comment referencing TASK-OPS-BDDM-8 / FEAT-BDDM.

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/`

Direct mode. Match forge's pattern. Isolated to dev/test deps; no runtime impact.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) recommendation R7.
- This repo's 21 feature files makes it the second-largest BDD scope after forge (also 7+) — getting it configured early avoids a future Wave-3-style remediation if/when tags get added.
