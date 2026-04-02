# FEAT-ROT: Register langchain-deepagents-orchestrator as Builtin Template

## Problem

The `langchain-deepagents-orchestrator` template was created via `/template-create` from the `deepagents-orchestrator-exemplar` repo and currently lives at `~/.agentecflow/templates/langchain-deepagents-orchestrator/`. It needs to be registered as a builtin template in the GuardKit installer so that `guardkit init langchain-deepagents-orchestrator` works out of the box.

The template captures the **Pipeline Orchestrator** pattern — an autonomous development pipeline agent using a two-model architecture (reasoning model orchestrates, implementation model executes).

## Solution

1. Fix generic metadata left by `/template-create` (display_name, description, frameworks, hardcoded paths)
2. Fix a broken import in `agents.py.template` (CompiledStateGraph)
3. Copy template to `installer/core/templates/langchain-deepagents-orchestrator/`
4. Update installer help text and documentation listings

**Architecture decision**: Standalone template (no `extends`). The orchestrator pattern is architecturally distinct from the adversarial Player-Coach pattern used by the base `langchain-deepagents` template.

## Subtasks

| Wave | Task | Description | Mode | Status |
|------|------|-------------|------|--------|
| 1 | TASK-ROT-001 | Fix manifest.json metadata | task-work | completed |
| 1 | TASK-ROT-002 | Fix CompiledStateGraph import | task-work | completed |
| 2 | TASK-ROT-003 | Copy template to installer | direct | completed |
| 3 | TASK-ROT-004 | Update init.py help text | direct | completed |
| 3 | TASK-ROT-005 | Update CLAUDE.md and docs | direct | backlog |
| 4 | TASK-ROT-006 | Add config templates (langgraph.json, config YAML, domain) | task-work | backlog |
| 4 | TASK-ROT-007 | Enhance agents with /agent-enhance --hybrid | task-work | backlog |
| 4 | TASK-ROT-008 | Add DeepAgents-specific pattern rules | task-work | backlog |
| 4 | TASK-ROT-009 | Update template .claude/CLAUDE.md content | direct | backlog |

## Review Report

See: [TASK-REV-TI25 Review Report](../../../.claude/reviews/TASK-REV-TI25-review-report.md)
