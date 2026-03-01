---
complexity: 7
dependencies:
- TASK-SAD-001
- TASK-SAD-002
- TASK-SAD-006
feature_id: FEAT-SAD
id: TASK-SAD-008
implementation_mode: task-work
parent_review: TASK-REV-AEE1
status: design_approved
task_type: feature
title: Write /arch-refine command specification
wave: 3
---

# Task: Write /arch-refine command specification

## Description

Write the complete command specification for `/arch-refine` at `installer/core/commands/arch-refine.md`. This command enables iterative refinement of architecture decisions with temporal superseding and downstream impact analysis.

## Acceptance Criteria

- [ ] Disambiguation flow:
  - Semantic search via `get_relevant_context_for_topic()` on user's natural language input
  - Present top 3-5 matches grouped by relevance (ASSUM-002)
  - Require explicit confirmation before any changes applied
  - Handle ambiguous queries safely (cap results, require confirmation)
- [ ] Temporal superseding (based on spike results from TASK-SAD-001):
  - If Option A confirmed: set existing ADR status to `"superseded"`, create new ADR with `supersedes` reference
  - Prior ADR remains queryable in Graphiti with its history
  - New ADR gets next available number in sequence
- [ ] Impact analysis:
  - Show which downstream artefacts are affected (feature specs, C4 diagrams, API contracts)
  - Flag feature specs that reference stale contracts
  - Present impact scope for user approval before applying changes
- [ ] C4 diagram re-review gate:
  - Revised L1/L2 diagrams generated and presented for mandatory approval
- [ ] Staleness flagging:
  - Affected downstream Graphiti nodes tagged with `stale: true` metadata
  - `/system-design` detects and reports stale decisions on next run
- [ ] Graphiti integration:
  - Upsert superseded and new episodes
  - Update group: `project_decisions`
- [ ] Graceful degradation when Graphiti unavailable
- [ ] Security: adversarial semantic search queries capped at 3-5 results with confirmation gate
- [ ] Execution protocol section
- [ ] Error handling section

## Implementation Notes

- File: `installer/core/commands/arch-refine.md`
- Depends on TASK-SAD-001 spike results to determine superseding mechanism
- The disambiguation flow is identical between `/arch-refine` and `/design-refine` — consider a shared reference section
- Reuse `get_relevant_context_for_topic()` from `SystemPlanGraphiti` for semantic search
- ADR numbering continues from highest existing number in `docs/architecture/decisions/`
- Impact analysis scope: query `project_design` and `feature_specs` groups for references to changed ADR entity_id