---
id: TASK-FIX-STUB-B
title: Create anti-stub quality rule for Coach enforcement
status: completed
updated: 2026-02-14T00:00:00Z
created: 2026-02-13T12:00:00Z
completed: 2026-02-14T00:00:00Z
priority: high
tags: [autobuild, quality-gates, rules, stub-detection]
parent_review: TASK-REV-STUB
feature_id: FEAT-STUB-QG
implementation_mode: direct
wave: 1
complexity: 3
task_type: documentation
---

# Task: Create anti-stub quality rule for Coach enforcement

## Description

Create `.claude/rules/anti-stub.md` that defines stub patterns and establishes enforcement rules for the Coach. This rule file becomes part of the Coach agent's prompt context, enabling it to detect and reject stub implementations for FEATURE and REFACTOR tasks.

Currently no quality gate inspects function bodies for stub patterns. A syntactically valid file containing only `pass` or `raise NotImplementedError` passes all gates (compilation, test pass/fail, coverage claims).

## Stub Definition

A **stub** is a function whose body consists of one or more of:
- `pass` (possibly preceded by a docstring or logger call)
- `raise NotImplementedError(...)`
- Only `# TODO` / `# FIXME` / `# STUB` comments
- `return None` or hardcoded defaults with no conditional logic
- `logger.*()` + `pass` / `return` (logging-only stub)

## Files to Create/Change

1. **NEW**: `.claude/rules/anti-stub.md` — Rule definition
2. **UPDATE**: Coach agent prompt (if applicable) to reference the new rule

## Acceptance Criteria

- [x] AC-001: `.claude/rules/anti-stub.md` exists with clear stub pattern definitions
- [x] AC-002: Rule specifies that FEATURE and REFACTOR tasks MUST NOT have primary deliverable functions as stubs
- [x] AC-003: Rule specifies that SCAFFOLDING/INFRASTRUCTURE tasks MAY create stubs if acceptance criteria explicitly permit it
- [x] AC-004: Rule provides concrete examples of stub vs non-stub implementations
- [x] AC-005: Rule defines "primary deliverable function" as the function(s) named or implied by the task's acceptance criteria

## Technical Notes

- This is a rules/documentation task — no Python code changes
- The rule file is loaded into Coach context via `.claude/rules/` glob
- Effectiveness depends on LLM comprehension (prompt-level enforcement)
- Consider adding stub detection patterns that the Coach can check for in code review

## References

- Review report: `.claude/reviews/TASK-REV-STUB-review-report.md` (RC-4, P0-B)
- Example stub: `guardkit/planning/system_plan.py` (70 lines, `pass` body)
