---
id: TASK-GMR-004
title: "Update /task-work Phase 1.7 to use MCP tools"
status: completed
created: 2026-03-29T12:00:00Z
updated: 2026-03-30T00:00:00Z
completed: 2026-03-30T00:00:00Z
completed_location: tasks/completed/TASK-GMR-004/
previous_state: in_review
state_transition_reason: "All 6 acceptance criteria met - Phase 1.7 MCP-first workflow complete"
priority: high
tags: [graphiti, mcp, task-work, command-spec]
task_type: implementation
parent_review: TASK-REV-85E4
feature_id: FEAT-GMR
implementation_mode: task-work
wave: 2
conductor_workspace: graphiti-mcp-restoration-wave2-1
complexity: 4
depends_on:
  - TASK-GMR-001
  - TASK-GMR-002
  - TASK-GMR-003
---

# Update /task-work Phase 1.7 to Use MCP Tools

## Description

Replace the fragile CLI wrapper integration in Phase 1.7 (`installer/core/commands/task-work.md`) with MCP-first Graphiti queries. The current approach crosses 8 boundaries (Claude → Bash → shell wrapper → Python → FalkorDB → JSON → Bash → Claude). MCP reduces this to 3 (Claude → MCP → FalkorDB).

## Current Phase 1.7 (lines 1691-1826 in task-work.md)

1. Run `graphiti-check --status --quiet` via Bash
2. Parse JSON output
3. If available, run `graphiti-check --task-context --task-id ...` via Bash
4. Parse JSON output again
5. Store in `task_context["graphiti_context"]`
6. Reference in Phase 2 prompt template

## Proposed Phase 1.7

1. Check if `mcp__graphiti__search_nodes` tool is available (native check)
2. If available:
   - Call `mcp__graphiti__search_nodes(query="{task_title} {task_description}", group_ids=["architecture_decisions", "guardkit__project_architecture", "guardkit__task_outcomes"])`
   - Call `mcp__graphiti__search_memory_facts(query="{task_title}", group_ids=["guardkit__project_decisions", "guardkit__task_outcomes"])`
   - Results are native tool outputs in conversation context
3. If MCP not available:
   - Fall back to existing CLI wrapper approach (keep as-is)
4. Use results in Phase 2 planning prompt

## Acceptance Criteria

- [x] AC-1: Phase 1.7 checks for MCP tool availability first
- [x] AC-2: MCP queries use appropriate group_ids (system + project groups from `.claude/rules/graphiti-knowledge-graph.md`)
- [x] AC-3: Query terms derived from task title and description
- [x] AC-4: CLI wrapper preserved as fallback when MCP not available
- [x] AC-5: Phase 2 injection template works with both MCP results and CLI wrapper results
- [x] AC-6: Display message indicates which path was used: "[Graphiti] Context loaded via MCP" or "[Graphiti] Context loaded via CLI"

## Implementation Notes

- This modifies `installer/core/commands/task-work.md` (markdown command spec)
- MCP tool results are natively in the conversation context — no JSON parsing needed
- The Phase 2 prompt template at lines 2460-2467 may need updating to reference MCP results vs the old `task_context.graphiti_context` pattern
- Keep the existing `graphiti_context_loader.py` and `graphiti_check.py` as they serve AutoBuild and CLI usage
