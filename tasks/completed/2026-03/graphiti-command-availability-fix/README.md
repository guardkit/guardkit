# Feature: Fix Graphiti Availability Detection Across All Commands

**Feature ID**: FEAT-CD64
**Parent Review**: REV-SD-001
**Created**: 2026-03-18

## Problem Statement

8 GuardKit commands (`/system-design`, `/system-arch`, `/system-plan`, `/system-overview`, `/impact-analysis`, `/arch-refine`, `/design-refine`, `/context-switch`) use Python pseudocode in their command spec markdown to check Graphiti availability. Since these commands are executed as LLM prompts (not Python scripts), the LLM cannot import `guardkit.knowledge.graphiti_client` or call `get_graphiti()`. It rationally takes the `else` branch and outputs "Graphiti unavailable" — even when Graphiti is fully configured and operational.

## Solution Approach

Replace Python pseudocode with tool-native instructions the LLM can execute:

1. **Availability check**: Use Read tool to read `.guardkit/graphiti.yaml` and check `enabled: true`
2. **Connectivity check** (optional): Use Bash tool to run `graphiti-check --status --quiet`
3. **Seeding operations**: Use Bash tool to run `guardkit graphiti add-context` CLI commands
4. **Shared preamble**: Create a reusable include for the availability check pattern

## Subtasks

| Task | Title | Wave | Mode | Dependencies |
|------|-------|------|------|--------------|
| TASK-GCA-001 | Create shared Graphiti preamble include | 1 | task-work | None |
| TASK-GCA-002 | Fix /system-design Graphiti availability | 2 | task-work | TASK-GCA-001 |
| TASK-GCA-003 | Fix /system-arch Graphiti availability | 2 | task-work | TASK-GCA-001 |
| TASK-GCA-004 | Fix /system-plan Graphiti availability | 2 | task-work | TASK-GCA-001 |
| TASK-GCA-005 | Fix /system-overview, /impact-analysis, /context-switch | 2 | task-work | TASK-GCA-001 |
| TASK-GCA-006 | Fix /arch-refine and /design-refine | 2 | task-work | TASK-GCA-001 |
| TASK-GCA-007 | Document group ID strategy in graphiti-knowledge.md | 1 | direct | None |

## Execution Strategy

**Wave 1** (parallel): TASK-GCA-001 + TASK-GCA-007
- Create the shared preamble and document group IDs (independent)

**Wave 2** (parallel after Wave 1): TASK-GCA-002 through TASK-GCA-006
- Apply the shared preamble pattern across all 8 commands (independent of each other)
