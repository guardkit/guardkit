---
id: TASK-REV-D0C1
title: Register dotnet-railway-fastendpoints as builtin template
status: review_complete
created: 2026-04-11T00:00:00Z
updated: 2026-04-11T12:00:00Z
previous_state: in_progress
state_transition_reason: "/task-review completed, awaiting decision"
priority: high
tags: [template, installer, documentation, dotnet, railway, fastendpoints, csharp]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 0
review_results:
  mode: architectural
  depth: standard
  score: 82
  findings_count: 7
  recommendations_count: 15
  decision: refactor
  report_path: .claude/reviews/TASK-REV-D0C1-review-report.md
  completed_at: 2026-04-11T12:00:00Z
---

# Task: Register dotnet-railway-fastendpoints as builtin template

## Description

Move the newly created `dotnet-railway-fastendpoints` template from its user-local location into the GuardKit builtin template directory and update all registration points so it appears as a first-class template.

**Template to register:**

- **dotnet-railway-fastendpoints** — from `~/.agentecflow/templates/dotnet-railway-fastendpoints/` to `installer/core/templates/dotnet-railway-fastendpoints/`

### Background

This template was created via `/template-create` and is the first C#/.NET builtin template for GuardKit. It captures a modern .NET Modular Monolith architecture using Railway-Oriented Programming with FastEndpoints, Dapper, NATS, and Keycloak.

**What was generated (source location `~/.agentecflow/templates/dotnet-railway-fastendpoints/`):**

- `manifest.json` (5.2 KB) — C# / ASP.NET Core 10.0 / Modular Monolith, complexity 10/10
- `settings.json` (3.4 KB) — 5 naming conventions, 7 layer mappings
- `.claude/rules/` (22 files) — modular rules structure with path-specific loading:
  - `code-style.md`, `testing.md`
  - 13 pattern rule files (Railway-Oriented Programming, Repository, Anti-Corruption Layer, etc.)
  - 7 agent guidance files
- `templates/` (20 files) — scaffold templates covering all layers: Domain, Application, Infrastructure, Endpoints, Contracts, Fleet, Host, Tests
- `agents/` (7 agents):
  - `railway-result-pipeline-specialist`
  - `fastendpoints-endpoint-specialist`
  - `dapper-postgresql-repository-specialist`
  - `bounded-context-domain-specialist`
  - `xunit-testcontainers-testing-specialist`
  - `nats-fleet-integration-specialist`
  - `keycloak-auth-observability-specialist`

### Reference

This task follows the same pattern as the recent Langchain DeepAgents template registrations:

- `TASK-REV-DF07` — Register python-library and nats-asyncio-service as builtin templates
- Existing builtin Langchain DeepAgents templates in `installer/core/templates/langchain-deepagents*/`

## Review Scope

### 1. Template Installation

- [ ] Copy template from `~/.agentecflow/templates/dotnet-railway-fastendpoints/` to `installer/core/templates/dotnet-railway-fastendpoints/`
- [ ] Review `manifest.json` — verify `display_name`, `description`, language, frameworks, and complexity score
- [ ] Check for author-specific paths, user-local references, or defaults that need generalising
- [ ] Verify template confidence score and identify any gaps for follow-up improvement
- [ ] Confirm directory structure matches conventions of existing builtin templates (`agents/`, `templates/`, `.claude/rules/`, `manifest.json`, `settings.json`)
- [ ] Verify `.claude/rules/` path-specific loading works with GuardKit's progressive disclosure conventions

### 2. Installer Registration

- [ ] Update `guardkit/cli/init.py` help text and any hardcoded template lists to include `dotnet-railway-fastendpoints`
- [ ] Confirm `guardkit init dotnet-railway-fastendpoints` works end-to-end
- [ ] Verify placeholders resolve correctly on a scaffolded project
- [ ] Run `/template-validate installer/core/templates/dotnet-railway-fastendpoints` and address any findings

### 3. Documentation Updates

- [ ] Update root `CLAUDE.md` — add the template to the Templates list (currently: `react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | python-library | nats-asyncio-service | langchain-deepagents | langchain-deepagents-orchestrator | langchain-deepagents-weighted-evaluation | default`)
- [ ] Update any template listing in `docs/` that enumerates available templates
- [ ] Add a brief description of the template's purpose and when to use it (first .NET/C# builtin, Railway-Oriented Programming, Modular Monolith)
- [ ] Update `installer/scripts/install.sh` if it contains template listings

### 4. Help & Discovery

- [ ] Ensure `guardkit init --help` shows the new template
- [ ] Verify template Q&A placeholders are correct and .NET-idiomatic
- [ ] Confirm template description distinguishes it from existing templates (the only .NET/C# template so far)

### 5. Template Quality

- [ ] Review each of the 7 agent definitions for completeness and accuracy
- [ ] Review `.claude/rules/` structure (22 files) for consistency with other templates' modular rules structure
- [ ] Validate the 13 pattern rule files (Railway-Oriented Programming, Repository, ACL, etc.) match GuardKit's pattern-rule conventions
- [ ] Review the 20 scaffold templates across all layers (Domain, Application, Infrastructure, Endpoints, Contracts, Fleet, Host, Tests) for correctness
- [ ] Check for hardcoded paths from the source exemplar
- [ ] Verify xUnit + Testcontainers testing setup is captured correctly
- [ ] Confirm NATS fleet integration and Keycloak auth/observability patterns are generic (not bound to a specific cluster or realm)
- [ ] Decide whether to run `/agent-enhance dotnet-railway-fastendpoints/<agent-name> --hybrid` before or after registration

## Acceptance Criteria

- [ ] Template is registered as builtin and listed by `guardkit init --help`
- [ ] All documentation references updated (root `CLAUDE.md`, `init.py` help, template guides)
- [ ] `guardkit init dotnet-railway-fastendpoints` scaffolds a project correctly
- [ ] `manifest.json` has accurate, template-specific metadata
- [ ] No hardcoded paths, user-local references, or author-specific defaults leak into the builtin
- [ ] `/template-validate` passes for the newly registered template

## Decision Points

1. **Template inheritance**: Should this template extend an existing template or remain standalone? (Likely standalone — no existing .NET base.)
2. **Manifest polish**: How much manifest cleanup is needed before registration vs. as a follow-up?
3. **Agent enhancement**: Should the 7 agents be enhanced with `/agent-enhance --hybrid` before or after registration?
4. **Complexity 10/10**: Template is rated maximum complexity — should the review recommend splitting into smaller templates (e.g., `dotnet-railway-minimal`, `dotnet-railway-full-stack`) or keep as a single template?
5. **Fleet/NATS/Keycloak coupling**: Are these included as optional layers or hardwired? Affects how portable the template is for users not using this exact stack.

## References

- Template source: `~/.agentecflow/templates/dotnet-railway-fastendpoints/`
- Reference task: `tasks/backlog/TASK-REV-DF07-register-python-library-and-nats-asyncio-service-templates.md`
- Existing builtin templates: `installer/core/templates/`
- Langchain DeepAgents templates (for structural reference): `installer/core/templates/langchain-deepagents*/`
- Installer CLI: `guardkit/cli/init.py`
- Root template list: `CLAUDE.md` (Installation section)
