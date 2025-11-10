# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Taskwright - Lightweight AI-Assisted Development

This is the **Taskwright** project - a lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

**Core Features:**
- **Quality Gates**: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- **Simple Workflow**: Create → Work → Complete (3 commands)
- **AI Collaboration**: AI handles implementation, humans make decisions
- **No Ceremony**: Minimal process, maximum productivity

### Core Principles

1. **Quality First**: Never compromise on test coverage or architecture
2. **Pragmatic Approach**: Right amount of process for task complexity
3. **AI/Human Collaboration**: AI does heavy lifting, humans make decisions
4. **Zero Ceremony**: No unnecessary documentation or process
5. **Fail Fast**: Block bad code early, don't let it reach production

## Essential Commands

### Core Workflow
```bash
/task-create "Title" [priority:high|medium|low]
/task-work TASK-XXX [--mode=standard|tdd]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Design-First Workflow (Complex Tasks)
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
# [Review and approve implementation plan]
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### UX Design Integration
```bash
/figma-to-react <file-key> [node-id]    # Figma → TypeScript React + Tailwind
/zeplin-to-maui <project-id> <screen-id> # Zeplin → .NET MAUI + XAML
```

### Utilities
```bash
/debug  # Troubleshoot issues
```

**See**: `installer/global/commands/*.md` for complete command specifications.

## Task Workflow Phases

The `/task-work` command executes these phases automatically:

```
Phase 1: Requirements Analysis (require-kit only - skipped in taskwright)
Phase 2: Implementation Planning (Markdown format)
Phase 2.5: Architectural Review (SOLID/DRY/YAGNI scoring)
Phase 2.7: Complexity Evaluation (0-10 scale)
Phase 2.8: Human Checkpoint (if complexity ≥7 or review required)
Phase 3: Implementation
Phase 4: Testing (compilation + coverage)
Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
Phase 5: Code Review
Phase 5.5: Plan Audit (scope creep detection)
```

**Note**: Taskwright starts directly at Phase 2 using task descriptions and acceptance criteria. For formal requirements analysis (EARS, BDD), use [require-kit](https://github.com/requirekit/require-kit).

**Key Decision Points:**
- **Phase 2.7**: Auto-proceed (1-3) vs checkpoint (7-10)
- **Phase 2.8**: Approve/Modify/Simplify/Reject/Postpone
- **Phase 4.5**: Auto-fix vs block task
- **Phase 5.5**: Approve vs escalate

## Complexity Evaluation

**Two-Stage System:**
1. **Upfront (task-create)**: Decide if task should be split (threshold: 7/10)
2. **Planning (task-work)**: Decide review mode (auto/quick/full)

**Scoring (0-10 scale):**
- File Complexity (0-3): Based on number of files
- Pattern Familiarity (0-2): Known vs new patterns
- Risk Assessment (0-3): Low/medium/high risk
- Dependencies (0-2): Number of external dependencies

**Complexity Levels:**
- **1-3 (Simple)**: <4 hours, AUTO_PROCEED
- **4-6 (Medium)**: 4-8 hours, QUICK_OPTIONAL (30s timeout)
- **7-10 (Complex)**: >8 hours, FULL_REQUIRED (mandatory checkpoint)

**See**: [Complexity Management Workflow](docs/workflows/complexity-management-workflow.md)

## UX Design Integration

Converts design system files (Figma, Zeplin) into components with **zero scope creep**.

**Supported:**
- `/figma-to-react` - Figma → TypeScript React + Tailwind + Playwright
- `/zeplin-to-maui` - Zeplin → XAML + C# + platform tests

**6-Phase Saga:**
1. MCP Verification
2. Design Extraction
3. Boundary Documentation (12-category prohibition checklist)
4. Component Generation
5. Visual Regression Testing (>95% similarity)
6. Constraint Validation (zero tolerance)

**Quality Gates:**
- Visual fidelity: >95%
- Constraint violations: 0
- Compilation: 100%

**See**: [UX Design Integration Workflow](docs/workflows/ux-design-integration-workflow.md)

## Template Validation

Taskwright provides a 3-level validation system for template quality assurance.

### Validation Levels

**Level 1: Automatic Validation** (Always On)
- Runs during `/template-create` (Phase 5.5)
- CRUD completeness checks
- Layer symmetry validation
- Auto-fix common issues
- Duration: ~30 seconds
- **No user action required**

**Level 2: Extended Validation** (Optional)
```bash
# Personal templates (default: ~/.agentecflow/templates/)
/template-create --validate

# Repository templates (installer/global/templates/)
/template-create --validate --output-location=repo
```
- All Level 1 checks
- Placeholder consistency validation
- Pattern fidelity spot-checks
- Documentation completeness
- Detailed quality report (saved in template directory)
- Exit code based on score
- Duration: 2-5 minutes
- Works with both personal and repository templates

**Level 3: Comprehensive Audit** (On-demand)
```bash
# Personal templates
/template-validate ~/.agentecflow/templates/my-template

# Repository templates
/template-validate installer/global/templates/react-typescript
```
- Interactive 16-section audit
- Section selection
- Session save/resume
- Inline issue fixes
- AI-assisted analysis (sections 8,11,12,13)
- Comprehensive audit report (saved in template directory)
- Decision framework
- Duration: 30-60 minutes (with AI)
- Works with templates in either location

### When to Use Each Level

**Use Level 1** (Automatic):
- Personal templates (default location: `~/.agentecflow/templates/`)
- Quick prototyping
- Learning template creation

**Use Level 2** (`--validate`):
- Before sharing with team
- Pre-deployment QA for repository templates (`--output-location=repo`)
- CI/CD integration
- Quality reporting

**Use Level 3** (`/template-validate`):
- Global template deployment (repository templates)
- Production-critical templates
- Comprehensive audit required
- Development/testing
- Works with templates in either personal or repository location

### Quality Reports

Level 2 and 3 generate markdown reports in the template directory:
- `validation-report.md` (Level 2)
- `audit-report.md` (Level 3)

Reports include:
- Quality scores (0-10)
- Detailed findings
- Actionable recommendations
- Production readiness assessment

**Template Locations**:
- **Personal templates**: `~/.agentecflow/templates/` (default, immediate use)
- **Repository templates**: `installer/global/templates/` (team/public distribution, requires `--output-location=repo` flag)

Validation works with templates in either location.

**See**: [Template Validation Guide](docs/guides/template-validation-guide.md)

## Design-First Workflow

Optional flags for complex tasks requiring upfront design approval.

**Flags:**
- `--design-only`: Phases 2-2.8, stops at checkpoint, saves plan
- `--implement-only`: Phases 3-5, requires `design_approved` state
- (default): All phases 2-5.5 in sequence

**Use `--design-only` when:**
- Complexity ≥7
- High-risk changes (security, breaking, schema)
- Multi-person teams (architect designs, dev implements)
- Multi-day tasks

**See**: [Design-First Workflow](docs/workflows/design-first-workflow.md)

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

## Template Philosophy

Taskwright includes **6 high-quality templates** for learning and evaluation:

### Stack-Specific Reference Templates (9+/10 Quality)
1. **react-typescript** - Frontend best practices (from Bulletproof React)
2. **fastapi-python** - Backend API patterns (from FastAPI Best Practices)
3. **nextjs-fullstack** - Full-stack application (Next.js App Router)

### Specialized Templates (8-9+/10 Quality)
4. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)
5. **taskwright-python** - Python CLI with orchestrator pattern (8+/10)

### Language-Agnostic Template (8+/10 Quality)
6. **default** - For Go, Rust, Ruby, Elixir, PHP, and other languages

### Why This Approach?

**Templates are learning resources, not production code.**

Each template demonstrates:
- ✅ How to structure templates for `/template-create`
- ✅ Stack-specific best practices (or language-agnostic patterns)
- ✅ Taskwright workflow integration
- ✅ High quality standards (all score 8+/10)

### For Production: Use `/template-create`

```bash
# Evaluate Taskwright (reference template)
taskwright init react-typescript

# Production workflow (recommended)
cd your-existing-project
/template-create
taskwright init your-custom-template
```

**Why?** Your production code is better than any generic template. Create templates from what you've proven works.

**See**: [Template Philosophy Guide](docs/guides/template-philosophy.md) for detailed explanation.

## Installation & Setup

```bash
# Install
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with template
taskwright init [react-typescript|fastapi-python|nextjs-fullstack|default]

# View template details
taskwright init react-typescript --info
```

**Template Documentation:**
- [react-typescript](installer/global/templates/react-typescript/README.md) - From Bulletproof React (28.5k stars)
- [fastapi-python](installer/global/templates/fastapi-python/README.md) - From FastAPI Best Practices (12k+ stars)
- [nextjs-fullstack](installer/global/templates/nextjs-fullstack/README.md) - Next.js App Router + production patterns
- [react-fastapi-monorepo](installer/global/templates/react-fastapi-monorepo/README.md) - React + FastAPI monorepo (9.2/10)
- [taskwright-python](installer/global/templates/taskwright-python/README.md) - Python CLI with orchestrator pattern (8+/10)
- [default](installer/global/templates/default/README.md) - Language-agnostic foundation

**See Also:**
- [Template Philosophy Guide](docs/guides/template-philosophy.md) - Why these 6 templates?
- [Creating Local Templates](docs/guides/creating-local-templates.md) - Team-specific templates
- [Template Migration Guide](docs/guides/template-migration.md) - Migrating from old templates

## Conductor Integration

Fully compatible with [Conductor.build](https://conductor.build) for parallel development.

**State Persistence:** ✅
- Symlink architecture + auto-commit
- 100% state preservation across worktrees
- Zero manual intervention required

**Setup:**
```bash
./installer/scripts/install.sh  # Creates symlinks automatically
taskwright doctor              # Verify integration
```

**How It Works:**
- Commands/agents: `~/.claude/* → ~/.agentecflow/*`
- State: `{worktree}/.claude/state → {main-repo}/.claude/state`
- All commands available in every worktree
- Automatic state sync across parallel sessions

## Testing by Stack

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

## Quality Gates (Automatic with `/task-work`)

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Review | ≥60/100 | Human checkpoint |
| Plan Audit | 0 violations | Variance review |

**Phase 4.5 Test Enforcement:**
1. Compilation check
2. Test execution
3. Failure analysis (if needed)
4. Auto-fix + re-run (up to 3 attempts)
5. Block if all attempts fail

**Phase 5.5 Plan Audit:**
- File count match (100%)
- Implementation completeness (100%)
- Scope creep detection (0 violations)
- LOC variance (±20% acceptable)
- Duration variance (±30% acceptable)

## Task States & Transitions

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

**States:**
- **BACKLOG**: New task, not started
- **DESIGN_APPROVED**: Design approved (design-first workflow)
- **IN_PROGRESS**: Active development
- **IN_REVIEW**: All quality gates passed
- **BLOCKED**: Tests failed or quality gates not met
- **COMPLETED**: Finished and archived

## Core AI Agents

**Global Agents:**
- **architectural-reviewer**: SOLID/DRY/YAGNI compliance review
- **task-manager**: Unified workflow management
- **test-verifier/orchestrator**: Test execution and quality gates
- **code-reviewer**: Code quality enforcement
- **software-architect**: System design decisions
- **devops-specialist**: Infrastructure patterns
- **security-specialist**: Security validation
- **database-specialist**: Data architecture

**Stack-Specific Agents:**
- API/Domain/Testing/UI specialists per technology stack

**See**: `installer/global/agents/*.md` for agent specifications.

## MCP Integration Best Practices

The system integrates with 4 MCP servers for enhanced capabilities. **All MCPs are optional** - the system works fine without them and falls back gracefully to training data.

### MCP Types

**Core MCPs** (used automatically during `/task-work`):
- **context7**: Library documentation (Phases 2, 3, 4 - automatic when task uses libraries)
- **design-patterns**: Pattern recommendations (Phase 2.5A - automatic during architectural review)

**Design MCPs** (ONLY used for specific commands):
- **figma-dev-mode**: Figma design extraction (ONLY for `/figma-to-react` command)
- **zeplin**: Zeplin design extraction (ONLY for `/zeplin-to-maui` command)

**Important**: Design MCPs should only be installed if you're actively using those specific design-to-code commands. They are NOT used during regular `/task-work` execution.

### Setup Guides

**Core MCPs** (recommended for all users):
- [Context7 MCP Setup](docs/guides/context7-mcp-setup.md) - Up-to-date library documentation
- [Design Patterns MCP Setup](docs/guides/design-patterns-mcp-setup.md) - Pattern recommendations

**Design MCPs** (only if using design-to-code workflows):
- [Figma MCP Setup](docs/mcp-setup/figma-mcp-setup.md) - For `/figma-to-react` command only
- [Zeplin MCP Setup](docs/mcp-setup/zeplin-mcp-setup.md) - For `/zeplin-to-maui` command only

### Performance & Optimization

**Optimization Status**: ✅ All MCPs optimized (4.5-12% context window usage)

**Token Budgets**:
- context7: 2000-6000 tokens (phase-dependent)
- design-patterns: ~5000 tokens (5 results), ~3000 per detailed pattern
- figma-dev-mode: Image-based (minimal token impact)
- zeplin: Design-based (minimal token impact)

**For detailed usage guidelines**: [MCP Optimization Guide](docs/guides/mcp-optimization-guide.md)

## Development Best Practices

**Quality Standards:**
1. **NEVER implement** features not explicitly specified (zero scope creep)
2. **ALWAYS use `/task-work`** for implementation (handles review, testing, gates automatically)
3. **Trust architectural review** (Phase 2.5 catches issues before implementation)
4. **Trust test enforcement** (Phase 4.5 ensures 100% pass rate)
5. **Track everything in tasks** (complete traceability)

**Development Mode Selection:**
- **TDD**: Complex business logic (Red → Green → Refactor)
- **Standard**: Straightforward implementations

**Note:** For BDD workflows (EARS → Gherkin → Implementation), use [require-kit](https://github.com/requirekit/require-kit) which provides complete requirements management.

**Architecture Compliance:**
- Pattern consistency per stack
- Self-documenting code
- Clean separation of concerns

## Key Workflow

**Simple Task Workflow:**
```bash
# Create task
/task-create "Add user authentication"

# Work on it (Phases 2-5.5 automatic)
/task-work TASK-001

# Complete
/task-complete TASK-001
```

**Complex Task Workflow (Design-First):**
```bash
# Create complex task
/task-create "Refactor authentication system" priority:high

# Design phase only
/task-work TASK-002 --design-only

# [Human reviews and approves plan]

# Implementation phase
/task-work TASK-002 --implement-only

# Complete
/task-complete TASK-002
```

**See**: [Taskwright Workflow](docs/guides/taskwright-workflow.md)

## Iterative Refinement

**`/task-refine`**: Lightweight improvement without full re-work.

**Use for:**
- Minor code improvements
- Linting fixes
- Renaming/formatting
- Adding comments

**Don't use for:**
- New features (use `/task-work`)
- Architecture changes
- Major refactoring

**See**: [Taskwright Workflow - Iterative Refinement](docs/guides/taskwright-workflow.md#37-iterative-refinement)

## Markdown Implementation Plans

All plans saved as human-readable Markdown in `.claude/task-plans/{task_id}-implementation-plan.md`.

**Benefits:**
- Human-reviewable (plain text)
- Git-friendly (meaningful diffs)
- Searchable (grep, ripgrep, IDE)
- Editable (manual edits before `--implement-only`)

## Quick Reference

**Command Specifications:** `installer/global/commands/*.md`
**Agent Definitions:** `installer/global/agents/*.md`
**Workflow Guides:** `docs/guides/*.md` and `docs/workflows/*.md`
**Stack Templates:** `installer/global/templates/*/`

## When to Use Taskwright

### Use When:
- Individual tasks or small features (1-8 hours)
- Solo dev or small teams (1-3 developers)
- Need quality enforcement without ceremony
- Want AI assistance with human oversight
- Small-to-medium projects
- **Learning new stack** (use reference templates)
- **Creating team templates** (use `/template-create`)

### Use RequireKit When:
- Need formal requirements management (EARS notation, BDD scenarios)
- Need epic/feature hierarchy
- Need requirements traceability matrices
- Need PM tool integration (Jira, Linear, Azure DevOps, GitHub)

## Need Requirements Management?

For formal requirements (EARS notation, BDD with Gherkin, epic/feature hierarchy, PM tool sync), see [RequireKit](https://github.com/requirekit/require-kit) which integrates seamlessly with Taskwright.
