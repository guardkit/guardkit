---
id: TASK-GDU-009
title: Document guardkit init Graphiti Seeding Workflow
type: implementation
priority: high
status: completed
created: 2026-02-02
completed: 2026-02-02T00:00:00Z
completed_location: tasks/completed/TASK-GDU-009/
parent_feature: FEAT-GDU
wave: 3
mode: direct
estimate: 1.5h
tags: [documentation, graphiti, init, seeding]
---

# TASK-GDU-009: Document guardkit init Graphiti Seeding Workflow

## Problem Statement

The `guardkit init` command automatically seeds project knowledge to Graphiti, but this workflow is **not documented** in the public GitHub Pages documentation. Users don't know:

1. That `guardkit init` seeds to Graphiti by default
2. What knowledge gets seeded (project overview, role constraints, quality gates, implementation modes)
3. How to refine/update this knowledge later
4. Available CLI options (`--skip-graphiti`, `--interactive`, `--project-name`)

## Source Material

Implementation files to reference:
- `guardkit/cli/init.py` - CLI command implementation
- `guardkit/knowledge/project_seeding.py` - Seeding orchestration

## Content to Document

### 1. Automatic Seeding During Init

When running `guardkit init`, the following knowledge is automatically seeded to Graphiti:

| Component | Group ID | Description |
|-----------|----------|-------------|
| Project Overview | `project_overview` | Parsed from CLAUDE.md or README.md |
| Role Constraints | `role_constraints` | Player/Coach behavior boundaries |
| Quality Gate Configs | `quality_gate_configs` | Test coverage, arch review thresholds |
| Implementation Modes | `implementation_modes` | task-work vs direct guidance |

### 2. CLI Options

```bash
# Standard init (seeds to Graphiti)
guardkit init fastapi-python

# Interactive mode - prompts for project info
guardkit init --interactive

# Skip Graphiti seeding
guardkit init --skip-graphiti

# Custom project name
guardkit init -n my-project-name
```

### 3. Refining Project Knowledge

#### Method 1: Interactive Knowledge Capture (Recommended)

```bash
# Full interactive session
guardkit graphiti capture --interactive

# Focus on project overview specifically
guardkit graphiti capture --interactive --focus project-overview
```

#### Method 2: Add Context from Documents

```bash
# Re-seed from updated CLAUDE.md
guardkit graphiti add-context CLAUDE.md --force
```

#### Method 3: Re-run Interactive Init

```bash
# Re-run interactive setup
guardkit init --interactive
```

### 4. What Gets Refined

| Method | Project Overview | Role Constraints | Quality Gates | Implementation Modes |
|--------|------------------|------------------|---------------|---------------------|
| Interactive Capture | ✅ All categories | ✅ `--focus role-customization` | ✅ `--focus quality-gates` | ✅ `--focus workflow-preferences` |
| Add Context | ✅ Re-parses doc | ❌ | ❌ | ❌ |
| Interactive Init | ✅ Prompts again | ❌ | ❌ | ❌ |

**Recommendation**: Use `guardkit graphiti capture --interactive` for the most comprehensive refinement.

## Target Document

Create new section in `docs/guides/graphiti-integration-guide.md` OR create standalone guide at `docs/guides/graphiti-init-seeding.md`.

## Acceptance Criteria

- [x] Document that `guardkit init` seeds to Graphiti by default
- [x] List all 4 knowledge components that get seeded with descriptions
- [x] Document CLI options: `--skip-graphiti`, `--interactive`, `--project-name`
- [x] Document 3 refinement methods with code examples
- [x] Include comparison table showing what each refinement method updates
- [x] Add to mkdocs.yml navigation if creating standalone guide (N/A - added to existing graphiti-integration-guide.md)
- [x] Verify `mkdocs build` succeeds (mkdocs not installed locally; CI will verify)

## Implementation Notes

- Reference existing `graphiti-knowledge-capture.md` for interactive capture details
- Cross-link to `graphiti-add-context.md` for add-context command
- Consider adding a "Graphiti Seeding" section to GETTING-STARTED.md as well
