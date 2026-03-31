---
id: TASK-REV-TI25
title: Register langchain-deepagents-orchestrator as builtin template
status: backlog
created: 2026-03-30T21:30:00Z
updated: 2026-03-30T21:30:00Z
priority: high
tags: [template, installer, documentation, langchain-deepagents]
task_type: review
complexity: 5
---

# Task: Register langchain-deepagents-orchestrator as builtin template

## Description

Move the newly created `langchain-deepagents-orchestrator` template from its user-local location (`~/.agentecflow/templates/langchain-deepagents-orchestrator/`) into the GuardKit builtin template directory (`installer/core/templates/langchain-deepagents-orchestrator/`), and update all registration points so it appears as a first-class template alongside the existing `langchain-deepagents` and `langchain-deepagents-weighted-evaluation` templates.

### Background

This template was created via `/template-create` from the `deepagents-orchestrator-exemplar` repo. It captures the **Pipeline Orchestrator** pattern — an autonomous development pipeline agent that drives the full GuardKit slash command lifecycle using a two-model architecture (reasoning model orchestrates, implementation model executes). The big-picture motivation is the "Dark Factory" vision documented in `docs/research/dark_factory/`.

### Template Contents (from /template-create output)

- `manifest.json` (1.8 KB) — template metadata
- `settings.json` (1.9 KB) — naming conventions, layer mappings
- `.claude/rules/` (17 files) — modular CLAUDE.md with code-style, testing, patterns, and agent guidance rules
- `templates/` (10 files) — .template files covering agents, tools, prompts layers
- `agents/` (7 agents) — specialized agents at 85% confidence:
  - deepagents-orchestrator-specialist (priority 10)
  - langchain-tool-decorator-specialist (priority 9)
  - system-prompt-template-specialist (priority 9)
  - subagent-composition-specialist (priority 9)
  - pytest-agent-testing-specialist (priority 8)
  - langgraph-deployment-config-specialist (priority 8)
  - domain-context-injection-specialist (priority 7)

### Source Exemplar

- Repo: `deepagents-orchestrator-exemplar`
- Template confidence score: 68.33%
- Architecture: Standard Structure (Python, pytest)
- Patterns: Builder, Engine, Entity, Factory, Handler, Model, Service Layer, Validator

## Review Scope

Analyse and plan the changes required across these areas:

### 1. Template Installation

- [ ] Copy template from `~/.agentecflow/templates/langchain-deepagents-orchestrator/` to `installer/core/templates/langchain-deepagents-orchestrator/`
- [ ] Review `manifest.json` — update `display_name` and `description` to be pipeline-orchestrator-specific (currently generic "Python Standard Structure")
- [ ] Review `manifest.json` — decide whether `extends: "langchain-deepagents"` is appropriate (as the weighted-evaluation template extends base)
- [ ] Check for author-specific paths or defaults that need generalising

### 2. Installer Registration

- [ ] Update `guardkit/cli/init.py` help text (line ~1631) to include `langchain-deepagents-orchestrator`
- [ ] Verify template inheritance chain resolves correctly if `extends` is used
- [ ] Confirm template directory structure matches conventions of existing langchain-deepagents templates (agents/, templates/, manifest.json, settings.json)

### 3. Documentation Updates

- [ ] Update `CLAUDE.md` root — add to Templates list (currently 7 templates)
- [ ] Update any template listing in `docs/` that enumerates available templates
- [ ] Add a brief description of the template's purpose and when to use it vs the other langchain-deepagents variants

### 4. Help & Discovery

- [ ] Ensure `guardkit init --help` shows the new template
- [ ] Verify `guardkit init langchain-deepagents-orchestrator` works end-to-end
- [ ] Confirm template Q&A placeholders are correct (ProjectName, Namespace, Author)

### 5. Template Quality

- [ ] Review confidence score (68.33%) — identify gaps that could be improved before registration
- [ ] Review agent definitions for completeness and accuracy
- [ ] Compare `.claude/rules/` structure against existing langchain-deepagents templates for consistency
- [ ] Check for any hardcoded paths from the source exemplar

## Acceptance Criteria

- [ ] Template is registered as builtin and listed by `guardkit init --help`
- [ ] All documentation references updated (CLAUDE.md, init.py help, any template guides)
- [ ] `guardkit init langchain-deepagents-orchestrator` scaffolds a project correctly
- [ ] manifest.json has accurate, pipeline-orchestrator-specific metadata
- [ ] No hardcoded paths or author-specific defaults leak into the builtin

## Decision Points

1. **Template inheritance**: Should this template `extend` `langchain-deepagents` (like weighted-evaluation does) or be standalone?
2. **Manifest polish**: How much manifest cleanup is needed before registration vs doing it as a follow-up?
3. **Agent enhancement**: Should agents be enhanced with `/agent-enhance --hybrid` before or after registration?

## References

- Dark Factory research: `docs/research/dark_factory/`
- Pipeline Orchestrator conversation starter: `docs/research/dark_factory/pipeline-orchestrator-conversation-starter.md`
- Adversarial template conversation starter: `docs/research/dark_factory/langchain-deepagents-adversarial-conversation-starter.md`
- Existing base template: `installer/core/templates/langchain-deepagents/`
- Existing weighted-eval template: `installer/core/templates/langchain-deepagents-weighted-evaluation/`
- Template source: `~/.agentecflow/templates/langchain-deepagents-orchestrator/`
- Installer CLI: `guardkit/cli/init.py`
