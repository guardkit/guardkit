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

## Clarifying Questions

GuardKit asks targeted clarifying questions before making assumptions during planning, reducing rework by ~15%.

### When Questions Trigger

Questions are gated by task complexity:
- **Complexity 1-2**: Skip (simple tasks)
- **Complexity 3-4**: Quick questions (15s timeout)
- **Complexity 5+**: Full questions (blocking)

### Three Contexts

1. **Review Scope** (`/task-review`, `/feature-plan`) - Before analysis
2. **Implementation Prefs** (`/feature-plan` [I]mplement) - Before subtask creation
3. **Implementation Planning** (`/task-work`) - Before planning (Phase 1.5)

### Control Flags

All commands support:
- `--no-questions` - Skip clarification
- `--with-questions` - Force clarification
- `--defaults` - Use defaults without prompting
- `--answers="..."` - Inline answers for automation
- `--reclarify` - Re-run even if saved

### Persistence

Decisions are saved to task frontmatter for audit trail and reproducibility.

See main CLAUDE.md for detailed examples and troubleshooting.

## Progressive Disclosure

GuardKit uses progressive disclosure to optimize context window usage while maintaining comprehensive documentation.

### How It Works

Agent and template files are split into:

1. **Core files** (`{name}.md`): Essential content always loaded
   - Quick Start examples (5-10)
   - Boundaries (ALWAYS/NEVER/ASK)
   - Capabilities summary
   - Phase integration
   - Loading instructions

2. **Extended files** (`{name}-ext.md`): Detailed reference loaded on-demand
   - Detailed code examples (30+)
   - Best practices with full explanations
   - Anti-patterns with code samples
   - Technology-specific guidance
   - Troubleshooting scenarios

### Loading Extended Content

When implementing detailed code, load the extended reference:

```bash
# For agents
cat agents/{agent-name}-ext.md

# For template patterns
cat docs/patterns/README.md

# For reference documentation
cat docs/reference/README.md
```

### Benefits

- **55-60% token reduction** in typical tasks
- **Faster responses** from reduced context
- **Same comprehensive content** available when needed
- **Competitive positioning** vs other AI dev tools

### For Template Authors

When creating templates with `/template-create`:
- CLAUDE.md is automatically split into core + docs/
- Agent files are automatically split during `/agent-enhance`
- Use `--no-split` flag for single-file output (not recommended)

### Guidance Architecture

When working with templates:
- **`agents/`** = Source of truth (full content, 6-12KB)
- **`rules/guidance/`** = Derived summary (slim, <3KB)

Never edit guidance files directly - they are regenerated from agents.

See [Progressive Disclosure Guide](../docs/guides/progressive-disclosure.md) for details.
