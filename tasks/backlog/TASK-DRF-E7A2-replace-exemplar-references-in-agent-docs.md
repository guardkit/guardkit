---
id: TASK-DRF-E7A2
title: Replace literal Exemplar.* references with {{Namespace}} in dotnet-railway-fastendpoints agent docs
status: backlog
created: 2026-04-11T12:40:00Z
updated: 2026-04-11T12:40:00Z
priority: low
tags: [template, dotnet, cosmetic, documentation, cleanup]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
complexity: 2
---

# Task: Replace literal Exemplar.* references with {{Namespace}} in dotnet-railway-fastendpoints agent docs

## Description

Filed as a follow-up to TASK-DRF-003. The smoke test revealed that 5 agent markdown files inside `installer/core/templates/dotnet-railway-fastendpoints/agents/` contain literal `Exemplar.*` namespace references in guidance/example text. These are cosmetic — they don't break init or any quality gate — but they expose the original internal project name to users who scaffold a template from a project named something else.

## Context

Discovered during `/task-work TASK-DRF-003` smoke test on 2026-04-11. The template works correctly as a GuardKit builtin; this task is purely about cleaning up sample text in the 7 guidance agent markdown files.

Affected files (non-exhaustive — grep to confirm):

- `installer/core/templates/dotnet-railway-fastendpoints/agents/fastendpoints-endpoint-specialist.md`
- `installer/core/templates/dotnet-railway-fastendpoints/agents/fastendpoints-endpoint-specialist-ext.md`
- `installer/core/templates/dotnet-railway-fastendpoints/agents/xunit-testcontainers-testing-specialist.md`
- `installer/core/templates/dotnet-railway-fastendpoints/agents/xunit-testcontainers-testing-specialist-ext.md`
- `installer/core/templates/dotnet-railway-fastendpoints/agents/keycloak-auth-observability-specialist-ext.md`

Example references: `Exemplar.Core.Functional`, `Exemplar.Core.Errors`, `ExemplarApiFactory`.

## Acceptance Criteria

- [ ] Run `grep -rn 'Exemplar' installer/core/templates/dotnet-railway-fastendpoints/agents/` to enumerate all occurrences.
- [ ] For each occurrence, decide: replace with `{{Namespace}}.*` placeholder (if the reference is to a namespace), or generalize to a language-neutral description (if the reference is to a specific class like `ExemplarApiFactory`).
- [ ] After replacement, `grep -c 'Exemplar' installer/core/templates/dotnet-railway-fastendpoints/agents/*.md` returns zero.
- [ ] Spot-check 2 edited files to verify the replacement reads naturally in context.

## Notes

- **Out of scope**: The `.cs.template` scaffold files under `installer/core/templates/dotnet-railway-fastendpoints/templates/` also contain literal `Exemplar` — those are the original working sample code and are NOT consumed by `guardkit init` today (see TASK-DRF-SCAF follow-up if filed). Do not touch them as part of this task.
- **Low priority**: Not user-facing until someone actively reads the template's agent docs after scaffolding a project with a different name.
