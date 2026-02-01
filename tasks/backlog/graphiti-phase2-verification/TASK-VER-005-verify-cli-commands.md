---
id: TASK-VER-005
title: Verify CLI Commands for GR-005 Features
status: backlog
created: 2026-02-01T20:00:00Z
updated: 2026-02-01T20:00:00Z
priority: medium
complexity: 3
implementation_mode: direct
wave: 2
parallel_group: wave2
parent_review: TASK-REV-0F4A
feature_id: FEAT-VER-0F4A
tags: [verification, testing, cli, graphiti]
estimated_minutes: 45
dependencies:
  - TASK-VER-004
---

# Task: Verify CLI Commands for GR-005 Features

## Description

Manually verify the new CLI commands added in GR-005 (Knowledge Query Commands) work correctly with live data.

## Prerequisites

- Neo4j running with seeded data
- Tier 2 tests passing

## Acceptance Criteria

- [ ] `guardkit graphiti show` displays knowledge correctly
- [ ] `guardkit graphiti search` returns relevant results
- [ ] `guardkit graphiti list` shows all categories
- [ ] `guardkit graphiti status` shows accurate counts
- [ ] Output formatting is correct (Rich console)
- [ ] Error handling works for invalid inputs

## Commands to Verify

### 1. Status Command
```bash
guardkit graphiti status --verbose
```

**Expected**: Shows enabled status, seeding state, group counts

### 2. Search Command
```bash
# Basic search
guardkit graphiti search "feature-plan" --limit 5

# Search with category filter
guardkit graphiti search "quality gate" --category quality_gate_phases
```

**Expected**: Returns relevant results with relevance scores

### 3. Show Command
```bash
# Show by feature ID
guardkit graphiti show FEAT-GR-003

# Show by entity name
guardkit graphiti show "GuardKit"
```

**Expected**: Displays entity details in formatted output

### 4. List Command
```bash
# List all features
guardkit graphiti list features

# List patterns
guardkit graphiti list patterns

# List with limit
guardkit graphiti list features --limit 10
```

**Expected**: Shows categorized list with metadata

### 5. Error Handling
```bash
# Invalid ID
guardkit graphiti show INVALID-ID

# Empty search
guardkit graphiti search ""

# Invalid category
guardkit graphiti list invalid_category
```

**Expected**: User-friendly error messages, no stack traces

## Verification Checklist

| Command | Works | Output Format | Error Handling |
|---------|-------|---------------|----------------|
| status | [ ] | [ ] | [ ] |
| search | [ ] | [ ] | [ ] |
| show | [ ] | [ ] | [ ] |
| list | [ ] | [ ] | [ ] |

## Documentation

Record any issues found and document in verification report.

## References

- GR-005 Tasks: `tasks/backlog/graphiti-refinement-phase2/TASK-GR5-*.md`
- CLI Implementation: `.guardkit/worktrees/FEAT-0F4A/guardkit/cli/graphiti_query_commands.py`
