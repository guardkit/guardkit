---
id: TASK-NIF-003
title: Add glob pattern validation to template-validate
status: completed
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T23:30:00Z
completed: 2026-04-03T23:30:00Z
completed_location: tasks/completed/TASK-NIF-003/
priority: medium
tags: [template-validate, yaml, glob-patterns, validation]
parent_review: TASK-REV-A8C2
feature_id: FEAT-NIF
implementation_mode: task-work
wave: 2
complexity: 3
depends_on: []
---

# Task: Add glob pattern validation to template-validate

## Description

Add a validation check to `/template-validate` that detects unquoted glob patterns in rule file YAML frontmatter. This prevents the YAML parsing bug (unquoted `*` treated as alias indicator) from being reintroduced when new templates or rules are created.

## Acceptance Criteria

- [ ] `/template-validate` checks all `rules/*.md` files for unquoted glob patterns in `paths:` frontmatter
- [ ] Fails validation with clear message: "Rule {file} has unquoted glob pattern in paths: frontmatter. Quote it: `paths: \"{value}\"`"
- [ ] Passes validation for correctly quoted patterns (string, list, or quoted values)
- [ ] Existing `/template-validate` checks are not affected

## Implementation Notes

- The check should attempt `yaml.safe_load()` on the frontmatter and report any `YAMLError` with the specific file path
- Alternatively, regex check for `^paths: [^"[\n]*\*` to catch unquoted asterisks
- The validation should be in the existing template validation pipeline (see `/template-validate` command spec)
- Expected interface: a new validation function in the template validation module that takes a rule file path and returns pass/fail with error message
