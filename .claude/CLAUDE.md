# GuardKit - Lightweight Task Workflow System

## Project Context

This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.

For formal agentic system development (LangGraph, multi-agent coordination), GuardKit integrates with RequireKit to provide EARS notation, BDD scenarios, and requirements traceability.

## Technology Stack Detection

The system will detect your project's technology stack and apply appropriate testing strategies:
- React/TypeScript → Playwright + Vitest
- Python API → pytest (pytest-bdd for BDD mode)
- .NET → xUnit/NUnit + platform-specific testing
- Mobile → Platform-specific testing
- Infrastructure → Terraform testing

## References

- Core principles, workflows, commands: See root `CLAUDE.md`
- Clarifying questions: See `.claude/rules/clarifying-questions.md`
- Progressive disclosure: Core files (`{name}.md`) always load; extended files (`{name}-ext.md`) load on-demand
