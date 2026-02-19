---
id: TASK-REV-9705
title: Review and decompose TASK-FP-1B6D into child tasks
status: review_complete
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: high
task_type: review
parent_review: TASK-REV-0E07
complexity: 2
dependencies: []
related_tasks:
  - TASK-FP-1B6D   # The task under review (now superseded)
  - TASK-IC-6F94   # Child A — output of this review
  - TASK-IC-DD44   # Child B — output of this review
  - TASK-IC-B4E6   # Child C — output of this review
  - TASK-REV-DAC9  # task-review boundary hint (companion, already created)
tags: [task-review, decomposition, integration-contracts, autobuild]
---

# Review: Decompose TASK-FP-1B6D into Child Tasks

## Review Summary

TASK-FP-1B6D ("Add Integration Contracts to feature-plan to prevent cross-task format mismatches") was reviewed and found to be well-analysed but incorrectly scoped for a single AutoBuild session.

## Review Findings

### Finding 1: Complexity score too low

TASK-FP-1B6D was rated complexity 6. It contains four distinct changes across different parts of the system — prompt templates, task metadata schema, a seam test generator, and a docker_fixtures refactor. Changes 2 and 3 touch the Coach validator and may introduce a new Python module. The true complexity is 7-8 given the cross-cutting nature.

### Finding 2: Violates single-deliverable principle

The task contains an internal dependency ("Change 1 MUST be done first") — which is the definition of a task that should be split. A Player taking this on in AutoBuild would attempt all four changes in one session, and the Coach would need to validate four heterogeneous deliverables with different verification methods (prompt output, YAML schema, Python module, fixtures behaviour).

### Finding 3: /task-review gap not addressed

TASK-FP-1B6D made no mention of the /task-review edge case (when it spawns fix tasks involving cross-component boundaries). This has been addressed by adding a one-line note to Child A (TASK-IC-6F94) rather than a separate task, as it is a prompt-only one-sentence addition.

### Finding 4: Technology-agnosticism acceptance criteria too vague

"Works for at least PostgreSQL+asyncpg, MySQL+aiomysql" is not a testable criterion. Replaced with concrete test method: generate feature plans for specific prompts and verify the output contracts specify the correct dialect (derived from the prompt, not from a hardcoded table).

### Finding 5: Factual check — feature-plan.md file exists

The review raised a concern that `installer/core/commands/feature-plan.md` might not exist yet. Verified: the file exists at that path. All child tasks correctly say "modify" not "create."

## Decision: [I]mplement — Decompose into Three Child Tasks

TASK-FP-1B6D is marked as **superseded** and must not be worked on. The work is decomposed into:

| Task | Title | Complexity | Depends On |
|------|-------|-----------|------------|
| TASK-IC-6F94 | Add Integration Contracts section to feature-plan prompt template | 3 | — |
| TASK-IC-DD44 | Add consumer_context metadata and seam test stub generation | 5 | TASK-IC-6F94 |
| TASK-IC-B4E6 | Refactor docker_fixtures.py to consumer-aware URL generation | 4 | TASK-IC-DD44 |

Execution order is strictly sequential — each child task depends on the previous being COMPLETED and verified.

TASK-REV-DAC9 (task-review boundary hint, created separately) covers the /task-review edge case and can be worked on independently or alongside TASK-IC-6F94.

## Action: Mark TASK-FP-1B6D Superseded

The original TASK-FP-1B6D file should be updated with `status: obsolete` and a note pointing to the child tasks. The child tasks carry forward all valid content from the original — analysis chain, constraints, reference documentation.
