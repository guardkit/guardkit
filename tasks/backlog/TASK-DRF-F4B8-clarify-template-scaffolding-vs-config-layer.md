---
id: TASK-DRF-F4B8
title: Clarify GuardKit template scaffolding model — config-layer vs project-scaffold
status: superseded
created: 2026-04-11T12:40:00Z
updated: 2026-04-11T15:15:00Z
priority: medium
tags: [template, architecture, documentation, guardkit-init, superseded]
parent_review: TASK-REV-D0C1
feature_id: FEAT-D0C1
implementation_mode: direct
complexity: 4
superseded_by:
  - TASK-PAT-1A5E
  - TASK-DOC-C3D7
  - TASK-REN-B9F2
superseded_reason: "TASK-REV-A5F8 analysed all three original options (document / extend init / delete files) and rejected them all. The real architectural fix is wiring scaffold templates into the AutoBuild Player as the missing consumer — filed as TASK-PAT-1A5E. The documentation component was reframed and re-scoped to all 10 templates as TASK-DOC-C3D7. The optional rename was carved out as TASK-REN-B9F2 (deferred). See .claude/reviews/TASK-REV-A5F8-review-report.md for full rationale."
---

> **⚠️ This task has been superseded and resolved.** The architectural fix has been implemented as FEAT-TPL-PLAYER (feature/template-pattern-player-context). The documentation component has been completed by TASK-TPL-007.
>
> **Resolution summary:**
> - **Architectural fix**: FEAT-TPL-PLAYER (TASK-TPL-001 through TASK-TPL-004) wired template `.template` files into the AutoBuild Player context pipeline. The Player now receives stack-specific pattern context at build time. See [FEAT-TPL-PLAYER spec](../../docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md) and the [AutoBuild Instrumentation Guide — Template Pattern Context](../../docs/guides/autobuild-instrumentation-guide.md#template-pattern-context).
> - **Documentation**: TASK-TPL-007 updated the AutoBuild Instrumentation Guide with a Template Pattern Context section documenting the data flow, components, selection rules, graceful degradation, and token impact.
> - **Rename decision**: TASK-REN-B9F2 closed — no rename needed now that the consumer exists (Decision D6 in FEAT-TPL-PLAYER spec).
>
> Original supersession notes preserved below for historical context:
>
> - [TASK-PAT-1A5E](template-pattern-layer/TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md) — the architectural fix (implemented as FEAT-TPL-PLAYER)
> - [TASK-DOC-C3D7](template-pattern-layer/TASK-DOC-C3D7-document-two-layer-template-model.md) — documentation (completed by TASK-TPL-007)
> - [TASK-REN-B9F2](template-pattern-layer/TASK-REN-B9F2-rename-templates-to-patterns.md) — optional rename (closed: consumer exists, no rename needed)
>
> The original F4B8 text below is preserved for historical context only.


# Task: Clarify GuardKit template scaffolding model — config-layer vs project-scaffold

## Description

Surfaced by `/task-work TASK-DRF-003` smoke test on 2026-04-11. The dotnet-railway-fastendpoints template ships a `templates/` subdirectory containing 20 `.cs.template` files (Program.cs.template, CustomerService.cs.template, etc.) that look like project scaffold source code. When `guardkit init dotnet-railway-fastendpoints` runs, it copies **only** `.claude/` (CLAUDE.md, rules/, agents/) plus `.guardkit/` and an empty `tasks/` directory. The `templates/` subdirectory is never consumed — no `src/MyApp.API/Program.cs` is generated.

The same behavior was confirmed for `python-library`: GuardKit's `init` is a pure config-layer installer, not a project scaffolder.

This is architecturally intentional but not documented anywhere the template author or task reviewer would see it. TASK-DRF-003's acceptance criteria assumed `guardkit init dotnet-railway-fastendpoints` would produce `src/MyApp.*/` directories — it does not. The criterion was a miscalibration, not a bug.

## Decision Needed

Pick one of:

1. **Document-only fix**: Add a "What `guardkit init` does (and doesn't do)" section to `docs/guides/` and `installer/core/templates/README.md` making clear that templates are config layers. Clarify that the `templates/` subdirectory convention is unused by init today (or used only by specific tooling — confirm what if anything consumes it).
2. **Implementation fix**: Extend `guardkit init` to also copy/process the `templates/` subdirectory with placeholder substitution so templates like dotnet-railway-fastendpoints actually produce a working project skeleton (`src/MyApp.API/Program.cs`, etc.) from the `.cs.template` files.
3. **Remove the dead subdirectory**: If nothing consumes `templates/*.cs.template`, remove those files from the template packages and document that GuardKit templates only contain `.claude/`, `manifest.json`, `settings.json`, `README.md`.

## Acceptance Criteria

- [ ] Decide on one of the 3 options above (or another).
- [ ] If option 1: produce the doc; update any templates whose README promises a working source scaffold.
- [ ] If option 2: design + implement + test the new init behavior (would be a larger task, split out).
- [ ] If option 3: remove dead files from all affected templates.

## Context

TASK-DRF-003 smoke test output:
```
$ guardkit init dotnet-railway-fastendpoints --no-questions -n MyApp
$ ls /tmp/test-dotnet-railway/
.claude  .guardkit  tasks
# No src/ directory. No .csproj. No .cs files.
```

Same result for `python-library` — no `src/`, no `pyproject.toml`, no scaffold.

## Notes

- Not a blocker for the template being accepted as a first-class builtin — the `.claude/` layer IS functional and provides real value (agents, rules, CLAUDE.md).
- This likely affects ALL templates' perceived behavior, not just dotnet-railway-fastendpoints. A user expecting `guardkit init react-typescript` to produce a working React project scaffold would be disappointed the same way.
