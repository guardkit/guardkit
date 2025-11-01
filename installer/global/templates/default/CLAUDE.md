# Project Context for Claude Code

This project uses the AI Engineer v2.0 system with the unified task workflow for streamlined development.

## Project Overview
[Describe your project here]

## Architecture
[Describe your system architecture]

## Key Technologies
- [List main technologies]

## Development Workflow - Simplified Task System

### The Streamlined Workflow
We use a unified task workflow that combines implementation and testing into an inseparable process:

```bash
# 1. Create Task
/task-create "Feature description"
/task-create "Add authentication" priority:high

# 2. Work on Task (Implementation + Testing Combined)
/task-work TASK-XXX [--mode=standard|tdd|bdd]

# 3. Complete Task
/task-complete TASK-XXX
```

### Development Modes

#### Standard Mode (Default)
- Implementation and tests created together
- Suitable for straightforward features
- Tests run automatically after implementation

#### TDD Mode
- Red-Green-Refactor cycle
- Tests written first, then implementation
- Best for complex business logic

#### BDD Mode
- Start from Gherkin scenarios
- Generate step definitions
- Best for user-facing features

### Quality Gates (Automatic)
Every task must pass these gates before completion:
- ✅ All tests passing (100%)
- ✅ Code coverage ≥ 80%
- ✅ Performance benchmarks met
- ✅ No security vulnerabilities
- ✅ All acceptance criteria satisfied

## Core Task Commands

### Task Management (Unified Workflow)
- `/task-create` - Create new task
- `/task-work` - Implement and test (unified command)
- `/task-complete` - Finalize task after review

### State Management
- `/task-status` - View task board
- `/update-state` - Update sprint progress

## Project Standards

### Code Quality
- **Minimum 80% test coverage** (enforced automatically)
- **All tests must pass** (enforced by /task-work)
- **TDD/BDD practices** supported natively
- **Quality gates** prevent low-quality code

### Documentation
- **ADRs** for architectural decisions
- **Automatic test reports** from /task-work

### Testing Philosophy
**"Implementation and testing are inseparable"** - Every implementation includes tests, enforced by the unified workflow.

## Project Structure

```
.
├── .claude/          # AI Engineer configuration
│   ├── agents/       # AI specialists
│   ├── commands/     # Available commands
│   ├── templates/    # File templates
│   └── settings.json # Project settings
├── docs/            # All documentation
│   ├── adr/         # Architecture decisions
│   └── state/       # Progress tracking
├── tasks/           # Task management
│   ├── backlog/     # Not started
│   ├── in_progress/ # Active work
│   ├── in_review/   # Pending review
│   ├── blocked/     # Failed quality gates
│   └── completed/   # Archived tasks
├── src/             # Source code
└── tests/           # Test suites
    ├── unit/        # Unit tests
    ├── integration/ # Integration tests
    └── e2e/         # End-to-end tests
```

## Quick Start

### Starting a New Feature
```bash
# 1. Create task
/task-create "Implement user login" priority:high

# 2. Work on task with your preferred mode
/task-work TASK-001 --mode=tdd

# 3. Complete after review
/task-complete TASK-001
```

### Working on Existing Task
```bash
# View available tasks
/task-status

# Work on a task (auto-detects technology stack)
/task-work TASK-042

# If tests fail, fix and retry
/task-work TASK-042 --fix-only

# Complete when all quality gates pass
/task-complete TASK-042
```

## Best Practices

1. **Choose the right mode**: TDD for logic, BDD for features, Standard for simple tasks
2. **Let quality gates guide you**: They ensure consistent quality
3. **Trust the workflow**: Implementation and testing together prevent bugs
4. **Document decisions**: Use ADRs for important choices

## Why the Unified Workflow?

The streamlined workflow delivers:
- **Simple task creation** - no complex hierarchies required
- **100% test guarantee** - testing is automatic, not optional
- **Faster delivery** - from idea to completed task
- **Zero manual errors** - quality gates and state management are automatic
- **Development flexibility** - choose Standard, TDD, or BDD mode based on needs

## Support and Documentation

- **User Guide**: `docs/guides/AI-ENGINEER-USER-GUIDE.md`
- **Quick Reference**: `.claude/TASK-WORKFLOW-QUICK-REFERENCE-V2.md`

Remember: **"Implementation and testing are inseparable"** - this is the core philosophy of the unified workflow.
