---
id: TASK-GI-DOC-001
title: Write Graphiti Integration Guide
status: backlog
created: 2026-01-29T11:00:00Z
updated: 2026-01-29T11:00:00Z
priority: high
tags: [documentation, graphiti, user-guide, github-pages]
complexity: 4
feature_id: FEAT-GI-DOC
parent_review: TASK-GI-DOC
implementation_mode: direct
wave: 1
parallel_group: wave1-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Write Graphiti Integration Guide

## Description

Create the main user-facing guide for Graphiti Integration at `docs/guides/graphiti-integration-guide.md`. This is the entry point for users wanting to understand and enable persistent memory features.

## Requirements

### Content Structure

1. **Overview Section**
   - What is Graphiti Integration?
   - One-paragraph explanation of temporal knowledge graphs
   - Value proposition: persistent memory across sessions

2. **Problem Statement**
   - Sessions losing context
   - Repeated mistakes
   - Architectural decisions forgotten
   - Adapt from `docs/research/knowledge-graph-mcp/feature-build-crisis-memory-analysis.md`

3. **Quick Start (5-Minute Setup)**
   - Prerequisites checklist
   - Docker command to start services
   - Environment variable for OpenAI key
   - Seed command
   - Verify command

4. **Core Concepts**
   - Knowledge Categories table (group_ids with descriptions)
   - How context loading works (3-step flow)
   - ADR lifecycle overview

5. **Using with GuardKit Commands**
   - /task-work integration
   - /feature-build integration
   - What context is automatically loaded

6. **Configuration**
   - Example `.guardkit/graphiti.yaml`
   - Environment variable overrides

7. **FAQ**
   - "Do I need Graphiti?" (No, graceful degradation)
   - "What if Docker unavailable?" (Commands still work)
   - "How much does OpenAI cost?" (<$1/month)

### Source Materials

- `docs/research/knowledge-graph-mcp/feature-build-crisis-memory-analysis.md` - Problem statement
- `docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md` - Knowledge categories
- `.guardkit/graphiti.yaml` - Configuration example
- `guardkit/cli/graphiti.py` - CLI command examples
- `.claude/reviews/TASK-GI-DOC-review-report.md` - Outline

### Style Guidelines

- Target audience: GuardKit users (not contributors)
- Accessible language, avoid jargon
- Include code blocks for all commands
- Use tables for structured data
- Keep to ~400 lines

## Acceptance Criteria

- [ ] File created at `docs/guides/graphiti-integration-guide.md`
- [ ] All 7 sections from outline included
- [ ] Quick Start is copy-paste ready
- [ ] Knowledge categories table complete
- [ ] FAQ addresses common concerns
- [ ] Links to setup and architecture docs included
- [ ] Markdown renders correctly (no broken formatting)

## Implementation Notes

This is a documentation task - no code changes required. Content should be adapted from existing research documents, not invented.

**Note**: If FEAT-GE (Graphiti Enhancements) has been implemented before this task runs, include any new knowledge categories or capabilities it adds (e.g., Feature Overview entities, Turn State episodes, Role Constraint facts). Check `guardkit/knowledge/` for the current implementation state.

## Test Requirements

- [ ] Markdown lints without errors
- [ ] All internal links valid
- [ ] Code examples are syntactically correct
