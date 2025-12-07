---
id: TASK-FIX-40B4
title: Improve layer classification for JavaScript projects in template-create
status: completed
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T12:30:00Z
completed: 2025-12-07T12:30:00Z
priority: medium
tags: [template-create, classification, javascript]
complexity: 5
related_tasks: [TASK-REV-7C49]
completed_location: tasks/completed/TASK-FIX-40B4/
quality_gates:
  tests_passed: 65/65
  line_coverage: 100%
  branch_coverage: 100%
  architectural_review: 88/100
  code_review: 9/10
---

# Task: Improve Layer Classification for JavaScript Projects

## Description

The `/template-create` command currently classifies 80% of JavaScript files as "other" instead of proper architectural layers. Improve the `LayerClassificationStrategy` to better recognize common JavaScript project patterns.

**Source**: Review finding from TASK-REV-7C49

## Current State

Files incorrectly classified as "other":
- `src/lib/query.js` → should be `infrastructure/` or `data/`
- `src/lib/firestore/sessions.js` → should be `data/` or `repository/`
- `src/lib/firestore-mock/firebase.js` → should be `testing/` or `mocks/`
- `upload/update-sessions-weather.js` → should be `scripts/` or `utilities/`
- `upload/upload-sessions.js` → should be `scripts/` or `utilities/`

## Target State

Layer classification should recognize:
1. `lib/` → `infrastructure/` or `utilities/`
2. `firestore/`, `api/`, `data/` → `data-access/`
3. `mock/`, `mocks/`, `__mocks__/` → `testing/`
4. `upload/`, `scripts/`, `bin/` → `scripts/`
5. `components/` → `presentation/`
6. `routes/`, `pages/` → `routes/`
7. `stores/`, `state/` → `state/`

## Acceptance Criteria

- [x] `LayerClassificationStrategy` updated for JavaScript patterns
- [x] "other" classification reduced from 80% to <30%
- [x] New patterns added for common JS directories
- [x] Unit tests added for new classification rules
- [x] Existing Python/C# classification unchanged

## Files to Modify

- `installer/scripts/lib/template_generator/layer_classifier.py`
- `installer/scripts/lib/codebase_analyzer/pattern_detector.py` (if exists)

## Implementation Notes

Consider adding JavaScript-specific heuristics:
- Check for `package.json` to identify JS projects
- Look for framework markers (Svelte, React, Vue)
- Parse import statements to infer layer purpose

## Estimated Effort

Medium (4-6 complexity) - Requires understanding of classification logic and testing.
