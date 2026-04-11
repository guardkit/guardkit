---
id: TASK-DRF-002
title: Copy dotnet-railway-fastendpoints into installer/core and register in docs
status: completed
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T12:30:00Z
completed: 2026-04-11T12:30:00Z
previous_state: in_review
priority: high
tags: [template, dotnet, installer, documentation, registration]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
wave: 2
complexity: 2
depends_on: [TASK-DRF-001]
---

# Task: Copy dotnet-railway-fastendpoints into installer/core and register in docs

## Description

Copy the fixed dotnet-railway-fastendpoints template from `~/.agentecflow/templates/` into `installer/core/templates/` and update the 2 hardcoded template lists. The CLI auto-discovers templates from the filesystem, so no discovery-layer code changes are required.

## Context

See `.claude/reviews/TASK-REV-D0C1-review-report.md` §6 (Registration Points) for the verified registration surface. Only 2 hardcoded lists need updating — everything else is auto-discovered or out of scope.

**Depends on TASK-DRF-001**: Source template must have blockers fixed before copy. Do not start until DRF-001 is completed and verified.

## Acceptance Criteria

### Copy

- [ ] **Copy template**: `cp -R ~/.agentecflow/templates/dotnet-railway-fastendpoints/ installer/core/templates/dotnet-railway-fastendpoints/`
- [ ] **Verify structure matches convention**: the copied directory must contain `.claude/CLAUDE.md`, `.claude/rules/` (22 files), `agents/` (14 files), `templates/` (20 files), `manifest.json`, `settings.json`. Compare to `installer/core/templates/python-library/` structure.
- [ ] **Verify no leaked files**: `grep -rn 'Exemplar' installer/core/templates/dotnet-railway-fastendpoints/settings.json` returns zero matches. `grep -rn 'Richard Woollcott' installer/core/templates/dotnet-railway-fastendpoints/manifest.json` returns zero matches.

### Root README.md

- [ ] **Add `installer/core/templates/dotnet-railway-fastendpoints/README.md`** (new file, ~30-50 lines). Should include:
  - One-paragraph description (first C#/.NET builtin, Railway-Oriented Programming, Modular Monolith with bounded-context isolation)
  - Quick start: `guardkit init dotnet-railway-fastendpoints`
  - Placeholder table (ProjectName, Namespace, Author) — values required/optional
  - Technology stack summary (ASP.NET Core 10.0, FastEndpoints, Dapper, NATS, Keycloak, xUnit+Testcontainers)
  - "When to use" section (1-2 sentences)
  - Reference python-library's README structure if one exists

### Registration edits

- [ ] **Edit [CLAUDE.md:223](../../../CLAUDE.md#L223)** — append `| dotnet-railway-fastendpoints` to the existing pipe-separated template list. Place it after `langchain-deepagents-weighted-evaluation` and before `| default`.

- [ ] **Edit [guardkit/cli/init.py:1719](../../../guardkit/cli/init.py#L1719)** — append `, dotnet-railway-fastendpoints` to the comma-separated list in the docstring. Place it after `langchain-deepagents-weighted-evaluation`.

## Verification

- [ ] `ls installer/core/templates/dotnet-railway-fastendpoints/` shows the expected directories and files.
- [ ] `cat installer/core/templates/dotnet-railway-fastendpoints/README.md` displays the new README.
- [ ] `grep -n 'dotnet-railway-fastendpoints' CLAUDE.md` finds exactly 1 match on line ~223.
- [ ] `grep -n 'dotnet-railway-fastendpoints' guardkit/cli/init.py` finds exactly 1 match on line ~1719.

## Notes

- **`installer/scripts/install.sh`** legacy template lists (lines 557, 834, 865-870) are already stale (missing python-library, nats-asyncio-service, langchain-*) — updating them is **out of scope**. Fixing install.sh comprehensively should be a separate cleanup task.
- **`tests/knowledge/test_seed_enrichment.py`** `EXPECTED_TEMPLATES` set at line 36 is also stale (excludes 5+ existing templates). **Out of scope** for this task.
- **`README.md`** root file only lists 5 templates as examples in a table — updating it is optional and **out of scope** unless the table claims to be comprehensive.
