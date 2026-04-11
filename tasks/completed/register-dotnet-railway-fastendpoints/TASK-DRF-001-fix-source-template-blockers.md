---
id: TASK-DRF-001
title: Fix blocker issues in dotnet-railway-fastendpoints source template
status: completed
created: 2026-04-11T12:00:00Z
updated: 2026-04-11T12:20:00Z
completed: 2026-04-11T12:20:00Z
priority: high
tags: [template, dotnet, manifest, settings, prep]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
previous_state: in_review
state_transition_reason: "Completed via /task-complete; all AC verified"
completed_location: tasks/completed/register-dotnet-railway-fastendpoints/
---

# Task: Fix blocker issues in dotnet-railway-fastendpoints source template

## Description

Fix 4 blocker issues and 2 minor polish items in the dotnet-railway-fastendpoints template at its source location `~/.agentecflow/templates/dotnet-railway-fastendpoints/`, before it is copied into `installer/core/templates/`. These fixes address issues identified by the architectural review in TASK-REV-D0C1.

All edits are to files **outside the guardkit repo** (at `~/.agentecflow/templates/dotnet-railway-fastendpoints/`). No files in the guardkit working tree are touched by this task.

## Context

See `.claude/reviews/TASK-REV-D0C1-review-report.md` §2 (Manifest Metadata) and §3 (settings.json) and §4 (Scaffold Templates) for full diagnosis.

## Acceptance Criteria

### manifest.json fixes

- [ ] **Remove phantom dependency**: delete `"agent:dotnet-domain-specialist"` from the `requires` array. The agent does not exist in `installer/core/agents/` (verified via grep). If `requires` becomes empty, set it to `[]`.
- [ ] **Set author to null**: change `"author": "Richard Woollcott"` to `"author": null` to match the [python-library convention](../../../installer/core/templates/python-library/manifest.json#L7).
- [ ] **Remove `source_project` field**: delete the `"source_project": "/Users/richardwoollcott/..."` key entirely — it leaks an author-local absolute path and has no functional purpose in a builtin.

### settings.json fix

- [ ] **Replace `Exemplar` with `{{ProjectName}}` in `layer_mappings` directory paths**: every `"directory"` value currently contains `Exemplar.*` (e.g. `src/Exemplar.Customers/Domain`). Replace `Exemplar` with `{{ProjectName}}` in all 7 layer directory paths. Namespaces already use `{{ProjectName}}` — do not touch those. After the change, confirm no literal `Exemplar` string remains in `settings.json`.

### CreateCustomer.cs.template fix

- [ ] **Parameterize `"admin"` role** in `templates/Endpoints/CreateCustomer.cs.template`. The existing comment `// {{TEMPLATE: PolicyNames}} — match Keycloak realm role names` acknowledges this. Either:
  - (preferred) Replace the literal `"admin"` with a placeholder `{{DefaultRole}}` and add a `DefaultRole` placeholder to `manifest.json` (optional, default `"admin"`), OR
  - Add a prominent comment block immediately above the role assignment warning users that this role name must be edited to match their Keycloak realm role names, and document the same in `.claude/CLAUDE.md`.

## Verification

- [ ] `grep -n 'Exemplar' ~/.agentecflow/templates/dotnet-railway-fastendpoints/settings.json` returns **zero matches**.
- [ ] `grep -n 'dotnet-domain-specialist' ~/.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json` returns **zero matches**.
- [ ] `grep -n 'Richard Woollcott' ~/.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json` returns **zero matches**.
- [ ] `grep -n 'source_project' ~/.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json` returns **zero matches**.
- [ ] `python -c "import json; json.load(open('/Users/richardwoollcott/.agentecflow/templates/dotnet-railway-fastendpoints/manifest.json'))"` succeeds (valid JSON after edits).
- [ ] `python -c "import json; json.load(open('/Users/richardwoollcott/.agentecflow/templates/dotnet-railway-fastendpoints/settings.json'))"` succeeds.

## Notes

- **Out of scope**: Do NOT copy the template into `installer/core/templates/` — that's TASK-DRF-002.
- **Out of scope**: Agent enhancement via `/agent-enhance --hybrid` — deferred to a follow-up task (see review report Wave 4).
- **Out of scope**: Fixing other scaffolds in `templates/` beyond `CreateCustomer.cs.template`. Spot-check in the review confirmed no other hardcoded infra.
