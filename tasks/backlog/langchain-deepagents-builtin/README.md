# Feature: Promote langchain-deepagents to Built-in Template

**Feature ID**: FEAT-LDB
**Parent Review**: TASK-REV-38D7 (in deepagents-tutor-exemplar repo)
**Review Report**: deepagents-tutor-exemplar/.claude/reviews/TASK-REV-38D7-review-report.md

## Problem Statement

The `langchain-deepagents` template was generated via `/template-create` and exists at
`~/.agentecflow/templates/langchain-deepagents/`. It already works with `guardkit init`
due to directory-based discovery, but lacks polish: no hardcoded description in the
init script, no Quick Start guidance, and documentation still lists only 4 specialized
templates.

## Solution Approach

Four small tasks to complete the promotion:

1. **TASK-LDB-001**: Update init-project.sh with description + Quick Start
2. **TASK-LDB-002**: Update CLAUDE.md template in the default template
3. **TASK-LDB-003**: Add auto-detection for Python+DeepAgents projects
4. **TASK-LDB-004**: Fix /template-create CLAUDE.md path display bug

## Execution Strategy

**Wave 1** (parallel, independent):
- TASK-LDB-001 (init-project.sh changes)
- TASK-LDB-002 (CLAUDE.md template update)
- TASK-LDB-004 (template-create bug fix)

**Wave 2** (depends on Wave 1):
- TASK-LDB-003 (auto-detection, benefits from understanding init-project.sh changes)
