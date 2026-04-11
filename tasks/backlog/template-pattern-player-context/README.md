# FEAT-TPL-PLAYER — Template Pattern Layer (AutoBuild Player Context)

Gives the AutoBuild Player access to parameterised `.template` files from the project's source template at build time, so generated code follows the template's canonical patterns rather than relying solely on agent prose descriptions.

## Source
- **Spec:** [docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md](../../../docs/features/FEAT-TPL-PLAYER-template-pattern-player-context.md)
- **Review:** [tasks/in_review/TASK-REV-B3F7-plan-template-pattern-player-context.md](../../in_review/TASK-REV-B3F7-plan-template-pattern-player-context.md)
- **Guide:** [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)

## Tasks

| ID | Title | Wave | Complexity | Type |
|----|-------|------|------------|------|
| [TASK-TPL-001](TASK-TPL-001-extract-template-resolver.md) | Extract template resolver into shared module | 1 | 3 | refactor |
| [TASK-TPL-002](TASK-TPL-002-template-pattern-loader-core.md) | Template pattern loader core + `TemplatePatternContext` | 2 | 5 | feature |
| [TASK-TPL-003](TASK-TPL-003-domain-hint-selector.md) | Domain-hint selector (tech_stack + file-path) | 3 | 5 | feature |
| [TASK-TPL-004](TASK-TPL-004-wire-into-autobuild-context-loader.md) | Wire into `AutoBuildContextLoader` + logging | 4 | 4 | feature |
| [TASK-TPL-005](TASK-TPL-005-unit-tests.md) | Unit tests | 4 | 4 | testing |
| [TASK-TPL-006](TASK-TPL-006-integration-test.md) | Integration test + seam tests | 5 | 5 | testing |
| [TASK-TPL-007](TASK-TPL-007-documentation.md) | Documentation | 5 | 3 | documentation |

## Execution

```bash
# Autonomous via AutoBuild
/feature-build FEAT-TPL-PLAYER

# Or manual
/task-work TASK-TPL-001
```

## Key corrections from spec

Three codebase-verification findings corrected the spec before decomposition (see review TASK-REV-B3F7):

- **F1:** manifest field is `name` (not `template`)
- **F2:** manifest at `.claude/manifest.json` (not `.guardkit/manifest.json`)
- **F3:** loader lives in `guardkit/knowledge/` (no `guardkit/autobuild/` package exists); selection uses `TaskCharacteristics.tech_stack` + file-path hints instead of a non-existent `domain_tags` field
