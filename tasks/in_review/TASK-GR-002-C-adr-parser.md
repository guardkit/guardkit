---
complexity: 3
conductor_workspace: gr-mvp-wave7-parsers
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-002-A
feature_id: FEAT-GR-MVP
id: TASK-GR-002-C
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- context-addition
- parser
- adr
- mvp-phase-2
task_type: feature
title: Implement ADRParser
updated: 2026-02-01 00:00:00+00:00
wave: 7
implementation_completed: 2026-02-01 00:00:00+00:00
test_coverage: 91
tests_passed: 33
tests_total: 33
---

# Task: Implement ADRParser

## Description

Implement a parser for Architecture Decision Records (ADR-*.md) that extracts decision information for Graphiti seeding.

## Acceptance Criteria

- [x] Parse ADR standard format
- [x] Extract: title, status, context, decision, consequences
- [x] Create decision episode for Graphiti
- [x] Handle various ADR formats
- [x] Support ADR numbering conventions

## Implementation Summary

**Files Created:**
- `guardkit/integrations/graphiti/parsers/adr.py` - ADRParser implementation
- `tests/integrations/graphiti/parsers/test_adr.py` - 33 comprehensive tests

**Key Features:**
- Dual detection: filename (`adr-*.md`) or content sections
- Extracts: title, status, context, decision, consequences
- Generates unique entity IDs from slugified titles
- Extracts ADR numbers from titles into metadata
- Case-insensitive section detection
- Handles various ADR status values (Accepted, Deprecated, Superseded, Proposed)

**Test Coverage:**
- 91% line coverage
- 33 tests passing
- TDD approach (RED → GREEN → REFACTOR)

## Test Requirements

- [x] Unit tests with sample ADRs
- [x] Test section extraction
- [x] Test various ADR formats

## Notes

Simpler than FeatureSpecParser - more standard format.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
