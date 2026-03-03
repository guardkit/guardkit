---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-03-02T13:41:58.239972'
  max_turns: 30
  started_at: '2026-03-02T13:36:04.697497'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-03-02T13:36:04.697497'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
complexity: 3
dependencies:
- TASK-INST-010
feature_id: FEAT-INST
id: TASK-INST-011
implementation_mode: task-work
parent_review: TASK-REV-2FE2
status: design_approved
task_type: integration
title: Wire sync_template_to_graphiti into guardkit init pipeline
wave: 1
---

# Task: Wire sync_template_to_graphiti into guardkit init Pipeline

## Description

`sync_template_to_graphiti()` in `guardkit/knowledge/template_sync.py` is currently dead code — defined but never called from any code path. This function reads template manifest, agents, and rules and creates Graphiti episodes for each.

This task wires it into the `guardkit init` pipeline so that after template files are copied to the project (TASK-INST-010), their content is automatically ingested into the Graphiti knowledge graph.

## Context

After TASK-INST-010, `guardkit init fastapi-python` will copy template agents, rules, and manifest into the project. This task ensures that content is also queryable from Graphiti — which is the prerequisite for the `digest+graphiti` prompt profile (TASK-INST-007) to return meaningful context.

### Current Data Flow (broken)
```
guardkit init fastapi-python
  → Creates empty dirs           ← No template content
  → Seeds project overview       ← Narrow (purpose/tech/arch headers only)
  → Graphiti has no template knowledge
```

### Target Data Flow (after this task)
```
guardkit init fastapi-python
  → Copies template files        ← TASK-INST-010
  → Seeds project overview       ← Existing
  → Syncs template to Graphiti   ← THIS TASK
  → Graphiti contains agents, rules, patterns, frameworks
```

## Requirements

### 1. Call sync_template_to_graphiti in _cmd_init

After Step 2 (Graphiti seeding) in `guardkit/cli/init.py:_cmd_init()`, add a Step 2.5:

- Import `sync_template_to_graphiti` from `guardkit.knowledge.template_sync`
- Resolve the template source path (same as TASK-INST-010's template resolution)
- Call `await sync_template_to_graphiti(template_source_path)`
- Report success/failure with console output

### 2. Handle Graphiti Unavailable

- If Graphiti client is unavailable or disabled: skip sync with warning (same pattern as existing Step 2)
- If `--skip-graphiti` flag is set: skip sync
- Template files should still be copied even if Graphiti sync fails

### 3. Handle Template Not Found or Minimal

- If template source directory doesn't exist: skip sync with warning
- If template has no `manifest.json` (e.g., `default` template): sync agents and rules without manifest metadata, or skip gracefully
- The current `sync_template_to_graphiti()` returns `False` if manifest is missing — this needs to be relaxed to still sync agents/rules when manifest is absent

### 4. Reuse Existing Client

- The `_cmd_init()` function already creates a `GraphitiClient` in Step 2
- Reuse the same client instance for template sync (don't create a second client)
- `sync_template_to_graphiti()` currently calls `get_graphiti()` internally — may need to accept a client parameter or rely on the singleton being initialised

### 5. Sync Scope

The existing `sync_template_to_graphiti()` already handles:
- Template metadata from `manifest.json`
- Agent files from `agents/*.md` (excluding `-ext.md` files)
- Rule files from `.claude/rules/**/*.md`

Verify this covers:
- All agent core files (frontmatter metadata + capabilities)
- All rule files (path patterns + topics + content preview)
- Template manifest (name, language, frameworks, patterns, tags)

Note: `sync_template_to_graphiti()` currently only checks `{template}/agents/` for agent files. It must also check `{template}/.claude/agents/` (used by fastmcp-python). Update the agent directory resolution to check both locations.

### 6. Full Content Ingestion (Enhancement)

The current `sync_rule_to_graphiti()` only syncs `content_preview` (first 500 chars). For the `digest+graphiti` profile to be effective, rules need their full content in Graphiti.

- Modify `sync_rule_to_graphiti()` to use the `FullDocParser` for rules over 500 chars
- Or increase `content_preview` to capture full rule content (most rules are under 10KB)
- Agent sync should also include the full agent body content, not just frontmatter metadata

## Acceptance Criteria

- [ ] `guardkit init fastapi-python` calls `sync_template_to_graphiti()` when Graphiti is available
- [ ] Template manifest metadata appears in Graphiti after init
- [ ] Template agent metadata appears in Graphiti after init
- [ ] Template rule content appears in Graphiti after init
- [ ] `--skip-graphiti` flag skips template sync
- [ ] Graphiti unavailable: template files still copied, sync skipped with warning
- [ ] Template not found: sync skipped gracefully
- [ ] Rule content includes full text (not just 500-char preview)
- [ ] Agent sync includes body content beyond frontmatter
- [ ] Unit tests cover: successful sync, Graphiti unavailable, template not found

## File Location

- `guardkit/cli/init.py` (add Step 2.5 in `_cmd_init()`)
- `guardkit/knowledge/template_sync.py` (enhance content sync)

## Test Location

- `tests/cli/test_init.py` (integration with sync)
- `tests/knowledge/test_template_sync.py` (enhanced content sync)