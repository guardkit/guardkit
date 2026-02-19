---
id: TASK-REV-DAC9
title: Add cross-component boundary hint to task-review fix task generation prompt
status: obsolete
superseded_by: TASK-IC-6F94
superseded_reason: Absorbed into TASK-IC-6F94 — the one-sentence task-review hint is included there as a same-session addition alongside the feature-plan prompt change
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: normal
task_type: feature
parent_review: TASK-REV-0E07
complexity: 2
dependencies:
  - TASK-FP-1B6D  # Integration Contracts in feature-plan (primary fix; this is lightweight complement)
related_tasks:
  - TASK-FP-1B6D  # Primary prevention task
  - TASK-REV-0E07 # Review that identified the root cause
tags: [task-review, fix-task-generation, integration-contracts, autobuild]
---

# Add Cross-Component Boundary Hint to task-review Fix Task Generation Prompt

## Description

When `/task-review` identifies a finding and spawns a TASK-FIX (or implementation subtask), the task-generation prompt has no instruction to include interface format information for cross-component boundaries. In the 90% of reviews that examine completed, single-technology code, this is irrelevant. But in the edge case where a review identifies a missing integration test — e.g. "add a test that verifies DATABASE_URL works with the async engine" — the generated fix task description may omit the expected format, leaving the implementer to guess.

This is a **lighter-touch complement** to TASK-FP-1B6D (Integration Contracts in `/feature-plan`). It does not add the full Integration Contracts section to `/task-review` output; it adds a single instructional line to the fix task generation prompt that activates only for boundary-crossing findings.

## Change Required

**File:** `installer/core/commands/task-review.md`

**Location:** The section that describes how `/task-review` generates fix/implementation tasks when the user selects `[I]mplement` — specifically the prompt instructions for generating subtask descriptions (Phase 5 / Step 8: "Generating subtask files").

**Change:** Add a single sentence to the subtask generation instructions:

> When creating fix tasks that involve cross-component boundaries (e.g. integration tests, environment variable consumers, API contracts between services), include the expected interface format in the task description.

**Exact placement:** In the instructions/prompt that drives subtask file generation (Step 8 of the Enhanced [I]mplement Flow), after the existing guidance on generating task descriptions, add:

```
Cross-component boundary note: If a subtask involves verifying or testing
an interface between two components (e.g. a database URL consumed by an
async engine, an API contract between services, an environment variable
read by application code), include the expected format of that interface
in the task description. Example: "The DATABASE_URL must use the
postgresql+asyncpg:// scheme for compatibility with SQLAlchemy async."
```

This is prompt-level documentation — no code change, no schema change, no additional output sections. The `/task-review` output format is unchanged.

## Acceptance Criteria

- [ ] The subtask generation instructions in `installer/core/commands/task-review.md` include the cross-component boundary note
- [ ] The note is a single paragraph (not a new section, not a mandatory output block)
- [ ] The existing `[I]mplement` flow output format is unchanged — no new sections appear in generated task files unless the subtask is a cross-component boundary fix
- [ ] When a subtask IS a cross-component boundary fix, the generated task description includes the expected interface format

## Constraints

- Do NOT add a full `## Integration Contracts` section to `/task-review` — that belongs only in `/feature-plan` (TASK-FP-1B6D)
- Do NOT add mandatory output sections — this must be a prompt hint, not a schema requirement
- The change must not add ceremony to the 90% of reviews that don't involve cross-component boundaries
- This task is a lightweight complement to TASK-FP-1B6D, not a substitute for it

## Implementation Notes

- Target file: `installer/core/commands/task-review.md`, Step 8 of the Enhanced [I]mplement Flow (around line 974: "Generating subtask files")
- The change is entirely within the command spec (prompt instructions to Claude), not in Python code
- See `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` §3 for the root cause analysis that motivated this
- Rationale: `/task-review` spawns fix tasks within a single technological context (low risk), but the edge case of "add an integration test for a cross-component boundary" is real and would benefit from format hints in the task description
