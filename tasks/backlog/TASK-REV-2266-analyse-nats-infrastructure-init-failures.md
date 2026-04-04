---
id: TASK-REV-2266
title: Analyse nats-infrastructure init failures
status: review_complete
created: 2026-04-04T12:00:00Z
updated: 2026-04-04T12:00:00Z
priority: high
tags: [nats, init, graphiti, template-sync, review]
task_type: review
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 68
  findings_count: 5
  recommendations_count: 5
  decision: fix_data
  report_path: .claude/reviews/TASK-REV-2266-review-report.md
  completed_at: 2026-04-04T14:00:00Z
---

# Task: Analyse nats-infrastructure init failures

## Description

Analyse failures observed during `guardkit init nats-asyncio-service` on the nats-infrastructure project. The Graphiti LLM was running locally on MacBook Pro (GB10 unavailable — busy creating a training dataset), which likely contributed to timeout and quality issues.

## Review Input

Log file: `docs/reviews/nats-infrastructure/init-project-1.md`

## Observed Issues

### 1. Agent Episode Timeout (CRITICAL)
- **Agent**: `faststream-nats-broker-specialist`
- **Error**: Episode creation timed out after 240s
- **Impact**: Agent knowledge not seeded into Graphiti graph
- **Log**: `WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 240s`

### 2. LLM Invalid Duplicate Facts (WARNING)
- **Error**: `LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)`
- **Occurrences**: 4 times during edge operations
- **Source**: `graphiti_core.utils.maintenance.edge_operations`
- **Impact**: Potential data quality issues in knowledge graph edges

### 3. Agent Frontmatter YAML Parse Failures (WARNING)
- **Error**: `Failed to parse agent frontmatter` — YAML expects block end but found comma
- **Occurrences**: 4 rules affected:
  1. Rule with `paths: "**/app.py", "**/handlers/*.py", "**/config.py"`
  2. Rule with `paths: "**/handlers/*.py", "**/services/*.py", "**/app.py"`
  3. Rule with `paths: "**/config.py", "**/.env*", "**/docker-compose..."`
  4. Rule with `paths: "**/tests/conftest.py", "**/tests/*.py"`
- **Root cause**: Comma-separated glob paths in YAML frontmatter not quoted as a list
- **Impact**: Rules synced to Graphiti without proper path metadata

### 4. Episode Processing Times (PERFORMANCE)
- Episodes ranged from ~69s to ~191s each
- Total init time heavily dominated by Graphiti seeding
- Local LLM (MacBook Pro) significantly slower than GB10 vLLM endpoint

## Acceptance Criteria

- [ ] Categorise each failure by severity and root cause
- [ ] Determine which failures are caused by local LLM performance vs code bugs
- [ ] Identify the YAML frontmatter parsing bug in template sync code
- [ ] Assess whether the 240s timeout is appropriate for local LLM scenarios
- [ ] Recommend fixes with priority ordering
- [ ] Determine if the `duplicate_facts` warnings indicate an upstream graphiti-core issue or a local LLM quality issue

## Review Scope

1. **Timeout analysis**: Is the 240s timeout configurable? Should it adapt to LLM backend?
2. **YAML parsing**: Trace the frontmatter parser to find why comma-separated paths fail
3. **LLM quality**: Are the `duplicate_facts` warnings caused by weaker local LLM reasoning?
4. **Performance baseline**: Document expected times for local vs GB10 LLM backends
5. **Idempotency**: The init correctly skipped existing files — verify this is fully robust

## Context

- **Environment**: MacBook Pro running local LLM (Graphiti extraction)
- **Normal backend**: vLLM on GB10 (Qwen2.5-14B) — unavailable during this init
- **Template**: nats-asyncio-service
- **Target project**: nats-infrastructure (re-init, most files already existed)

## Implementation Notes

[Space for review findings]

## Test Execution Log

[Automatically populated by /task-review]
