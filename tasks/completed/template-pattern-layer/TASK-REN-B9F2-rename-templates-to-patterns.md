---
id: TASK-REN-B9F2
title: Rename templates/ subdirectory to patterns/ across all templates and consumers (deferred)
status: closed
created: 2026-04-11T15:15:00Z
updated: 2026-04-11T18:00:00Z
priority: low
tags: [templates, rename, cleanup, deferred, cross-cutting, closed, wont-do]
parent_review: TASK-REV-A5F8
feature_id: FEAT-1A5E
implementation_mode: task-work
complexity: 5
depends_on: [TASK-PAT-1A5E]
closed_by: TASK-TPL-007
closed_reason: "Consumer exists, no rename needed. FEAT-TPL-PLAYER (TASK-TPL-001 through TASK-TPL-004) implemented the AutoBuild Player as the consumer of templates/*.template files. Per Decision D6 in the FEAT-TPL-PLAYER specification: 'The templates/ directory in each builtin template is not renamed. Now that these files have a proper consumer, templates/ is accurate — they are template files.' The name collision concern (templates/{name}/templates/) is mitigated by the documentation added in TASK-TPL-007. Renaming would introduce unnecessary churn across 10+ template packages, all agent cross-references, and the consumer code for zero functional gain."
---

# Task: Rename `templates/` subdirectory to `patterns/` across all templates and consumers

> **Closed: will not implement.** Consumer exists, no rename needed. See `closed_reason` in frontmatter for full rationale.

## Background

Surfaced by [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md) as TASK-DRF-F4B8b. See [review report](../../../.claude/reviews/TASK-REV-A5F8-review-report.md) Section 1 "Recommended F4B8 plan".

The current directory name `templates/` collides with the concept of "templates" one level up (the template package itself: `installer/core/templates/{name}/templates/...`). New contributors regularly misread it as "Yeoman-style project scaffolds that `init` will expand", and it was a factor in TASK-REV-D0C1's smoke-test confusion and TASK-REV-A5F8's scope expansion.

Once [TASK-PAT-1A5E](TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md) lands and the AutoBuild Player is reading these files as stack-pattern guidance, the name `patterns/` becomes the natural fit. This task delivers the rename.

## Deferral justification

**This is pure directory-renaming work with no functional change.** It is worth doing only if:

1. TASK-PAT-1A5E has landed (not just design-approved — must be in main so the rename does not conflict with in-flight wiring work)
2. TASK-DOC-C3D7's `templates/README.md` stubs did NOT prove sufficient to disambiguate the name in practice
3. Someone has bandwidth for a coordinated cross-file rename pass

If any of those are false, this task should stay deferred or be dropped entirely. It is filed so the decision is visible, not because it must happen.

## Description

Rename `templates/` to `patterns/` across the entire GuardKit codebase: template packages, producer code, consumer code, agent documentation cross-references, and user-facing docs.

## Acceptance Criteria

### Template packages (10 builtins)

- [ ] `installer/core/templates/default/templates/` → `patterns/`
- [ ] `installer/core/templates/dotnet-railway-fastendpoints/templates/` → `patterns/`
- [ ] `installer/core/templates/fastapi-python/templates/` → `patterns/`
- [ ] `installer/core/templates/fastmcp-python/templates/` → `patterns/`
- [ ] `installer/core/templates/langchain-deepagents/templates/` → `patterns/`
- [ ] `installer/core/templates/mcp-typescript/templates/` → `patterns/`
- [ ] `installer/core/templates/nats-asyncio-service/templates/` → `patterns/`
- [ ] `installer/core/templates/nextjs-fullstack/templates/` → `patterns/`
- [ ] `installer/core/templates/python-library/templates/` → `patterns/`
- [ ] `installer/core/templates/react-fastapi-monorepo/templates/` → `patterns/`
- [ ] `installer/core/templates/react-typescript/templates/` → `patterns/`

### Producer code (`/template-create`)

- [ ] [installer/core/lib/template_generator/template_generator.py](../../../installer/core/lib/template_generator/template_generator.py) — any hardcoded `templates/` output path
- [ ] [installer/core/lib/template_generator/path_resolver.py](../../../installer/core/lib/template_generator/path_resolver.py) — any `templates/` path assumptions
- [ ] Any `.template` output path construction across `installer/core/lib/template_generator/`

### Consumer code (TASK-PAT-1A5E output)

- [ ] Any `templates/` path resolution added by TASK-PAT-1A5E (if that task references the old name, update)
- [ ] The `.guardkit/patterns/` injection path chosen by TASK-PAT-1A5E is unaffected (that path is new and should already be `patterns/`)

### Installer skip list

- [ ] [guardkit/cli/init.py:50-51](../../../guardkit/cli/init.py#L50) — update `_SKIP_DIRS = {"templates", "config", "docker"}` to `_SKIP_DIRS = {"patterns", "config", "docker"}` (and verify backward compatibility does NOT silently copy an old `templates/` directory from a stale template package)

### Agent cross-references

- [ ] Grep all agent `-ext.md` files under `installer/core/templates/*/agents/` for references to `templates/*` paths and update to `patterns/*`. Minimum known count: 16 references in dotnet-railway-fastendpoints agents (verified in TASK-REV-A5F8 review)
- [ ] Grep all agent base `.md` files under `installer/core/templates/*/agents/` likewise

### Documentation

- [ ] Update any docs written by TASK-DOC-C3D7 that referenced the old name
- [ ] Update `installer/core/templates/README.md` (if exists) and `docs/guides/template-layers-guide.md` (if exists)
- [ ] Grep root docs for any remaining references

### Verification

- [ ] `grep -r "templates/" installer/core/templates/` returns only matches that are part of the outer template package path (`installer/core/templates/{name}/...`), not the old inner subdirectory
- [ ] Fresh `guardkit init <template>` smoke test on 3 representative templates (python, dotnet, react) — no regression
- [ ] `/template-create` smoke test — output lands in `patterns/`, not `templates/`
- [ ] AutoBuild smoke test — Player still receives patterns correctly post-rename

## Must NOT

- [ ] Must not rename without running this after TASK-PAT-1A5E has landed — a mid-flight rename would stall PAT-1A5E
- [ ] Must not rename the outer `installer/core/templates/` directory (that is the template package directory, and is correctly named)
- [ ] Must not introduce a backward-compatibility shim that reads BOTH old and new names — delete the old and update atomically

## References

- Parent review: [TASK-REV-A5F8](../../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md)
- Review report: [.claude/reviews/TASK-REV-A5F8-review-report.md](../../../.claude/reviews/TASK-REV-A5F8-review-report.md)
- Dependency: [TASK-PAT-1A5E](TASK-PAT-1A5E-wire-template-patterns-into-autobuild-player.md) (must have landed)
- Related: [TASK-DOC-C3D7](TASK-DOC-C3D7-document-two-layer-template-model.md)
