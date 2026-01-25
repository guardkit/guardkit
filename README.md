# GuardKit

![version](https://img.shields.io/badge/version-1.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)
![integration](https://img.shields.io/badge/integration-requirekit%20optional-yellow)
![detection](https://img.shields.io/badge/detection-automatic-blueviolet)
[![documentation](https://img.shields.io/badge/docs-online-blue)](https://guardkit.github.io/guardkit/)

**Plan Features. Build Faster.**

GuardKit is built on **Feature Plan Development (FPD)** — a feature-first workflow where a single `/feature-plan` command generates a complete, consistent plan, subtask breakdown, and implementation guide.

## Feature Plan Development (FPD)

GuardKit treats **features as the unit of planning** and **tasks as the unit of execution**.

```bash
/feature-plan "add user authentication"

# System automatically:
# ✅ Creates review task
# ✅ Analyzes technical options
# ✅ Generates subtask breakdown
# ✅ Detects parallel execution waves
# ✅ Creates implementation guide
```

## What You Get

- **Feature Planning**: Single `/feature-plan` command creates feature directory, README, implementation guide, and subtasks
- **Clarifying Questions**: Targeted questions before assumptions, complexity-gated
- **Hash-Based Task IDs**: Collision-free IDs enable concurrent creation and parallel development (Conductor.build compatible)
- **PM Tool Integration**: Automatic mapping to JIRA, Azure DevOps, Linear, GitHub sequential IDs
- **Architectural Review**: SOLID, DRY, YAGNI evaluation before coding
- **Test Enforcement**: Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **AI Agent Discovery**: Automatic specialist matching via metadata (stack, phase, keywords)
- **Stack-Specific Optimization**: Haiku agents for lower-cost, faster implementation of routine tasks
- **Specialized Agents**: Stack-specific AI agents for React, Python, .NET, TypeScript
- **Quality Gates**: Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **State Management**: Automatic kanban tracking (backlog → in_progress → in_review → completed)
- **Design-First Workflow**: Optional design approval checkpoint for complex tasks (complexity ≥7)
- **AutoBuild**: Fully autonomous task implementation with Player-Coach adversarial workflow

## AI-Powered Customization

GuardKit learns from your codebase:

- **Template Creation**: `/template-create` analyzes your code and generates stack-specific templates with your patterns
- **Agent Discovery**: Automatically matches tasks to specialist AI agents based on file patterns and keywords
- **Rules Structure**: Path-specific Claude rules load conditionally to reduce context usage
- **Progressive Disclosure**: Essential guidance always loaded, detailed references on-demand

Start with reference templates for learning, then create your own from production code.

## Quality Gates & Human Oversight

**AI does heavy lifting. Humans make decisions.**

### Clarifying Questions

GuardKit asks targeted questions before making assumptions:

```bash
/task-work TASK-a3f8

📋 CLARIFYING QUESTIONS (complexity: 5)

Q1. Implementation Scope
    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases
    Your choice: S

Q2. Testing Approach
    [U]nit tests only
    [I]ntegration + unit (DEFAULT)
    [F]ull coverage (unit + integration + e2e)
    Your choice: I

✓ Recorded 2 decisions - proceeding with implementation...
```

**Complexity-gated**: Simple tasks (1-2) skip questions, medium tasks (3-4) get quick questions with timeout, complex tasks (5+) get full clarification.

**Flags**: `--no-questions` (skip), `--with-questions` (force), `--defaults` (use defaults), `--answers="..."` (inline for CI/CD)

### Human-in-the-Loop Checkpoints
- **Phase 1.6: Clarifying Questions** - Scope, approach, testing preferences (complexity-gated)
- **Phase 2.5: Architectural Review** - SOLID/DRY/YAGNI scoring (60/100 minimum)
- **Phase 2.8: Complexity Checkpoint** - Tasks ≥7 complexity require approval before implementation
- **Phase 4.5: Test Enforcement** - Auto-fix up to 3 attempts, block if tests fail
- **Phase 5.5: Plan Audit** - Detect scope creep (file count, LOC variance ±20%, duration ±30%)

### Complexity Evaluation (Upfront Task Sizing)
- **0-10 Scale** - Automatic complexity scoring before work begins
- **Auto-Split Recommendations** - Tasks ≥7 complexity flagged for breakdown
- **Prevents Oversized Tasks** - Blocks 8+ hour tasks from entering backlog

### Plan Audit (Scope Creep Detection)
- **File Count Matching** - Verify implementation matches plan
- **LOC Variance Tracking** - Flag ±20% deviations for review
- **Duration Variance Tracking** - Flag ±30% deviations for retrospective

## Parallel Task Development

**Work on multiple tasks simultaneously without context switching chaos.**

GuardKit integrates seamlessly with [Conductor.build](https://conductor.build) for parallel development:

### How It Works
- **Multiple Worktrees** - Work on 3-5 tasks in parallel, each in isolated git worktree
- **State Preservation** - State synchronsiation across worktrees (no manual intervention)
- **Zero Context Switching** - Each worktree maintains its own implementation context
- **Automatic Sync** - All commands available in every worktree, state updates propagate automatically

### Benefits
- **Blocked on one task? Switch to another** - No waiting for CI, reviews, or external dependencies
- **Parallel experimentation** - Try different approaches simultaneously, keep the best
- **Team collaboration** - Different team members work on different tasks without merge conflicts
- **Faster iteration** - Work on multiple tasks without losing context

### Competitive Advantage
- **Linear/Jira**: Sequential task switching (lose context on every switch)
- **GitHub Projects**: No parallel workspace support
- **GuardKit + Conductor**: True parallel development with state preservation

**Setup**: One command - `./installer/scripts/install.sh` creates symlinks automatically

## 5-Minute Quickstart

📚 **[Full Documentation](https://guardkit.github.io/guardkit/)** | **[Core Concepts](https://guardkit.github.io/guardkit/concepts/)** | **[Templates](https://guardkit.github.io/guardkit/templates/)**

### 1. Install

```bash
# Basic installation
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# Or with pip (Python package)
pip install guardkit-py

# With AutoBuild support (required for /feature-build)
pip install guardkit-py[autobuild]
```

**Note**: AutoBuild features (`/feature-build`, `guardkit autobuild`) require the optional `claude-agent-sdk` dependency. If you see "Claude Agent SDK not installed", run `pip install guardkit-py[autobuild]`.

### 2. Initialize & Use

```bash
# Initialize your project
guardkit init react-typescript  # or: fastapi-python, nextjs-fullstack, default

# Create and work on a task (natural language description)
/task-create "We need to add a user login feature with email and password"
/task-work TASK-h8j3  # Does everything: plan, review, implement, test, verify
/task-complete TASK-h8j3
```

> **VS Code users**: Reload window after installation (`Cmd+Shift+P` → `Developer: Reload Window`)

## Why GuardKit?

| Feature | GuardKit | Competitors |
|---------|----------|-------------|
| **AutoBuild** | Autonomous Player-Coach implementation with human review | Manual coding or basic autocomplete |
| **Quality Gates** | Built-in (architectural review, test enforcement, plan audit) | Manual or missing |
| **Complexity Awareness** | Upfront 0-10 scoring, auto-split recommendations | React after problems |
| **Parallel Development** | Conductor.build integration, State sync | Sequential switching |
| **AI Customization** | Template creation, agent discovery from your code | Generic tooling |
| **Vendor Lock-In** | Zero (Markdown files, self-hosted) | SaaS platforms |

**Start with GuardKit (FPD)** → **Add Conductor for parallel work** → **Add [RequireKit](https://github.com/requirekit/require-kit) for Spec-Driven Development**

## Commands

### Feature Planning (Recommended Starting Point)
```bash
/feature-plan "feature description"    # Single command → complete feature plan
```

This creates a review task, analyzes options, generates subtasks, and sets up the implementation workspace.

### Core Workflow
```bash
/task-create "description" [priority:high|medium|low]  # Natural language, auto-infers title
/task-work TASK-XXX [--mode=standard|tdd] [--micro] [--design-only] [--implement-only]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX  # Lightweight improvements
```

### Development Modes
- **Standard** (default): Implementation + tests together
- **TDD**: Test-Driven Development (Red → Green → Refactor)
- **Micro** (`--micro`): Skip planning phases for trivial tasks

### Design-First Workflow
```bash
# Complex task? Split design and implementation
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
# [Review and approve plan]
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### Autonomous Build (AutoBuild)
```bash
# Fully autonomous implementation with Player-Coach workflow
/feature-build TASK-XXX                # Single task autonomous build
/feature-build FEAT-XXX                # Feature mode - all tasks with dependencies

# After review, merge approved work
/feature-complete TASK-XXX             # Merge single task
/feature-complete FEAT-XXX             # Merge entire feature
```

**What AutoBuild does:**
- Creates isolated git worktree per task
- Runs Player-Coach dialectical loop (Player implements → Coach validates)
- Preserves worktree for human review (never auto-merges)
- Supports checkpoint/resume for interrupted sessions

### Utilities
```bash
/debug                     # Troubleshoot issues
```

## Templates

**5 reference templates** for learning and evaluation (all 8+/10 quality):

| Template | Focus | Source |
|----------|-------|--------|
| `react-typescript` | Frontend | [Bulletproof React](https://github.com/alan2207/bulletproof-react) (28.5k ⭐) |
| `fastapi-python` | Backend API | [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) (12k+ ⭐) |
| `nextjs-fullstack` | Full-stack | Next.js App Router |
| `react-fastapi-monorepo` | Monorepo | React + FastAPI |
| `default` | Any stack | Go, Rust, Ruby, etc. |

**For production**: Create templates from your own code with `/template-create`.

**See**: [Template Philosophy](docs/guides/template-philosophy.md) | [Template Migration](docs/guides/template-migration.md)

## Quality Gates (Automatic)

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Review | ≥60/100 | Human checkpoint |
| Plan Audit | 0 violations | Variance review |

## AutoBuild: Autonomous Implementation

**Let AI implement while you review.**

AutoBuild uses a **Player-Coach adversarial workflow** for fully autonomous task implementation:

```
┌──────────────┐                    ┌──────────────┐
│   PLAYER     │───Implementation──▶│    COACH     │
│   (builds)   │◀─────Feedback──────│  (validates) │
└──────────────┘                    └──────────────┘
```

- **Player Agent**: Full file system access, implements code, writes tests
- **Coach Agent**: Read-only access, runs tests, validates against acceptance criteria
- **Dialectical Loop**: Player implements → Coach validates → repeat until approval

### When to Use AutoBuild

| Use `/feature-build` | Use `/task-work` |
|---------------------|------------------|
| Well-defined requirements | Exploratory work |
| Standard implementation patterns | Complex architectural decisions |
| Clear acceptance criteria | High-risk changes |
| Low to medium risk | Unusual or novel requirements |

### AutoBuild Workflow

```bash
# 1. Plan feature (generates tasks + dependencies)
/feature-plan "implement OAuth2 authentication"
# → Creates FEAT-A1B2 with 4 subtasks

# 2. Run autonomous implementation
/feature-build FEAT-A1B2
# → Executes tasks in dependency order
# → Creates worktree: .guardkit/worktrees/FEAT-A1B2/

# 3. Review AI output
cd .guardkit/worktrees/FEAT-A1B2
git diff main

# 4. Merge if approved
/feature-complete FEAT-A1B2
```

**Installation**: AutoBuild requires `pip install guardkit-py[autobuild]` for the Claude Agent SDK.

## Optional: MCP Enhancements

**Model Context Protocol (MCP)** servers enhance GuardKit. **All optional** - system works without them.

| MCP | Purpose | Setup |
|-----|---------|-------|
| **context7** | Up-to-date library docs | `npx -y @smithery/cli@latest install @upstash/context7-mcp --client claude` |
| **design-patterns** | Pattern recommendations | [Setup Guide](docs/guides/design-patterns-mcp-setup.md) |

**See**: [MCP Integration](https://guardkit.github.io/guardkit/mcp-integration/)

## Example Workflow

```bash
# Feature planning (recommended for new features)
/feature-plan "add user authentication"
# → Creates review task, analyzes options, generates subtasks with FEAT-XXX ID

# OPTION A: Interactive implementation (human-in-the-loop)
/task-work TASK-p9r3   # Plans, reviews, implements, tests (with checkpoints)
/task-complete TASK-p9r3

# OPTION B: Autonomous implementation (AutoBuild)
/feature-build FEAT-XXX                 # AI implements entire feature autonomously
# → Player-Coach loop runs until approved or max turns
# → Work preserved in .guardkit/worktrees/ for review
cd .guardkit/worktrees/FEAT-XXX && git diff main  # Review changes
/feature-complete FEAT-XXX              # Merge approved work to main

# Simple task (for bug fixes, small features)
/task-create "The login button styling is broken on mobile devices"
/task-work TASK-p9r3   # Plans, reviews, implements, tests (all automatic)
/task-complete TASK-p9r3
```

**See**: [GuardKit Workflow](docs/guides/guardkit-workflow.md) for complete details.

## Contributing

1. Fork → `/task-create "Your contribution"` → `/task-work TASK-XXX` → Submit PR

All contributions go through the same quality gates.

## License

MIT License - See LICENSE file for details

## Support

📚 **[Documentation](https://guardkit.github.io/guardkit/)** | 🐛 **[GitHub Issues](https://github.com/guardkit/guardkit/issues)**

---

**Plan Features. Build Faster.** Built for pragmatic developers who ship quality code.
