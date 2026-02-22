# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GuardKit - Lightweight AI-Assisted Development

A lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

**Core Features:** Quality Gates (Phase 2.5 + 4.5) | Simple Workflow (Create → Work → Complete) | AI Collaboration | Zero Ceremony

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
/task-work TASK-XXX [--mode=standard|tdd] [--intensity=minimal|light|standard|strict] [--micro]
/task-complete TASK-XXX
/task-status [TASK-XXX]
/task-refine TASK-XXX
```

### Review Workflow
```bash
/task-create "Title" task_type:review
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH]
```

### Feature Planning & Build
```bash
/feature-plan "description" [--context file.md]
/feature-build TASK-XXX [--max-turns N] [--resume] [--verbose]
/feature-complete TASK-XXX [--dry-run] [--verify]
```

### Design-First Workflow
```bash
/task-work TASK-XXX --design-only      # Phases 2-2.8, stops at checkpoint
/task-work TASK-XXX --implement-only   # Phases 3-5, requires approved plan
```

### Agent & Template Management
```bash
/agent-format <template>/<agent>
/agent-validate <agent-file>
/agent-enhance <agent-file> <template-dir> [--strategy=ai|static|hybrid]
/template-validate <template-path>
/template-create [--no-rules-structure]
```

### System Context Commands
```bash
/system-overview [--verbose] [--section=SECTION]  # Architecture summary
/impact-analysis TASK-XXX [--depth=DEPTH]         # Pre-task validation
/context-switch [project-name]                    # Multi-project navigation
```

### Utilities
```bash
/debug                                 # Troubleshoot issues
guardkit autobuild task TASK-XXX       # CLI autobuild
guardkit graphiti capture --interactive # Knowledge capture
guardkit graphiti search "query"       # Search knowledge
```

**See**: `installer/core/commands/*.md` for complete command specifications.

## AutoBuild

Autonomous task implementation using Player-Coach adversarial workflow.
See: `.claude/rules/autobuild.md` for full documentation.

## Hash-Based Task IDs

Format: `TASK-{hash}` or `TASK-{prefix}-{hash}` (e.g., `TASK-FIX-a3f8`)
See: `.claude/rules/hash-based-ids.md` for full documentation.

## Task Workflow Phases

```
Phase 2: Implementation Planning (Markdown format)
Phase 2.5: Architectural Review (SOLID/DRY/YAGNI scoring)
Phase 2.7: Complexity Evaluation (0-10 scale)
Phase 2.8: Human Checkpoint (if complexity >=7)
Phase 3: Implementation
Phase 4: Testing (compilation + coverage)
Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
Phase 5: Code Review
Phase 5.5: Plan Audit (scope creep detection)
```

**Key Decision Points:** Phase 2.7 auto-proceed (1-3) vs checkpoint (7-10) | Phase 4.5 auto-fix vs block | Phase 5.5 approve vs escalate

## Complexity Evaluation

| Level | Score | Duration | Review Mode |
|-------|-------|----------|-------------|
| Simple | 1-3 | <4 hours | AUTO_PROCEED |
| Medium | 4-6 | 4-8 hours | QUICK_OPTIONAL |
| Complex | 7-10 | >8 hours | FULL_REQUIRED |

**See**: [Complexity Management Workflow](docs/workflows/complexity-management-workflow.md)

## Quality Gates

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | >=80% | Request more tests |
| Branch Coverage | >=75% | Request more tests |
| Architectural Review | >=60/100 | Human checkpoint |
| Plan Audit | 0 violations | Variance review |

## Task States & Transitions

```
BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED
              ↓              ↓
          BLOCKED        BLOCKED

BACKLOG → (--design-only) → DESIGN_APPROVED → (--implement-only) → IN_PROGRESS
```

**States:** BACKLOG | DESIGN_APPROVED | IN_PROGRESS | IN_REVIEW | REVIEW_COMPLETE | BLOCKED | COMPLETED

## Testing by Stack

```bash
# Python
pytest tests/ -v --cov=src --cov-report=term --cov-report=json
# TypeScript/JavaScript
npm test -- --coverage
# .NET
dotnet test --collect:"XPlat Code Coverage" --logger:"json"
```

## Project Structure

```
.claude/                    # Configuration (agents, commands, task-plans)
tasks/                      # Task management (backlog, in_progress, in_review, blocked, completed)
docs/                       # Documentation (guides, workflows)
guardkit/                   # Python package source
installer/core/             # Global resources (agents, commands, templates)
```

## Development Best Practices

1. **NEVER implement** features not explicitly specified (zero scope creep)
2. **ALWAYS use `/task-work`** for implementation
3. **Trust architectural review** (Phase 2.5) and **test enforcement** (Phase 4.5)
4. **Track everything in tasks** for complete traceability

## Key References

| Resource | Location |
|----------|----------|
| Command Specs | `installer/core/commands/*.md` |
| Agent Definitions | `installer/core/agents/*.md` |
| Workflow Guides | `docs/guides/*.md`, `docs/workflows/*.md` |
| System Context | `docs/guides/system-overview-guide.md`, `impact-analysis-guide.md`, `context-switch-guide.md` |
| Stack Templates | `installer/core/templates/*/` |
| Rules & Patterns | `.claude/rules/` |
| MCP Integration | `docs/deep-dives/mcp-integration/` |
| Graphiti Knowledge | `.claude/rules/graphiti-knowledge.md` |
| Installation | `pip install guardkit-py` or `./installer/scripts/install.sh` |

## Clarifying Questions

Flags: `--no-questions` | `--with-questions` | `--defaults` | `--answers="..."`
See: `.claude/rules/clarifying-questions.md`

## BDD / Specification Workflow

```bash
/feature-spec "description" [--from file.md] [--output dir/] [--auto] [--stack name] [--context file.md]
```

Generate BDD Gherkin specifications from natural language using Propose-Review methodology.
See: [Feature Spec Command Reference](docs/commands/feature-spec.md)

For agentic systems requiring formal behavior specs: `/task-work TASK-XXX --mode=bdd`
Requires: [require-kit](https://github.com/requirekit/require-kit)
See: [BDD Workflow Guide](docs/guides/bdd-workflow-for-agentic-systems.md)

## Graphiti Knowledge Capture

Persistent knowledge capture across sessions. See: `.claude/rules/graphiti-knowledge.md`

## MCP Integration

Optional MCP servers: **context7** (library docs) | **design-patterns** (pattern recommendations)
All MCPs are optional - falls back gracefully to training data.
See: `docs/deep-dives/mcp-integration/` for setup and optimization.

## Conductor Integration

Fully compatible with [Conductor.build](https://conductor.build) for parallel development.
See: `docs/deep-dives/conductor-integration.md`

## Installation

```bash
pip install guardkit-py              # Basic
pip install guardkit-py[autobuild]   # With AutoBuild support
pip install guardkit-py[dev]         # Development
guardkit init [template-name]        # Initialize project
```

Templates: react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | default
