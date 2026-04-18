---
id: TASK-LCL-005
title: Add AGENTS.md.template with TASK-REV-R2A1 ainvoke contract to orchestrator template
status: completed
created: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
priority: high
tags: [templates, langchain-deepagents-orchestrator, ainvoke-contract, les1-doc-code-co-evolution]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 2
conductor_workspace: langchain-template-lessons-wave2-2
complexity: 2
completed_location: tasks/completed/TASK-LCL-005/
---

# Task: Add AGENTS.md.template with TASK-REV-R2A1 ainvoke contract to orchestrator template

## Description

The orchestrator template calls `create_deep_agent(..., memory=["./AGENTS.md"])`
but ships **no** `AGENTS.md.template`. Any consumer who writes a retry /
feedback mechanism on top of this template will re-invent the dual-
system-messages-crashes-vLLM failure that TASK-REV-R2A1 documented.

Port the base template's `AGENTS.md.template` §"Framework Contract:
ainvoke() Message Rules (TASK-REV-R2A1)" section into a new
orchestrator-specific `AGENTS.md.template` tuned to the orchestrator /
subagent structure.

## Evidence

- Base `installer/core/templates/langchain-deepagents/templates/other/other/AGENTS.md.template` lines 10-22 contain the canonical R2A1 contract wording.
- Orchestrator's `agents.py.template:182` passes `memory=["./AGENTS.md"]` but no `AGENTS.md.template` is rendered.

## Acceptance Criteria

- [ ] New file `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/AGENTS.md.template`.
- [ ] Includes a §"Framework Contract: ainvoke() Message Rules (TASK-REV-R2A1)" section lifted from the base template (keep wording identical where it generalises).
- [ ] Adds orchestrator-specific role sections: Orchestrator (reasoning + coordination), Implementer (execution with tools), Evaluator (zero-tools evaluation), Builder (async remote execution) — each with ALWAYS / NEVER / ASK bullets that reflect the actual responsibilities in `agents.py.template`.
- [ ] "Evaluator" section's NEVER list includes: "Write to output files — the Evaluator evaluates only. If you find yourself with filesystem tools available, that is a template bug — raise the issue instead of using them."
- [ ] File is referenced correctly by the existing `memory=["./AGENTS.md"]` call (no path change needed — just file creation).

## Files

- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/AGENTS.md.template` (new)

## Implementation Notes

- Reuse the base template's wording for the R2A1 framework contract to keep
  the "canonical" phrasing consistent across the template family.
- The Evaluator NEVER rule above is a *defence-in-depth* stopgap ahead of
  TASK-LCL-007's factory-level assertion.

## Links

- Review: [TASK-REV-LES1 report §HIGH-2](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- Base AGENTS.md.template §"Framework Contract" for reference wording
