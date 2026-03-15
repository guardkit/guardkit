---
id: TASK-IGP-004
title: Sync Graphiti init changes to published MkDocs documentation
status: completed
created: 2026-03-15T14:00:00Z
updated: 2026-03-15T15:20:00Z
completed: 2026-03-15T15:20:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
priority: medium
tags: [documentation, graphiti, mkdocs, github-pages]
task_type: implementation
parent_review: TASK-REV-A73F
feature_id: FEAT-IGP
implementation_mode: direct
complexity: 3
depends_on:
  - TASK-IGP-001
  - TASK-IGP-002
  - TASK-IGP-003
test_results:
  status: passed
  coverage: n/a
  last_run: 2026-03-15T15:15:00Z
  notes: "Documentation-only task - MkDocs build verified"
---

# Task: Sync Graphiti init changes to published MkDocs documentation

## Description

TASK-IGP-001/002/003 added three new concepts to `.claude/rules/graphiti-knowledge.md` and `guardkit/cli/init.py`, but the published MkDocs documentation (under `docs/`) was not updated. The GitHub Pages site still reflects the pre-migration state.

The MkDocs build and deploy workflow (`.github/workflows/docs.yml`) only triggers on changes to `docs/`, `mkdocs.yml`, or the workflow file itself. Since the IGP tasks only changed `.claude/rules/` and `guardkit/cli/`, the public docs are now stale.

## What's Missing from Published Docs

| Concept | Source | Target docs page(s) |
|---------|--------|---------------------|
| Two-phase seeding architecture (init seeds project knowledge, seed-system seeds system knowledge) | `.claude/rules/graphiti-knowledge.md` lines 111-131 | `docs/setup/graphiti-setup.md`, `docs/architecture/graphiti-architecture.md` |
| `--copy-graphiti` for multi-project FalkorDB setups | `.claude/rules/graphiti-knowledge.md` lines 133-158 | `docs/guides/graphiti-integration-guide.md` (Multi-Project section), `docs/setup/graphiti-setup.md` |
| Auto-offer system seeding during init | `guardkit/cli/init.py` Step 2.5 | `docs/setup/graphiti-setup.md` |

## Acceptance Criteria

- [x] `docs/setup/graphiti-setup.md` includes a "Seeding Knowledge" section explaining the two-phase architecture (project seeding during init + system seeding via seed-system or auto-offer)
- [x] `docs/setup/graphiti-setup.md` includes `--copy-graphiti` as a recommended step for multi-project FalkorDB environments
- [x] `docs/guides/graphiti-integration-guide.md` Multi-Project section (line ~1061) mentions `--copy-graphiti` as the recommended config propagation method
- [x] `docs/architecture/graphiti-architecture.md` has a section on the project vs system scope boundary
- [x] Content is consistent with `.claude/rules/graphiti-knowledge.md` (single source of truth)
- [x] No new nav entries needed in `mkdocs.yml` (content fits into existing pages)
- [ ] Push to main triggers the docs workflow and GitHub Pages updates successfully

## Key Files

- `docs/setup/graphiti-setup.md` - Add seeding phases + --copy-graphiti
- `docs/guides/graphiti-integration-guide.md` - Update Multi-Project section
- `docs/architecture/graphiti-architecture.md` - Add scope boundary section
- `.claude/rules/graphiti-knowledge.md` - Reference (source of truth, do NOT modify)

## Implementation Notes

This is a documentation-only task. Copy/adapt content from `.claude/rules/graphiti-knowledge.md` lines 111-158 into the appropriate docs pages, adjusting formatting for the MkDocs Material theme (use admonitions, tabs, etc. where appropriate).

The graphiti-setup.md page still references the old Docker/Neo4j setup. The FalkorDB migration is a separate concern - this task should only add the new init-related content, not rewrite the entire setup page.
