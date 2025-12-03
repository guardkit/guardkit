# EPIC-001 Solo Developer Guide (Conductor App + Claude Code)

**Date**: 2025-11-01
**Epic**: EPIC-001 - Template Creation Automation
**Developer**: Solo developer using Conductor app with Claude Code integration
**Strategy**: Flexible worktree switching with `/task-work` command

---

## Overview

This guide is for implementing EPIC-001 as a **solo developer** using:
- **Conductor app** (not CLI) for worktree management
- **Claude Code** integration for AI-assisted implementation
- **`/task-work`** command for automated task implementation

**Timeline**: 8-10 weeks as solo developer (vs. 12 weeks pure sequential)
- Flexibility to work on multiple tasks in parallel worktrees
- Switch between tasks as needed (no blocking)
- `/task-work` handles implementation, testing, and review automatically

---

## How This Works: Conductor App + /task-work

### Conductor App Workflow

1. **Create worktree** in Conductor app for a task
2. **Open worktree** in Claude Code (automatic via Conductor integration)
3. **Run `/task-work TASK-XXX`** to implement the task
4. **Complete task** (tests pass, code reviewed)
5. **Switch to next worktree** in Conductor app
6. **Repeat**

### Why Use Multiple Worktrees (Solo Dev)?

Even as a solo developer, multiple worktrees let you:
- **Avoid blocking**: If TASK-038A is blocked, switch to TASK-037
- **Context switching**: Different worktrees = different contexts (no git stash needed)
- **Parallel experiments**: Try different approaches in different worktrees
- **Review later**: Leave a task in IN_PROGRESS, work on another, come back

### The Wave Structure

Tasks are organized into **6 waves** based on dependencies:
- **Wave 0**: No dependencies - can start ANY of these 6 tasks immediately
- **Wave 1**: Depends on Wave 0 only - start as soon as relevant Wave 0 tasks complete
- **Wave 2**: Depends on Wave 1 - etc.

**You choose** which task to work on based on:
1. What's unblocked (dependencies met)
2. What you're interested in working on now
3. What fits your available time

---

## Task Dependency Map

### Wave 0: Foundation (6 Tasks - NO Dependencies)

**Start with ANY of these - all are unblocked:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-037A: Universal Language Mapping (3h, Complexity 3/10)     │
│   • Create language database for 50+ languages                  │
│   • Extension to language mapping                               │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-lang-mapping                              │
│   • Command: /task-work TASK-037A                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-037: Technology Stack Detection (6h, Complexity 5/10)      │
│   • Detect primary language, frameworks, build tools            │
│   • File pattern analysis                                       │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-stack-detect                              │
│   • Command: /task-work TASK-037                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-048B: Local Agent Scanner (4h, Complexity 4/10)            │
│   • Scan installer/global/agents/ directory                     │
│   • Discover 15+ existing guardkit agents                     │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-local-agents                              │
│   • Command: /task-work TASK-048B                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-048: Subagents.cc Scraper (6h, Complexity 6/10)            │
│   • Web scraper for subagents.cc marketplace                    │
│   • Caching with 15-minute TTL                                  │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-subagents-scraper                         │
│   • Command: /task-work TASK-048                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-049: GitHub Agent Parsers (8h, Complexity 7/10)            │
│   • Parse wshobson/agents and VoltAgent repositories            │
│   • Agent metadata extraction                                   │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-github-agents                             │
│   • Command: /task-work TASK-049                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-053: Template-init QA Flow (6h, Complexity 5/10)           │
│   • 9-section Q&A flow structure                                │
│   • Session persistence (save/resume)                           │
│   • No dependencies - START IMMEDIATELY                          │
│   • Worktree: epic001-qa-flow                                   │
│   • Command: /task-work TASK-053                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 25 hours across 6 tasks
**Suggested Order**: TASK-037A → TASK-037 → TASK-048B (builds foundation)

---

### Wave 1: First Tier (7 Tasks)

**Start when dependencies complete:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-038A: Generic Structure Analyzer (6h, Complexity 6/10)     │
│   REQUIRES: TASK-037A ✓                                          │
│   • Universal layer detection from folder structure             │
│   • Pattern inference (MVVM, Clean Arch, etc.)                  │
│   • Worktree: epic001-struct-analyzer                           │
│   • Command: /task-work TASK-038A                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-038: Architecture Pattern Analyzer (7h, Complexity 6/10)   │
│   REQUIRES: TASK-037 ✓                                           │
│   • Detect MVVM, Clean Architecture, Repository patterns        │
│   • Confidence scoring                                          │
│   • Worktree: epic001-arch-analyzer                             │
│   • Command: /task-work TASK-038                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-045A: Language Syntax Database (4h, Complexity 4/10)       │
│   REQUIRES: TASK-037A ✓                                          │
│   • Syntax database for 50+ languages                           │
│   • Comment styles, placeholder formats                         │
│   • Worktree: epic001-syntax-db                                 │
│   • Command: /task-work TASK-045A                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-048C: Configurable Agent Sources (3h, Complexity 3/10)     │
│   REQUIRES: TASK-048B ✓                                          │
│   • JSON-based agent source configuration                       │
│   • Priority ordering and bonus scoring                         │
│   • Worktree: epic001-agent-sources                             │
│   • Command: /task-work TASK-048C                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-054: Basic Info Section (4h, Complexity 4/10)              │
│   REQUIRES: TASK-053 ✓                                           │
│   • Project name, description, author Q&A                       │
│   • Input validation                                            │
│   • Worktree: epic001-qa-basic                                  │
│   • Command: /task-work TASK-054                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-055: Technology Section (5h, Complexity 5/10)              │
│   REQUIRES: TASK-053 ✓                                           │
│   • Language, framework, testing framework selection            │
│   • Conditional branching                                       │
│   • Worktree: epic001-qa-tech                                   │
│   • Command: /task-work TASK-055                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-058: Quality Section (4h, Complexity 4/10)                 │
│   REQUIRES: TASK-053 ✓                                           │
│   • Linting, testing, coverage preferences                      │
│   • Quality gate configuration                                  │
│   • Worktree: epic001-qa-quality                                │
│   • Command: /task-work TASK-058                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 33 hours across 7 tasks

---

### Wave 2: Second Tier (7 Tasks)

**Multiple dependencies - start when all required tasks complete:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-039A: Generic Text Extraction (5h, Complexity 5/10)        │
│   REQUIRES: TASK-037A ✓, TASK-038A ✓                            │
│   • Text-based code pattern extraction (regex)                  │
│   • Works for ANY language                                      │
│   • Worktree: epic001-text-extract                              │
│   • Command: /task-work TASK-039A                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-039: Code Pattern Extraction (8h, Complexity 7/10)         │
│   REQUIRES: TASK-037 ✓, TASK-038 ✓                              │
│   • Extract patterns from React, .NET, Python code              │
│   • Multi-language pattern extraction                           │
│   • Worktree: epic001-pattern-extract                           │
│   • Command: /task-work TASK-039                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-040: Naming Convention Inference (5h, Complexity 5/10)     │
│   REQUIRES: TASK-038 ✓                                           │
│   • Infer naming patterns from actual files                     │
│   • PascalCase, snake_case, camelCase detection                 │
│   • Worktree: epic001-naming                                    │
│   • Command: /task-work TASK-040                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-041: Layer Structure Detection (4h, Complexity 4/10)       │
│   REQUIRES: TASK-038 ✓                                           │
│   • Map directories to architectural layers                     │
│   • Domain, Application, Infrastructure detection               │
│   • Worktree: epic001-layers                                    │
│   • Command: /task-work TASK-041                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-042: Manifest Generator (5h, Complexity 4/10)              │
│   REQUIRES: TASK-037 ✓, TASK-038 ✓                              │
│   • Generate manifest.json from detected patterns               │
│   • Template metadata                                           │
│   • Worktree: epic001-manifest                                  │
│   • Command: /task-work TASK-042                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-044: CLAUDE.md Generator (6h, Complexity 5/10)             │
│   REQUIRES: TASK-037 ✓, TASK-038 ✓                              │
│   • Generate architectural guidance document                    │
│   • Stack-specific patterns                                     │
│   • Worktree: epic001-claude-md                                 │
│   • Command: /task-work TASK-044                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-056 + TASK-057: Architecture + Testing Sections (9h total) │
│   REQUIRES: TASK-053 ✓, TASK-055 ✓                              │
│   • Architecture pattern selection Q&A                          │
│   • Testing strategy Q&A                                        │
│   • Worktree: epic001-qa-arch-test                              │
│   • Command: /task-work TASK-056 then /task-work TASK-057       │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 42 hours across 7 tasks

---

### Wave 3: Integration Layer (4 Tasks)

**Complex integration tasks:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-043 + TASK-062: Settings + Versioning (8h total)           │
│   REQUIRES: TASK-040 ✓, TASK-041 ✓ (for 043), TASK-042 ✓ (062)  │
│   • Generate settings.json with naming conventions              │
│   • Semantic versioning for templates                           │
│   • Worktree: epic001-settings-version                          │
│   • Command: /task-work TASK-043 then /task-work TASK-062       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-045: Code Template Generator (8h, Complexity 7/10)         │
│   REQUIRES: TASK-039 ✓                                           │
│   • Generate .template files with placeholders                  │
│   • Pattern-based code generation                               │
│   • Worktree: epic001-template-gen                              │
│   • Command: /task-work TASK-045                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-050: Agent Matching Algorithm (7h, Complexity 6/10)        │
│   REQUIRES: TASK-037 ✓, TASK-038 ✓, TASK-048 ✓,                 │
│             TASK-048B ✓, TASK-048C ✓, TASK-049 ✓                │
│   • Score agents based on tech/pattern/tools match              │
│   • Source priority bonus (+20 for local)                       │
│   • Worktree: epic001-agent-match                               │
│   • Command: /task-work TASK-050                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-046: Template Validation (6h, Complexity 5/10)             │
│   REQUIRES: TASK-042 ✓, TASK-043 ✓, TASK-044 ✓, TASK-045 ✓      │
│   • Validate manifest structure, templates, placeholders        │
│   • NOTE: Must wait for TASK-043, TASK-045 from this wave       │
│   • Worktree: epic001-validation                                │
│   • Command: /task-work TASK-046                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 29 hours across 4 tasks (some sequential within wave)

---

### Wave 4: Command Orchestration (3 Tasks)

**High-level orchestration:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-047: /template-create Orchestrator (6h, Complexity 6/10)   │
│   REQUIRES: TASK-037 ✓, TASK-038 ✓, TASK-039 ✓, TASK-042 ✓,     │
│             TASK-043 ✓, TASK-045 ✓, TASK-046 ✓                  │
│   • Integrate all 8 phases into cohesive command                │
│   • End-to-end template creation                                │
│   • Worktree: epic001-template-create                           │
│   • Command: /task-work TASK-047                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-051 + TASK-052: Agent UI + Download (9h total)             │
│   REQUIRES: TASK-050 ✓ (for both)                               │
│   • Interactive CLI for agent selection (grouped by source)     │
│   • Download and save agents to template                        │
│   • Worktree: epic001-agent-ui                                  │
│   • Command: /task-work TASK-051 then /task-work TASK-052       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-059: Agent Discovery Integration (5h, Complexity 5/10)     │
│   REQUIRES: TASK-053 ✓, TASK-050 ✓, TASK-051 ✓                  │
│   • Integrate agent discovery into template-init Q&A            │
│   • Optional agent selection step                               │
│   • Worktree: epic001-agent-integrate                           │
│   • Command: /task-work TASK-059                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 20 hours across 3 tasks

---

### Wave 5: Template-init Completion (1 Task)

**Massive integration task:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-060: /template-init Orchestrator (6h, Complexity 6/10)     │
│   REQUIRES: TASK-042 ✓, TASK-043 ✓, TASK-044 ✓, TASK-045 ✓,     │
│             TASK-046 ✓, TASK-053 ✓, TASK-054 ✓, TASK-055 ✓,     │
│             TASK-056 ✓, TASK-057 ✓, TASK-058 ✓, TASK-059 ✓      │
│   • Integrate all Q&A sections                                  │
│   • Generate template from answers                              │
│   • Worktree: epic001-template-init                             │
│   • Command: /task-work TASK-060                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 6 hours

---

### Wave 6: Distribution & Documentation (7 Tasks)

**Final polish:**

```
┌─────────────────────────────────────────────────────────────────┐
│ TASK-061 → TASK-064: Packaging → Helpers (9h sequential)        │
│   REQUIRES: TASK-047 ✓, TASK-060 ✓ (for 061), TASK-042 ✓ (062), │
│             TASK-062 ✓ (063), TASK-061 ✓ (064)                  │
│   • Template packaging (.tar.gz)                                │
│   • Versioning, update/merge, distribution helpers              │
│   • Worktree: epic001-distribution                              │
│   • Commands: /task-work TASK-061, 062, 063, 064 in sequence    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-065: Integration Tests (10h, Complexity 7/10)              │
│   REQUIRES: TASK-047 ✓, TASK-060 ✓                              │
│   • End-to-end tests for both commands                          │
│   • Multi-language template validation                          │
│   • Worktree: epic001-tests                                     │
│   • Command: /task-work TASK-065                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-066: User Documentation (8h, Complexity 5/10)              │
│   REQUIRES: TASK-047 ✓, TASK-060 ✓, TASK-065 ✓                  │
│   • User guides for both commands                               │
│   • Examples and tutorials                                      │
│   • Worktree: epic001-docs                                      │
│   • Command: /task-work TASK-066                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TASK-067: Example Templates (10h, Complexity 6/10)              │
│   REQUIRES: TASK-047 ✓                                           │
│   • Create 3+ example templates (Go, Rust, Ruby)                │
│   • Validation of template quality                              │
│   • Worktree: epic001-examples                                  │
│   • Command: /task-work TASK-067                                │
└─────────────────────────────────────────────────────────────────┘
```

**Total**: 37 hours across 7 tasks

---

## Solo Developer Strategy

### Recommended Approach: Wave-Based Progression

**Principle**: Complete all tasks in a wave before moving to the next wave.

**Why?**
- Ensures dependencies are always met
- Clear progress markers (wave completion)
- No blocked tasks when starting next wave

### Flexible Worktree Switching

**Even as solo dev, keep 2-3 worktrees active at once:**

**Example Week 1:**
```
epic001-lang-mapping    → TASK-037A (working on this now)
epic001-stack-detect    → TASK-037 (ready to switch if blocked)
epic001-local-agents    → TASK-048B (alternative if both blocked)
```

**Benefits:**
- If blocked on TASK-037A, immediately switch to TASK-037
- No context loss (different worktrees = different git branches)
- Can experiment in one worktree while stable in another

### Using /task-work Command

For each task:

```
1. Open worktree in Conductor app
2. Claude Code opens automatically
3. Run: /task-work TASK-XXX
4. Claude Code implements:
   - Phase 1: Requirements Analysis
   - Phase 2: Implementation Planning
   - Phase 2.5: Architectural Review (SOLID/DRY/YAGNI)
   - Phase 2.7: Complexity Evaluation
   - Phase 2.8: Human Checkpoint (if complexity ≥7)
   - Phase 3: Implementation
   - Phase 4: Testing (compilation + coverage)
   - Phase 4.5: Test Enforcement (auto-fix up to 3 attempts)
   - Phase 5: Code Review
   - Phase 5.5: Plan Audit (scope creep detection)
5. Task moves to COMPLETED automatically
6. Switch to next worktree in Conductor app
```

**Time Saved**: `/task-work` handles implementation, testing, review automatically
**Your Role**: Approve checkpoints (Phase 2.8), resolve blocks, guide direction

---

## Estimated Timeline (Solo Developer)

### Conservative: 10-12 Weeks

**Standard pace** (18-20 hours/week):
```
Weeks 1-2:   Wave 0 (25h) + Wave 1 start
Weeks 3-4:   Wave 1 (33h) + Wave 2 start
Weeks 5-6:   Wave 2 (42h) + Wave 3 start
Weeks 7-8:   Wave 3 (29h) + Wave 4 (20h)
Weeks 9-10:  Wave 5 (6h) + Wave 6 (37h)
Weeks 11-12: Wave 6 completion + polish
```

### Aggressive: 8-9 Weeks

**Intensive pace** (25-30 hours/week):
```
Weeks 1-2:   Wave 0 (25h) + Wave 1 (33h) complete
Weeks 3-4:   Wave 2 (42h) + Wave 3 start (29h)
Weeks 5-6:   Wave 3 complete + Wave 4 (20h) + Wave 5 (6h)
Weeks 7-8:   Wave 6 (37h) + documentation
Week 9:      Final polish + testing
```

### Using Conductor App Flexibility

**Key advantage**: Switch tasks without losing context
- Stuck on TASK-039? Switch to TASK-040 in Conductor app
- Both worktrees stay active with different states
- Return to TASK-039 when unblocked

**Time saved**: ~15-20% vs. pure sequential (no blocking time)

---

## Task Selection Strategy

### Option 1: Depth-First (Complete one path)

```
TASK-037A → TASK-038A → TASK-039A
          → TASK-045A → TASK-045
```

**Benefit**: Builds one complete feature stack
**Drawback**: Other waves blocked longer

### Option 2: Breadth-First (Complete wave before next)

```
Wave 0: Complete ALL 6 tasks before starting Wave 1
Wave 1: Complete ALL 7 tasks before starting Wave 2
etc.
```

**Benefit**: Clear progress markers, no dependencies blocked
**Drawback**: Requires more context switching

### Option 3: Interest-Driven (Work on what excites you)

```
Week 1: TASK-037A, TASK-048B (both quick, interesting)
Week 2: TASK-037, TASK-053 (different domains)
etc.
```

**Benefit**: Higher motivation, better quality
**Drawback**: Must track dependencies manually

**Recommended**: **Option 2 (Breadth-First)** for solo dev
- Ensures dependencies always met
- Clear milestones for tracking progress
- Natural testing points at wave boundaries

---

## Using Conductor App (Not CLI)

### Creating Worktrees in Conductor App

1. **Open Conductor app**
2. **Click "New Worktree"** button
3. **Enter worktree name**: `epic001-lang-mapping`
4. **Enter branch name** (optional): `task/037a-universal-language-mapping`
5. **Click Create**
6. **Worktree appears** in Conductor sidebar
7. **Click worktree** → Opens in Claude Code automatically

### Switching Between Worktrees

1. **Click different worktree** in Conductor sidebar
2. **Claude Code switches** to that worktree automatically
3. **All state preserved** via symlinks (guardkit's Conductor integration)
4. **Run `/task-work TASK-XXX`** in new context

### Completing a Task

1. **Task completes** (tests pass, review done)
2. **Commit in worktree**:
   ```
   git commit -m "feat(TASK-037A): Universal language mapping"
   ```
3. **In Conductor app**: Mark worktree as "Complete" (optional)
4. **Switch to next worktree**

---

## Progress Tracking

### Checklist Format

Use this checklist as you progress:

#### Wave 0: Foundation ✅
- [ ] TASK-037A: Universal Language Mapping (3h)
- [ ] TASK-037: Technology Stack Detection (6h)
- [ ] TASK-048B: Local Agent Scanner (4h)
- [ ] TASK-048: Subagents.cc Scraper (6h)
- [ ] TASK-049: GitHub Agent Parsers (8h)
- [ ] TASK-053: Template-init QA Flow (6h)

**Exit Criteria**:
- [ ] 50+ languages mapped
- [ ] Stack detection working for test projects
- [ ] 15+ local agents discovered
- [ ] External sources integrated
- [ ] Q&A flow structure ready

#### Wave 1: First Tier ✅
- [ ] TASK-038A: Generic Structure Analyzer (6h)
- [ ] TASK-038: Architecture Pattern Analyzer (7h)
- [ ] TASK-045A: Language Syntax Database (4h)
- [ ] TASK-048C: Configurable Agent Sources (3h)
- [ ] TASK-054: Basic Info Section (4h)
- [ ] TASK-055: Technology Section (5h)
- [ ] TASK-058: Quality Section (4h)

**Exit Criteria**:
- [ ] Structure analysis working
- [ ] Patterns detected correctly
- [ ] Syntax DB complete
- [ ] Agent sources configurable

#### Wave 2: Second Tier ✅
- [ ] TASK-039A: Generic Text Extraction (5h)
- [ ] TASK-039: Code Pattern Extraction (8h)
- [ ] TASK-040: Naming Convention Inference (5h)
- [ ] TASK-041: Layer Structure Detection (4h)
- [ ] TASK-042: Manifest Generator (5h)
- [ ] TASK-044: CLAUDE.md Generator (6h)
- [ ] TASK-056: Architecture Section (5h)
- [ ] TASK-057: Testing Section (4h)

**Exit Criteria**:
- [ ] Pattern extraction working for 50+ languages
- [ ] Naming conventions inferred
- [ ] Generators producing valid output

#### Wave 3: Integration ✅
- [ ] TASK-043: Settings Generator (4h)
- [ ] TASK-062: Template Versioning (4h)
- [ ] TASK-045: Code Template Generator (8h)
- [ ] TASK-050: Agent Matching Algorithm (7h)
- [ ] TASK-046: Template Validation (6h)

**Exit Criteria**:
- [ ] Template generation end-to-end working
- [ ] Agent matching with bonuses
- [ ] Validation catching errors

#### Wave 4: Commands ✅
- [ ] TASK-047: /template-create Orchestrator (6h)
- [ ] TASK-051: Agent Selection UI (5h)
- [ ] TASK-052: Agent Download Integration (4h)
- [ ] TASK-059: Agent Discovery Integration (5h)

**Exit Criteria**:
- [ ] `/template-create` working end-to-end
- [ ] Agent UI functional

#### Wave 5: Template-init ✅
- [ ] TASK-060: /template-init Orchestrator (6h)

**Exit Criteria**:
- [ ] `/template-init` working end-to-end

#### Wave 6: Polish ✅
- [ ] TASK-061: Template Packaging (5h)
- [ ] TASK-062: Template Versioning (4h - may be done in Wave 3)
- [ ] TASK-063: Template Update/Merge (6h)
- [ ] TASK-064: Distribution Helpers (4h)
- [ ] TASK-065: Integration Tests (10h)
- [ ] TASK-066: User Documentation (8h)
- [ ] TASK-067: Example Templates (10h)

**Exit Criteria**:
- [ ] All tests passing
- [ ] Documentation complete
- [ ] 3+ example templates

---

## Tips for Solo Development with Conductor

### 1. Keep Multiple Worktrees Active

Even if working on one task, have 2-3 worktrees ready:
- **Primary**: Current task you're implementing
- **Backup**: Alternative task if blocked
- **Review**: Completed task pending final review

### 2. Use /task-work for Everything

Don't manually implement - use `/task-work`:
- Handles all phases automatically
- Enforces quality gates
- Consistent implementation patterns
- Saves 40-50% time (vs. manual implementation)

### 3. Complete Waves, Not Individual Tasks

**Don't**:
- Jump around randomly between waves
- Start Wave 3 before Wave 2 complete

**Do**:
- Complete all Wave 0 before any Wave 1
- Clear milestone at each wave boundary
- Test integration at wave boundaries

### 4. Leverage Conductor State Sync

GuardKit's Conductor integration ensures:
- All worktrees share same state (symlinks)
- No manual syncing needed
- Task completion in one worktree visible everywhere

### 5. Take Breaks Between Waves

After completing a wave:
1. Run integration tests
2. Review all completed tasks
3. Take a break (day or two)
4. Start next wave fresh

**Prevents**: Burnout, context overload
**Improves**: Code quality, creativity

---

## Success Metrics

### Timeline Goals
- [ ] Complete all 37 tasks
- [ ] Stay within 8-12 week timeline
- [ ] No blocked time (use worktree switching)

### Quality Gates
- [ ] All integration tests passing
- [ ] Both commands working end-to-end
- [ ] Templates generated successfully for 3+ languages
- [ ] Documentation complete

### /task-work Effectiveness
- [ ] >90% tasks complete via `/task-work` (not manual)
- [ ] <3 checkpoint rejections per task (Phase 2.8)
- [ ] 100% test pass rate (Phase 4.5 auto-fix working)

---

## Quick Reference: Conductor App Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Open Conductor App                                        │
│    → See list of worktrees in sidebar                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Click "New Worktree"                                      │
│    → Enter name: epic001-lang-mapping                        │
│    → Click Create                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Worktree Appears in Sidebar                               │
│    → Click worktree                                          │
│    → Claude Code opens automatically                         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. In Claude Code                                            │
│    → Run: /task-work TASK-037A                              │
│    → Claude implements entire task                           │
│    → Approve checkpoints when prompted                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Task Completes                                            │
│    → Commit: git commit -m "feat(TASK-037A): ..."          │
│    → Back to Conductor app                                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Click Next Worktree                                       │
│    → Claude Code switches automatically                      │
│    → Run: /task-work TASK-XXX                               │
│    → Repeat                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Conclusion

**Total Tasks**: 37
**Total Hours**: 220
**Timeline**: 8-12 weeks (solo developer)
**Method**: Conductor app + Claude Code + /task-work
**Strategy**: Wave-based progression with flexible worktree switching

**Key Advantages**:
- `/task-work` automates 90% of implementation
- Conductor app prevents blocking (switch worktrees)
- Wave structure ensures dependencies always met
- State sync automatic (guardkit integration)

**Next Step**: Open Conductor app → Create first worktree → Run `/task-work TASK-037A`

---

**Created**: 2025-11-01
**Status**: ✅ **READY FOR SOLO IMPLEMENTATION**
**Recommended Starting Task**: TASK-037A (Universal Language Mapping)
