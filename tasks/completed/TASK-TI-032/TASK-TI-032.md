---
id: TASK-TI-032
title: Document templating convention differences between base and extension
status: completed
created: 2026-03-30T12:00:00Z
updated: 2026-03-30T18:00:00Z
completed: 2026-03-30T18:00:00Z
completed_location: tasks/completed/TASK-TI-032/
priority: low
tags: [template, documentation, consistency]
task_type: implementation
complexity: 2
parent_review: TASK-REV-4F71
feature_id: FEAT-TI
implementation_mode: direct
wave: 5
depends_on: []
---

# Task: Document Templating Convention Differences

## Description

The base template uses `.py.template` files with `{{placeholder}}` syntax for simple variable substitution. The extension uses `.py.j2` files with Jinja2 syntax for more complex scaffolding (loops over criteria, conditionals for intensity modes). Both conventions are valid but using different approaches in the same extends chain could confuse contributors.

Additionally, the extension includes a `SKILL.md` for template variable definitions while the base only uses `manifest.json`. This inconsistency should be documented.

## Finding Reference

TASK-REV-4F71, Findings F6 and F7 (INFO severity).

## What to Do

1. Add a section to the extension's CLAUDE.md explaining:
   - Base uses simple `{{placeholder}}` substitution (`.template` files)
   - Extension uses Jinja2 (`.j2` files) for loops and conditionals
   - When to use which: simple substitution for leaf files, Jinja2 for structural scaffolding
2. Document `SKILL.md` purpose:
   - `manifest.json` is the canonical source for template metadata (both templates)
   - `SKILL.md` provides richer variable definitions with defaults, examples, and Anthropic terminology mapping (extension pattern)
3. Consider adding a `SKILL.md` to the base template for parity (optional)

## Acceptance Criteria

- [x] Extension CLAUDE.md documents `.template` vs `.j2` convention
- [x] SKILL.md purpose documented
- [x] Contributors understand which templating approach to use
