# Taskwright

![version](https://img.shields.io/badge/version-0.9.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)
![integration](https://img.shields.io/badge/integration-requirekit%20optional-yellow)
![detection](https://img.shields.io/badge/detection-automatic-blueviolet)

**Lightweight AI-assisted development with built-in quality gates.**

Stop shipping broken code. Get architectural review before implementation and automatic test enforcement after. Simple task workflow, no ceremony.

## What You Get

- **Architectural Review**: SOLID, DRY, YAGNI evaluation before coding (saves 40-50% rework time)
- **Test Enforcement**: Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **Specialized Agents**: Stack-specific AI agents for React, Python, .NET, TypeScript
- **Quality Gates**: Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **State Management**: Automatic kanban tracking (backlog → in_progress → in_review → completed)
- **Design-First Workflow**: Optional design approval checkpoint for complex tasks (complexity ≥7)

## 5-Minute Quickstart

### Option 1: Quick Install (Recommended)
```bash
# Direct install
curl -sSL https://raw.githubusercontent.com/taskwright-dev/taskwright/main/installer/scripts/install.sh | bash

# Initialize your project (choose a template)
taskwright init react  # or: python, typescript-api, maui-appshell, default
```

**If using VS Code:** Reload the window to enable slash commands:
- Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
- Type `Developer: Reload Window` and press Enter
- Or close and reopen VS Code

**Using Claude Code Web?** See the [Claude Code Web Setup Guide](docs/guides/claude-code-web-setup.md) for web-specific instructions.

> **⚠️ Important - Working Directory**
>
> Always run `/task-work` from your **project root directory** (where your code lives), not from the Taskwright installation directory. The command uses your current directory to detect the tech stack and create files.
>
> ```bash
> cd /path/to/your/project  # ✅ Navigate to project root first
> ```

```bash
# In Claude Code - create and work on a task
/task-create "Add user login feature"
/task-work TASK-001  # Does everything: plan, review, implement, test, verify
/task-complete TASK-001
```

### Option 2: Clone Repository
```bash
# Clone and install
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize your project
cd /path/to/your/project
taskwright init react

# IMPORTANT: Stay in your project directory for task work
/task-create "Add user login feature"
/task-work TASK-001
```

**If using VS Code:** Reload the window after initialization (see instructions above).

That's it! Three commands from idea to production-ready code.

## What Makes This Different?

### Architectural Review
Before writing a single line of code, get automated evaluation of:
- **SOLID Principles** (60/100 minimum score)
- **DRY Violations** (detect duplication risks)
- **YAGNI Compliance** (flag over-engineering)

**Result**: Catches design flaws before implementation, saving 40-50% rework time.

### Test Enforcement Loop
After implementation, automatic test fixing:
1. Run all tests
2. If failures detected → analyze root cause
3. Auto-fix code (up to 3 attempts)
4. Re-run tests
5. Block task if all attempts fail (zero tolerance for failing tests)

**Result**: 100% test pass rate before code review. No "we'll fix it later."

### Complexity Evaluation
Automatic complexity scoring (0-10 scale):
- **1-3 (Simple)**: Auto-proceed, no checkpoint (<4 hours)
- **4-6 (Medium)**: Quick optional checkpoint (30s timeout)
- **7-10 (Complex)**: Mandatory design approval (>8 hours)

**Result**: Right level of oversight for task complexity.

## When to Use Taskwright

### Use When:
- Individual tasks or small features (1-8 hours)
- Solo dev or small teams (1-3 developers)
- Need quality enforcement without ceremony
- Want AI assistance with human oversight
- Small-to-medium projects

### Don't Use When:
- Just want a code editor (use plain Claude Code)
- Need formal requirements management (use RequireKit instead)
- Enterprise compliance workflows required
- Multi-epic portfolio management (10+ features, 5+ devs)

## Need Requirements Management?

For formal requirements (EARS notation, BDD scenarios, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with Taskwright.

## Available Commands

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

### UX Design Integration
```bash
/figma-to-react <file-key> [node-id]    # Figma → TypeScript React + Tailwind
/zeplin-to-maui <project-id> <screen-id> # Zeplin → .NET MAUI + XAML
```

### Utilities
```bash
/debug                     # Troubleshoot issues
```

## Supported Stacks

Choose your template during initialization:

| Template | Technologies | Use For |
|----------|-------------|---------|
| **react** | React + TypeScript + Next.js + Tailwind + Vitest + Playwright | Web applications |
| **python** | FastAPI + pytest + LangGraph + Pydantic | Python APIs |
| **typescript-api** | NestJS + Result patterns + domain modeling | TypeScript APIs |
| **dotnet-fastendpoints** | .NET + FastEndpoints + Either monad (LanguageExt) | .NET APIs (functional) |
| **dotnet-minimalapi** | .NET + Minimal APIs + Vertical Slices + ErrorOr | .NET APIs (lightweight) |
| **fullstack** | React + TypeScript + Python + FastAPI | Full-stack web apps |
| **maui-appshell** | .NET MAUI + AppShell + MVVM + ErrorOr | Mobile (tab-based) |
| **maui-navigationpage** | .NET MAUI + NavigationPage + MVVM + ErrorOr | Mobile (page-based) |

**Note**: Templates `dotnet-aspnetcontroller` and `default` were removed in v2.0. See [Template Migration Guide](docs/guides/template-migration.md) for migration paths.

See [Creating Local Templates](docs/guides/creating-local-templates.md) for custom team templates.

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

installer/global/           # Global resources
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

**Model Context Protocol (MCP)** servers enhance Taskwright with specialized capabilities. **All are optional** - system works fine without them.

### Core MCPs (General Development)

These enhance regular `/task-work` execution for all tasks:

| MCP | Purpose | Used During | Setup Time |
|-----|---------|-------------|------------|
| **context7** | Up-to-date library docs | Phases 2, 3, 4 (automatic) | 2 min |
| **design-patterns** | Pattern recommendations | Phase 2.5A (automatic) | 5 min |

**Recommended**: Set up Context7 for the most value. Design Patterns is optional but helpful.

### Design MCPs (Only for Design-to-Code Workflows)

**⚠️ Only set these up if you're using the specific design-to-code commands:**

| MCP | Purpose | Required For | Setup Time |
|-----|---------|--------------|------------|
| **figma-dev-mode** | Figma → React code | `/figma-to-react` command only | 10 min |
| **zeplin** | Zeplin → MAUI code | `/zeplin-to-maui` command only | 10 min |

**Skip these** if you're not converting Figma/Zeplin designs to code. They're not used during regular development.

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
/task-work TASK-001
📚 Fetching latest documentation for React...
✅ Retrieved React documentation (topic: hooks)
[Implementation uses latest React 19 patterns]
```

**Without Context7**:
```
/task-work TASK-001
⚠️ Context7 unavailable, using training data
[Implementation uses training data patterns - still works!]
```

### Setup Guides

**Core MCPs** (for general development):
- [Context7 Setup](docs/guides/context7-mcp-setup.md) - Up-to-date library docs (recommended)
- [Design Patterns Setup](docs/guides/design-patterns-mcp-setup.md) - Pattern recommendations

**Design MCPs** (only if using design-to-code commands):
- [Figma Setup](docs/mcp-setup/figma-mcp-setup.md) - For `/figma-to-react` command
- [Zeplin Setup](docs/mcp-setup/zeplin-mcp-setup.md) - For `/zeplin-to-maui` command

**Performance**: All MCPs optimized, <15% context window usage, <2s query time.

## Documentation

### Getting Started
- [Claude Code Web Setup](docs/guides/claude-code-web-setup.md) - Using Taskwright with Claude Code Web (installation, persistence, multi-repo)
- [Taskwright Workflow](docs/guides/taskwright-workflow.md) - Complete workflow guide
- [Complexity Management](docs/workflows/complexity-management-workflow.md) - Understanding complexity evaluation
- [Design-First Workflow](docs/workflows/design-first-workflow.md) - When and how to split design/implementation

### Advanced
- [UX Design Integration](docs/workflows/ux-design-integration-workflow.md) - Figma/Zeplin → Code
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

### Real-World: User Authentication Feature

```bash
# 1. Create task
/task-create "Add JWT-based user authentication"

# 2. Work on it (automatic phases)
/task-work TASK-001

# Output:
# Phase 2: Implementation Planning ✅
# Phase 2.5: Architectural Review (Score: 75/100) ✅
# Phase 2.7: Complexity Evaluation (3/10 - Simple) ✅
# Phase 2.8: Auto-proceed (no checkpoint needed)
# Phase 3: Implementation (7 files created) ✅
# Phase 4: Testing (15 tests, 92% coverage) ✅
# Phase 4.5: Test Enforcement (All tests passing) ✅
# Phase 5: Code Review ✅
# Phase 5.5: Plan Audit (0 violations) ✅
#
# Task moved to IN_REVIEW

# 3. Complete
/task-complete TASK-001
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
taskwright doctor              # Verify integration
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

- Check [Taskwright Workflow](docs/guides/taskwright-workflow.md)
- Read [Complexity Management](docs/workflows/complexity-management-workflow.md)
- See [Design-First Workflow](docs/workflows/design-first-workflow.md)
- Create a GitHub issue

---

**Built for pragmatic developers who ship quality code fast.**
