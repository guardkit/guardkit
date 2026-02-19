---
id: TASK-IC-6F94
title: Add Integration Contracts section to feature-plan prompt template
status: completed
created: 2026-02-18T00:00:00Z
updated: 2026-02-19T00:00:00Z
completed: 2026-02-19T00:00:00Z
completed_location: tasks/completed/TASK-IC-6F94/
priority: high
task_type: feature
parent_feature: TASK-FP-1B6D
parent_review: TASK-REV-0E07
complexity: 3
dependencies: []
related_tasks:
  - TASK-IC-DD44  # Child B — depends on this task
  - TASK-IC-B4E6  # Child C — depends on B
  - TASK-REV-DAC9 # task-review boundary hint (companion change, can be done in same session)
  - TASK-FP-1B6D  # Superseded parent task (do not work on)
tags: [feature-plan, integration-contracts, prompt-template, autobuild]
---

# Add Integration Contracts Section to feature-plan Prompt Template

## Context

This is Child A of the TASK-FP-1B6D decomposition. It is the highest-value, lowest-effort change in the integration contracts prevention strategy, and must be completed before TASK-IC-DD44 (Child B) and TASK-IC-B4E6 (Child C).

Root cause: The feature planner decomposes user requests into producer and consumer tasks without specifying the format contract at their boundary. See `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` for full analysis.

## Change Required

**File:** `installer/core/commands/feature-plan.md`

**What:** Add a mandatory `## §4: Integration Contracts` output section to the feature planner's prompt template. This section is required whenever the planner generates tasks where one task's output is consumed by another task's input.

**Locate:** The existing §4 mapping section in `feature-plan.md` (FEAT-FP-002 already includes `integration_points` in this section). This change formalises what `integration_points` must contain: not just "these tasks interact" but "this is the format contract at their boundary."

**Template to add/expand:**

```markdown
## §4: Integration Contracts

For each cross-task data dependency, specify:

### Contract: {artifact_name}
- **Producer task:** TASK-xxx
- **Consumer task(s):** TASK-xxx, TASK-xxx
- **Artifact type:** environment variable / config file / API endpoint / etc.
- **Format constraint:** {What format must the artifact be in for the consumer to use it without modification?}
- **Validation method:** {How should the Coach verify this contract is met?}

⚠️ If any task produces an artifact consumed by another task and no integration
contract is specified, add one. Unspecified cross-task contracts are the #1 source
of integration-boundary bugs.
```

**Planner prompt instruction to add:**

The prompt driving the feature planner must include this instruction:

> Whenever the user request mentions both an infrastructure service AND a consuming framework (e.g. "PostgreSQL with SQLAlchemy async", "Redis with aioredis", "MongoDB with Motor", "MySQL with aiomysql"), you MUST generate an Integration Contract specifying the exact connection URL or interface format required by the consuming framework. The format must be derived from the user's stated framework — do not use a hardcoded lookup table.

**Also add (task-review companion):**

In `installer/core/commands/task-review.md`, at the subtask generation instructions (Step 8 of the Enhanced [I]mplement Flow), add one sentence:

> When creating fix tasks that involve cross-component boundaries (e.g. integration tests, environment variable consumers, API contracts between services), include the expected interface format in the task description.

This is a prompt hint only — no new output sections, no schema changes, no impact on reviews that don't cross component boundaries. It is included here (not in a separate task) because it is a one-line addition and logically part of the same planning-time intervention.

## Acceptance Criteria

- [x] `installer/core/commands/feature-plan.md` contains a mandatory `§4: Integration Contracts` output section with the template above
- [x] The feature planner prompt includes the instruction to derive connection URL formats from the user's stated framework (not a hardcoded lookup)
- [x] `installer/core/commands/task-review.md` subtask generation instructions include the one-sentence cross-component boundary hint
- [x] **Machine-verifiable:** The string `§4: Integration Contracts` appears in `installer/core/commands/feature-plan.md`
- [x] **Machine-verifiable:** The string `cross-component boundaries` appears in `installer/core/commands/task-review.md`
- [x] `/feature-plan` output for a single-technology prompt (no cross-task data dependency) does NOT require an Integration Contracts section

### Manual Verification (post-merge, not automatable by Coach)

- Run `/feature-plan` with the prompt: `"Add MySQL database integration using SQLAlchemy async with aiomysql"` — verify the output contains an Integration Contract specifying `mysql+aiomysql://` format
- Run `/feature-plan` with the prompt: `"Add PostgreSQL database integration using SQLAlchemy async"` — verify the output contains an Integration Contract specifying `postgresql+asyncpg://` format
- In both cases, the format must be derived from the prompt text, not from a hardcoded driver table

## Constraints

- This task is prompt/documentation only — no Python code changes
- Do NOT hardcode any framework-to-URL mappings in the template or prompt — all format specifics must come from the user's stated consumer framework in the prompt
- Do NOT add mandatory output sections to `/task-review` — only a one-sentence hint in the subtask generation instructions
- TASK-IC-DD44 (Child B) must not begin until this task is COMPLETED and verified

## Implementation Notes

- File exists: `installer/core/commands/feature-plan.md` — modify, do not create
- File exists: `installer/core/commands/task-review.md` — add one sentence to the subtask generation instructions in Step 8 of the Enhanced [I]mplement Flow (search for the subtask generation section rather than relying on a specific line number)
- FEAT-FP-002 context: The §4 section in feature-plan already has `integration_points` — this task formalises their required content
- FEAT-DG-001 relationship: Data flow diagrams catch missing connections; integration contracts catch format mismatches at existing connections — these complement each other
- See: `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` §5.1 for the full template rationale
