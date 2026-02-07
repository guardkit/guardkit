---
id: TASK-GBF-003
title: Add retrieval fidelity guidance to baseline documentation
status: completed
created: 2026-02-07T12:00:00Z
updated: 2026-02-07T14:30:00Z
completed: 2026-02-07T14:30:00Z
completed_location: tasks/completed/TASK-GBF-003/
priority: medium
tags: [graphiti, documentation, best-practices]
parent_review: TASK-REV-C632
feature_id: FEAT-GBF
complexity: 2
wave: 1
implementation_mode: direct
dependencies: []
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: Add Retrieval Fidelity Guidance to Baseline Documentation

## Description

The existing `graphiti_code_retrieval_fidelity.md` analysis revealed that Graphiti extracts semantic facts, not verbatim content. This critical insight is not yet reflected in the new baseline documents produced by TASK-REV-C632.

Update the baseline reference documents to include clear guidance on:
- What Graphiti can and cannot retrieve faithfully
- When to use Graphiti vs static files for different content types
- The semantic extraction pipeline and its implications

## Objectives

- [x] Add "Retrieval Fidelity" section to `graphiti-storage-theory.md`
- [x] Add warning to `graphiti-technical-reference.md` API section about content preservation
- [x] Reference the existing fidelity assessment (`docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md`)

## Scope

### In Scope
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md`
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md`

### Out of Scope
- Code changes
- New fidelity testing

## Acceptance Criteria

1. Both baseline docs include retrieval fidelity guidance
2. Cross-reference to existing fidelity assessment included
3. Clear guidance on when to use Graphiti vs static files
