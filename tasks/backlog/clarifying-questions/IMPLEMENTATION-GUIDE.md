# Implementation Guide: Clarifying Questions Feature

## Execution Strategy

This feature is organized into **4 waves** with parallel execution opportunities using Conductor workspaces. Each wave builds on the previous, so waves must be completed sequentially, but tasks within each wave can run in parallel.

---

## Wave 1: Core Module (2 days)

**Goal**: Create the shared clarification infrastructure

### Parallel Execution (3 Conductor workspaces)

```bash
# Start all 3 in parallel using Conductor
conductor spawn clarifying-questions-wave1-core
conductor spawn clarifying-questions-wave1-detection
conductor spawn clarifying-questions-wave1-display
```

| Task | Workspace | Method | Why This Method |
|------|-----------|--------|-----------------|
| **TASK-CLQ-001** | wave1-core | `/task-work` | Complex dataclasses, needs architectural review |
| **TASK-CLQ-002** | wave1-detection | `/task-work` | Algorithm design, needs quality gates |
| **TASK-CLQ-003** | wave1-display | Direct | UI formatting, straightforward patterns |

### Execution Commands

**Workspace 1: Core Module**
```bash
cd ~/conductor/clarifying-questions-wave1-core
/task-work TASK-CLQ-001
```

**Workspace 2: Detection Algorithms**
```bash
cd ~/conductor/clarifying-questions-wave1-detection
/task-work TASK-CLQ-002
```

**Workspace 3: Display Formatting**
```bash
cd ~/conductor/clarifying-questions-wave1-display
# Direct implementation - no /task-work needed
# Read spec from review report, implement display.py
```

### Wave 1 Completion Criteria

- [ ] `clarification/__init__.py` exists with exports
- [ ] `clarification/core.py` has ClarificationContext, Decision, Question dataclasses
- [ ] `clarification/detection.py` has all 5 detection functions
- [ ] `clarification/display.py` has full/quick/skip display functions
- [ ] All files have basic unit tests

### Dependencies

**None** - Wave 1 has no dependencies on other waves

---

## Wave 2: Question Templates (1 day)

**Goal**: Create context-specific question templates

**Depends on**: Wave 1 (core module must exist)

### Parallel Execution (3 Conductor workspaces)

```bash
# Start all 3 in parallel using Conductor
conductor spawn clarifying-questions-wave2-context-c
conductor spawn clarifying-questions-wave2-context-a
conductor spawn clarifying-questions-wave2-context-b
```

| Task | Workspace | Method | Why This Method |
|------|-----------|--------|-----------------|
| **TASK-CLQ-004** | wave2-context-c | `/task-work` | Most complex, 6 question categories |
| **TASK-CLQ-005** | wave2-context-a | Direct | Simpler, 4 question categories |
| **TASK-CLQ-006** | wave2-context-b | Direct | Simpler, 4 question categories |

### Execution Commands

**Workspace 1: Context C (task-work) - Most Complex**
```bash
cd ~/conductor/clarifying-questions-wave2-context-c
/task-work TASK-CLQ-004
```

**Workspace 2: Context A (task-review)**
```bash
cd ~/conductor/clarifying-questions-wave2-context-a
# Direct implementation
# Create templates/review_scope.py with REVIEW_FOCUS_QUESTIONS, etc.
```

**Workspace 3: Context B (feature-plan)**
```bash
cd ~/conductor/clarifying-questions-wave2-context-b
# Direct implementation
# Create templates/implementation_prefs.py
```

### Wave 2 Completion Criteria

- [ ] `templates/implementation_planning.py` (Context C) complete with 6 categories
- [ ] `templates/review_scope.py` (Context A) complete with 4 categories
- [ ] `templates/implementation_prefs.py` (Context B) complete with 4 categories
- [ ] `generators/planning_generator.py` complete
- [ ] `generators/review_generator.py` complete
- [ ] `generators/implement_generator.py` complete

### Dependencies

- Wave 1 core.py (imports ClarificationContext, Question, Decision)
- Wave 1 detection.py (imports detection functions)

---

## Wave 3: Command Integration (2 days)

**Goal**: Integrate clarification into all three commands

**Depends on**: Wave 2 (templates and generators must exist)

### Parallel Execution (3 Conductor workspaces)

```bash
# Start all 3 in parallel using Conductor
conductor spawn clarifying-questions-wave3-task-work
conductor spawn clarifying-questions-wave3-task-review
conductor spawn clarifying-questions-wave3-feature-plan
```

| Task | Workspace | Method | Why This Method |
|------|-----------|--------|-----------------|
| **TASK-CLQ-007** | wave3-task-work | `/task-work` | Core integration, needs quality gates |
| **TASK-CLQ-008** | wave3-task-review | `/task-work` | Two integration points (Phase 1 + [I]mplement) |
| **TASK-CLQ-009** | wave3-feature-plan | Direct | Mostly inherits from task-review |

### Execution Commands

**Workspace 1: task-work.md Integration**
```bash
cd ~/conductor/clarifying-questions-wave3-task-work
/task-work TASK-CLQ-007
```

**Workspace 2: task-review.md Integration**
```bash
cd ~/conductor/clarifying-questions-wave3-task-review
/task-work TASK-CLQ-008
```

**Workspace 3: feature-plan.md Integration**
```bash
cd ~/conductor/clarifying-questions-wave3-feature-plan
# Direct implementation
# Add flag documentation, clarification flow documentation
```

### Wave 3 Completion Criteria

- [ ] task-work.md has Phase 1.5 specification
- [ ] task-work.md Phase 2 accepts clarification context
- [ ] task-review.md Phase 1 has review clarification
- [ ] task-review.md [I]mplement handler has implementation prefs
- [ ] feature-plan.md documents clarification flow
- [ ] All three commands support --no-questions, --with-questions, --defaults flags

### Dependencies

- Wave 2 templates (all three contexts)
- Wave 2 generators (all three)
- Wave 1 display.py (for UI formatting)

---

## Wave 4: Polish & Documentation (1 day)

**Goal**: Persistence, documentation, and user testing

**Depends on**: Wave 3 (integration must be complete)

### Parallel Execution (3 Conductor workspaces)

```bash
# Start all 3 in parallel using Conductor
conductor spawn clarifying-questions-wave4-persistence
conductor spawn clarifying-questions-wave4-docs
conductor spawn clarifying-questions-wave4-testing
```

| Task | Workspace | Method | Why This Method |
|------|-----------|--------|-----------------|
| **TASK-CLQ-010** | wave4-persistence | Direct | YAML frontmatter, straightforward |
| **TASK-CLQ-011** | wave4-docs | Direct | Documentation updates |
| **TASK-CLQ-012** | wave4-testing | `/task-work` | Comprehensive testing needs quality gates |

### Execution Commands

**Workspace 1: Persistence & Audit Trail**
```bash
cd ~/conductor/clarifying-questions-wave4-persistence
# Direct implementation
# Update persist_to_frontmatter() in core.py
# Define YAML schema for clarification decisions
```

**Workspace 2: Documentation**
```bash
cd ~/conductor/clarifying-questions-wave4-docs
# Direct implementation
# Update CLAUDE.md with clarification workflow
# Add examples to command files
```

**Workspace 3: Testing**
```bash
cd ~/conductor/clarifying-questions-wave4-testing
/task-work TASK-CLQ-012
```

### Wave 4 Completion Criteria

- [ ] Clarification decisions persist to task frontmatter
- [ ] CLAUDE.md documents clarification workflow
- [ ] All command files have flag documentation
- [ ] User guide examples added
- [ ] Integration tests pass for all 3 contexts
- [ ] User acceptance testing complete

### Dependencies

- Wave 3 (all integrations complete)

---

## Quick Reference: Method Selection

### Use `/task-work` When:
- Task is complex (score 5+)
- Algorithm design needed
- Multiple files involved
- Quality gates important
- Architectural review needed

### Use Direct Implementation When:
- Task is straightforward
- Pattern is well-defined (from spec)
- Single file or simple changes
- Following existing patterns
- UI/formatting work

---

## Execution Timeline

```
Day 1-2: Wave 1 (Core Module)
├── Workspace 1: TASK-CLQ-001 (core.py) ─────────────┐
├── Workspace 2: TASK-CLQ-002 (detection.py) ────────┼── Parallel
└── Workspace 3: TASK-CLQ-003 (display.py) ──────────┘

Day 3: Wave 2 (Templates)
├── Workspace 1: TASK-CLQ-004 (Context C) ───────────┐
├── Workspace 2: TASK-CLQ-005 (Context A) ───────────┼── Parallel
└── Workspace 3: TASK-CLQ-006 (Context B) ───────────┘

Day 4-5: Wave 3 (Integration)
├── Workspace 1: TASK-CLQ-007 (task-work.md) ────────┐
├── Workspace 2: TASK-CLQ-008 (task-review.md) ──────┼── Parallel
└── Workspace 3: TASK-CLQ-009 (feature-plan.md) ─────┘

Day 6: Wave 4 (Polish)
├── Workspace 1: TASK-CLQ-010 (persistence) ─────────┐
├── Workspace 2: TASK-CLQ-011 (documentation) ───────┼── Parallel
└── Workspace 3: TASK-CLQ-012 (testing) ─────────────┘
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Wave dependency failure** | Each wave has clear completion criteria before proceeding |
| **Parallel merge conflicts** | Each task touches different files, minimal overlap |
| **Integration issues** | Wave 3 tasks can coordinate via shared review report |
| **Testing gaps** | Wave 4 has dedicated testing task with /task-work quality gates |

---

## Files Created by This Feature

```
installer/core/commands/lib/clarification/
├── __init__.py                          # Wave 1
├── core.py                              # Wave 1 (TASK-CLQ-001)
├── detection.py                         # Wave 1 (TASK-CLQ-002)
├── display.py                           # Wave 1 (TASK-CLQ-003)
├── templates/
│   ├── implementation_planning.py       # Wave 2 (TASK-CLQ-004)
│   ├── review_scope.py                  # Wave 2 (TASK-CLQ-005)
│   └── implementation_prefs.py          # Wave 2 (TASK-CLQ-006)
└── generators/
    ├── planning_generator.py            # Wave 2 (TASK-CLQ-004)
    ├── review_generator.py              # Wave 2 (TASK-CLQ-005)
    └── implement_generator.py           # Wave 2 (TASK-CLQ-006)

Modified files:
├── installer/core/commands/task-work.md      # Wave 3 (TASK-CLQ-007)
├── installer/core/commands/task-review.md    # Wave 3 (TASK-CLQ-008)
├── installer/core/commands/feature-plan.md   # Wave 3 (TASK-CLQ-009)
└── CLAUDE.md                                   # Wave 4 (TASK-CLQ-011)
```

---

## Success Metrics

After completion, verify:

1. **task-work** asks clarifying questions for complexity ≥5 tasks
2. **task-review** asks review scope questions for decision mode
3. **feature-plan [I]mplement** asks implementation preference questions
4. All commands respect `--no-questions` flag
5. Clarification decisions persist to task frontmatter
6. Planning rework rate reduced (measure over 10 tasks)
