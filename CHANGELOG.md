# Changelog

All notable changes to GuardKit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

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
