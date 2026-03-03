---
id: TASK-INST-012
title: Enrich system seeding with actual template markdown content
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-INST-010
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T21:58:05.851344'
  last_updated: '2026-03-02T22:05:25.705375'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T21:58:05.851344'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Enrich System Seeding with Actual Template Markdown Content

## Description

The current system seeding modules (`seed_templates.py`, `seed_agents.py`, `seed_rules.py`) contain hardcoded metadata descriptions of templates, agents, and rules. These are static summaries — they do NOT read the actual rich markdown content from `installer/core/templates/`.

For example, `seed_templates.py` seeds entries like:
```python
("fastapi-python", "FastAPI Python template with clean architecture, SQLAlchemy, Alembic...")
```

But the actual `installer/core/templates/fastapi-python/agents/fastapi-specialist.md` contains detailed, queryable knowledge about FastAPI patterns, routing conventions, dependency injection, testing strategies — none of which enters the knowledge graph.

This task replaces the hardcoded metadata in system seeding with content read from the actual template files, so that `guardkit graphiti seed` (GuardKit's own system knowledge) contains the full richness of template content.

## Context

This is distinct from TASK-INST-011 (which ingests template content during `guardkit init` for a specific project). This task enriches GuardKit's own system knowledge — the seeding that runs via `seed_all_system_context()` / `guardkit graphiti seed`.

### Why Both Are Needed

| Seed Type | When | What | Who Uses |
|-----------|------|------|----------|
| System seeding (this task) | `guardkit graphiti seed` | GuardKit product knowledge (all templates) | GuardKit itself, template recommendations |
| Project seeding (TASK-INST-011) | `guardkit init {template}` | Chosen template content for this project | AutoBuild player/coach for this project |

## Requirements

### 1. Replace Hardcoded Template Metadata

Update `guardkit/knowledge/seed_templates.py`:
- Instead of hardcoded description strings, read actual files from `installer/core/templates/{template}/`
- For each template: read `manifest.json`, list agents, list rules
- Create episodes with actual content (not summary descriptions)

### 2. Replace Hardcoded Agent Metadata

Update `guardkit/knowledge/seed_agents.py`:
- Instead of hardcoded agent descriptions, read actual agent `.md` files from templates
- Parse YAML frontmatter for structured metadata
- Include agent body content (capabilities, technologies, patterns) as episode text
- Skip `-ext.md` files (supplementary content)

### 3. Replace Hardcoded Rule Metadata

Update `guardkit/knowledge/seed_rules.py`:
- Instead of hardcoded rule descriptions, read actual rule `.md` files from templates
- Include full rule content (not just summaries)
- Organise by template for queryability

### 4. Content Chunking

- Agent files under 10KB: single episode with full content
- Agent files over 10KB: use `FullDocParser` chunking strategy (split by ## headers)
- Rule files: typically small, single episode each
- Maintain `group_id` convention: `templates`, `agents`, `rules`

### 5. Version Tracking

- Current seeding uses `SEEDING_VERSION = "1.1.0"` to prevent re-seeding
- Bump seeding version to "1.2.0" to force re-seed when this change lands
- Consider file hash-based change detection for future incremental re-seeding

### 6. Template Discovery

- Scan `installer/core/templates/` for all template directories
- Include templates without `manifest.json` (e.g., `default`) — use directory name as template ID
- Check both `agents/` and `.claude/agents/` for agent files (fastmcp-python uses the latter)
- Handle missing optional files gracefully (template may not have rules, agents may be empty, etc.)
- All 7 templates must be discoverable: default, fastapi-python, fastmcp-python, mcp-typescript, nextjs-fullstack, react-fastapi-monorepo, react-typescript

## Acceptance Criteria

- [ ] `seed_templates.py` reads actual `manifest.json` from each template directory
- [ ] `seed_agents.py` reads actual agent `.md` files from each template
- [ ] `seed_rules.py` reads actual rule `.md` files from each template
- [ ] Agent content includes full body text (not just frontmatter metadata)
- [ ] Rule content includes full text (not just topic headings)
- [ ] Content chunking applied for files over 10KB
- [ ] `SEEDING_VERSION` bumped to "1.2.0"
- [ ] Missing template files handled gracefully (warning, not error)
- [ ] Existing `group_id` conventions maintained
- [ ] Unit tests cover: template discovery, content extraction, chunking, missing files

## File Location

- `guardkit/knowledge/seed_templates.py`
- `guardkit/knowledge/seed_agents.py`
- `guardkit/knowledge/seed_rules.py`
- `guardkit/knowledge/seed_helpers.py` (version bump)

## Test Location

- `tests/knowledge/test_seed_templates.py`
- `tests/knowledge/test_seed_agents.py`
- `tests/knowledge/test_seed_rules.py`
