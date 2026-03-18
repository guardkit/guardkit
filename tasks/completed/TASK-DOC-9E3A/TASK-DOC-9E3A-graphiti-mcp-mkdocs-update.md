---
id: TASK-DOC-9E3A
title: Update MkDocs documentation for Graphiti MCP Claude Code integration
status: completed
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T13:30:00Z
completed: 2026-03-18T13:30:00Z
priority: medium
tags: [documentation, mkdocs, graphiti, mcp, claude-code]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
task_type: documentation
complexity: 4
depends_on:
  - TASK-GCI-001
  - TASK-GCI-002
  - TASK-GCI-004
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update MkDocs documentation for Graphiti MCP Claude Code integration

## Description

Update the GitHub Pages / MkDocs documentation site to cover the new Graphiti MCP + Claude Code integration being implemented in the `tasks/backlog/graphiti-claude-code-integration/` feature tasks (FEAT-GCI). This includes new pages, updates to existing pages, and nav structure changes.

## Context

The FEAT-GCI feature adds the ability for Claude Code sessions to access the Graphiti knowledge graph via MCP, complementing the existing Python client CLI access. The MkDocs site already has a "Knowledge Graph" section and a "Deep Dives > MCP Integration" section that need updating.

### Reference

- Review report: `.claude/reviews/TASK-REV-C166-review-report.md`
- Feature tasks: `tasks/backlog/graphiti-claude-code-integration/`
- Current MkDocs nav: `mkdocs.yml` (Knowledge Graph section, lines 115-132)
- MCP Integration section: `mkdocs.yml` (lines 110-113)

## Deliverables

### 1. New Page: Claude Code Integration Guide

**Path**: `docs/guides/graphiti-claude-code-integration.md`

Content to cover:
- Overview of dual-access architecture (MCP for Claude Code, Python client for CLI)
- Infrastructure topology diagram (from review report Appendix B)
- Setup instructions (`guardkit init --with-mcp`)
- Configuration files explained (`.mcp.json`, MCP server config, `.guardkit/graphiti.yaml`)
- Project isolation with shared FalkorDB (group ID namespacing)
- How Claude Code searches and adds knowledge via MCP tools
- Troubleshooting: MCP server won't start, group ID mismatch, embedding dimension issues

### 2. New Page: Shared Infrastructure Guide

**Path**: `docs/guides/graphiti-shared-infrastructure.md` (already exists — update it)

Add/update content for:
- Multi-project setup with `--copy-graphiti`
- MCP server sharing across projects
- Group ID isolation between MCP and Python client access
- Embedding dimension alignment requirements

### 3. Update Existing Pages

**`docs/guides/graphiti-integration-guide.md`** (Knowledge Graph overview):
- Add section on Claude Code MCP access as a complementary method
- Reference new Claude Code integration guide
- Update architecture diagram to show both access paths

**`docs/setup/graphiti-setup.md`**:
- Add `guardkit init --with-mcp` flag documentation
- Add `.mcp.json` configuration section
- Add MCP server prerequisites (uv, graphiti repo)

**`docs/guides/graphiti-project-namespaces.md`**:
- Document group ID behaviour differences between MCP and Python client
- Explain isolation gap and how it's resolved

### 4. Update MkDocs Navigation

Update `mkdocs.yml` nav to add new pages:

```yaml
- Knowledge Graph:
    - Overview: guides/graphiti-integration-guide.md
    - Setup: setup/graphiti-setup.md
    - Architecture: architecture/graphiti-architecture.md
    - Claude Code Integration: guides/graphiti-claude-code-integration.md  # NEW
    - Commands:
        - CLI Reference: guides/graphiti-commands.md
        - Add Context: guides/graphiti-add-context.md
        - Query Commands: guides/graphiti-query-commands.md
    - Features:
        - Interactive Capture: guides/graphiti-knowledge-capture.md
        - Job-Specific Context: guides/graphiti-job-context.md
        - Project Namespaces: guides/graphiti-project-namespaces.md
        - Shared Infrastructure: guides/graphiti-shared-infrastructure.md  # NEW/UPDATED
    - Reference:
        # ... existing items ...
```

Also add to MCP Integration deep dive:

```yaml
- MCP Integration:
    - Context7 Setup: deep-dives/mcp-integration/context7-setup.md
    - Design Patterns Setup: deep-dives/mcp-integration/design-patterns-setup.md
    - Graphiti MCP Setup: deep-dives/mcp-integration/graphiti-mcp-setup.md  # NEW
    - MCP Optimization: deep-dives/mcp-integration/mcp-optimization.md
```

### 5. New Page: Graphiti MCP Deep Dive

**Path**: `docs/deep-dives/mcp-integration/graphiti-mcp-setup.md`

Technical deep dive covering:
- MCP server architecture and configuration
- Per-project config generation
- `.mcp.json` schema reference
- MCP server config YAML schema reference
- Environment variables
- How MCP server connects to FalkorDB and vLLM
- Comparison with Python client internals

## Acceptance Criteria

- [x] New Claude Code integration guide created at `docs/guides/graphiti-claude-code-integration.md`
- [x] New MCP deep dive created at `docs/deep-dives/mcp-integration/graphiti-mcp-setup.md`
- [x] Existing integration guide updated with MCP access method
- [x] Setup guide updated with MCP `.mcp.json` configuration section
- [x] Project namespaces guide updated with MCP isolation details
- [x] Shared infrastructure guide updated for MCP (full rewrite from stub)
- [x] `mkdocs.yml` nav updated with new pages
- [x] `mkdocs build` succeeds (no new warnings introduced)
- [x] All internal cross-references resolve correctly

## Implementation Notes

- This task depends on TASK-GCI-001, GCI-002, and GCI-004 being completed first (or at least designed), since the docs need to reflect the actual implementation
- Use the infrastructure topology diagram from the review report (Appendix B of TASK-REV-C166)
- Follow the existing documentation style and structure in the MkDocs site
- Ensure Mermaid diagrams render correctly (MkDocs has superfences + mermaid configured)
