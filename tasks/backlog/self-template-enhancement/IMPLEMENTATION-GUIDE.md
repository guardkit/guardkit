# Implementation Guide: Self-Template Enhancement

## Wave Breakdown

### Wave 1: Reference Analysis (Parallel - 2 tasks)

Run `/template-create --dry-run` to understand what improvements would be generated without modifying files.

**Tasks:**
- TASK-STE-001: Analyze GuardKit structure
- TASK-STE-002: Analyze fastapi-python template

**Method:** Direct execution (no task-work needed)

**Expected Output:**
- Analysis JSON showing quality scores
- Identified gaps in agent content
- Suggested rules structure
- Enhancement opportunities

**Conductor Workspaces:**
- `self-template-wave1-guardkit`
- `self-template-wave1-fastapi`

---

### Wave 2: Agent Enhancement (Parallel - 3 tasks)

Apply `/agent-enhance` directly to existing Python agents based on Wave 1 analysis.

**Tasks:**
- TASK-STE-003: Enhance fastapi-specialist
- TASK-STE-004: Enhance fastapi-testing-specialist
- TASK-STE-005: Enhance fastapi-database-specialist

**Method:** `/task-work` with dry-run first

**Enhancement Focus:**
- Add more code examples from template source
- Strengthen ALWAYS/NEVER/ASK boundaries
- Add best practices with rationale
- Include anti-patterns to avoid
- Improve discovery metadata

**Conductor Workspaces:**
- `self-template-wave2-specialist`
- `self-template-wave2-testing`
- `self-template-wave2-database`

---

### Wave 3: Rules Structure (Parallel - 2 tasks)

Add `.claude/rules/` structure for conditional loading.

**Tasks:**
- TASK-STE-006: Add rules to fastapi-python template
- TASK-STE-007: Add rules to GuardKit .claude/

**Method:** `/task-work`

**Rules Structure for fastapi-python:**
```
installer/core/templates/fastapi-python/.claude/rules/
├── python-style.md          # paths: **/*.py
├── testing.md               # paths: tests/**/*.py, **/test_*.py
├── database.md              # paths: **/models/*.py, **/crud/*.py
└── guidance/
    └── fastapi-patterns.md  # paths: src/**/*.py
```

**Rules Structure for GuardKit:**
```
.claude/rules/
├── testing.md              # paths: tests/**/*
├── task-workflow.md        # paths: tasks/**/*
├── patterns/
│   └── template.md         # paths: installer/core/templates/**/*
└── guidance/
    └── agent-development.md # paths: **/agents/**/*.md
```

**Conductor Workspaces:**
- `self-template-wave3-fastapi-rules`
- `self-template-wave3-guardkit-rules`

---

### Wave 4: Validation (Sequential - 1 task)

Validate improvements with a Python test task.

**Tasks:**
- TASK-STE-008: Validation task

**Method:** `/task-work`

**Validation Steps:**
1. Create a Python/FastAPI task
2. Verify agents are discovered
3. Verify rules load conditionally
4. Verify content quality is improved
5. Document any remaining gaps

---

## Execution Commands

### Wave 1 (Parallel)
```bash
# Terminal 1 - GuardKit analysis
/template-create --name guardkit-analysis --dry-run --save-analysis

# Terminal 2 - FastAPI template analysis
/template-create --name fastapi-analysis --dry-run --save-analysis \
  --source installer/core/templates/fastapi-python
```

### Wave 2 (Parallel)
```bash
# Terminal 1
/task-work TASK-STE-003

# Terminal 2
/task-work TASK-STE-004

# Terminal 3
/task-work TASK-STE-005
```

### Wave 3 (Parallel)
```bash
# Terminal 1
/task-work TASK-STE-006

# Terminal 2
/task-work TASK-STE-007
```

### Wave 4 (Sequential)
```bash
/task-work TASK-STE-008
```

---

## Dependencies

```
Wave 1 (Analysis)
    │
    ├── TASK-STE-001 ─┐
    │                 │
    └── TASK-STE-002 ─┴─→ Wave 2 (Enhancement)
                              │
                              ├── TASK-STE-003 ─┐
                              │                 │
                              ├── TASK-STE-004 ─┼─→ Wave 3 (Rules)
                              │                 │       │
                              └── TASK-STE-005 ─┘       ├── TASK-STE-006 ─┐
                                                        │                 │
                                                        └── TASK-STE-007 ─┴─→ Wave 4
                                                                                  │
                                                                           TASK-STE-008
```

---

## Estimated Effort

| Wave | Tasks | Effort | Parallel? |
|------|-------|--------|-----------|
| 1 | 2 | 1 hour | Yes |
| 2 | 3 | 2-3 hours | Yes |
| 3 | 2 | 2-3 hours | Yes |
| 4 | 1 | 1 hour | No |
| **Total** | **8** | **6-8 hours** | - |

With Conductor parallel execution: **~4 hours**
