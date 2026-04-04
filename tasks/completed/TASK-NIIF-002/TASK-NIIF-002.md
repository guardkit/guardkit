---
id: TASK-NIIF-002
title: Add YAML paths validation to template-validate pipeline
status: completed
created: 2026-04-04T14:00:00Z
updated: 2026-04-04T15:00:00Z
completed: 2026-04-04T15:00:00Z
priority: medium
tags: [validation, templates, yaml, regression-prevention]
parent_review: TASK-REV-2266
feature_id: FEAT-NIIF
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-NIIF-001
---

# Task: Add YAML paths validation to template-validate pipeline

## Description

Add a validation check to the template validation pipeline that detects invalid YAML in rule frontmatter `paths:` fields. This prevents two known failure patterns:
1. Unquoted glob patterns (fixed in TASK-NIF-001)
2. Comma-separated quoted strings (found in TASK-REV-2266)

The validator should parse each rule file's frontmatter with `yaml.safe_load()` and report any `YAMLError` as a validation failure.

## Acceptance Criteria

- [x] Validation check added to template-validate pipeline
- [x] Detects invalid YAML frontmatter in rule files
- [x] Reports file path and specific error for each failure
- [x] Passes for all current template rule files (after TASK-NIIF-001 fix)
- [x] Unit tests cover both known failure patterns
- [x] Integrated into existing validation section or new section

## Implementation Notes

Key directory: `installer/core/lib/template_validation/sections/`
Reference: TASK-NIF-003 (completed) may have added related validation — check for overlap.

Expected interface: The validator iterates all `.md` files under `.claude/rules/` for a template, extracts frontmatter, and runs `yaml.safe_load()`. Failures are reported as validation errors with severity HIGH.
