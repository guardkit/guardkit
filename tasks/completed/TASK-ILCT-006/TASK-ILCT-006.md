---
id: TASK-ILCT-006
title: Extend settings.json code_style for both templates
status: completed
created: 2026-04-03T23:15:00Z
completed: 2026-04-03T23:45:00Z
priority: low
tags: [template, settings, code-style]
parent_review: TASK-REV-81AA
feature_id: FEAT-ILCT
implementation_mode: direct
wave: 2
complexity: 2
depends_on: []
completed_location: tasks/completed/TASK-ILCT-006/
---

# Task: Extend settings.json code_style for both templates

## Description

Both low-confidence templates have minimal code_style sections (4 fields) compared to high-confidence templates which include 10+ fields. Add the missing fields to improve code generation quality.

## Changes Required

Add these fields to `code_style` in both templates' settings.json:

```json
"code_style": {
    "indentation": "spaces",
    "indent_size": 4,
    "line_length": 88,
    "trailing_commas": true,
    "quote_style": "double",
    "async_preferred": true,
    "type_hints": "required",
    "docstrings": "google",
    "linter": "ruff",
    "formatter": "ruff"
}
```

### Templates to update

1. `installer/core/templates/nats-asyncio-service/settings.json`
2. `installer/core/templates/langchain-deepagents-orchestrator/settings.json`

## Acceptance Criteria

- [x] Both settings.json files have 10+ code_style fields
- [x] Values match Python conventions used in each template
- [x] JSON remains valid

## References

- High-confidence reference: fastapi-python settings.json code_style section
- Review report: `.claude/reviews/TASK-REV-81AA-review-report.md` (Finding 12)
