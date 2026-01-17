# GuardKit - Lightweight Task Workflow System

## Project Context

This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.

For formal agentic system development (LangGraph, multi-agent coordination), GuardKit integrates with RequireKit to provide EARS notation, BDD scenarios, and requirements traceability.

## Core Principles

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **Quality Gates**: Automated architectural review and test enforcement
4. **State Tracking**: Transparent progress monitoring through markdown
5. **Technology Agnostic**: Core methodology works across all stacks
6. **Optional Formality**: Standard workflow for features, BDD workflow for agentic systems

## System Philosophy

- Start simple, iterate toward complexity
- Markdown-driven for human and AI readability
- Verification through actual test execution
- Lightweight Architecture Decision Records
- Comprehensive changelogs for traceability

## Workflow Overview

### Standard Workflow (Most Tasks)
1. **Create Task**: Define what needs to be done
2. **Work on Task**: AI implements with quality gates (Phases 2-5.5)
3. **Review**: Human reviews approved implementation
4. **Complete**: Archive and track

### BDD Workflow (Agentic Systems - Requires RequireKit)
1. **Formalize Requirements**: Create EARS requirements in RequireKit
2. **Generate Scenarios**: Convert EARS → Gherkin scenarios
3. **Implement with BDD**: Run `/task-work TASK-XXX --mode=bdd`
4. **Verify**: BDD tests ensure requirements met
5. **Complete**: Archive with full traceability

**Use BDD for**: LangGraph state machines, safety-critical workflows, formal behavior specifications
**Use Standard for**: General features, bug fixes, UI components, CRUD operations

## Technology Stack Detection

The system will detect your project's technology stack and apply appropriate testing strategies:
- React/TypeScript → Playwright + Vitest
- Python API → pytest (pytest-bdd for BDD mode)
- .NET → xUnit/NUnit + platform-specific testing
- Mobile → Platform-specific testing
- Infrastructure → Terraform testing

## Getting Started

### Standard Tasks
Run `/task-create "Your task"` to begin a new task, then use `/task-work TASK-XXX` to implement it with automatic quality gates.

### BDD Mode (Agentic Systems)
For formal agentic systems, first install RequireKit:
```bash
cd ~/Projects/require-kit
./installer/scripts/install.sh
```

Then use BDD workflow:
```bash
# In RequireKit: Create requirements
/req-create "System behavior"
/formalize-ears REQ-001
/generate-bdd REQ-001

# In GuardKit: Implement from scenarios
/task-create "Implement behavior" requirements:[REQ-001]
/task-work TASK-042 --mode=bdd
```

See [BDD Workflow for Agentic Systems](../docs/guides/bdd-workflow-for-agentic-systems.md) for complete details.

## Development Mode Selection

GuardKit supports three development modes:

### Standard Mode (Default)
```bash
/task-work TASK-042
```
Use for straightforward implementations, CRUD features, simple UI components.

### TDD Mode
```bash
/task-work TASK-042 --mode=tdd
```
Use for complex business logic, algorithms, features with clear test cases.

### BDD Mode (Agentic Systems)
```bash
/task-work TASK-042 --mode=bdd
```

**Use BDD for**: LangGraph state machines, multi-agent coordination, safety-critical logic.
**Requires**: RequireKit installation (`~/.agentecflow/require-kit.marker`).
**Not for**: CRUD features, simple UI, bug fixes, general refactoring.

See [BDD Workflow for Agentic Systems](../docs/guides/bdd-workflow-for-agentic-systems.md) for complete guide.

## Clarifying Questions

See: `.claude/rules/clarifying-questions.md` for details on complexity gating, control flags, and persistence.

## Progressive Disclosure

Core files (`{name}.md`) always load; extended files (`{name}-ext.md`) load on-demand.
See root CLAUDE.md for detailed structure.
