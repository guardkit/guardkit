---
id: TASK-GDU-003
title: Create graphiti-job-context.md guide
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T00:05:00Z
completed: 2026-02-02T00:05:00Z
priority: high
tags: [documentation, graphiti, github-pages]
complexity: 3
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 1
implementation_mode: direct
conductor_workspace: graphiti-docs-wave1-3
completed_location: tasks/completed/TASK-GDU-003/
---

# Task: Create graphiti-job-context.md Guide

## Description

Create a new public documentation page for Job-Specific Context Retrieval (FEAT-GR-006).

## Source Content

Primary source: `CLAUDE.md` lines 1056-1139 (Job-Specific Context Retrieval section)

Additional sources:
- `docs/research/graphiti-refinement/FEAT-GR-006-job-specific-context.md`
- `guardkit/knowledge/task_analyzer.py`
- `guardkit/knowledge/budget_calculator.py`
- `guardkit/knowledge/job_context_retriever.py`

## Requirements

Create `docs/guides/graphiti-job-context.md` with:

1. **Overview** - What job-specific context is and why it matters
2. **How It Works** - 5-step process explained
3. **Context Categories**:
   - Feature Context
   - Similar Outcomes
   - Relevant Patterns
   - Architecture Context
   - Warnings
   - Domain Knowledge
4. **AutoBuild Additional Context**:
   - Role Constraints
   - Quality Gate Configs
   - Turn States
   - Implementation Modes
5. **Budget Allocation Table** - By task complexity
6. **Budget Adjustments** - First-of-type, refinement, autobuild modifiers
7. **Relevance Filtering** - Threshold explanations
8. **Performance Metrics** - Retrieval times, cache rates
9. **Context in Action** - Examples with task-work and feature-build
10. **Troubleshooting** - Common issues

## Acceptance Criteria

- [x] Document created at `docs/guides/graphiti-job-context.md`
- [x] Budget allocation table included
- [x] AutoBuild context categories explained
- [x] Performance section with actual metrics
- [x] Example context loading shown
- [x] Follows existing GuardKit documentation style
- [x] Builds successfully with MkDocs (added to nav)

## Estimated Effort

2 hours
