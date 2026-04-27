# Changelog

All notable changes to GuardKit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

#### AutoBuild: `bootstrap_failure_mode` smart default (TASK-ABSR-A1B2)

When neither `.guardkit/config.yaml` (`autobuild.bootstrap.failure_mode`) nor
the `--bootstrap-failure-mode` CLI flag set an explicit value, GuardKit now
resolves the bootstrap failure-mode from detected manifests:

- **`block`** when any manifest declares a `requires-python` constraint —
  matches the case where pip would otherwise fail with an interpreter
  mismatch and (for `task_type=declarative` + `implementation_mode=task-work`
  tasks) trap the run in a feedback-stall trapdoor.
- **`warn`** otherwise (preserves prior behaviour for projects without a
  `requires-python` declaration).

**Why**: closes the failure class identified in TASK-REV-FA04 — silent
continuation past a Python interpreter mismatch that produced
`installs_failed=1, installs_attempted=1` and stalled FEAT-J004-702C. With
the smart default in place, the existing requires-python pre-check raises
`FeatureOrchestrationError` before Wave 1 starts, naming `uv python install`,
`pyenv install`, and `conda create` as remediation paths.

**Impact**: any consumer with `requires-python` declared in their manifests
who relied on the previous warn-by-default behaviour will now see a hard
stop at preflight when their active interpreter doesn't satisfy the
constraint.

**Opt-out**: set `bootstrap_failure_mode: warn` explicitly in
`.guardkit/config.yaml` under `autobuild.bootstrap`, or pass
`--bootstrap-failure-mode warn` on the command line. Both routes are
documented in the existing remediation hint emitted by the gate.

The `BOOTSTRAP_FAILURE_MODES = ("block", "warn")` tuple is unchanged — the
smart default is *which* of those two is returned by default, not a new
mode.

#### Installer: Manifest-Driven CLI Symlinks (TASK-ISH-D09E)

`installer/scripts/install.sh` no longer blindly walks `installer/core/commands/`
and `installer/core/commands/lib/` and creates a `~/.agentecflow/bin/` symlink
for every `.py` file it encounters. The walk is replaced by an explicit
manifest at **`installer/core/commands/bin-entries.txt`** which is the sole
source of truth for which Python scripts become user-facing CLI commands.

**Why**: The old blind walk silently promoted ~60 internal library modules
(`agent_discovery`, `task_breakdown`, `plan_modifier`, `phase_execution`, ...)
to global shell commands even though they are imports, not CLI entry points.
It also kept dead handlers for abandoned commands (e.g.
`upfront_complexity_cli`) alive long after their slash-command counterparts
were removed. The blind walk was the structural reason dead shims went
unnoticed in the audits behind TASK-REV-C1B4.

**What's still installed** (unchanged for users):

- Top-level commands: `agent-enhance`, `agent-format`, `agent-validate`
- Library-resident CLIs: `graphiti-diagnose`
- Wrapper scripts (created by `create_cli_commands`, untouched by this change):
  `guardkit`, `guardkit-init`, `gk`, `gki`, `graphiti-check`

**What's removed on next reinstall** — 62 symlinks in `~/.agentecflow/bin/`
that pointed at internal library modules and were never intended to be run
from a shell. The full list (each is a `~/.agentecflow/bin/<name>` symlink
pointing into `installer/core/commands/lib/`):

```
agent-discovery, agent-invocation-tracker, agent-invocation-validator,
agent-utils, api-call-preview, breakdown-strategies, change-tracker,
checkpoint-display, complexity-calculator, complexity-factors,
complexity-models, constants, distribution-helpers, duplicate-detector,
error-messages, feature-detection, flag-validator, generate-feature-yaml,
git-state-helper, graphiti-context-loader, greenfield-qa-session,
library-context, library-detector, micro-task-detector, micro-task-workflow,
modification-applier, modification-persistence, modification-session,
pager-display, phase-execution, phase-gate-validator, plan-audit,
plan-markdown-parser, plan-markdown-renderer, plan-modifier, plan-persistence,
qa-manager, refinement-handler, review-mode-executor, review-modes,
review-report-generator, review-router, spec-drift-detector, split-models,
task-breakdown, task-completion-helper, task-review-orchestrator,
task-split-advisor, task-utils, template-create-orchestrator, template-merger,
template-packager, template-qa-display, template-qa-persistence,
template-qa-questions, template-qa-session, template-qa-validator,
template-versioning, user-interaction, version-manager, visualization,
worktree-cleanup
```

If you have shell history, scripts, or muscle memory invoking any of these
as commands, they will stop resolving after the next reinstall. None of
them have a documented public interface — they were never advertised as
CLIs — so the migration path is to call the corresponding Python module
via `python -m installer.core.commands.lib.<module_name>` or import it
from a Python script.

**Adding a new CLI**: create the script with a `main()` function or an
`if __name__ == "__main__":` block, then add its repo-relative path to
`installer/core/commands/bin-entries.txt` and re-run `install.sh`. Files
not in the manifest still trigger an informational warning during install
("File not in bin-entries.txt — will not be exposed as a CLI"), so drift
is visible at install time.

Builds on TASK-FIX-CF8D's prune pass (which removes the now-unlisted
symlinks on reinstall).


#### Template Overhaul

Reduced template count from 10 to 8, removing low-quality templates based on comprehensive audit findings.

**Removed Templates**:
- `dotnet-aspnetcontroller` (scored 6.5/10) - Traditional ASP.NET MVC Controller pattern
  - **Reason**: Redundant with `dotnet-fastendpoints` and `dotnet-minimalapi`, uses legacy MVC pattern
  - **Migration**: Use `dotnet-fastendpoints` for modern REPR pattern with FastEndpoints
  - **Alternative**: Use `dotnet-minimalapi` for lightweight .NET APIs
- `default` (scored 6.0/10) - Language-agnostic generic template
  - **Reason**: Too generic, provides minimal architectural guidance
  - **Migration**: Choose technology-specific template (react, python, typescript-api, etc.)
  - **Alternative**: Create custom template with `/template-create` command

**Migration Path**:
See [Template Migration Guide](docs/guides/template-migration.md) for detailed migration instructions, code examples, and FAQ.

**Archived Templates**:
Old templates are preserved in git tag `v1.9-templates-before-removal` for reference or recovery.

### Kept Templates (8 Total)

**High Quality (8+/10)** - Reference implementations:
- `maui-appshell` (8.8/10) - .NET MAUI + AppShell navigation
- `maui-navigationpage` (8.5/10) - .NET MAUI + NavigationPage
- `fullstack` (8.0/10) - React + Python full-stack

**Medium Quality (6-7.9/10)** - Functional, being improved:
- `react` (7.5/10) - React + TypeScript + Next.js
- `python` (7.5/10) - FastAPI + pytest + LangGraph
- `typescript-api` (7.2/10) - NestJS + Domain modeling
- `dotnet-fastendpoints` (7.0/10) - FastEndpoints + REPR pattern
- `dotnet-minimalapi` (6.8/10) - .NET Minimal API + Vertical slices

### Rationale

**Quality Over Quantity**: Focus on fewer, higher-quality reference implementations based on production-proven patterns.

**Audit Findings**: Comprehensive 16-section validation (TASK-056) revealed:
- Only 30% of templates met 8+/10 quality threshold
- `dotnet-aspnetcontroller` was redundant with modern alternatives
- `default` provided insufficient value compared to technology-specific templates

**Strategy**: Developers should use technology-specific templates or create custom templates from their production codebases using `/template-create`.

See [Template Strategy Decision](docs/research/template-strategy-decision.md) and [Template Audit Comparative Analysis](docs/research/template-audit-comparative-analysis.md) for complete analysis.

---

## [1.0.0] - 2025-01-08

### Added

- **Task Management System**: Complete workflow with phases 2-5.5
- **Quality Gates**: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- **Design-First Workflow**: Optional `--design-only` and `--implement-only` flags
- **Complexity Evaluation**: 0-10 scale with automatic checkpoint determination
- **Template System**: 10 initial project templates covering multiple stacks
- **Template Validation**: 3-level validation system (automatic, extended, comprehensive)
- **Plan Audit**: Scope creep detection and variance analysis (Phase 5.5)
- **AI Agents**: Core global agents (architectural-reviewer, task-manager, test-orchestrator, code-reviewer)
- **Stack-Specific Agents**: Specialized agents for React, Python, .NET, TypeScript
- **Conductor Integration**: Symlink architecture for parallel development
- **Migration Guides**: Template migration paths and custom template creation

### Documentation

- Complete workflow guides
- Template validation guide
- MCP optimization guide
- Complexity management workflow
- Design-first workflow
- UX design integration workflow

---

## Release Notes

### v1.0.0 - Initial Release

First public release of GuardKit, a lightweight AI-assisted development workflow system.

**Core Features**:
- Task workflow (create → work → complete)
- Quality gates (architectural review, test enforcement)
- Template system (10 templates)
- AI agent ecosystem (10+ agents)
- Conductor.build integration

**Philosophy**:
- Quality first, pragmatic approach
- AI/human collaboration
- Zero ceremony
- Fail fast

---

## Migration Support

For questions about template removal or migration:
- See [Template Migration Guide](docs/guides/template-migration.md)
- Report issues: [GitHub Issues](https://github.com/guardkit/guardkit/issues)
- Ask questions: [GitHub Discussions](https://github.com/guardkit/guardkit/discussions)

---

**Changelog Maintenance**: This file is updated with each release. See [git commits](https://github.com/guardkit/guardkit/commits) for detailed change history.
