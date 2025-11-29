# Getting Started with Taskwright

## Welcome to Lightweight Task Workflow!

Taskwright is an AI-powered task workflow system with built-in quality gates that prevents broken code from reaching production. Work on individual tasks with automatic architectural review, test enforcement, and quality verification.

## Quick Start (5 Minutes!)

### Step 1: Initialize Your Project
```bash
# Clone and setup
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh
```

> **Using Claude Code Web?** See the [Claude Code Web Setup Guide](claude-code-web-setup.md) for detailed web-specific instructions including persistence and multi-repository usage.

### Step 2: Create Your First Task (in Claude Code)
```bash
# Create a task
/task-create "Add user authentication"

# Work on it (automatic planning + implementation + testing)
/task-work TASK-001

# Complete it
/task-complete TASK-001
```

That's it! The `/task-work` command handles planning, implementation, architectural review, testing, and quality verification automatically.

## Documentation Structure

```
docs/
├── guides/
│   ├── GETTING-STARTED.md         # This guide (START HERE!)
│   ├── taskwright-workflow.md     # Complete workflow guide
│   ├── creating-local-templates.md # Template customization
│   └── template-philosophy.md     # Why these templates?
├── workflows/
│   ├── complexity-management-workflow.md
│   ├── quality-gates-workflow.md
│   └── task-review-workflow.md
└── Landing pages: concepts.md, advanced.md, templates.md, agents.md
```

## What is Taskwright?

### The Core Features

**Workflow Automation**:
- Creates implementation plans automatically
- Performs architectural review (SOLID/DRY/YAGNI)
- Evaluates task complexity (1-10 scale)
- Implements code based on approved plans
- Runs comprehensive test suites
- Enforces quality gates (100% test pass, ≥80% coverage)

**State Management**:
```
BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED
            ↓              ↓
         BLOCKED        BLOCKED
```

**Available Templates** (4 high-quality):
- **react-typescript**: React + TypeScript (from Bulletproof React, 9.3/10)
- **fastapi-python**: FastAPI + pytest (from best practices, 9.2/10)
- **nextjs-fullstack**: Next.js App Router (full-stack, 9.4/10)
- **default**: Language-agnostic (Go, Rust, Ruby, etc., 8.0+/10)

**For Production**: Use `/template-create` from your own codebase

## The Complete Development Flow

### 1. Create a Task
```bash
# Simple task creation
/task-create "Feature name"

# With priority
/task-create "Critical bug fix" priority:critical

# With tags
/task-create "Add logging" tags:infrastructure,logging
```

### 2. Work on the Task (One Command!)
```bash
# Standard mode (default)
/task-work TASK-001

# TDD mode (for complex logic)
/task-work TASK-001 --mode=tdd

# Design-first workflow (for complex tasks)
/task-work TASK-001 --design-only
# [Review and approve plan]
/task-work TASK-001 --implement-only
```

### 3. Complete the Task
```bash
# After review
/task-complete TASK-001
```

## Key Features Explained

### Automatic Quality Gates
| Gate | Threshold | Enforcement |
|------|-----------|-------------|
| Compilation | 100% | Required |
| Tests Pass | 100% | Required |
| Line Coverage | ≥80% | Required |
| Branch Coverage | ≥75% | Required |
| Architectural Review | ≥60/100 | Required |

### Smart State Management
```
Tests Pass + Coverage Good → IN_REVIEW
Tests Fail → BLOCKED (auto-fix up to 3 attempts)
Coverage Low → Stay IN_PROGRESS
Architectural Issues → Human checkpoint
```

### Clear Feedback
```
✅ Task Work Complete - TASK-001
Tests: 15/15 passing
Coverage: 92%
Status: IN_PROGRESS → IN_REVIEW
Next: /task-complete TASK-001
```

## Real-World Example

### Implementing User Authentication with TDD

```bash
# 1. Create the task
/task-create "Implement user authentication" priority:high

# 2. Work on it with TDD
/task-work TASK-042 --mode=tdd

# Claude's response:
# 🔴 RED Phase: Creating 8 failing tests...
#    ❌ All tests failing (expected)
#
# 🟢 GREEN Phase: Implementing code...
#    ✅ 8/8 tests passing
#
# 🔵 REFACTOR Phase: Improving quality...
#    ✅ All tests still passing
#
# 📊 Coverage: 92%
# ✅ Task moved to IN_REVIEW

# 3. Complete the task
/task-complete TASK-042
```

Total time: ~2 minutes (vs ~10 minutes with manual workflow)

## Common Scenarios

### Scenario 1: Simple Feature
```bash
/task-create "Add user profile page"
/task-work TASK-050              # Standard mode by default
/task-complete TASK-050
```

### Scenario 2: Complex Business Logic
```bash
/task-create "Calculate tax rates"
/task-work TASK-051 --mode=tdd   # TDD for complex logic
/task-complete TASK-051
```

### Scenario 3: Bug Fix
```bash
/task-create "Fix login timeout" priority:critical
/task-work TASK-053               # Quick fix
/task-complete TASK-053
```

### Scenario 4: Design-First Workflow
```bash
/task-create "Refactor authentication system" priority:high
/task-work TASK-054 --design-only
# [Human reviews and approves plan]
/task-work TASK-054 --implement-only
/task-complete TASK-054
```

## Decision Tree

```
Need to implement a task?
    ↓
Is it complex (multiple files, new patterns)?
    Yes → /task-work --design-only (review plan first)
    No ↓
Is it complex business logic?
    Yes → /task-work --mode=tdd
    No → /task-work (standard)
```

## Common Workflows

Beyond the basic `/task-work` command, these specialized workflows handle specific scenarios:

**Trivial Tasks (typos, doc updates)**:
```bash
/task-work TASK-XXX --micro    # 3-5 min vs 15+ min, skips planning/review
```
Auto-detected for simple tasks. [Details: task-work.md](../../installer/global/commands/task-work.md#flag---micro)

**Iterative Refinement (minor tweaks)**:
```bash
/task-refine TASK-XXX          # Quick fixes after code review
```
For small adjustments without full re-work. [Details: Taskwright Workflow](taskwright-workflow.md#37-iterative-refinement)

**Analysis & Reviews (decisions, audits)**:
```bash
/task-review TASK-XXX --mode=architectural --depth=standard
```
For architectural reviews, security audits, technical decisions (no implementation). [Details: Task Review Workflow](../workflows/task-review-workflow.md)

> **Pro tip:** Start with `/task-work` for implementation. Use these specialized commands as you encounter specific needs.

## Essential Commands

### Task Commands
```bash
/task-create "name" [priority:high|medium|low] [tags:tag1,tag2]
/task-work TASK-XXX [--mode=standard|tdd] [--design-only|--implement-only]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Options for task-work
```bash
--mode=standard          # Default: implementation + tests
--mode=tdd              # Test-driven development cycle
--design-only           # Planning only (complex tasks)
--implement-only        # Implementation only (requires approved plan)
```

## Best Practices

1. **Keep tasks small** - 1-4 hour chunks work best
2. **Choose the right mode** - TDD for complex logic, standard for straightforward features
3. **Trust the process** - Let `/task-work` complete all phases
4. **Use design-first for complex tasks** - Review plans before implementation
5. **Review quality gates** - Don't skip architectural review feedback

## Quality Standards

All enforced automatically by `/task-work`:
- ✅ 100% of tasks have tests
- ✅ ≥80% code coverage
- ✅ All tests must pass
- ✅ Architectural review (SOLID/DRY/YAGNI)
- ✅ Proper documentation

## Technology Stack Support

**Reference templates** demonstrate patterns for:
- **react-typescript**: Vitest, Playwright, React Testing Library
- **fastapi-python**: pytest, FastAPI Test Client, Pydantic validation
- **nextjs-fullstack**: Vitest, Playwright, Next.js testing patterns
- **default**: Language-agnostic (configure for your stack)

**Your custom template** can use any stack via `/template-create`.

Reference templates for learning and evaluation:
```bash
# Stack-specific reference templates (9+/10 quality)
taskwright init react-typescript       # React + TypeScript (from Bulletproof React)
taskwright init fastapi-python         # FastAPI + pytest (from best practices)
taskwright init nextjs-fullstack       # Next.js App Router (full-stack)

# Language-agnostic template (8+/10 quality)
taskwright init default                # Go, Rust, Ruby, Elixir, PHP, etc.

# For production: Create from your codebase
cd your-production-codebase
/template-create
taskwright init your-custom-template
```

## Key Benefits

### Developer Experience
- **Fewer commands** to remember (3-step workflow)
- **50% faster** task completion
- **Zero** manual quality checks

### Code Quality
- **Automatic** architectural review
- **100%** test enforcement
- **Built-in** TDD support

### Team Collaboration
- **Clear** task states
- **Transparent** progress
- **Consistent** standards

## Getting Help

### Quick Help
```bash
/task-work --help           # Command help
/task-status               # View all tasks
```

### Documentation
- [Claude Code Web Setup](claude-code-web-setup.md) - Using with Claude Code Web (installation, persistence, multi-repo)
- [Quick Reference](quick-reference.md) - Command cheat sheet
- [Taskwright Workflow](taskwright-workflow.md) - Complete workflow guide
- [Migration Guide](migration-guide.md) - Migrate from old workflow
- [MCP Optimization](../deep-dives/mcp-integration/mcp-optimization.md) - Library docs integration (Advanced)

### Common Issues
| Problem | Solution |
|---------|----------|
| Tests failing | `/task-work` auto-fixes (up to 3 attempts) |
| Wrong mode | Re-run with different `--mode` |
| Low coverage | Check uncovered lines in test report |

## Start Building!

You now have everything you need to use Taskwright:

1. **Create** tasks with clear descriptions
2. **Work** on them with your preferred mode
3. **Complete** with confidence knowing quality is built-in

The workflow ensures every piece of code is tested, reviewed, and ready for production.

> **Need Formal Requirements?**
> RequireKit adds EARS notation, BDD scenarios, and epic/feature hierarchy.
> See: https://github.com/requirekit/require-kit

---

*"Quality without ceremony" - Start with `/task-create` and let `/task-work` handle the rest!*
