# Taskwright - Lightweight Task Workflow System

## Project Context

This is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. The system is technology-agnostic with stack-specific plugins.

## Core Principles

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **Quality Gates**: Automated architectural review and test enforcement
4. **State Tracking**: Transparent progress monitoring through markdown
5. **Technology Agnostic**: Core methodology works across all stacks

## System Philosophy

- Start simple, iterate toward complexity
- Markdown-driven for human and AI readability
- Verification through actual test execution
- Lightweight Architecture Decision Records
- Comprehensive changelogs for traceability

## Workflow Overview

1. **Create Task**: Define what needs to be done
2. **Work on Task**: AI implements with quality gates (Phases 2-5.5)
3. **Review**: Human reviews approved implementation
4. **Complete**: Archive and track

## Technology Stack Detection

The system will detect your project's technology stack and apply appropriate testing strategies:
- React/TypeScript → Playwright + Vitest
- Python API → pytest
- .NET → xUnit/NUnit + platform-specific testing
- Mobile → Platform-specific testing
- Infrastructure → Terraform testing

## Getting Started

Run `/task-create "Your task"` to begin a new task, then use `/task-work TASK-XXX` to implement it with automatic quality gates.

## Development Mode Selection

TaskWright supports three development modes:

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

**Use BDD for agentic orchestration systems**:
- Requires RequireKit installation
- Delegates to bdd-generator agent
- EARS → Gherkin → Implementation workflow
- Full requirements traceability

**When to use**:
```python
# Example: LangGraph state routing
if building_state_machine or safety_critical or formal_spec_needed:
    use_bdd_mode = True
else:
    use_standard_or_tdd = True
```

**Plugin Discovery**:
```python
from lib.feature_detection import supports_bdd

if supports_bdd():  # Checks ~/.agentecflow/require-kit.marker
    # RequireKit available, BDD mode enabled
    execute_bdd_workflow()
else:
    # RequireKit not installed
    show_installation_guidance()
```

**BDD Workflow**:
1. Create requirements in RequireKit (EARS notation)
2. Generate Gherkin scenarios (`/generate-bdd REQ-001`)
3. Link scenarios in task frontmatter (`bdd_scenarios: [BDD-001]`)
4. Execute BDD mode (`/task-work TASK-042 --mode=bdd`)
5. BDD tests run as quality gate (100% pass required)

**Example Use Cases**:
- LangGraph state machines with complexity-based routing
- Multi-agent coordination workflows
- Quality gate orchestration with approval checkpoints
- Safety-critical authentication/authorization logic

**Not for**:
- CRUD features
- Simple UI components
- Bug fixes
- General refactoring

See [BDD Workflow for Agentic Systems](../docs/guides/bdd-workflow-for-agentic-systems.md) for complete guide.
