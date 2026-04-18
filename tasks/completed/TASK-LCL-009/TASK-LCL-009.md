---
id: TASK-LCL-009
title: Add patterns/long-running-tools.md rule to base and orchestrator templates
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
state_transition_reason: "Task completed via /task-complete"
completed_location: tasks/completed/TASK-LCL-009/
priority: medium
tags: [templates, docs, les1-polr, long-running]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 3
conductor_workspace: langchain-template-lessons-wave3-2
complexity: 2
---

# Task: Add patterns/long-running-tools.md rule to base and orchestrator templates

## Description

None of the three templates encode LES1 §4's long-running-tool discipline:
fire-and-forget + poll for tools that can exceed 30s, 240s MCP-timeout
awareness, description-matches-implementation contract, latency-class
separation. Any consumer wrapping a template-derived agent behind an MCP
interface will re-hit POLR.

Add a short pattern rule (in base — inherited by weighted-eval via
overlay; vendored into orchestrator) documenting the discipline.

## Acceptance Criteria

- [ ] New `installer/core/templates/langchain-deepagents/.claude/rules/patterns/long-running-tools.md` with sections:
  - Purpose — prevent POLR / MCP 240s timeout class of bugs
  - The 30s threshold rule (from LES1 §4)
  - Fire-and-forget + poll pattern (return `session_id` immediately; expose `_status` / `_cancel` companion)
  - "Description is a contract" rule — if the description says "long-running — session tracked", the implementation MUST be async / return immediately
  - Latency-class separation — don't share one tool shape for sync + generation-loop paths
  - Concrete do/don't code sketches
- [ ] Orchestrator-template copy at `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/long-running-tools.md` — can be identical; document the vendor relationship with a header comment.
- [ ] Weighted-eval specifically: flag `AdversarialOrchestrator.process_target()` retry loop as an accumulated-latency surface (LES1 row 21). Add a NOTE in the pattern rule OR in the weighted-eval CLAUDE.md that consumers wrapping this as an MCP tool must use fire-and-forget.
- [ ] File follows the project's existing `patterns/*.md` frontmatter convention (`paths:` header).

## Files

- `installer/core/templates/langchain-deepagents/.claude/rules/patterns/long-running-tools.md` (new)
- `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/long-running-tools.md` (new)
- Optional: NOTE added to `installer/core/templates/langchain-deepagents-weighted-evaluation/.claude/CLAUDE.md`

## Links

- Review: [TASK-REV-LES1 report §MEDIUM-2](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- LES1 §4 POLR
