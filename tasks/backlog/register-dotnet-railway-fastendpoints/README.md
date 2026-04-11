# Feature: Register dotnet-railway-fastendpoints Template

**Feature ID**: FEAT-D0C1
**Parent Review**: TASK-REV-D0C1
**Status**: Planned — awaiting execution
**Review score**: 82/100 (REFACTOR THEN REGISTER)

## Problem

GuardKit has no C#/.NET builtin template. A new `dotnet-railway-fastendpoints` template was created via `/template-create` from a modern .NET Modular Monolith exemplar (Railway-Oriented Programming, FastEndpoints, Dapper, NATS, Keycloak, xUnit+Testcontainers), currently sitting at `~/.agentecflow/templates/dotnet-railway-fastendpoints/`.

It must be:
1. Fixed for 4 blocker issues (phantom agent dependency, hardcoded author, hardcoded "Exemplar" layer paths, leaked absolute source path)
2. Copied into `installer/core/templates/`
3. Registered in the 2 hardcoded template lists (CLAUDE.md, init.py docstring)
4. Validated end-to-end via `/template-validate` and a scaffolding smoke test

## Solution

Sequential 3-wave implementation that fixes the template at its source first, then copies + registers, then validates. No parallelism — each wave strictly depends on the previous wave's output.

## Subtasks

| ID | Title | Wave | Mode | Priority | Depends On |
|----|-------|------|------|----------|------------|
| [TASK-DRF-001](TASK-DRF-001-fix-source-template-blockers.md) | Fix blocker issues in source template | 1 | direct | high | — |
| [TASK-DRF-002](TASK-DRF-002-copy-and-register-template.md) | Copy into installer/core and register in docs | 2 | direct | high | DRF-001 |
| [TASK-DRF-003](TASK-DRF-003-validate-and-smoke-test.md) | Validate and smoke-test registered template | 3 | direct | high | DRF-002 |
| [TASK-DRF-004](TASK-DRF-004-shorten-display-name.md) | Shorten verbose `display_name` in registered manifest (cosmetic) | 3 | direct | low | DRF-002 |

**Total estimated effort**: ~60-90 minutes sequential for DRF-001→002→003. DRF-004 is ~5 min cosmetic polish, can run in parallel with or after DRF-003.

## Related Follow-Up Tasks (Standalone)

These are cross-cutting cleanup / design tasks filed separately in `tasks/backlog/`. They're not blockers for this feature and can run independently:

| Task | Scope | Blocks this feature? |
|------|-------|----------------------|
| [TASK-TSE-8A1C](../TASK-TSE-8A1C-fix-stale-expected-templates-set.md) | Fix stale `test_seed_enrichment.py` `EXPECTED_TEMPLATES` set (missing 6+ templates) | No |
| [TASK-ISH-3F02](../TASK-ISH-3F02-update-legacy-install-sh-template-lists.md) | Update 3 stale template lists in legacy `install.sh` | No |
| [TASK-REV-C7B9](../TASK-REV-C7B9-dotnet-minimal-template-variant-review.md) | Design review — split into minimal/full variants? (depends on DRF-003) | No |

**Note**: `/agent-enhance` has **already been run** on all 7 template agents (verified by presence of `-ext.md` files with code examples). No further agent work is needed.

## Key References

- [Review report](../../../.claude/reviews/TASK-REV-D0C1-review-report.md)
- [Implementation guide](IMPLEMENTATION-GUIDE.md)
- Source template: `~/.agentecflow/templates/dotnet-railway-fastendpoints/`
- Convention reference: [python-library](../../../installer/core/templates/python-library/)

## Next Steps

1. Read [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
2. Start with TASK-DRF-001 (`/task-work TASK-DRF-001`)
3. Work through sequentially — DRF-002 and DRF-003 must wait for their dependencies
