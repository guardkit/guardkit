---
id: TASK-INST-010
title: "Reconcile guardkit init and agentic_init template application paths"
task_type: refactor
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
autobuild:
  enabled: true
  max_turns: 5
  mode: standard
---

# Task: Reconcile guardkit init and agentic_init Template Application Paths

## Description

Currently there are two separate init paths that diverge in behaviour:

1. **`guardkit init fastapi-python`** (`guardkit/cli/init.py` → `apply_template()`) — Creates empty directory scaffolds only (`.claude/`, `tasks/`, `.guardkit/`). Does NOT copy any template content (agents, rules, CLAUDE.md).

2. **`agentic_init`** (`installer/core/commands/lib/agentic_init/command.py`) — Copies `manifest.json`, `settings.json`, `CLAUDE.md`, agents, and code scaffold templates from `installer/core/templates/{template}/` into the project.

This task reconciles these two paths so that `guardkit init` becomes the single, authoritative init command that both creates the directory structure AND copies template-specific content.

## Requirements

### 1. Enhance `apply_template()` to Copy Template Content

Update `guardkit/cli/init.py:apply_template()` to:

- **Locate template source**: Resolve `installer/core/templates/{template_name}/` relative to the guardkit package installation path
- **Copy agents**: Copy agent `.md` files → `{target}/.claude/agents/`. Check BOTH `{template}/agents/` AND `{template}/.claude/agents/` (fastmcp-python uses the latter)
- **Copy rules**: Copy `{template}/.claude/rules/**/*.md` → `{target}/.claude/rules/` preserving directory structure
- **Copy CLAUDE.md**: Check both `{template}/CLAUDE.md` (root) and `{template}/.claude/CLAUDE.md`. Copy whichever exists to appropriate location in target. If both exist, copy both. Skip if target already has one.
- **Copy manifest.json**: Copy `{template}/manifest.json` → `{target}/.claude/manifest.json` (skip if not present — `default` template has no manifest)
- **Skip code scaffolds**: Do NOT copy `{template}/templates/`, `{template}/config/`, or `{template}/docker/` directories (code scaffold generation is a separate concern)

### Template Structural Variations

Not all templates follow the same layout. The copy logic must handle:

| Template | Agents Location | manifest.json | CLAUDE.md Location |
|----------|----------------|---------------|-------------------|
| default | `agents/` (empty, .gitkeep only) | Missing | `.claude/CLAUDE.md` only |
| fastapi-python | `agents/` | Present | Both root and `.claude/` |
| fastmcp-python | `.claude/agents/` | Present | Root only |
| mcp-typescript | `agents/` | Present | Root only |
| nextjs-fullstack | `agents/` | Present | `.claude/CLAUDE.md` only |
| react-fastapi-monorepo | `agents/` | Present | `.claude/CLAUDE.md` only |
| react-typescript | `agents/` | Present | Root only |

### 2. Template Source Resolution

- Use `importlib.resources` or `__file__`-relative path to locate the installed `installer/core/templates/` directory
- Fall back to checking `~/.guardkit/templates/` for user-installed templates
- If template not found: warn and continue with empty scaffold (current behaviour)

### 3. Conflict Handling

- If target file already exists: skip with warning (don't overwrite user's customisations)
- Log which files were copied vs skipped
- `--force` flag to overwrite existing files (optional, not required for MVP)

### 4. Backward Compatibility

- `guardkit init` with no template still creates the basic scaffold (unchanged behaviour)
- `guardkit init default` applies the default template (minimal agents/rules)
- Existing `agentic_init` command continues to work but is marked as deprecated

## Acceptance Criteria

- [ ] `guardkit init fastapi-python` copies agents from `agents/` to `.claude/agents/`
- [ ] `guardkit init fastmcp-python` copies agents from `.claude/agents/` to `.claude/agents/`
- [ ] `guardkit init fastapi-python` copies rules from template to `.claude/rules/`
- [ ] `guardkit init fastapi-python` copies CLAUDE.md from template to project root
- [ ] `guardkit init default` works without manifest.json (skip with info, not error)
- [ ] `guardkit init` copies manifest.json to `.claude/manifest.json` when present
- [ ] Existing files in target directory are NOT overwritten (skip with warning)
- [ ] Template not found produces a warning, not an error
- [ ] `guardkit init` with no args still creates basic scaffold
- [ ] Template source resolved from installed package location
- [ ] Unit tests cover: all 7 templates, template not found, file conflict, agent location variants

## File Location

`guardkit/cli/init.py` (modify `apply_template()`)

## Test Location

`tests/cli/test_init.py`
