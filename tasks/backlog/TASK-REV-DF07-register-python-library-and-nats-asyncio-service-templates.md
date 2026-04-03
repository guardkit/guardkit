---
id: TASK-REV-DF07
title: Register python-library and nats-asyncio-service as builtin templates
status: review_complete
created: 2026-04-03T12:00:00Z
updated: 2026-04-03T12:00:00Z
priority: high
tags: [template, installer, documentation, python-library, nats-asyncio-service, dark-factory]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 0
review_results:
  mode: architectural
  depth: standard
  score: 45
  findings_count: 14
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-DF07-review-report.md
---

# Task: Register python-library and nats-asyncio-service as builtin templates

## Description

Move the two newly created templates from their user-local locations into the GuardKit builtin template directory and update all registration points so they appear as first-class templates.

**Templates to register:**

1. **python-library** — from `~/.agentecflow/templates/python-library/` to `installer/core/templates/python-library/`
2. **nats-asyncio-service** — from `~/.agentecflow/templates/nats-asyncio-service/` to `installer/core/templates/nats-asyncio-service/`

### Background

These templates were created via `/template-create` as part of the "Dark Factory" initiative documented in `docs/research/dark_factory/`. They capture two key patterns needed for the autonomous development pipeline:

- **python-library**: Standalone Python packages using hatchling, src layout, pytest with markers, ruff, mypy strict. Targets repos like nats-core, youtube-channel-intelligence, guardkit-types.
- **nats-asyncio-service**: NATS event-driven services using FastStream with TestNatsBroker, pydantic-settings, JetStream support. Targets repos like youtube-pipeline and Ship's Computer agents.

### Reference

This task follows the same pattern as TASK-REV-TI25 (Register langchain-deepagents-orchestrator as builtin template), which was completed successfully.

## Review Scope

### 1. Template Installation

#### python-library
- [ ] Copy template from `~/.agentecflow/templates/python-library/` to `installer/core/templates/python-library/`
- [ ] Review `manifest.json` — update `display_name` and `description` to be python-library-specific
- [ ] Check for author-specific paths or defaults that need generalising
- [ ] Verify template confidence score and identify gaps for improvement

#### nats-asyncio-service
- [ ] Copy template from `~/.agentecflow/templates/nats-asyncio-service/` to `installer/core/templates/nats-asyncio-service/`
- [ ] Review `manifest.json` — update `display_name` and `description` to be nats-asyncio-service-specific
- [ ] Check for author-specific paths or defaults that need generalising
- [ ] Verify template confidence score and identify gaps for improvement

### 2. Installer Registration

- [ ] Update `guardkit/cli/init.py` help text to include `python-library` and `nats-asyncio-service`
- [ ] Verify template directory structure matches conventions of existing builtin templates (agents/, templates/, manifest.json, settings.json)
- [ ] Confirm `guardkit init python-library` works end-to-end
- [ ] Confirm `guardkit init nats-asyncio-service` works end-to-end

### 3. Documentation Updates

- [ ] Update `CLAUDE.md` root — add both templates to the Templates list
- [ ] Update any template listing in `docs/` that enumerates available templates
- [ ] Add brief descriptions of each template's purpose and when to use them
- [ ] Update `installer/scripts/install.sh` if it contains template listings

### 4. Help & Discovery

- [ ] Ensure `guardkit init --help` shows both new templates
- [ ] Verify template Q&A placeholders are correct for each template
- [ ] Confirm template descriptions distinguish them from existing templates

### 5. Template Quality

#### python-library
- [ ] Review agent definitions for completeness and accuracy
- [ ] Review `.claude/rules/` structure for consistency with other templates
- [ ] Check for hardcoded paths from the source exemplar
- [ ] Verify py.typed marker pattern is included
- [ ] Confirm MCP-specific patterns are removed (per spec)

#### nats-asyncio-service
- [ ] Review agent definitions for completeness and accuracy
- [ ] Review `.claude/rules/` structure for consistency with other templates
- [ ] Check for hardcoded paths from the source exemplar
- [ ] Verify FastStream/TestNatsBroker patterns are correctly captured
- [ ] Confirm JetStream support patterns are included

## Acceptance Criteria

- [ ] Both templates are registered as builtin and listed by `guardkit init --help`
- [ ] All documentation references updated (CLAUDE.md, init.py help, template guides)
- [ ] `guardkit init python-library` scaffolds a project correctly
- [ ] `guardkit init nats-asyncio-service` scaffolds a project correctly
- [ ] manifest.json files have accurate, template-specific metadata
- [ ] No hardcoded paths or author-specific defaults leak into the builtins

## Decision Points

1. **Template inheritance**: Should either template extend an existing template or be standalone?
2. **Manifest polish**: How much manifest cleanup is needed before registration vs doing it as a follow-up?
3. **Agent enhancement**: Should agents be enhanced with `/agent-enhance --hybrid` before or after registration?
4. **Registration order**: Register both simultaneously or one at a time?

## References

- Dark Factory research: `docs/research/dark_factory/`
- python-library spec: `docs/research/dark_factory/template-spec-python-library.md`
- nats-asyncio-service spec: `docs/research/dark_factory/template-spec-nats-asyncio-service.md`
- Reference task: `tasks/in_review/TASK-REV-TI25-register-langchain-deepagents-orchestrator-template.md`
- Template source (python-library): `~/.agentecflow/templates/python-library/`
- Template source (nats-asyncio-service): `~/.agentecflow/templates/nats-asyncio-service/`
- Existing builtin templates: `installer/core/templates/`
- Installer CLI: `guardkit/cli/init.py`
