# GuardKit

![version](https://img.shields.io/badge/version-0.9.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)
![integration](https://img.shields.io/badge/integration-requirekit%20optional-yellow)
![detection](https://img.shields.io/badge/detection-automatic-blueviolet)
[![documentation](https://img.shields.io/badge/docs-online-blue)](https://guardkit.github.io/guardkit/)

**Plan Features. Build Faster.**

Stop shipping broken code. GuardKit is built on **Feature Plan Development (FPD)** — a feature-first workflow where a single `/feature-plan` command generates a complete, consistent plan, subtask breakdown, and implementation workspace.

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
# ✅ Sets up feature workspace
```

### The FPD Manifesto

We believe that:

- **Features over files** — Every capability deserves a clear Feature Plan
- **Plans over improvisation** — AI excels at generating structured, repeatable plans
- **Structured decomposition over ad-hoc tasking** — Developers do their best work when guided, not constrained
- **Parallel execution over sequential bottlenecks** — Consistency is a feature, not a chore
- **Automation where possible, human oversight where needed** — Quality gates built-in, not bolted on

### FPD vs Spec-Driven Development

| | Feature Plan Development (GuardKit) | Spec-Driven (Kiro, Tessl, etc.) |
|---|---|---|
| **Starting Point** | Feature description → auto-generated plan | Manual specification authoring |
| **Ceremony** | Minimal (single command) | Heavy (30+ minutes per spec) |
| **Output** | Complete feature workspace + subtasks | Specification documents |
| **Parallel Support** | Built-in wave detection + Conductor integration | Manual coordination |
| **Target** | Solo devs to medium teams | Large teams, regulated industries |

### Optional: Formal Requirements

For teams needing formal requirements (EARS notation, BDD scenarios, epic hierarchy, PM tool sync), combine GuardKit with [RequireKit](https://github.com/requirekit/require-kit) for full Spec-Driven Development.

## What You Get

- **Hash-Based Task IDs**: Collision-free IDs enable concurrent creation and parallel development (Conductor.build compatible)
- **PM Tool Integration**: Automatic mapping to JIRA, Azure DevOps, Linear, GitHub sequential IDs
- **Architectural Review**: SOLID, DRY, YAGNI evaluation before coding (saves 40-50% rework time)
- **Test Enforcement**: Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **AI Agent Discovery**: Automatic specialist matching via metadata (stack, phase, keywords)
- **Stack-Specific Optimization**: Haiku agents for 48-53% cost savings, 4-5x faster implementation
- **Specialized Agents**: Stack-specific AI agents for React, Python, .NET, TypeScript
- **Quality Gates**: Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **State Management**: Automatic kanban tracking (backlog → in_progress → in_review → completed)
- **Design-First Workflow**: Optional design approval checkpoint for complex tasks (complexity ≥7)

## Quality Gates & Human Oversight

**AI does heavy lifting. Humans make decisions.**

### Human-in-the-Loop Checkpoints
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
- **State Preservation** - 100% state sync across worktrees (no manual intervention)
- **Zero Context Switching** - Each worktree maintains its own implementation context
- **Automatic Sync** - All commands available in every worktree, state updates propagate automatically

### Benefits
- **Blocked on one task? Switch to another** - No waiting for CI, reviews, or external dependencies
- **Parallel experimentation** - Try different approaches simultaneously, keep the best
- **Team collaboration** - Different team members work on different tasks without merge conflicts
- **Faster iteration** - 3-5x productivity boost when multiple tasks are in flight

### Competitive Advantage
- **Linear/Jira**: Sequential task switching (lose context on every switch)
- **GitHub Projects**: No parallel workspace support
- **GuardKit + Conductor**: True parallel development with state preservation

**Setup**: One command - `./installer/scripts/install.sh` creates symlinks automatically

## Documentation

📚 **[View Full Documentation](https://guardkit.github.io/guardkit/)**

Comprehensive guides, workflows, and references:

- **[Quickstart Guide](https://guardkit.github.io/guardkit/guides/GETTING-STARTED/)** - Get up and running in 5 minutes
- **[Core Concepts](https://guardkit.github.io/guardkit/concepts/)** - Workflow, complexity, quality gates, task states
- **[Advanced Topics](https://guardkit.github.io/guardkit/advanced/)** - Design-first, UX integration, review workflows
- **[Templates](https://guardkit.github.io/guardkit/templates/)** - Stack-specific templates and customization
- **[Agent System](https://guardkit.github.io/guardkit/agents/)** - Discovery, enhancement, and boundary sections
- **[Task Review](https://guardkit.github.io/guardkit/task-review/)** - Analysis workflows and review modes
- **[MCP Integration](https://guardkit.github.io/guardkit/mcp-integration/)** - Optional enhancements (context7, design-patterns)
- **[Troubleshooting](https://guardkit.github.io/guardkit/troubleshooting/)** - Common issues and solutions

## 5-Minute Quickstart

📚 **[View Full Documentation](https://guardkit.github.io/guardkit/)**

### Option 1: Quick Install (Recommended)

**macOS / Linux:**
```bash
# Install GuardKit
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# Initialize your project (choose a template)
guardkit init react-typescript  # or: fastapi-python, nextjs-fullstack, default
```

**Windows (WSL2):**
```bash
# 1. Install WSL2 (if not already installed)
wsl --install

# 2. Open WSL2 terminal and run installer
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# 3. Initialize your project
guardkit init react-typescript  # or: fastapi-python, nextjs-fullstack, default
```

> **Note for Windows users**: GuardKit requires bash and runs best on WSL2. Native PowerShell installation is not currently supported.

**If using VS Code:** Reload the window to enable slash commands:
- Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
- Type `Developer: Reload Window` and press Enter
- Or close and reopen VS Code

**Using Claude Code Web?** See the [Claude Code Web Setup Guide](docs/guides/claude-code-web-setup.md) for web-specific instructions.

> **⚠️ Important - Working Directory**
>
> Always run `/task-work` from your **project root directory** (where your code lives), not from the GuardKit installation directory. The command uses your current directory to detect the tech stack and create files.
>
> ```bash
> cd /path/to/your/project  # ✅ Navigate to project root first
> ```

```bash
# In Claude Code - create and work on a task
/task-create "Add user login feature"
# Created: TASK-h8j3
/task-work TASK-h8j3  # Does everything: plan, review, implement, test, verify
/task-complete TASK-h8j3
```

### Option 2: Clone Repository
```bash
# Clone and install
git clone https://github.com/guardkit/guardkit.git
cd guardkit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize your project
cd /path/to/your/project
guardkit init react-typescript

# IMPORTANT: Stay in your project directory for task work
/task-create "Add user login feature"
# Created: TASK-k2m9
/task-work TASK-k2m9
```

**If using VS Code:** Reload the window after initialization (see instructions above).

That's it! Three commands from idea to production-ready code.

## What Makes GuardKit Different?

1. **AI-Assisted with Human Oversight** ⚖️
   - Not fully automated (AI writes code)
   - Not fully manual (human reviews quality gates)
   - **Balanced**: AI does heavy lifting, humans make decisions

2. **Quality Gates Built-In** 🛡️
   - Architectural review (Phase 2.5)
   - Test enforcement (Phase 4.5)
   - Plan audit (Phase 5.5)
   - **Competitor gap**: Linear lacks mandatory quality gates

3. **Complexity Awareness** 🧠
   - Upfront task sizing (0-10 scale)
   - Auto-split recommendations (≥7 complexity)
   - **Prevents oversized tasks proactively** (competitors react, we prevent)

4. **Parallel Development Support** 🚀
   - Conductor.build integration
   - Work on 3-5 tasks simultaneously
   - 100% state preservation across worktrees
   - **Competitor gap**: Linear/Jira require sequential context switching

5. **Feature-First Planning** 📊
   - Lightweight: GuardKit alone (FPD)
   - Full-featured: GuardKit + RequireKit (SDD)
   - **Right amount of process for your team size**

6. **Zero Vendor Lock-In** 🔓
   - Markdown files (human-readable, git-friendly)
   - Self-hosted (no SaaS required)
   - **Competitor gap**: Linear is proprietary platform

## Who Should Use GuardKit?

| Audience | Use Case | Solution | Planning | Parallel? |
|----------|----------|----------|----------|-----------|
| **Solo Developers** | Quick prototyping, personal projects | GuardKit (FPD) | Feature plans + tasks | Optional (Conductor) |
| **Small Teams (2-5)** | Agile development, startup MVPs | GuardKit (FPD) | Feature plans + tasks | Recommended (Conductor) |
| **Medium Teams (5-20)** | Structured development, traceability | GuardKit + RequireKit | + EARS + Gherkin | Recommended (Conductor) |
| **Large Teams (20+)** | Regulated industries, compliance | GuardKit + RequireKit | + EARS + PM sync | Essential (Conductor) |

### Migration Path
- ✅ Start with GuardKit (FPD) - "One command, complete feature plan"
- ✅ Add Conductor when parallelizing - "Work on multiple tasks simultaneously"
- ✅ Add RequireKit when needed - "Team grew? Need compliance? Upgrade seamlessly"

## Available Commands

### Feature Planning (Recommended Starting Point)
```bash
/feature-plan "feature description"    # Single command → complete feature plan
```

This creates a review task, analyzes options, generates subtasks, and sets up the implementation workspace.

### Core Workflow
```bash
/task-create "Title" [priority:high|medium|low]
/task-work TASK-XXX [--mode=standard|tdd] [--design-only] [--implement-only]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX  # Lightweight improvements
```

### Development Modes
- **Standard** (default): Implementation + tests together
- **TDD**: Test-Driven Development (Red → Green → Refactor)

### Design-First Workflow
```bash
# Complex task? Split design and implementation
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
# [Review and approve plan]
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### Utilities
```bash
/debug                     # Troubleshoot issues
```

## Templates

GuardKit ships with **5 high-quality templates**: Stack-specific reference implementations, specialized patterns, and language-agnostic foundation.

### High-Quality Reference Templates

#### Stack-Specific (Production-Proven)

| Template | Source | Stars | Focus | Score |
|----------|--------|-------|-------|-------|
| **react-typescript** | [Bulletproof React](https://github.com/alan2207/bulletproof-react) | 28.5k | Frontend | 9.3/10 |
| **fastapi-python** | [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) | 12k+ | Backend API | 9.2/10 |
| **nextjs-fullstack** | Next.js App Router + Patterns | Official | Full-stack | 9.4/10 |

#### Specialized Templates

| Template | Purpose | Focus | Score |
|----------|---------|-------|-------|
| **react-fastapi-monorepo** | Full-stack monorepo | React + FastAPI | 9.2/10 |

#### Language-Agnostic Template

| Template | Purpose | Use For | Score |
|----------|---------|---------|-------|
| **default** | Language-agnostic foundation | Go, Rust, Ruby, Elixir, PHP, evaluation | 8.0+/10 |

All templates validated using comprehensive quality audit.

### Quick Start with Templates

```bash
# Try a reference template (evaluation)
guardkit init react-typescript

# Create your own template (production)
cd your-production-codebase
/template-create
guardkit init your-custom-template
```

### Why These 5 Templates?

**Templates are learning resources, not production code.**

Your production codebase is better than any generic template. Use `/template-create` to generate templates from code you've proven works.

**Stack-specific templates** (react, fastapi, nextjs) demonstrate:
- How to structure templates
- Stack-specific best practices
- Quality standards to target (9+/10)
- GuardKit workflow patterns

**Default template** provides:
- Language-agnostic foundation for unsupported stacks (Go, Rust, Ruby, etc.)
- Evaluation workflow without stack commitment
- Starting point before using `/template-create`

### Create Your Own Templates

```bash
cd your-production-codebase
/template-create

# Template created with:
# ✅ Your patterns and conventions
# ✅ Your proven architecture
# ✅ Your team's best practices
# ✅ Quality validation
```

**See**: [Template Philosophy Guide](docs/guides/template-philosophy.md) for detailed explanation.

**Migration**: [Template Migration Guide](docs/guides/template-migration.md) for migrating from old templates.

## Quality Gates (Automatic)

All enforced automatically during `/task-work`:

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Review | ≥60/100 | Human checkpoint required |
| Plan Audit | 0 violations | Variance review (scope creep detection) |

## Philosophy

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **AI/Human Collaboration**: AI does heavy lifting, humans make decisions
4. **Zero Ceremony**: No unnecessary documentation or process
5. **Fail Fast**: Block bad code early, don't let it reach production

## Project Structure

```
.claude/                    # Configuration
├── agents/                # Specialized AI agents
├── commands/              # Command specifications
└── task-plans/            # Implementation plans (Markdown)

tasks/                      # Task management
├── backlog/
├── in_progress/
├── in_review/
├── blocked/
└── completed/

docs/                       # Documentation
├── guides/                # Workflow guides
└── workflows/             # Detailed workflows

installer/core/           # Global resources
├── agents/                # Core AI agents
├── commands/              # Command specs
└── templates/             # Stack templates
```

## Task States

```
BACKLOG
   ├─ (task-work) ──────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                            ↓              ↓
   │                        BLOCKED        BLOCKED
   │
   └─ (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (task-work --implement-only) ─→ IN_PROGRESS ──→ IN_REVIEW
```

**Automatic transitions based on results:**
- ✅ All gates pass → `IN_REVIEW`
- ❌ Tests fail → `BLOCKED`
- ⚠️ Coverage low → Request more tests
- 🔄 Design approved → `DESIGN_APPROVED`

## Optional: MCP Enhancements

**Model Context Protocol (MCP)** servers enhance GuardKit with specialized capabilities. **All are optional** - system works fine without them.

### Core MCPs (General Development)

These enhance regular `/task-work` execution for all tasks:

| MCP | Purpose | Used During | Setup Time |
|-----|---------|-------------|------------|
| **context7** | Up-to-date library docs | Phases 2, 3, 4 (automatic) | 2 min |
| **design-patterns** | Pattern recommendations | Phase 2.5A (automatic) | 5 min |

**Recommended**: Set up Context7 for the most value. Design Patterns is optional but helpful.

### Quick Setup (Context7 Recommended)

Context7 provides the most value for day-to-day development:

```bash
# One command setup
npx -y @smithery/cli@latest install @upstash/context7-mcp --client claude
```

Restart Claude Code, done! Now `/task-work` automatically fetches latest docs.

### How It Works

**With Context7**:
```
/task-work TASK-n7p4
📚 Fetching latest documentation for React...
✅ Retrieved React documentation (topic: hooks)
[Implementation uses latest React 19 patterns]
```

**Without Context7**:
```
/task-work TASK-n7p4
⚠️ Context7 unavailable, using training data
[Implementation uses training data patterns - still works!]
```

### Setup Guides

**Core MCPs** (for general development):
- [Context7 Setup](docs/guides/context7-mcp-setup.md) - Up-to-date library docs (recommended)
- [Design Patterns Setup](docs/guides/design-patterns-mcp-setup.md) - Pattern recommendations

**Performance**: All MCPs optimized, <15% context window usage, <2s query time.

## Documentation

### Getting Started
- [Claude Code Web Setup](docs/guides/claude-code-web-setup.md) - Using GuardKit with Claude Code Web (installation, persistence, multi-repo)
- [GuardKit Workflow](docs/guides/guardkit-workflow.md) - Complete workflow guide
- [Complexity Management](docs/workflows/complexity-management-workflow.md) - Understanding complexity evaluation

### Advanced
- [MCP Optimization Guide](docs/guides/mcp-optimization-guide.md) - Model Context Protocol integration
- [Domain Layer Pattern](docs/patterns/domain-layer-pattern.md) - Verb-based Domain operations

### Templates
- [MAUI Template Selection](docs/guides/maui-template-selection.md) - AppShell vs NavigationPage
- [Creating Local Templates](docs/guides/creating-local-templates.md) - Team-specific templates

### Template Validation
- [Template Validation Guide](docs/guides/template-validation-guide.md) - 3-level validation system overview
- [Template Validation Workflows](docs/guides/template-validation-workflows.md) - Common usage patterns
- [Template Validation AI Assistance](docs/guides/template-validation-ai-assistance.md) - AI-assisted validation features

**Research & Implementation**:
- [Template Validation Strategy](docs/research/template-validation-strategy.md) - Design decisions and architecture
- [Template Validation Implementation Guide](docs/research/template-validation-implementation-guide.md) - Developer workflow
- [Template Validation Tasks Summary](docs/research/template-validation-tasks-summary.md) - Task overview

## Example Workflow

### Feature Planning Flow (Recommended)

```bash
# 1. Plan the feature
/feature-plan "add user authentication"

# Output:
# ✅ Created review task: TASK-REV-a3f8
# 🔍 Analyzing technical options...
#
# TECHNICAL OPTIONS:
#   Option 1: JWT with refresh tokens (Recommended)
#   Option 2: Session-based auth
#   Option 3: OAuth 2.0 integration
#
# DECISION: [A]ccept [R]evise [I]mplement [C]ancel
# Your choice: I
#
# ✅ Created: tasks/backlog/user-authentication/
#   ├── README.md
#   ├── IMPLEMENTATION-GUIDE.md (2 parallel waves)
#   ├── TASK-AUTH-001-setup-jwt-middleware.md
#   ├── TASK-AUTH-002-create-user-model.md
#   └── ... (3 more subtasks)

# 2. Work through subtasks (use Conductor for parallel execution)
/task-work TASK-AUTH-001
/task-complete TASK-AUTH-001
# ... continue through all subtasks
```

### Direct Task Flow (Simple Tasks)

```bash
# 1. Create task
/task-create "Fix login button styling"
# Created: TASK-p9r3

# 2. Work on it (automatic phases)
/task-work TASK-p9r3

# Output:
# Phase 2: Implementation Planning ✅
# Phase 2.5: Architectural Review (Score: 75/100) ✅
# Phase 3: Implementation (2 files modified) ✅
# Phase 4: Testing (5 tests, 95% coverage) ✅
# Phase 5: Code Review ✅
# Task moved to IN_REVIEW

# 3. Complete
/task-complete TASK-p9r3
```

Total time: ~2 minutes. Zero manual quality checks.

## Contributing

1. Fork the repository
2. Create a task: `/task-create "Your contribution"`
3. Implement: `/task-work TASK-XXX`
4. Quality gates pass automatically
5. Submit PR

All contributions go through the same quality gates as regular development tasks.

## Conductor Integration

Fully compatible with [Conductor.build](https://conductor.build) for parallel development across worktrees.

**Features:**
- Symlink architecture for shared state
- Auto-commit state changes
- 100% state preservation across parallel sessions
- Zero manual intervention required

**Setup:**
```bash
./installer/scripts/install.sh  # Creates symlinks automatically
guardkit doctor              # Verify integration
```

## Testing by Stack

Automatic detection and execution:

**Python:**
```bash
pytest tests/ -v --cov=src --cov-report=term --cov-report=json
```

**TypeScript/JavaScript:**
```bash
npm test -- --coverage
```

**.NET:**
```bash
dotnet test --collect:"XPlat Code Coverage" --logger:"json"
```

All handled automatically by `/task-work`!

## License

MIT License - See LICENSE file for details

## Support

- Check [GuardKit Workflow](docs/guides/guardkit-workflow.md)
- Read [Complexity Management](docs/workflows/complexity-management-workflow.md)
- See [Design-First Workflow](docs/workflows/design-first-workflow.md)
- Create a GitHub issue

---

**Plan Features. Build Faster.** Built for pragmatic developers who ship quality code.
