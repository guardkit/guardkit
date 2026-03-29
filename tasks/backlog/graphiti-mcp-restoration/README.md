# Feature: Graphiti MCP Restoration

## Problem Statement

Graphiti knowledge graph integration delivers zero practical value in GuardKit's 13 core commands despite fully operational infrastructure (FalkorDB, vLLM, seeded knowledge graph). The MCP server — the correct integration path for Claude Code commands — was deliberately removed from guardkit based on advice that conflated AutoBuild's architecture (Python, doesn't need MCP) with commands' architecture (markdown prompt specs, need MCP).

## Root Cause (from TASK-REV-85E4)

1. MCP was removed from guardkit's `.mcp.json` based on incomplete AI advice
2. Anti-MCP instruction added to task-work.md:1701-1703 explicitly blocks MCP usage
3. Only 1 of 13 commands even attempts the fragile CLI wrapper alternative
4. No automatic write path captures knowledge from task lifecycle events

## Solution

Restore the Graphiti MCP server configuration (proven working in agentic-dataset-factory), reverse the blocking instruction, update command specs to use MCP tools natively, and add write paths for automatic knowledge capture.

## Subtasks

| Wave | Task | Title | Mode | Complexity |
|------|------|-------|------|------------|
| 1 | TASK-GMR-001 | Restore Graphiti MCP configuration | task-work | 2 |
| 1 | TASK-GMR-002 | Reverse anti-MCP instruction in task-work.md | task-work | 2 |
| 1 | TASK-GMR-003 | Verify MCP tools available in Claude Code | direct | 2 |
| 2 | TASK-GMR-004 | Update /task-work Phase 1.7 to use MCP | task-work | 4 |
| 2 | TASK-GMR-005 | Add context loading to /task-review | task-work | 4 |
| 2 | TASK-GMR-006 | Add pre-planning context to /feature-plan | task-work | 4 |
| 3 | TASK-GMR-007 | Add /task-complete write path | task-work | 3 |
| 3 | TASK-GMR-008 | Add /task-review knowledge capture write path | task-work | 3 |
| 4 | TASK-GMR-009 | Add context influence observability markers | task-work | 2 |
| 4 | TASK-GMR-010 | Add MCP query result logging | task-work | 2 |

## Execution Strategy

- **Wave 1** (3 tasks, parallel): Restore MCP, verify it works
- **Wave 2** (3 tasks, parallel): Update highest-value command specs
- **Wave 3** (2 tasks, parallel): Add write paths for learning flywheel
- **Wave 4** (2 tasks, parallel): Observability

## Parent Review

TASK-REV-85E4 — Graphiti Integration Zero Value Review
