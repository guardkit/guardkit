---
id: TASK-FIX-40B4
title: Improve layer classification for JavaScript projects in template-create
status: backlog
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T11:45:00Z
priority: medium
tags: [template-create, classification, javascript]
complexity: 5
related_tasks: [TASK-REV-7C49]
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

- [ ] `LayerClassificationStrategy` updated for JavaScript patterns
- [ ] "other" classification reduced from 80% to <30%
- [ ] New patterns added for common JS directories
- [ ] Unit tests added for new classification rules
- [ ] Existing Python/C# classification unchanged

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
