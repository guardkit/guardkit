---
id: TASK-REV-A012
title: Copy langchain-deepagents template into guardkit repo as builtin
status: review_complete
created: 2026-03-16T16:00:00Z
updated: 2026-03-16T16:00:00Z
priority: high
tags: [langchain-deepagents, template, builtin, review]
task_type: review
feature_id: FEAT-LDB
depends_on:
  - TASK-LDB-001
  - TASK-LDB-002
  - TASK-LDB-003
  - TASK-LDB-004
complexity: 4
---

# Task: Copy langchain-deepagents template into guardkit repo as builtin

## Description

The `langchain-deepagents` template was generated via `/template-create` and currently lives at
`~/.agentecflow/templates/langchain-deepagents/`. The supporting tasks (LDB-001 through LDB-004)
have already updated the init script description, CLAUDE.md template list, auto-detection logic,
and fixed the template-create CLAUDE.md path bug.

This review task covers the final step: copying the template files from the user-local directory
into `installer/core/templates/langchain-deepagents/` so it ships as a builtin template in the
guardkit repository.

## Source Location

`~/.agentecflow/templates/langchain-deepagents/`

## Target Location

`installer/core/templates/langchain-deepagents/`

## What Needs Copying

### Root files
- `manifest.json` — template metadata
- `settings.json` — template configuration

### Agents (7 specialist agents)
- `agents/adversarial-cooperation-architect.md`
- `agents/deepagents-factory-specialist.md`
- `agents/domain-driven-config-specialist.md`
- `agents/langchain-tool-specialist.md`
- `agents/langgraph-entrypoint-specialist.md`
- `agents/pytest-factory-test-specialist.md`
- `agents/system-prompt-engineer.md`

### Template files (14 files across layers)
- `templates/other/agents/coach.py.template`
- `templates/other/agents/player.py.template`
- `templates/other/example-domain/DOMAIN.md.template`
- `templates/other/other/.env.example.template`
- `templates/other/other/AGENTS.md.template`
- `templates/other/other/agent.py.template`
- `templates/other/other/coach-config.yaml.template`
- `templates/other/other/langgraph.json.template`
- `templates/other/other/pyproject.toml.template`
- `templates/other/prompts/coach_prompts.py.template`
- `templates/other/prompts/player_prompts.py.template`
- `templates/other/tools/search_data.py.template`
- `templates/other/tools/write_output.py.template`
- `templates/testing/tests/test_agents.py.template`

### Rules structure (.claude/)
- `.claude/CLAUDE.md`
- `.claude/rules/code-style.md`
- `.claude/rules/testing.md`
- `.claude/rules/patterns/adversarial-cooperation.md`
- `.claude/rules/patterns/domain-driven-configuration.md`
- `.claude/rules/patterns/factory.md`
- `.claude/rules/patterns/memory-injection.md`
- `.claude/rules/patterns/tool-delegation.md`
- `.claude/rules/guidance/adversarial-cooperation-architect.md`
- `.claude/rules/guidance/deepagents-factory-specialist.md`
- `.claude/rules/guidance/domain-driven-config-specialist.md`
- `.claude/rules/guidance/langchain-tool-specialist.md`
- `.claude/rules/guidance/langgraph-entrypoint-specialist.md`
- `.claude/rules/guidance/pytest-factory-test-specialist.md`
- `.claude/rules/guidance/system-prompt-engineer.md`

## Review Checklist

- [ ] Verify all files copy cleanly (no path issues, no missing files)
- [ ] Confirm directory structure matches other builtin templates (manifest.json, settings.json, agents/, templates/)
- [ ] Verify `.claude/` rules structure is included (this is unique to this template)
- [ ] Check manifest.json has correct template name and metadata
- [ ] Confirm `guardkit init langchain-deepagents` works from the repo copy
- [ ] Verify no leftover absolute paths or user-specific content in template files
- [ ] Cross-check with init-project.sh that the template name matches the hardcoded description (TASK-LDB-001)
- [ ] Cross-check with CLAUDE.md template list (TASK-LDB-002)
- [ ] Cross-check with auto-detection logic (TASK-LDB-003)

## Acceptance Criteria

- [ ] All template files copied to `installer/core/templates/langchain-deepagents/`
- [ ] Directory structure is complete and correct
- [ ] No user-local paths or absolute paths in any template file
- [ ] Template is discoverable by `guardkit init`
- [ ] Existing builtin templates unaffected

## Implementation Notes

This is a straightforward `cp -r` operation followed by verification. The key risk is
missing files or incorrect directory nesting. The `.claude/` subdirectory with rules
is a newer pattern not present in all existing templates — verify it's handled correctly
by the init script.
