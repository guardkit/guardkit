---
id: TASK-TI-005
title: Type-aware domain validator
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-005/
priority: p1
tags: [template, validation, domain-config, base-template]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 2
implementation_mode: task-work
depends_on: []
test_results:
  status: passed
  total_tests: 79
  passed: 79
  failed: 0
  coverage: "dynamic-import (79 tests across 10 classes)"
  last_run: 2026-03-29T00:00:00Z
quality_gates:
  tests_passing: true
  compilation: true
organized_files:
  - TASK-TI-005-type-aware-domain-validator.md
  - completion-report.md
---

# Task: Type-Aware Domain Validator

## Description

Create a validation framework for the `langchain-deepagents` base template that handles type coercion, array fields, and range notation — preventing the 4 validation bugs that required fixes TRF-004, TRF-028, FRF-002, and TRF-022.

## What to Build

### 1. Type coercion at model-output boundary
- Auto-coerce model output types to match schema: `str(value)`, `int(value)`, `list(value)`
- Applied BEFORE comparison with valid_values (TRF-004 lesson: model sends int, schema has strings)

### 2. Array vs scalar field handling
- Detect `MetadataField.type` for array vs scalar
- Array validation: `set(field_values) <= set(valid_values)` (TRF-FRF-002 lesson)
- Scalar validation: `field_value in valid_values`

### 3. Range notation support
- Recognise patterns: `1+`, `0+`, `1-10`, `0-100`
- Range fields return empty valid_values list (not treated as enum)
- Validate with numeric comparison, not string membership

### 4. Required config fields validation
- `max_tokens` must be explicitly set (TRF-022 lesson)
- Warn if context window not documented in config
- Validate temperature is within model-recommended range

## Fixes Prevented

TRF-004, TRF-022, TRF-028, FRF-002

## Target Location

`lib/domain_validator.py` (in the template output)

## Acceptance Criteria

- [x] Type coercion at model-output boundary
- [x] Array field detection and set-based validation
- [x] Range notation regex: `r'^(\d+)\+$'`, `r'^(\d+)-(\d+)$'`
- [x] Required config fields checked at startup
- [x] Unit tests for each validation type
- [x] Regression tests from actual failing values in runs 1, 3, 9

## Effort Estimate

2 days
