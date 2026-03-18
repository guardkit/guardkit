---
id: TASK-REV-C166
title: Investigate Graphiti integration for Claude Code sessions in GuardKit repos
status: review_complete
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T00:00:00Z
priority: high
tags: [graphiti, claude-code, mcp, knowledge-graph, cross-project]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 4
review_results:
  mode: architectural
  depth: standard
  findings_count: 6
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-C166-review-report.md
  completed_at: 2026-03-18T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate Graphiti integration for Claude Code sessions in GuardKit repos

## Description

Review how Graphiti was set up in the **agentic-dataset-factory** project to work with Claude Code sessions, and investigate what's needed to enable the same capability across all repos that use GuardKit.

The agentic-dataset-factory has a working Graphiti + Claude Code integration. The goal is to understand that setup and determine how to replicate/generalize it for any GuardKit-enabled project.

## Reference Implementation (agentic-dataset-factory)

Key files to review in the agentic-dataset-factory repo:
- `/.claude/CLAUDE.md` - How Graphiti is referenced in project instructions
- `.claude/rules/graphiti-knowledge-graph.md` - Graphiti knowledge graph rules
- `docs/reviews/graphiti-setup/graphiti-mcp-claude-code-setup.md` - MCP setup for Claude Code

## Current State in GuardKit

GuardKit currently uses Graphiti via a **Python client library** (NOT MCP):
- Access: `guardkit.knowledge` Python client → FalkorDB
- Config: `.guardkit/graphiti.yaml` (FalkorDB at whitestocks:6379)
- LLM: vLLM on promaxgb10-41b1:8000 (Qwen2.5-14B-Instruct-FP8)
- Embeddings: vLLM on promaxgb10-41b1:8001 (nomic-embed-text-v1.5)

## Key Questions to Investigate

1. **MCP vs Python Client**: The agentic-dataset-factory uses Graphiti MCP server with Claude Code. GuardKit uses a Python client. Should GuardKit also expose Graphiti via MCP for Claude Code sessions?

2. **Session-Level Knowledge**: How does the agentic-dataset-factory capture and retrieve knowledge within Claude Code sessions? What hooks or rules trigger knowledge capture?

3. **Project Isolation**: Both projects share FalkorDB on whitestocks. How is project isolation maintained? Does `project_id` namespacing work correctly across MCP and Python client access?

4. **Configuration Portability**: What configuration is needed in each repo's `.claude/` directory to enable Claude Code to use Graphiti? Can this be templated via `guardkit init`?

5. **LLM/Embedding Compatibility**: Both projects should use the same embedding model to share vector indices. Is there a risk of dimension mismatch when one uses MCP and the other uses the Python client?

6. **Installer Integration**: Should `guardkit init` set up the Claude Code MCP configuration for Graphiti automatically? What does this look like in practice?

## Acceptance Criteria

- [ ] Document how Graphiti works in agentic-dataset-factory Claude Code sessions
- [ ] Compare MCP approach vs Python client approach for Claude Code integration
- [ ] Identify configuration requirements for enabling Graphiti in Claude Code sessions
- [ ] Assess project isolation when multiple repos share FalkorDB
- [ ] Recommend approach for generalizing this to all GuardKit repos
- [ ] Identify any blockers or prerequisites (infrastructure, configuration, etc.)

## Implementation Notes

This is a review/analysis task. The output should be a findings report with recommendations, not code changes. If implementation is needed, separate tasks should be created from the recommendations.
