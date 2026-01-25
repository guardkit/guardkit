# GuardKit Workflow Guide

**Version**: 2.1.0
**Last Updated**: 2026-01-24
**Compatibility**: Claude Code with task-work command v1.0+
**Document Type**: Comprehensive Workflow Guide

---

## Table of Contents

### Part 1: Quick Start (5 Minutes)
- [What is GuardKit?](#what-is-guardkit)
- [5-Minute Getting Started](#5-minute-getting-started)
- [When to Use GuardKit](#when-to-use-guardkit)
- [Review vs Implementation Workflows](#review-vs-implementation-workflows)
- [Manual Task-Work vs AutoBuild Delegation](#manual-task-work-vs-autobuild-delegation) 🆕

### Part 2: Core Workflow (15 Minutes)
- [The 10 Workflow Phases](#the-10-workflow-phases)
- [Quality Gates](#quality-gates)
- [State Management](#state-management)

### Part 3: Feature Deep Dives (30+ Minutes)
- [3.1 Clarifying Questions](#31-clarifying-questions)
- [3.2 Complexity Evaluation](#32-complexity-evaluation)
- [3.3 Design-First Workflow](#33-design-first-workflow)
- [3.4 Test Enforcement Loop](#34-test-enforcement-loop)
- [3.5 Architectural Review](#35-architectural-review)
- [3.6 Human Checkpoints](#36-human-checkpoints)
- [3.7 Plan Audit](#37-plan-audit)
- [3.8 Iterative Refinement](#38-iterative-refinement)
- [3.9 MCP Tool Discovery](#39-mcp-tool-discovery)
- [3.10 Design System Detection](#310-design-system-detection)

### Part 4: Practical Usage
- [4.1 Complete Workflow Examples](#41-complete-workflow-examples)
- [4.2 Decision Trees & Flowcharts](#42-decision-trees--flowcharts)
- [4.3 Troubleshooting & FAQ](#43-troubleshooting--faq)

---

# Part 1: QUICK START (5 Minutes)

## What is GuardKit?

**GuardKit** is a lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

### Core Philosophy

- **Quality First**: Never compromise on test coverage or architecture
- **Pragmatic**: Right amount of process for task complexity
- **AI/Human Collaboration**: AI does heavy lifting, humans make decisions
- **Zero Ceremony**: No unnecessary documentation or process

### What You Get

**Automated Workflow**:
- Implementation planning with architectural review
- Complexity evaluation (1-10 scale)
- Human checkpoints for critical decisions
- Automatic test enforcement (100% pass rate required)
- Code quality review (SOLID/DRY/YAGNI)
- Scope creep detection (plan audit)

**State Management**:
```
BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED
            ↓              ↓
         BLOCKED        BLOCKED
```

**Technology Agnostic**:
- Works with all major stacks (React, Python, .NET, etc.)
- Stack-specific templates available
- Custom templates supported

### When to Use GuardKit

**Use GuardKit when**:
- Working on individual tasks (1-8 hour chunks)
- Solo dev or small teams (1-3 developers)
- Want quality gates without ceremony
- Need AI assistance with human oversight
- Small-to-medium projects

**Benefits**:
- Streamlined task completion
- Zero manual quality checks
- Automatic architectural review
- Automatic test enforcement
- Clear task states and progress

---

## 5-Minute Getting Started

### Prerequisites

```bash
# Verify task-work command available
/task-work --help
```

### Your First Task

**Step 1**: Create a simple task (natural language description)

```bash
/task-create "There's a typo in the authentication error message that needs to be fixed"
```

**Step 2**: Work on the task

```bash
/task-work TASK-001
```

**Step 3**: Watch the workflow execute

```
═══════════════════════════════════════════════════════
🔄 PHASE 1: LOAD TASK CONTEXT
═══════════════════════════════════════════════════════
✅ Found: TASK-001 (state: backlog)
✅ Transitioned TASK-001 from backlog to IN_PROGRESS

═══════════════════════════════════════════════════════
📋 PHASE 2: IMPLEMENTATION PLANNING
═══════════════════════════════════════════════════════
Plan: Edit src/services/AuthService.py line 45
Estimated duration: 2 minutes

═══════════════════════════════════════════════════════
🔍 PHASE 2.5B: ARCHITECTURAL REVIEW
═══════════════════════════════════════════════════════
Score: 95/100 (Auto-approved)
  SOLID: 95/100 ✅
  DRY: 100/100 ✅
  YAGNI: 90/100 ✅

═══════════════════════════════════════════════════════
📊 PHASE 2.7: COMPLEXITY EVALUATION
═══════════════════════════════════════════════════════
Complexity: 1/10 (Simple)
Review Mode: AUTO_PROCEED

Auto-approving (low complexity)...

═══════════════════════════════════════════════════════
🚀 PHASE 3: IMPLEMENTATION
═══════════════════════════════════════════════════════
Edited src/services/AuthService.py:45
  - raise Exception("Authentication occured successfully")
  + raise Exception("Authentication occurred successfully")

═══════════════════════════════════════════════════════
✅ PHASE 4: TESTING
═══════════════════════════════════════════════════════
Compilation: PASSED ✅
Tests: 5/5 PASSED ✅
Coverage: 85% line, 78% branch ✅

═══════════════════════════════════════════════════════
👀 PHASE 5: CODE REVIEW
═══════════════════════════════════════════════════════
Quality: APPROVED ✅
  Lint: 0 issues
  Style: Consistent
  Documentation: Adequate

═══════════════════════════════════════════════════════
✅ TASK WORK COMPLETE
═══════════════════════════════════════════════════════
State: BACKLOG → IN_REVIEW
Duration: 1 minute 47 seconds
All quality gates passed ✅
```

**Step 4**: Complete the task

```bash
/task-complete TASK-001
```

### What Just Happened?

In under 2 minutes, GuardKit:

1. **Analyzed** your task description
2. **Planned** the implementation approach
3. **Reviewed** the architecture (SOLID/DRY/YAGNI)
4. **Evaluated** complexity (determined it was simple)
5. **Implemented** the fix automatically
6. **Tested** the change (compilation + tests)
7. **Reviewed** code quality
8. **Moved** the task to IN_REVIEW state

All without you writing any code, running any tests, or managing state transitions manually.

---

## Review vs Implementation Workflows

GuardKit provides two distinct workflows depending on whether you're **building code** or **analyzing/deciding**:

### Implementation Workflow (`/task-work`)

Use for **building** features, fixing bugs, refactoring:

```bash
/task-create "Add user authentication"
/task-work TASK-001  # Phases: Planning → Review → Implementation → Testing → Code Review
/task-complete TASK-001
```

**Best for:**
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

### Review Workflow (`/task-review`)

Use for **analysis** and **decision-making** tasks:

```bash
/task-create "Review authentication architecture" task_type:review
/task-review TASK-002 --mode=architectural  # Phases: Load Context → Analyze → Report → Decision
# Optional: /task-work TASK-003 (implement recommendations)
/task-complete TASK-002
```

**Best for:**
- Architectural reviews
- Code quality assessments
- Technical decisions ("Should we...?")
- Technical debt inventory
- Security audits

### Quick Comparison

| Aspect | `/task-work` | `/task-review` |
|--------|--------------|----------------|
| **Purpose** | Build/fix code | Analyze/decide |
| **Output** | Working code + tests | Analysis report + recommendations |
| **Phases** | 9 phases (planning → testing) | 5 phases (context → decision) |
| **Quality Gates** | Tests pass, coverage ≥80% | N/A (review only) |
| **Duration** | 5min - 4 hours | 15min - 6 hours |
| **End State** | `IN_REVIEW` or `BLOCKED` | `REVIEW_COMPLETE` |

### How to Choose

**Use `/task-work` if your task title starts with:**
- "Implement..."
- "Add..."
- "Fix..."
- "Refactor..."
- "Create..."

**Use `/task-review` if your task title starts with:**
- "Review..."
- "Analyze..."
- "Evaluate..."
- "Should we..."
- "Assess..."
- "Audit..."

**Note:** The system automatically detects review tasks during `/task-create` and suggests the appropriate command.

**See:** [Task Review Workflow Guide](../workflows/task-review-workflow.md) for complete review workflow documentation.

---

### Manual Task-Work vs AutoBuild Delegation

GuardKit supports two ways to execute the task-work workflow:

> **📖 Comprehensive AutoBuild Documentation**
>
> For complete AutoBuild documentation including architecture deep-dive, CLI reference,
> and troubleshooting, see the [AutoBuild Workflow Guide](autobuild-workflow.md).

#### Manual Execution (`/task-work`)

Direct human-driven execution:

```bash
/task-work TASK-042
# Human monitors Phases 2-5.5
# Human approves checkpoints
# Task moves to IN_REVIEW when quality gates pass
```

**Best for:**
- Exploratory work requiring human judgment
- Complex architectural decisions
- High-risk changes requiring human oversight
- Learning how quality gates work

**Characteristics:**
- Human in the loop for checkpoints
- Interactive Phase 2.8 approval
- Can modify plan before implementation
- Single execution (no iteration)

#### AutoBuild Delegation (`/feature-build`)

Autonomous execution via Player-Coach adversarial loop:

```bash
/feature-build TASK-042
# Player delegates to task-work --implement-only --mode=tdd
# Quality gates execute automatically (Phases 3-5.5)
# Coach validates results
# Iterates until approval or max turns
```

**Requirements**: AutoBuild requires the optional `claude-agent-sdk` dependency:
```bash
pip install guardkit-py[autobuild]
# OR
pip install claude-agent-sdk
```

If you see "Claude Agent SDK not installed", install the dependency above.

**Best for:**
- Well-defined requirements
- Standard implementation patterns
- Autonomous iteration without human intervention
- Parallel feature development (multiple tasks)

**Characteristics:**
- No human checkpoints (autonomous)
- Automatic Phase 2.8 approval
- Iterative improvement (up to 5 turns)
- Player-Coach dialectic

**See Also:** [AutoBuild Architecture](autobuild-workflow.md#part-2-architecture-deep-dive) for technical details on Player-Coach pattern.

#### Comparison Table

| Aspect | Manual Task-Work | AutoBuild Delegation |
|--------|------------------|---------------------|
| **Execution** | Human-driven | Autonomous (Player-Coach) |
| **Checkpoints** | Interactive | Automatic |
| **Iteration** | Single pass | Up to 5 turns |
| **Quality Gates** | Same (Phases 2-5.5) | Same (Phases 2-5.5) |
| **Human Oversight** | During execution | After completion (worktree review) |
| **Use Case** | Exploration, high-risk | Standard patterns, low-risk |
| **Code Reuse** | Direct execution | 100% (delegates to task-work) |

#### When to Choose

**Use Manual Task-Work** if:
- Requirements are unclear (need human judgment)
- Architecture is experimental
- High security/safety risk
- Want to learn the system

**Use AutoBuild** if:
- Requirements are clear and complete
- Standard implementation patterns
- Can tolerate autonomous iteration
- Want parallel development of multiple tasks

**Both Use Same Quality Gates** (100% code reuse):
- Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
- Phase 4.5: Test Enforcement Loop (100% pass rate)
- Phase 5: Code Review
- Phase 5.5: Plan Audit (scope creep detection)

The key difference is **who drives execution**: human (manual) or AI (AutoBuild).

**For complete CLI reference:** See [AutoBuild CLI Commands](autobuild-workflow.md#cli-command-reference).

---

### Pre-Loop Decision Guide

Use this decision tree to determine whether pre-loop design phases are needed:

```
Starting AutoBuild?
│
├─► Using feature-build (guardkit autobuild feature)?
│   │
│   ├─► Tasks from /feature-plan?
│   │   └─► Pre-loop NOT needed (default: disabled)
│   │       Tasks already have detailed specs from feature-plan
│   │
│   └─► Custom feature.yaml with minimal task specs?
│       │
│       ├─► Tasks have clear acceptance criteria?
│       │   └─► Pre-loop NOT needed (default: disabled)
│       │
│       └─► Tasks need clarification/design?
│           └─► Use --enable-pre-loop
│               Adds 60-90 min per task for design phases
│
└─► Using task-build (guardkit autobuild task)?
    │
    ├─► Task from /task-create with detailed requirements?
    │   └─► Pre-loop runs by default (can skip with --no-pre-loop)
    │
    └─► Simple bug fix or documentation task?
        └─► Consider --no-pre-loop for faster execution
```

### Pre-Loop Quick Reference

| Scenario | Command | Pre-Loop? | Duration |
|----------|---------|-----------|----------|
| Feature from feature-plan | `guardkit autobuild feature FEAT-XXX` | No | 15-25 min/task |
| Feature needing design | `guardkit autobuild feature FEAT-XXX --enable-pre-loop` | Yes | 75-105 min/task |
| Standalone task | `guardkit autobuild task TASK-XXX` | Yes | 75-105 min |
| Simple standalone task | `guardkit autobuild task TASK-XXX --no-pre-loop` | No | 15-25 min |

---

# Part 2: CORE WORKFLOW (15 Minutes)

## The 10 Workflow Phases

The `/task-work` command executes 10 phases automatically:

```
/task-work TASK-XXX
│
├─ PHASE 1: Load Task Context
│
├─ PHASE 1.6: Clarifying Questions ─────────┐
│   └─ Complexity-gated                        │ Human
│                                              │ Input
├─ PHASE 2: Implementation Planning            │
│   ├─ Feature 8: MCP Tool Discovery           │
│   └─ Feature 9: Design System Detection      │
│                                              │
├─ PHASE 2.5A: Pattern Suggestion              │
│                                              │
├─ PHASE 2.5B: Architectural Review ───────────┤ Quality
│   └─ SOLID/DRY/YAGNI Scoring                 │ Gates
│                                              │
├─ PHASE 2.7: Complexity Evaluation ───────────┤
│   └─ 1-10 Scoring & Review Routing           │
│                                              │
├─ PHASE 2.8: Human Checkpoint ────────────────┤
│   └─ Smart Approval (complexity-based)       │
│                                              │
├─ PHASE 3: Implementation                     │
│   └─ Code Generation from Plan               │
│                                              │
├─ PHASE 4: Testing                            │
│                                              │
├─ PHASE 4.5: Test Enforcement Loop ───────────┤
│   └─ Auto-Fix (up to 3 attempts)             │
│                                              │
├─ PHASE 5: Code Review                        │
│                                              │
├─ PHASE 5.5: Plan Audit ──────────────────────┤
│   └─ Scope Creep Detection                   │
│                                              │
└─ PHASE 6: Iterative Refinement               │
    └─ /task-refine Command ───────────────────┘
```

### Phase Descriptions

**Phase 1: Load Task Context**
- Locates task file in filesystem
- Parses frontmatter metadata
- Transitions BACKLOG → IN_PROGRESS
- Loads task description and acceptance criteria

**Phase 1.6: Clarifying Questions**
- Asks targeted questions before making assumptions
- Complexity-gated: simple tasks skip, complex tasks get full clarification
- Persists decisions to task frontmatter for audit trail
- Flags: `--no-questions`, `--with-questions`, `--defaults`, `--answers="..."`

**Phase 2: Implementation Planning**
- Generates structured implementation plan
- Identifies files to create/modify
- Lists dependencies and patterns
- Estimates duration and LOC
- Detects MCP tools and design systems

**Phase 2.5A: Pattern Suggestion**
- Suggests design patterns for implementation
- Provides pattern-specific guidance
- Integrates with design-patterns MCP

**Phase 2.5B: Architectural Review**
- Evaluates plan against SOLID principles
- Scores DRY (Don't Repeat Yourself)
- Scores YAGNI (You Aren't Gonna Need It)
- Overall score 0-100 (≥60 required to proceed)

**Phase 2.7: Complexity Evaluation**
- Calculates complexity score 1-10
- Analyzes 4 factors: files, patterns, risks, dependencies
- Determines review mode (auto/quick/full)
- Suggests task breakdown for complex tasks (≥7)

**Phase 2.8: Human Checkpoint**
- Complexity-based routing:
  - 1-3 (Simple): AUTO_PROCEED (no checkpoint)
  - 4-6 (Medium): QUICK_OPTIONAL (10s timeout)
  - 7-10 (Complex): FULL_REQUIRED (mandatory)
- Interactive plan review
- Options: Approve, Modify, View, Question, Cancel

**Phase 3: Implementation**
- Generates code based on approved plan
- Creates new files
- Modifies existing files
- Applies design patterns

**Phase 4: Testing**
- Compiles/interprets code
- Runs test suite
- Measures code coverage
- Captures test results

**Phase 4.5: Test Enforcement Loop**
- Zero tolerance for test failures
- Auto-fix attempts (up to 3 iterations)
- Blocks task if all fixes fail
- Ensures 100% test pass rate

**Phase 5: Code Review**
- Linting and style checking
- Code quality analysis
- Documentation verification
- SOLID principle adherence

**Phase 5.5: Plan Audit**
- Compares actual vs planned implementation
- Detects scope creep (unplanned files/features)
- Flags variance >50% for review
- Requires explanation for deviations

**Phase 6: Iterative Refinement**
- `/task-refine` command for IN_REVIEW tasks
- Preserves original context
- Re-runs quality gates
- Lightweight improvement cycle

---

## Quality Gates

All quality gates are enforced automatically. Tasks cannot proceed to IN_REVIEW without passing all gates.

### Required Quality Gates

| Gate | Threshold | Phase | Action if Failed |
|------|-----------|-------|-----------------|
| Architectural Review | ≥60/100 | 2.5B | Human checkpoint or rejection |
| Compilation | 100% | 4 | Task → BLOCKED |
| Tests Pass | 100% | 4.5 | Auto-fix (3 attempts) then BLOCKED |
| Line Coverage | ≥80% | 4 | Request more tests |
| Branch Coverage | ≥75% | 4 | Request more tests |
| Code Quality | Pass | 5 | Human review required |
| Plan Audit | 0 violations | 5.5 | Variance explanation required |

### Gate Execution Flow

```
Architectural Review (Phase 2.5B)
        ↓
   Score ≥60?
        ↓ Yes
Complexity Evaluation (Phase 2.7)
        ↓
   Human Checkpoint (Phase 2.8)
        ↓ Approved
Implementation (Phase 3)
        ↓
   Compilation Check (Phase 4)
        ↓ Pass
   Test Execution (Phase 4)
        ↓
   All Tests Pass?
        ↓ No → Auto-Fix (Phase 4.5) → Re-Test → Pass?
        ↓ Yes                                     ↓ No
   Coverage Check                            BLOCKED
        ↓ ≥80% line, ≥75% branch
   Code Review (Phase 5)
        ↓ Pass
   Plan Audit (Phase 5.5)
        ↓ No scope creep
    IN_REVIEW
```

---

## State Management

GuardKit uses filesystem-based state management. Task files move between directories to represent state transitions.

### State Directories

```
tasks/
├── backlog/              # BACKLOG state
│   └── TASK-XXX.md
├── design_approved/      # DESIGN_APPROVED state (design-first workflow)
│   └── TASK-XXX.md
├── in_progress/          # IN_PROGRESS state
│   └── TASK-XXX.md
├── in_review/            # IN_REVIEW state (implementation quality gates passed)
│   └── TASK-XXX.md
├── review_complete/      # REVIEW_COMPLETE state (review tasks awaiting decision)
│   └── TASK-XXX.md
├── blocked/              # BLOCKED state (quality gates failed)
│   └── TASK-XXX.md
└── completed/            # COMPLETED state
    └── TASK-XXX.md
```

### State Transitions

```
BACKLOG
   ├─ (task-work) ──────────────────→ IN_PROGRESS ──→ IN_REVIEW ──→ COMPLETED
   │                                         ↓              ↓
   │                                     BLOCKED        BLOCKED
   │
   ├─ (task-review) ─────────────────→ IN_PROGRESS ──→ REVIEW_COMPLETE ──→ COMPLETED
   │                                         ↓              ↓                      ↑
   │                                     BLOCKED     [I]mplement → task-work ─────┘
   │
   └─ (task-work --design-only) ─→ DESIGN_APPROVED
                                        │
                                        └─ (task-work --implement-only) ─→ IN_PROGRESS ──→ IN_REVIEW
                                                                                   ↓
                                                                               BLOCKED
```

**Automatic Transitions (Implementation)**:
- `/task-work` moves BACKLOG → IN_PROGRESS
- Quality gates determine IN_PROGRESS → IN_REVIEW or BLOCKED
- `/task-complete` moves IN_REVIEW → COMPLETED
- `/task-refine` keeps in IN_REVIEW (iterative improvement)

**Automatic Transitions (Review)**:
- `/task-review` moves BACKLOG → IN_PROGRESS
- Review completion moves IN_PROGRESS → REVIEW_COMPLETE
- Decision checkpoint offers:
  - [A]ccept → COMPLETED
  - [I]mplement → Creates new task, original stays REVIEW_COMPLETE
  - [R]evise → Stays REVIEW_COMPLETE, re-runs review
  - [C]ancel → Back to BACKLOG

**Manual Transitions**:
- `/task-unblock` moves BLOCKED → IN_PROGRESS (after fixes)
- Task file can be manually moved between directories

---

# Part 3: FEATURE DEEP DIVES (30+ Minutes)

## 3.1 Clarifying Questions

**Phase**: 1.6 of /task-work command
**Purpose**: Ask targeted questions before making assumptions.

### Quick Start

Clarifying questions appear automatically based on task complexity:

```bash
/task-work TASK-042

Phase 1: Loading context...
Phase 1.6: Clarifying Questions (complexity: 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CLARIFYING QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Implementation Scope
    How comprehensive should this implementation be?

    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases

    Your choice [M/S/C]: S

Q2. Testing Approach
    What testing strategy?

    [U]nit tests only
    [I]ntegration tests included (DEFAULT)
    [F]ull coverage (unit + integration + e2e)

    Your choice [U/I/F]: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 2 decisions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Planning implementation with clarifications...
```

### Complexity Gating

Questions are triggered based on task complexity:

| Complexity | Behavior | Timeout |
|------------|----------|---------|
| **1-2 (Simple)** | Skip questions entirely | N/A |
| **3-4 (Medium)** | Quick questions | 15 seconds |
| **5+ (Complex)** | Full clarification | Blocking |

### Command-Line Flags

All clarification behavior can be controlled:

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip clarification entirely |
| `--with-questions` | Force clarification even for simple tasks |
| `--defaults` | Use default answers without prompting |
| `--answers="1:S 2:I"` | Inline answers for CI/CD automation |
| `--reclarify` | Re-run clarification even if previous decisions exist |

### Example: CI/CD Automation

```bash
# Skip questions entirely
/task-work TASK-042 --no-questions

# Use defaults without prompting
/task-work TASK-042 --defaults

# Provide inline answers
/task-work TASK-042 --answers="scope:standard testing:integration"
```

### Persistence

Decisions are saved to task frontmatter for audit trail:

```yaml
clarification:
  context: implementation_planning
  timestamp: 2025-12-08T14:30:00Z
  mode: full
  decisions:
    - question_id: scope
      answer: standard
      default_used: true
    - question_id: testing
      answer: integration
      default_used: false
```

**Benefits:**
- Task resumption without re-asking questions
- Audit trail of planning decisions
- Reproducibility of AI behavior

### Multi-Command Support

Clarifying questions work across multiple commands:

| Command | Context Type | When | Purpose |
|---------|--------------|------|---------|
| `/task-work` | implementation_planning | Phase 1.6 | Guide implementation scope and approach |
| `/feature-plan` | review_scope | Before review | Guide what to analyze |
| `/feature-plan` | implementation_prefs | At [I]mplement | Guide subtask creation |
| `/task-review` | review_scope | Phase 1 | Guide review focus |

---

## 3.2 Complexity Evaluation

**Phase**: 2.7 of /task-work command
**Purpose**: Automatically evaluate task complexity to route to appropriate review mode and suggest task breakdown.

### Quick Start

Complexity evaluation happens automatically during task execution:

```bash
/task-work TASK-042

# Phase 2.7 executes:
Phase 2.7: Complexity Evaluation
  Analyzing implementation plan...

  Complexity Score: 3/10 (Simple)

  Factors:
    File Complexity: 1/3 (2 files)
    Pattern Familiarity: 0/2 (familiar patterns)
    Risk Level: 0/3 (low risk)
    Dependencies: 0/2 (no new deps)

  Review Mode: AUTO_PROCEED

  ✅ Auto-proceeding to implementation...
```

### Complexity Scoring System

Tasks are scored on a 1-10 scale using 4 weighted factors:

| Factor | Max Points | Scoring Rules |
|--------|------------|---------------|
| **File Complexity** | 3 | 1-2 files: 1pt, 3-5 files: 2pt, 6+ files: 3pt |
| **Pattern Familiarity** | 2 | All familiar: 0pt, Mixed: 1pt, New/unfamiliar: 2pt |
| **Risk Level** | 3 | Low: 0pt, Medium (ext deps): 1pt, High (security/breaking): 3pt |
| **Dependencies** | 2 | 0 deps: 0pt, 1-2 deps: 1pt, 3+ deps: 2pt |

**Score Thresholds**:
- **1-3 (Simple)**: Single developer, <4 hours, clear approach → AUTO_PROCEED
- **4-6 (Medium)**: Single developer, 4-8 hours, may need research → QUICK_OPTIONAL
- **7-10 (Complex)**: Consider breakdown, >8 hours, high risk → FULL_REQUIRED

### Integration with Human Checkpoints

Complexity evaluation feeds directly into Phase 2.8:

```python
if complexity_score <= 3:
    review_mode = "AUTO_PROCEED"  # Skip checkpoint
elif complexity_score <= 6:
    review_mode = "QUICK_OPTIONAL"  # 10-second timeout
else:  # complexity_score >= 7
    review_mode = "FULL_REQUIRED"  # Mandatory checkpoint
```

### Task Breakdown Suggestion

For complex tasks (≥7), the system suggests breaking into smaller tasks:

```bash
/task-work TASK-050

Phase 2.7: Complexity Evaluation

  ⚠️  Complexity Score: 8/10 (Complex)

  Factors:
    File Complexity: 3/3 (8 files - 5 create, 3 modify)
    Pattern Familiarity: 2/2 (Event Sourcing - unfamiliar)
    Risk Level: 3/3 (database schema migration)
    Dependencies: 2/2 (4 new packages)

  Review Mode: FULL_REQUIRED

  ⚠️  RECOMMENDATION: Consider splitting this task

  SUGGESTED BREAKDOWN:
  1. TASK-050.1: Design Event Sourcing architecture (Complexity: 5/10)
  2. TASK-050.2: Implement EventStore infrastructure (Complexity: 6/10)
  3. TASK-050.3: Implement Order aggregate (Complexity: 5/10)
  4. TASK-050.4: Add schema migration (Complexity: 4/10)
  5. TASK-050.5: Testing and integration (Complexity: 6/10)

  OPTIONS:
  1. [C]ontinue - Proceed with current scope (complexity 8/10)
  2. [S]plit - Create 5 subtasks instead (recommended)
  3. [M]odify - Adjust task scope to reduce complexity
  4. [A]bort - Cancel task and re-plan

  Your choice (C/S/M/A):
```

---

## 3.3 Design-First Workflow

**Phase**: 2-3 of /task-work command with optional flags
**Purpose**: Separate design and implementation phases for complex tasks requiring upfront design approval.

### Quick Start

Separate design from implementation for complex tasks:

```bash
# Step 1: Design-only (stops at approval checkpoint)
/task-work TASK-042 --design-only

# Phase 2-2.8 execute, task moves to design_approved state
✅ Design Approved
Task State: BACKLOG → DESIGN_APPROVED
Implementation plan saved: docs/state/TASK-042/implementation_plan.json

# Step 2: Human reviews saved design, approves

# Step 3: Implement approved design (same day or later)
/task-work TASK-042 --implement-only

# Phase 3-5 execute, task moves to in_review state
✅ Task Complete
Task State: DESIGN_APPROVED → IN_REVIEW
Tests: 100% passing
```

### Workflow Flags

| Mode | Flag | Phases Executed | Use Case |
|------|------|----------------|----------|
| **Design-Only** | `--design-only` | 1 → 2 → 2.5A → 2.5B → 2.7 → 2.8 | Design approval before implementation |
| **Implement-Only** | `--implement-only` | 3 → 4 → 4.5 → 5 | Implement previously approved design |
| **Standard** | (no flags) | 1 → 2 → ... → 5 | Complete workflow in single session |

### When to Use Design-First Workflow

Use `--design-only` when:
- **High complexity** (score ≥7) - system recommends automatically
- **High-risk changes** (security, breaking changes, schema changes)
- **Multiple team members** (architect designs, developer implements)
- **Multi-day tasks** (design Day 1, implement Day 2+)
- **Unclear requirements** (need design exploration)

Use `--implement-only` when:
- Task is in `design_approved` state
- Different person implementing than who designed
- Continuing work after design approval

Use default workflow (no flags) when:
- **Simple to medium complexity** (score ≤6)
- **Low risk changes** (bug fixes, minor features)
- **Single developer** handling both design and implementation
- **Same-day tasks** (design and implement in one session)

### Implementation Plan Storage

Plans are saved as Markdown in `.claude/task-plans/{task_id}-implementation-plan.md`:

**Benefits**:
- Human-reviewable (plain text)
- Git-friendly (meaningful diffs)
- Searchable (grep, ripgrep, IDE)
- Editable (manual edits before `--implement-only`)

---

## 3.4 Test Enforcement Loop

**Phase**: 4.5 of /task-work command
**Purpose**: Zero tolerance for test failures. Automatically fix and re-test up to 3 times before blocking.

### Quick Start

Test enforcement happens automatically after Phase 4:

```bash
/task-work TASK-042

# Phase 4: Testing
Tests: 3/5 PASSED ❌
  ✅ test_user_authentication
  ✅ test_password_hashing
  ❌ test_token_generation (KeyError: 'user_id')
  ✅ test_logout
  ❌ test_session_expiry (AssertionError: expected 3600, got 7200)

# Phase 4.5: Test Enforcement Loop
🔄 Attempt 1/3: Analyzing failures...
  - test_token_generation: Missing user_id in token payload
  - test_session_expiry: Default expiry misconfigured

🔧 Applying fixes...
  ✅ Fixed: Added user_id to token payload
  ✅ Fixed: Updated session expiry default to 3600

🧪 Re-running tests...
Tests: 5/5 PASSED ✅

✅ All tests passing. Proceeding to Phase 5...
```

### Enforcement Rules

**Zero Tolerance**:
- 100% of tests must pass
- No compilation errors allowed
- Coverage must meet threshold (≥80% line, ≥75% branch)

**Auto-Fix Strategy**:
1. Analyze test failures and compilation errors
2. Generate fixes based on error messages
3. Apply fixes to codebase
4. Re-run full test suite
5. Repeat up to 3 times

**Blocking Condition**:
- If tests still fail after 3 fix attempts
- Task moves to BLOCKED state
- Human intervention required

### Fix Loop Workflow

```
Phase 4: Testing
     ↓
All Tests Pass?
     ↓ No
Phase 4.5: Attempt 1
     ↓
Analyze Failures
     ↓
Generate Fixes
     ↓
Apply Fixes
     ↓
Re-Run Tests
     ↓
All Tests Pass?
     ↓ No
Attempt 2/3
     ↓
... (repeat)
     ↓
All Tests Pass?
     ↓ No (after 3 attempts)
BLOCKED
     ↓ Yes
Phase 5: Code Review
```

### Example: Compilation Error

```bash
Phase 4: Testing
❌ Compilation Failed

Error: SyntaxError: Unexpected token (line 42)

Phase 4.5: Attempt 1/3
🔧 Fixing compilation error...
  - Missing closing brace on line 42

✅ Compilation PASSED
🧪 Running tests...
Tests: 5/5 PASSED ✅
```

---

## 3.5 Architectural Review

**Phase**: 2.5B of /task-work command
**Purpose**: Evaluate implementation plans against SOLID, DRY, and YAGNI principles before implementation.

### Quick Start

Architectural review happens automatically after planning:

```bash
/task-work TASK-042

# Phase 2.5B: Architectural Review
🔍 Reviewing implementation plan...

Architectural Score: 85/100 (Approved with Recommendations)

Principle Scores:
  SOLID: 90/100 ✅
    ✅ Single Responsibility: Well-defined classes
    ✅ Open/Closed: Extension points provided
    ✅ Liskov Substitution: Not applicable
    ⚠️  Interface Segregation: UserService interface too large (6 methods)
    ✅ Dependency Inversion: Proper dependency injection

  DRY: 85/100 ✅
    ✅ No code duplication detected
    ⚠️  Authentication logic repeated in 2 endpoints (consider middleware)

  YAGNI: 80/100 ✅
    ✅ Minimal feature set
    ⚠️  OAuth2 provider scaffolding not needed for current requirements

Recommendations:
  1. Split UserService into UserAuthService and UserProfileService
  2. Extract authentication logic to middleware
  3. Remove OAuth2 scaffolding (not in requirements)

Status: APPROVED (proceed with recommendations)
```

### Scoring System

**Overall Score Calculation**:
```
overall_score = (solid_score + dry_score + yagni_score) / 3
```

**Score Thresholds**:
- **≥80**: Auto-approved (excellent architecture)
- **60-79**: Approved with recommendations
- **<60**: Rejected (requires redesign)

**SOLID Principles** (0-100 points):
- Single Responsibility Principle (SRP): One reason to change
- Open/Closed Principle (OCP): Open for extension, closed for modification
- Liskov Substitution Principle (LSP): Subtype substitutability
- Interface Segregation Principle (ISP): Small, focused interfaces
- Dependency Inversion Principle (DIP): Depend on abstractions

**DRY - Don't Repeat Yourself** (0-100 points):
- No code duplication
- Shared logic extracted to reusable functions/classes
- Configuration centralized

**YAGNI - You Aren't Gonna Need It** (0-100 points):
- Only implement what's needed now
- No speculative features
- No over-engineering

### Rejection Example

```bash
Phase 2.5B: Architectural Review
❌ Architectural Score: 45/100 (REJECTED)

Principle Scores:
  SOLID: 40/100 ❌
    ❌ Single Responsibility: God class UserManager handles auth, profile, settings
    ❌ Dependency Inversion: Direct instantiation of dependencies

  DRY: 50/100 ⚠️
    ❌ Password hashing duplicated in 4 places

  YAGNI: 45/100 ❌
    ❌ AI recommendation engine not in requirements
    ❌ Multi-factor auth scaffolding not needed

Critical Issues:
  1. UserManager violates SRP (8 responsibilities)
  2. No dependency injection
  3. Out-of-scope features (AI, MFA)

Status: REJECTED

REQUIRED ACTIONS:
  1. Split UserManager into focused services
  2. Add dependency injection
  3. Remove out-of-scope features
  4. Re-run /task-work after redesign
```

---

## 3.6 Human Checkpoints

**Phase**: 2.8 of /task-work command
**Purpose**: Complexity-based routing with interactive plan review for critical decisions.

### Quick Start

Human checkpoints trigger automatically based on complexity:

**Simple Task (1-3)**: Auto-proceed (no checkpoint)
```bash
/task-work TASK-001

Phase 2.7: Complexity: 2/10 (Simple)
Phase 2.8: AUTO_PROCEED (skipping checkpoint)

Proceeding to implementation...
```

**Medium Task (4-6)**: Quick optional checkpoint (10s timeout)
```bash
/task-work TASK-042

Phase 2.8: QUICK_OPTIONAL Checkpoint

Complexity: 5/10 (Medium)
Files: 3 files to modify
Estimated: 4 hours

Press ENTER to review in detail, 'c' to cancel
Auto-approving in 10...9...8...

# User presses ENTER
Escalating to full review...

[Interactive plan review...]
```

**Complex Task (7-10)**: Mandatory checkpoint (no timeout)
```bash
/task-work TASK-050

Phase 2.8: FULL_REQUIRED Checkpoint

═══════════════════════════════════════════════════════
IMPLEMENTATION PLAN CHECKPOINT
═══════════════════════════════════════════════════════

TASK: TASK-050 - Refactor authentication system

COMPLEXITY: 8/10 (Complex)

FILES TO CREATE (5):
  - src/auth/AuthService.ts
  - src/auth/TokenManager.ts
  - src/middleware/authMiddleware.ts
  - tests/auth/AuthService.test.ts
  - tests/auth/TokenManager.test.ts

FILES TO MODIFY (3):
  - src/server.ts (add middleware)
  - src/routes/user.ts (use AuthService)
  - package.json (add jwt library)

PATTERNS:
  - Singleton (AuthService)
  - Factory (TokenManager)
  - Middleware (Express)

NEW DEPENDENCIES:
  - jsonwebtoken (JWT handling)
  - bcrypt (password hashing)

RISKS:
  - Breaking change: API authentication required
  - Security: Token expiry must be configured correctly

ESTIMATED: 12 hours

OPTIONS:
[A] Approve - Proceed to implementation
[M] Modify - Edit plan (Coming soon)
[V] View - Show full plan in pager (Coming soon)
[Q] Question - Ask questions about plan (Coming soon)
[C] Cancel - Cancel task, return to backlog

Your choice (A/M/V/Q/C): A

✅ Plan approved. Proceeding to implementation...
═══════════════════════════════════════════════════════
```

### Checkpoint Modes

| Mode | Trigger | Timeout | Actions |
|------|---------|---------|---------|
| **AUTO_PROCEED** | Complexity 1-3 | None | Automatic approval |
| **QUICK_OPTIONAL** | Complexity 4-6 | 10 seconds | ENTER (escalate), 'c' (cancel), timeout (approve) |
| **FULL_REQUIRED** | Complexity 7-10 | None | A/M/V/Q/C (user must choose) |

### Force Triggers

Certain conditions force FULL_REQUIRED mode regardless of complexity:

**Security Keywords**:
- authentication, authorization, security
- password, encryption, token
- oauth, jwt, crypto

**Breaking Changes**:
- Public API modifications
- Interface changes
- Schema changes

**Flags**:
- `--review` command-line flag
- `hotfix` or `critical` priority

---

## 3.7 Plan Audit

**Phase**: 5.5 of /task-work command
**Purpose**: Compare actual implementation vs planned implementation to detect scope creep.

### Quick Start

Plan audit happens automatically after code review:

```bash
Phase 5.5: Plan Audit
🔍 Comparing implementation to plan...

FILE COUNT:
  Planned: 5 files (3 create, 2 modify)
  Actual: 5 files (3 create, 2 modify)
  ✅ Match

SCOPE:
  ✅ All planned files implemented
  ✅ No unplanned files added
  ✅ No unplanned dependencies

LOC VARIANCE:
  Planned: 450 lines
  Actual: 485 lines (+7.8%)
  ✅ Within acceptable range (±20%)

DURATION VARIANCE:
  Estimated: 4 hours
  Actual: 4.5 hours (+12.5%)
  ✅ Within acceptable range (±30%)

✅ PLAN AUDIT PASSED
No scope creep detected. Proceeding to IN_REVIEW...
```

### Variance Thresholds

**File Count**: 100% match required
- If actual ≠ planned → Requires explanation

**LOC Variance**: ±20% acceptable
- If |actual - planned| / planned > 0.20 → Flag for review

**Duration Variance**: ±30% acceptable
- If |actual - estimated| / estimated > 0.30 → Flag for review

### Scope Creep Detection

```bash
Phase 5.5: Plan Audit
⚠️  SCOPE CREEP DETECTED

FILE COUNT:
  Planned: 3 files
  Actual: 5 files (+2 unplanned files)

UNPLANNED FILES:
  ❌ src/utils/logger.ts (not in plan)
  ❌ src/config/logging.ts (not in plan)

UNPLANNED DEPENDENCIES:
  ❌ winston (logging library)

LOC VARIANCE:
  Planned: 200 lines
  Actual: 385 lines (+92.5%)
  ❌ Exceeds threshold (±20%)

EXPLANATION REQUIRED:
Why were these files and dependencies added?
(Enter explanation or 'skip' to proceed without explanation)

> Added centralized logging for debugging. Required for production monitoring.

✅ Explanation recorded. Proceeding to IN_REVIEW...
```

### Audit Metrics

| Metric | Calculation | Threshold | Action |
|--------|-------------|-----------|--------|
| File Count Match | actual == planned | 100% | Require explanation if mismatch |
| LOC Variance | abs(actual - planned) / planned | ±20% | Flag if exceeded |
| Duration Variance | abs(actual - estimated) / estimated | ±30% | Flag if exceeded |
| Unplanned Files | len(actual_files - planned_files) | 0 | List all unplanned |
| Unplanned Dependencies | len(actual_deps - planned_deps) | 0 | List all unplanned |

---

## 3.8 Iterative Refinement

**Phase**: 6 (separate `/task-refine` command)
**Purpose**: Lightweight improvements for tasks in IN_REVIEW state without full re-work.

### Quick Start

Refine an implementation after initial completion:

```bash
# Task is in IN_REVIEW state
/task-status TASK-042
State: IN_REVIEW
Tests: 100% passing
Coverage: 85%

# Make iterative improvements
/task-refine TASK-042

🔄 Iterative Refinement Mode

What would you like to refine?
1. Code quality (linting, formatting)
2. Test coverage (add missing tests)
3. Documentation (add comments, docstrings)
4. Performance (optimize hot paths)
5. Error handling (improve error messages)

Your choice (1-5): 2

Analyzing coverage gaps...

UNCOVERED CODE:
  - src/auth/AuthService.ts:45-52 (error handling branch)
  - src/auth/AuthService.ts:78-81 (token refresh logic)

Adding tests...
  ✅ test_auth_service_error_handling
  ✅ test_auth_service_token_refresh

🧪 Running tests...
Tests: 17/17 PASSED ✅
Coverage: 92% (+7%)

✅ Refinement complete. Task remains in IN_REVIEW.
```

### When to Use /task-refine

**Use /task-refine for**:
- Minor code improvements
- Increasing test coverage
- Adding documentation
- Linting fixes
- Renaming/formatting
- Performance optimizations

**Don't use /task-refine for**:
- New features (use `/task-create` + `/task-work`)
- Architecture changes (use `/task-work` with new plan)
- Major refactoring (create new task)
- Bug fixes (create new task)

### Refinement Categories

| Category | Examples | Re-Test Required |
|----------|----------|-----------------|
| **Code Quality** | Linting, formatting, naming | No |
| **Test Coverage** | Add missing tests | Yes |
| **Documentation** | Comments, docstrings, README | No |
| **Performance** | Optimize algorithms, caching | Yes |
| **Error Handling** | Better error messages, logging | Yes |

---

## 3.9 MCP Tool Discovery

**Phase**: 2 (during implementation planning)
**Purpose**: Automatically detect available MCP tools and enhance plans with tool-specific capabilities.

### Quick Start

MCP tool discovery happens automatically if tools are configured:

```bash
/task-work TASK-042

Phase 2: Implementation Planning
📚 Detecting MCP tools...

AVAILABLE TOOLS:
  ✅ context7 (library documentation)
  ✅ design-patterns (pattern recommendations)

TOOL USAGE IN PLAN:
  - context7: Fetch fastapi documentation for dependency injection
  - design-patterns: Suggest patterns for authentication service

Generating plan with MCP enhancements...
```

### Supported MCP Tools

**context7** (Library Documentation):
- Retrieves up-to-date library documentation
- Token budget: 2000-6000 (phase-dependent)
- Use during implementation for API details

**design-patterns** (Pattern Recommendations):
- Suggests appropriate design patterns
- Token budget: ~5000 for 5 results
- Use during planning for architecture guidance

### Context7 Integration Example

```bash
Phase 3: Implementation
📚 Fetching latest documentation for fastapi...

context7: get-library-docs(
  library="/tiangolo/fastapi",
  topic="dependency-injection",
  tokens=5000
)

✅ Retrieved fastapi documentation (dependency injection)

Implementing with latest patterns...
```

**Token Budget Guidelines**:
- Planning (Phase 2): 3000-4000 tokens
- Implementation (Phase 3): 5000 tokens (default)
- Testing (Phase 4): 2000-3000 tokens

---

## 3.10 Design System Detection (Coming Soon)

> **Status: Under Development**
>
> Design system detection and design-to-code workflows are under active development.
> See `tasks/backlog/design-url-integration/` for implementation progress.

**Planned Features**:
- Automatic detection of Figma/Zeplin URLs in task descriptions
- Design-to-code workflow suggestions
- Visual regression testing integration
- Zero scope creep enforcement

**Planned Supported Design Systems**:
- Figma → TypeScript React + Tailwind (`/figma-to-react`)
- Zeplin → XAML + C# + platform tests (`/zeplin-to-maui`)

### Design Workflow Quality Gates (Planned)

When design-to-code workflows are available, additional gates will apply:

| Gate | Threshold | Enforcement |
|------|-----------|-------------|
| Visual Fidelity | >95% similarity | Required |
| Constraint Violations | 0 | Required (zero tolerance) |
| Compilation | 100% | Required |

---

# Part 4: PRACTICAL USAGE

## 4.1 Complete Workflow Examples

### Example 1: Simple Bug Fix

```bash
# Create task (natural language description)
/task-create "There's a null pointer exception in UserService that crashes the app" priority:critical

# Work on task (auto-proceeds, no checkpoint)
/task-work TASK-001

# Output:
# Complexity: 2/10 (Simple)
# Review Mode: AUTO_PROCEED
# Files: 1 file modified
# Tests: 5/5 PASSED ✅
# Coverage: 87%
# State: BACKLOG → IN_REVIEW

# Complete task
/task-complete TASK-001
```

### Example 2: Medium Complexity Feature

```bash
# Create task (natural language description)
/task-create "We need to add a user profile page with avatar upload capability" priority:medium

# Work on task (quick optional checkpoint)
/task-work TASK-002

# Output:
# Complexity: 5/10 (Medium)
# Review Mode: QUICK_OPTIONAL
# [10-second timeout, auto-approved]
# Files: 4 files created, 2 modified
# Tests: 12/12 PASSED ✅
# Coverage: 91%
# State: BACKLOG → IN_REVIEW

# Complete task
/task-complete TASK-002
```

### Example 3: Complex Refactoring (Design-First)

```bash
# Create task (natural language description)
/task-create "Refactor the entire authentication system to support OAuth2 providers" priority:high

# Design phase only
/task-work TASK-003 --design-only

# Output:
# Complexity: 8/10 (Complex)
# Review Mode: FULL_REQUIRED
# [Human reviews plan, approves]
# State: BACKLOG → DESIGN_APPROVED

# [Next day or different person]
# Implementation phase
/task-work TASK-003 --implement-only

# Output:
# Loading approved design...
# Files: 8 files created, 5 modified
# Tests: 25/25 PASSED ✅
# Coverage: 89%
# State: DESIGN_APPROVED → IN_REVIEW

# Refine to improve coverage
/task-refine TASK-003

# Output:
# Coverage: 93% (+4%)
# State: Remains IN_REVIEW

# Complete task
/task-complete TASK-003
```

### Example 4: Test Failures with Auto-Fix

```bash
/task-work TASK-004

# Phase 4: Testing
# Tests: 3/5 PASSED ❌

# Phase 4.5: Test Enforcement Loop
# Attempt 1/3: Analyzing failures...
# Applying fixes...
# Re-running tests...
# Tests: 5/5 PASSED ✅

# State: BACKLOG → IN_REVIEW
```

### Example 5: Blocked Task (Fix Exhausted)

```bash
/task-work TASK-005

# Phase 4: Testing
# Tests: 2/5 PASSED ❌

# Phase 4.5: Test Enforcement Loop
# Attempt 1/3: Fixes applied, re-testing...
# Tests: 3/5 PASSED ❌
# Attempt 2/3: Fixes applied, re-testing...
# Tests: 3/5 PASSED ❌
# Attempt 3/3: Fixes applied, re-testing...
# Tests: 4/5 PASSED ❌

# ❌ All fix attempts exhausted
# State: BACKLOG → BLOCKED
# Reason: Tests failing after 3 fix attempts

# Human investigates, fixes manually, then:
/task-unblock TASK-005
/task-work TASK-005
```

---

## 4.2 Decision Trees & Flowcharts

### Decision Tree: Which Mode to Use?

```
Start
  ↓
Is task simple (1-3 files, familiar patterns)?
  ↓ Yes
Use standard mode: /task-work TASK-XXX
  ↓ No
Is task complex (7+ complexity, high risk)?
  ↓ Yes
Use design-first: /task-work TASK-XXX --design-only
  ↓ No
Is task already designed?
  ↓ Yes
Use implement-only: /task-work TASK-XXX --implement-only
  ↓ No
Is it complex business logic?
  ↓ Yes
Use TDD mode: /task-work TASK-XXX --mode=tdd
  ↓ No
Use standard mode: /task-work TASK-XXX
```

### Complete Workflow Flowchart

```
BACKLOG
  ↓
/task-work TASK-XXX
  ↓
Phase 1: Load Task Context
  ↓
Phase 2: Implementation Planning
  ↓
Phase 2.5A: Pattern Suggestion
  ↓
Phase 2.5B: Architectural Review
  ↓
Score ≥60?
  ↓ No → REJECTED (redesign required)
  ↓ Yes
Phase 2.7: Complexity Evaluation
  ↓
Phase 2.8: Human Checkpoint
  ↓
Complexity 1-3: AUTO_PROCEED
Complexity 4-6: QUICK_OPTIONAL (10s)
Complexity 7-10: FULL_REQUIRED
  ↓
Approved?
  ↓ No → BACKLOG (cancelled)
  ↓ Yes
Phase 3: Implementation
  ↓
Phase 4: Testing
  ↓
Compilation Pass?
  ↓ No → Phase 4.5: Fix Loop (3 attempts) → Pass? → No → BLOCKED
  ↓ Yes
Tests Pass?
  ↓ No → Phase 4.5: Fix Loop (3 attempts) → Pass? → No → BLOCKED
  ↓ Yes
Coverage ≥80%?
  ↓ No → Request more tests → Retry
  ↓ Yes
Phase 5: Code Review
  ↓
Quality Pass?
  ↓ No → Human review required
  ↓ Yes
Phase 5.5: Plan Audit
  ↓
Scope creep detected?
  ↓ Yes → Require explanation → Approved?
  ↓ No/Approved
IN_REVIEW
  ↓
/task-refine TASK-XXX (optional)
  ↓
/task-complete TASK-XXX
  ↓
COMPLETED
```

---

## 4.3 Troubleshooting & FAQ

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Tests fail repeatedly | Test logic incorrect | Manual investigation required after 3 fix attempts |
| Complexity score too low | Implementation plan lacks detail | Re-run Phase 2 with more thorough planning |
| Complexity score too high | Over-engineered solution | Simplify approach, remove unnecessary patterns |
| Architectural review rejected | Design violates SOLID/DRY/YAGNI | Redesign following recommendations |
| Coverage too low | Missing test cases | Add tests for uncovered code paths |
| Plan audit flags variance | Unplanned files/dependencies added | Provide explanation or remove unplanned additions |
| Task stuck in BLOCKED | Quality gates failed | Fix issues manually, then `/task-unblock` |

### FAQ

**Q: Can I skip the human checkpoint for complex tasks?**
A: No. Tasks with complexity ≥7 require mandatory human approval (FULL_REQUIRED mode). This is a safety mechanism to prevent large, risky changes without review.

**Q: Can I modify the implementation plan during checkpoint?**
A: Currently limited (MVP). Full modification interface coming in TASK-003B-3. For now, cancel task and re-create with adjusted scope.

**Q: What happens if I cancel during checkpoint?**
A: Task returns to BACKLOG state. No code is generated. You can re-run `/task-work` later with modified task description.

**Q: Can I use --design-only and --implement-only together?**
A: No. These flags are mutually exclusive. Use `--design-only` first, then `--implement-only` later.

**Q: How do I unblock a task?**
A: Fix the issues manually (tests, compilation, etc.), then run `/task-unblock TASK-XXX` to move from BLOCKED to IN_PROGRESS. Re-run `/task-work TASK-XXX` to complete.

**Q: Can I skip test enforcement?**
A: No. Test enforcement is mandatory. If tests fail after 3 fix attempts, task moves to BLOCKED and requires manual intervention.

**Q: What's the difference between /task-work and /task-refine?**
A: `/task-work` is the full workflow (planning through code review). `/task-refine` is lightweight improvements on already-completed tasks (IN_REVIEW state). Use `/task-refine` for minor tweaks without full re-work.

**Q: Can I configure complexity thresholds?**
A: Yes. Edit `.claude/settings.json` to adjust `auto_split_threshold`, `auto_proceed_max`, and `quick_review_max`.

**Q: Does architectural review slow down simple tasks?**
A: No. Simple tasks (complexity 1-3) auto-proceed without checkpoint, so review adds minimal overhead (~5 seconds).

**Q: Can I use GuardKit without MCP tools?**
A: Yes. MCP tools are optional enhancements. GuardKit works perfectly without them.

**Q: What's the difference between GuardKit and RequireKit?**
A: GuardKit is lightweight task workflow with quality gates. RequireKit adds formal requirements management (EARS notation, BDD scenarios, epic/feature hierarchy, PM tool integration). See: https://github.com/requirekit/require-kit

---

## Need Formal Requirements Management?

GuardKit focuses on lightweight task workflow with quality gates. For formal requirements management, use **RequireKit** which adds:

- EARS notation (structured requirements)
- BDD scenarios (Gherkin)
- Epic/Feature hierarchy
- PM tool integration (Jira, Linear, Azure DevOps, GitHub)
- Requirements traceability matrices

> **Need Formal Requirements?**
> RequireKit adds EARS notation, BDD scenarios, and epic/feature hierarchy.
> See: https://github.com/requirekit/require-kit

---

**Version**: 2.0.0 | **License**: MIT | **Repository**: https://github.com/guardkit/guardkit
