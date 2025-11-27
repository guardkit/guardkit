# Core Concepts

Understand the fundamentals of Taskwright's workflow and quality gates.

## 🔄 [Taskwright Workflow](guides/taskwright-workflow.md)

The complete workflow from task creation to completion, including all phases and quality gates.

**Workflow Phases:**

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

## 📊 [Complexity Management](workflows/complexity-management-workflow.md)

How Taskwright evaluates task complexity and decides when to require human review.

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

## 📋 [Task States & Transitions](guides/taskwright-workflow.md#task-states)

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

## 🎯 [Development Modes](guides/taskwright-workflow.md#development-modes)

Standard vs TDD mode for different types of tasks.

**Mode Selection:**

- **TDD (Test-Driven Development)**: Complex business logic, critical algorithms
- **Standard**: Straightforward implementations, CRUD operations, UI components

**TDD Workflow:** Red → Green → Refactor

Learn when to use each mode for optimal productivity.

## 🤖 [Agent Discovery](guides/agent-discovery-guide.md)

How Taskwright automatically matches tasks to specialized AI agents.

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
