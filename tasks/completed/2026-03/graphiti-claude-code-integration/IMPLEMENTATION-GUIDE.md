# Implementation Guide: Graphiti Claude Code Integration

**Feature ID**: FEAT-GCI
**Parent Review**: [TASK-REV-C166 Review Report](../../../.claude/reviews/TASK-REV-C166-review-report.md)

## Execution Strategy

### Wave 1: Core Configuration (3 tasks, parallel)

Tasks GCI-001, GCI-002, and GCI-005 can execute in parallel — they touch different files with no conflicts.

| Task | Method | Workspace |
|------|--------|-----------|
| TASK-GCI-001 | task-work | graphiti-claude-code-wave1-init |
| TASK-GCI-002 | task-work | graphiti-claude-code-wave1-isolation |
| TASK-GCI-005 | direct | graphiti-claude-code-wave1-template |

**Start with**:
```bash
/task-work TASK-GCI-001
/task-work TASK-GCI-002
```
TASK-GCI-005 is simple enough for direct implementation.

### Wave 2: Alignment and Documentation (2 tasks, parallel)

After Wave 1 completes, Wave 2 tasks can run in parallel.

| Task | Method | Workspace |
|------|--------|-----------|
| TASK-GCI-003 | task-work | graphiti-claude-code-wave2-dimensions |
| TASK-GCI-004 | direct | graphiti-claude-code-wave2-docs |

## Key Design Decisions

1. **MCP config is opt-in** (`--with-mcp` flag) — not all environments have the Graphiti MCP server installed
2. **Per-project MCP server configs** — ensures group ID isolation when multiple projects share FalkorDB
3. **Merge, don't overwrite** `.mcp.json` — projects may have other MCP servers configured
4. **Explicit embedding dimensions** — prevents silent vector search corruption

## Reference Files

| File | Project | Purpose |
|------|---------|---------|
| `.mcp.json` | agentic-dataset-factory | Working MCP config example |
| `config-guardkit.yaml` | graphiti repo | MCP server config example |
| `.claude/rules/graphiti-knowledge-graph.md` | agentic-dataset-factory | Rules file example |
| `guardkit/knowledge/graphiti_client.py` | guardkit | Python client (group ID prefixing) |
| `guardkit/knowledge/config.py` | guardkit | Config schema |

## Verification

After all tasks complete:
1. Run `guardkit init --with-mcp` in a test project
2. Verify `.mcp.json` is generated correctly
3. Open project in VS Code with Claude Code
4. Verify `mcp__graphiti__search_nodes` tool is available
5. Search for knowledge and confirm results match Python client queries
