---
id: TASK-REV-A8C2
title: Analyse nats-core init project failures
status: review_complete
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
priority: high
tags: [graphiti, init, nats-core, configuration, review]
task_type: review
review_mode: decision
review_depth: standard
complexity: 3
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 3
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-A8C2-review-report.md
  completed_at: 2026-04-03T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse nats-core init project failures

## Description

Analyse the failures captured in `docs/reviews/nats-core/init-project-1.md` from running `guardkit init python-library` on the nats-core project. Two categories of failure need investigation:

### Failure Category 1: LLM Connection Errors (Graphiti System Seeding)

During Step 3 (system knowledge seeding), all LLM calls fail with "Connection error" after retries. The OpenAI-compatible client retries twice then fails, Graphiti retries 3 times with backoff, then disables itself entirely. This causes:
- Template sync partially fails (template synced but 0 agents, 0 rules)
- Agent sync fails: `python-testing-specialist`, `python-library-specialist`
- Rule sync fails: `code-style`, `testing`, `model`, `validator`, `factory`, and agent rule chunks
- Role constraints: 0 seeded
- Implementation modes: 0 seeded

**Hypothesis**: The CLI/shell Graphiti config (`.guardkit/graphiti.yaml`) still points the LLM at `promaxgb10-41b1:8000` (GB10), which is currently busy generating a training set. The MCP server in Claude Code was reconfigured to use the MacBook Pro LLM, which is why Graphiti works via MCP but fails from the CLI.

**Investigation needed**:
- Confirm the `.guardkit/graphiti.yaml` LLM endpoint in the nats-core project
- Compare with the working MCP config (`.mcp.json`)
- Determine if the fix is simply updating the `graphiti.yaml` LLM endpoint
- Consider whether `guardkit init` should detect LLM unreachability faster and provide a clearer error message

### Failure Category 2: YAML Frontmatter Parsing Errors

Two rules fail with YAML parsing errors before even reaching the LLM:
```
Failed to parse agent frontmatter: while scanning an alias
  paths: **/*.py
         ^
expected alphabetic or numeric character, but found '*'
```

This affects rules with glob patterns in their frontmatter (`paths: **/*.py`, `paths: **/*.test.*`). The YAML parser interprets `*` as an alias indicator.

**Investigation needed**:
- Identify which rule files contain unquoted glob patterns in frontmatter
- Determine if the glob values should be quoted in the source files
- Or if the `template_sync` YAML parser needs to handle this edge case
- Check if this is a pre-existing bug or specific to the python-library template

## Acceptance Criteria

- [ ] Root cause confirmed for LLM connection errors (config mismatch vs other)
- [ ] All rule files with unquoted glob patterns identified
- [ ] Fix approach recommended for both failure categories
- [ ] Determine if `guardkit init` needs better error handling for LLM unavailability
- [ ] Determine if YAML parsing in template_sync needs hardening

## Review Artifacts

- Primary: `docs/reviews/nats-core/init-project-1.md`
- Config: `.guardkit/graphiti.yaml` (nats-core project)
- Config: `.mcp.json` (Claude Code MCP config)
- Code: `guardkit/knowledge/template_sync.py` (YAML parsing)
- Code: `guardkit/knowledge/graphiti_client.py` (retry/connection logic)

## Context

- Graphiti MCP works correctly in Claude Code (reconfigured to MacBook Pro LLM)
- GB10 (`promaxgb10-41b1:8000`) is currently occupied generating a training set
- The CLI graphiti config was copied from agentic-dataset-factory project during init
- Step 2 (project knowledge seeding) succeeded — only Step 3 (system seeding) failed
