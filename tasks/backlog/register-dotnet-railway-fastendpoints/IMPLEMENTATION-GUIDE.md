# Implementation Guide: Register dotnet-railway-fastendpoints Template

**Feature ID**: FEAT-D0C1
**Parent Review**: [TASK-REV-D0C1](../../in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md)
**Review Report**: [.claude/reviews/TASK-REV-D0C1-review-report.md](../../../.claude/reviews/TASK-REV-D0C1-review-report.md)
**Feature score from review**: 82/100 (REFACTOR THEN REGISTER)

## Goal

Register the `dotnet-railway-fastendpoints` template (GuardKit's first C#/.NET builtin) as a first-class builtin in `installer/core/templates/`, after fixing 4 blocker issues identified in the architectural review.

## Why Sequential (Not Parallel)

Each wave strictly depends on the previous wave's output:

- **Wave 2** cannot start until **Wave 1** finishes, because the copy source must be fixed first.
- **Wave 3** cannot start until **Wave 2** finishes, because there is nothing to validate before the copy + registration is complete.

Parallelization would not save time and would create race conditions on the source template. Conductor workspaces are **not** recommended for this feature.

## Execution Strategy

```
Wave 1: TASK-DRF-001 (Fix source blockers)
   │  Scope: manifest.json (3 fixes) + settings.json (1 fix) + CreateCustomer.cs.template (1 fix)
   │  Location: ~/.agentecflow/templates/dotnet-railway-fastendpoints/ (OUTSIDE repo)
   ▼
Wave 2: TASK-DRF-002 (Copy + register)
   │  Scope: cp -R into installer/core/templates/ + README.md + CLAUDE.md:223 + init.py:1719
   │  Location: guardkit repo
   ▼
Wave 3: TASK-DRF-003 (Validate + smoke test)  ║  TASK-DRF-004 (Shorten display_name)
        Scope: /template-validate + smoke     ║  Scope: manifest.json display_name polish
        test + grep audit                     ║  Location: installer/core/ only (copied version)
        (blocks feature completion)           ║  (low priority cosmetic, can run in parallel)
```

## Wave Breakdown

### Wave 1 — TASK-DRF-001: Fix Source Template Blockers

**Mode**: direct
**Estimated effort**: 20-30 minutes
**Outputs**: Cleaned manifest.json, settings.json, and CreateCustomer.cs.template at source

**Key fixes**:
1. Strip `requires: ["agent:dotnet-domain-specialist"]` from manifest (phantom dependency, agent does not exist in GuardKit)
2. Set `author` to `null` in manifest (convention match with python-library)
3. Remove `source_project` key from manifest (leaks absolute user path)
4. Replace `Exemplar` with `{{ProjectName}}` in settings.json `layer_mappings` directory paths (7 paths affected)
5. Parameterize or document the hardcoded `"admin"` role in CreateCustomer endpoint

**Verification**: 4 grep commands + 2 JSON validity checks (all defined in task AC).

### Wave 2 — TASK-DRF-002: Copy and Register

**Mode**: direct
**Estimated effort**: 20-30 minutes
**Outputs**:
- `installer/core/templates/dotnet-railway-fastendpoints/` (full copy)
- `installer/core/templates/dotnet-railway-fastendpoints/README.md` (new, ~30-50 lines)
- Edit to [CLAUDE.md:223](../../../CLAUDE.md#L223)
- Edit to [guardkit/cli/init.py:1719](../../../guardkit/cli/init.py#L1719)

**Out of scope (intentional)**:
- Updating `installer/scripts/install.sh` — already stale for 5+ existing templates; should be its own cleanup task
- Updating `tests/knowledge/test_seed_enrichment.py` `EXPECTED_TEMPLATES` — same reason
- Updating root `README.md` table — only shows 5 templates as examples, not comprehensive

### Wave 3 — TASK-DRF-003: Validate and Smoke Test

**Mode**: direct
**Estimated effort**: 15-30 minutes
**Outputs**: Validation report + cleaned-up test scaffold

**Key verifications**:
- `/template-validate` passes (or only reports non-critical findings)
- `guardkit init --help` shows the new template
- End-to-end scaffold: `guardkit init dotnet-railway-fastendpoints` with ProjectName=`MyApp` produces a `src/MyApp.*/` layout (NOT `src/Exemplar.*/`)
- No residual `Exemplar`, `Richard Woollcott`, or `/Users/` strings in the scaffolded output

### Wave 3 (parallel) — TASK-DRF-004: Shorten `display_name`

**Mode**: direct
**Estimated effort**: ~5 minutes
**Priority**: low (cosmetic polish, non-blocking)
**Outputs**: Updated `display_name` in the registered manifest only

**Key fixes**:
- Replace `"C# Modular Monolith With Bounded Context Isolation"` with a terse name (recommended: `"C# Railway-Oriented Monolith"`)
- Edit **only** the registered copy at `installer/core/templates/dotnet-railway-fastendpoints/manifest.json` — leave the source at `~/.agentecflow/` alone to avoid merge conflicts with DRF-001
- Update README.md if the long name appears there

## Agent Enhancement Status

**Already completed** — `/agent-enhance` was run on all 7 agents before the review. Verified by:
- All 7 agents have `-ext.md` extended files (121-177 lines each, 1,799 lines total)
- Extended files contain "Related Templates", numbered "Code Examples", template cross-references
- No further agent work required for registration

## Related Follow-Up Tasks (Standalone, in `tasks/backlog/`)

These cross-cutting cleanup / design tasks have been filed separately. They are **not** blockers for this feature:

1. **[TASK-TSE-8A1C](../TASK-TSE-8A1C-fix-stale-expected-templates-set.md)** — Fix stale `tests/knowledge/test_seed_enrichment.py` `EXPECTED_TEMPLATES` set (currently missing 6+ templates, will worsen when dotnet-railway-fastendpoints is added). Independent of this feature.

2. **[TASK-ISH-3F02](../TASK-ISH-3F02-update-legacy-install-sh-template-lists.md)** — Update 3 stale template enumerations in legacy `installer/scripts/install.sh` (lines 557, 834, 865-870). Consider retiring the shell installer path entirely if it's no longer supported. Independent of this feature.

3. **[TASK-REV-C7B9](../TASK-REV-C7B9-dotnet-minimal-template-variant-review.md)** — Design review for a potential `dotnet-minimal` variant to address the complexity 10/10 concern. This task depends on **TASK-DRF-003** (run only after the template has been registered and has had time to collect usage signal).

## Key References

- Review report: [.claude/reviews/TASK-REV-D0C1-review-report.md](../../../.claude/reviews/TASK-REV-D0C1-review-report.md)
- Convention reference: [installer/core/templates/python-library/](../../../installer/core/templates/python-library/)
- Convention reference: [installer/core/templates/langchain-deepagents/](../../../installer/core/templates/langchain-deepagents/)
- Source template: `~/.agentecflow/templates/dotnet-railway-fastendpoints/` (outside repo)
- CLI entry: [guardkit/cli/init.py:1710-1719](../../../guardkit/cli/init.py#L1710)
- Templates line in docs: [CLAUDE.md:223](../../../CLAUDE.md#L223)
