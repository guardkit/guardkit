# Core Concepts

Understand the fundamentals of GuardKit's workflow and quality gates.

## 🎯 Feature Plan Development (FPD)

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

**FPD Manifesto:**
- Features over files
- Plans over improvisation
- Structured decomposition over ad-hoc tasking
- Parallel execution over sequential bottlenecks
- Automation where possible, human oversight where needed

## 🔄 [GuardKit Workflow](guides/guardkit-workflow.md)

The complete workflow from task creation to completion, including all phases and quality gates.

**Workflow Phases:**

- Phase 1.6: Clarifying Questions (complexity-gated, ~15% rework reduction)
- Phase 2: Implementation Planning (Markdown format)
- Phase 2.5: Architectural Review (SOLID/DRY/YAGNI scoring)
- Phase 2.7: Complexity Evaluation (0-10 scale)
- Phase 2.8: Human Checkpoint (if complexity ≥7 or review required)
- Phase 3: Implementation
- Phase 4: Testing (compilation + coverage)
- Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
- Phase 5: Code Review
- Phase 5.5: Plan Audit (scope creep detection)

**Start here** to understand the end-to-end process.

## 💬 Clarifying Questions

GuardKit asks targeted questions before making assumptions (~15% rework reduction):

```bash
/task-work TASK-a3f8

📋 CLARIFYING QUESTIONS (complexity: 5)

Q1. Implementation Scope
    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases
    Your choice: S
```

**Complexity-gated**: Simple tasks (1-2) skip questions, medium tasks (3-4) get quick questions with timeout, complex tasks (5+) get full clarification.

**Flags**: `--no-questions` (skip), `--with-questions` (force), `--defaults` (use defaults), `--answers="..."` (inline for CI/CD)

## 🔑 Hash-Based Task IDs

GuardKit uses collision-free hash-based task IDs to enable parallel development and concurrent task creation.

**Format:**

- Simple: `TASK-a3f8`
- With prefix: `TASK-E01-b2c4`, `TASK-FIX-a3f8`
- With subtask: `TASK-E01-b2c4.1`

**Benefits:**

- ✅ **Zero duplicates** - Mathematically guaranteed unique IDs
- ✅ **Concurrent creation** - Safe for parallel development across Conductor.build worktrees
- ✅ **PM tool integration** - Automatic mapping to JIRA, Azure DevOps, Linear, GitHub sequential IDs

**Learn More:**

- [Hash-Based ID Parallel Development](guides/hash-id-parallel-development.md) - 20-33% faster completion with Conductor.build
- [Hash-Based IDs and PM Tools](guides/hash-id-pm-tools.md) - Bidirectional ID mapping

## 📊 [Complexity Management](workflows/complexity-management-workflow.md)

How GuardKit evaluates task complexity and decides when to require human review.

**Complexity Scoring (0-10):**

- **1-3 (Simple)**: <4 hours, AUTO_PROCEED
- **4-6 (Medium)**: 4-8 hours, QUICK_OPTIONAL (30s timeout)
- **7-10 (Complex)**: >8 hours, FULL_REQUIRED (mandatory checkpoint)

**Two-Stage System:**

1. **Upfront (task-create)**: Decide if task should be split (threshold: 7/10)
2. **Planning (task-work)**: Decide review mode (auto/quick/full)

Learn how complexity evaluation saves time and prevents over-engineering.

## ✅ [Quality Gates](workflows/quality-gates-workflow.md)

Automatic enforcement of compilation, testing, coverage, and architectural standards.

**Quality Thresholds:**

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Compilation | 100% | Task → BLOCKED |
| Tests Pass | 100% | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | Request more tests |
| Branch Coverage | ≥75% | Request more tests |
| Architectural Review | ≥60/100 | Human checkpoint |
| Plan Audit | 0 violations | Variance review |

**Phase 4.5 Test Enforcement** ensures no broken code reaches production.

## 📋 [Task States & Transitions](guides/guardkit-workflow.md#task-states)

How tasks move through backlog, in_progress, in_review, blocked, and completed states.

**State Flow:**

```
BACKLOG
   ├─ (task-work) ──────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                            ↓              ↓
   │                        BLOCKED        BLOCKED
   │
   ├─ (task-review) ─────→ IN_PROGRESS ──→ REVIEW_COMPLETE ──→ COMPLETED
   │                            ↓              ↓                      ↑
   │                        BLOCKED     [I]mplement → task-work ─────┘
   │
   └─ (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (task-work --implement-only) ─→ IN_PROGRESS
```

**Key States:**

- **BACKLOG**: New task, not started
- **IN_PROGRESS**: Active development
- **IN_REVIEW**: All quality gates passed
- **REVIEW_COMPLETE**: Review finished, awaiting decision (review tasks)
- **BLOCKED**: Tests failed or quality gates not met
- **COMPLETED**: Finished and archived

## 🎯 [Development Modes](guides/guardkit-workflow.md#development-modes)

Standard vs TDD mode for different types of tasks.

**Mode Selection:**

- **TDD (Test-Driven Development)**: Complex business logic, critical algorithms
- **Standard**: Straightforward implementations, CRUD operations, UI components

**TDD Workflow:** Red → Green → Refactor

Learn when to use each mode for optimal productivity.

## 🤖 [Agent Discovery](guides/agent-discovery-guide.md)

How GuardKit automatically matches tasks to specialized AI agents.

**Discovery Process:**

1. System analyzes task context (file extensions, keywords, project structure)
2. Scans all agents for metadata match (stack + phase + capabilities)
3. Selects specialist if found, falls back to task-manager if not
4. Shows which agent selected and why

**Stack-Specific Agents:**

- **python-api-specialist**: FastAPI endpoints, async patterns, Pydantic schemas (Haiku)
- **react-state-specialist**: React hooks, TanStack Query, state management (Haiku)
- **dotnet-domain-specialist**: Domain models, DDD patterns, value objects (Haiku)

**Benefits:** 4-5x faster implementation, 48-53% cost savings, 90%+ quality maintained.

---

## Next Steps

- **Getting Started**: [5-Minute Quickstart](guides/GETTING-STARTED.md)
- **First Task**: Try `/task-create` and `/task-work`
- **Advanced**: Explore [Design-First Workflow](workflows/design-first-workflow.md)
