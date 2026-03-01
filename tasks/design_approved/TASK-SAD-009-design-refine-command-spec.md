---
complexity: 6
dependencies:
- TASK-SAD-001
- TASK-SAD-005
- TASK-SAD-007
feature_id: FEAT-SAD
id: TASK-SAD-009
implementation_mode: task-work
parent_review: TASK-REV-AEE1
status: design_approved
task_type: feature
title: Write /design-refine command specification
wave: 3
---

# Task: Write /design-refine command specification

## Description

Write the complete command specification for `/design-refine` at `installer/core/commands/design-refine.md`. This command enables iterative refinement of design decisions (DDRs, API contracts, data models) with temporal superseding and feature spec staleness detection.

## Acceptance Criteria

- [ ] Disambiguation flow (identical pattern to `/arch-refine`):
  - Semantic search via `SystemDesignGraphiti.search_design_context()` on user input
  - Present top 3-5 matches grouped by relevance
  - Require explicit confirmation before any changes applied
- [ ] Temporal superseding for DDRs:
  - Same mechanism as ADR superseding (based on spike results)
  - Set existing DDR status to `"superseded"`, create new DDR with `supersedes` reference
  - Prior DDR remains queryable
- [ ] API contract update flow:
  - Present current contract, proposed changes, and diff
  - Regenerate OpenAPI spec section for affected bounded context
  - Validate updated OpenAPI spec
- [ ] Feature spec staleness detection:
  - Query `feature_specs` group for scenarios referencing changed API contracts or domain entities
  - Flag affected feature specs as potentially stale
  - Offer choice: re-run `/feature-spec` on affected areas or accept delta
- [ ] C4 L3 diagram re-review gate:
  - Revised Component diagrams generated and presented for mandatory approval
- [ ] Staleness flagging on downstream Graphiti nodes
- [ ] Graphiti integration: update `project_design` and `api_contracts` groups
- [ ] Graceful degradation when Graphiti unavailable
- [ ] Contradiction detection: flag if proposed design change contradicts existing ADRs
- [ ] Execution protocol section
- [ ] Error handling section

## Implementation Notes

- File: `installer/core/commands/design-refine.md`
- Depends on TASK-SAD-001 spike results
- Shares disambiguation flow pattern with `/arch-refine` — reference shared spec section
- DDR numbering continues from highest existing number in `docs/design/decisions/`
- Feature spec staleness: search `feature_specs` group for entity_ids matching changed contract/model
- Contradiction detection: query `project_decisions` group for ADRs constraining the affected domain