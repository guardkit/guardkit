---
id: TASK-REV-A73F
title: Review init Graphiti migration integrity
status: review_complete
created: 2026-03-15T10:00:00Z
updated: 2026-03-15T12:00:00Z
priority: high
tags: [architecture-review, init, graphiti, context-reduction, regression-check]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 4
review_results:
  mode: architectural
  depth: comprehensive
  score: 82
  findings_count: 5
  recommendations_count: 3
  reclassified_findings: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-A73F-review-report.md
  completed_at: 2026-03-15T12:30:00Z
  revision: deep-analysis-with-c4-sequence-diagrams
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review init Graphiti migration integrity

## Description

Review the recent changes made to the GuardKit project init workflow to verify that nothing has been fundamentally broken. The changes were part of an initiative to reduce context token usage in AutoBuild by providing job-specific context via Graphiti instead of static markdown files.

Key concerns:
1. **Static file copying still required**: Not all information can be stored in Graphiti yet, so some static markdown file copying during init must remain functional
2. **Graphiti integration**: Verify that information moved to Graphiti is correctly seeded/accessible during project init
3. **No regression in init output**: Projects initialised after these changes should have all the files and configuration they need
4. **Context token reduction goal**: Confirm changes actually serve the goal of reducing AutoBuild context overhead

## Context

Relevant commits (chronological):
- `b72b6254` - Copy graphiti config file on project init
- `d9f21393` - Fixes for project init and graphiti
- `f86fef47` - Reviews and fixes for project init with Graphiti
- `c3461c05` - Further fixes for project init Graphiti seeding
- `5e09f866` - Reviews and fixes for loading project context into Graphiti
- `3afc32fe` - Graphiti init and seed fixes
- `39fd6a51` - Reviews and filtering of seeding templates
- `1bc0c333` - Further reviews and fixes for graphiti seeding
- `2c1b11f0` - Complete TASK-EMB-003: auto-offer --copy-graphiti during guardkit init

Related existing tasks:
- TASK-REV-5F19 (in_progress) - Reduce context via Graphiti migration
- TASK-D3A1 (backlog) - Review template init architecture

## Review Focus Areas

1. **Init file completeness**: Are all required static files still being copied during `guardkit init`?
2. **Graphiti vs static boundary**: Is there a clear boundary between what lives in Graphiti and what must remain as static files?
3. **Fallback behaviour**: If Graphiti is unavailable, does init still produce a functional project?
4. **Seeding correctness**: Is the Graphiti seeding during init populating the right entities/relationships?
5. **AutoBuild compatibility**: Can AutoBuild still function correctly with the new init output?

## Acceptance Criteria

- [ ] Init workflow produces all required files for a functional project
- [ ] Static markdown files that must be present on disk are still copied
- [ ] Graphiti seeding runs without errors when Graphiti is available
- [ ] Init degrades gracefully when Graphiti is not available
- [ ] No orphaned or missing configuration after init completes
- [ ] Changes align with the context token reduction objective

## Key Files to Examine

- `guardkit/commands/init_project.py` (or equivalent init entry point)
- `guardkit/graphiti/` (seeding and context modules)
- `installer/core/templates/` (template files being copied)
- `installer/scripts/install.sh` (if init logic lives here)
- Any recent test changes related to init

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-A73F` for execution.
