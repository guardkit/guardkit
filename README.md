# Taskwright

![version](https://img.shields.io/badge/version-2.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![standalone](https://img.shields.io/badge/standalone-no%20dependencies-blueviolet)
![integration](https://img.shields.io/badge/integration-requirekit%20optional-yellow)
![detection](https://img.shields.io/badge/detection-automatic-blueviolet)

**Lightweight AI-assisted development with built-in quality gates.**

Stop shipping broken code. Get architectural review before implementation and automatic test enforcement after. Simple task workflow, no ceremony.

## What You Get

- **Phase 2.5 - Architectural Review**: SOLID, DRY, YAGNI evaluation before coding (saves 40-50% rework time)
- **Phase 4.5 - Test Enforcement**: Automatic test fixing (up to 3 attempts), ensures 100% pass rate
- **Specialized Agents**: Stack-specific AI agents for React, Python, .NET, TypeScript
- **Quality Gates**: Coverage thresholds (80% line, 75% branch), compilation checks, code review
- **State Management**: Automatic kanban tracking (backlog → in_progress → in_review → completed)
- **Design-First Workflow**: Optional design approval checkpoint for complex tasks (complexity ≥7)

## 5-Minute Quickstart

```bash
# Install
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize your project (choose a template)
taskwright init react  # or: python, typescript-api, maui-appshell, default

# In Claude Code - create and work on a task
/task-create "Add user login feature"
/task-work TASK-001  # Does everything: plan, review, implement, test, verify
/task-complete TASK-001
```

That's it! Three commands from idea to production-ready code.

## What Makes This Different?

### Phase 2.5: Architectural Review
Before writing a single line of code, get automated evaluation of:
- **SOLID Principles** (60/100 minimum score)
- **DRY Violations** (detect duplication risks)
- **YAGNI Compliance** (flag over-engineering)

**Result**: Catches design flaws before implementation, saving 40-50% rework time.

### Phase 4.5: Test Enforcement Loop
After implementation, automatic test fixing:
1. Run all tests
2. If failures detected → analyze root cause
3. Auto-fix code (up to 3 attempts)
4. Re-run tests
5. Block task if all attempts fail (zero tolerance for failing tests)

**Result**: 100% test pass rate before code review. No "we'll fix it later."

### Phase 2.7: Complexity Evaluation
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

**Note**: For BDD mode (Behavior-Driven Development with Gherkin scenarios), use [RequireKit](https://github.com/requirekit/require-kit).

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
| **maui-appshell** | .NET MAUI + AppShell + MVVM + ErrorOr | Mobile (tab-based) |
| **maui-navigationpage** | .NET MAUI + NavigationPage + MVVM | Mobile (page-based) |
| **dotnet-fastendpoints** | .NET + FastEndpoints + REPR pattern | .NET APIs |
| **default** | Language-agnostic | Any other stack |

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

## Documentation

### Getting Started
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

All handled automatically by Phase 4 and 4.5!

## License

MIT License - See LICENSE file for details

## Support

- Check [Taskwright Workflow](docs/guides/taskwright-workflow.md)
- Read [Complexity Management](docs/workflows/complexity-management-workflow.md)
- See [Design-First Workflow](docs/workflows/design-first-workflow.md)
- Create a GitHub issue

---

**Built for pragmatic developers who ship quality code fast.**
