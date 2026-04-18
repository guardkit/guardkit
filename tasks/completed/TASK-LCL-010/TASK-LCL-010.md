---
id: TASK-LCL-010
title: Clarify Source path convention in base template patterns intro
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-LCL-010/
priority: low
tags: [templates, docs, les1-doc-code-co-evolution]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 3
conductor_workspace: langchain-template-lessons-wave3-3
complexity: 1
previous_state: in_review
---

# Task: Clarify `Source:` path convention in base template patterns intro

## Description

Pattern rule files in `installer/core/templates/langchain-deepagents/.claude/rules/patterns/`
end with `Source: <path>` lines like `Source: scaffold/orchestrator_pattern.py.template`.
These paths are **post-render** paths (relative to the user's rendered
project), not template-tree paths. In the template source tree the files
live under `templates/other/scaffold/...` which confuses contributors.

## Acceptance Criteria

- [ ] One-paragraph clarification added to `installer/core/templates/langchain-deepagents/.claude/CLAUDE.md` — under a new "Pattern rule conventions" subsection or appended to the Detailed Guidance block — stating that `Source:` paths in pattern rules refer to the **post-render** project layout.
- [ ] If a `patterns/README.md` exists (create if sensible), repeat the note there.
- [ ] No changes to any existing pattern rule file content.

## Files

- `installer/core/templates/langchain-deepagents/.claude/CLAUDE.md`
- Optional: `installer/core/templates/langchain-deepagents/.claude/rules/patterns/README.md` (new)

## Links

- Review: [TASK-REV-LES1 report §MEDIUM-1](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
