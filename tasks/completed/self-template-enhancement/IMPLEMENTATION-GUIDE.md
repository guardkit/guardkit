# Implementation Guide: Self-Template Enhancement (REVISED)

## Key Insight

**GuardKit is a Python library/CLI tool, NOT a FastAPI application.**

The original plan focused on enhancing FastAPI specialists, but these templates are for **users creating FastAPI apps**, not for developing GuardKit itself.

### What GuardKit Actually Uses
- Pydantic v2 models for data validation
- Dataclasses for internal state
- pytest with complex fixtures and mocking
- Module organization patterns for CLI tools
- Type hints with strict mypy

### The Gap
No existing guidance covers Python library development patterns. The FastAPI specialists in `installer/core/templates/fastapi-python/` are irrelevant for GuardKit development.

---

## Wave Breakdown (REVISED)

### Wave 1: Reference Analysis (1 task)

Run `/template-create --dry-run` to understand what improvements would be generated.

**Tasks:**
- TASK-STE-001: Analyze GuardKit structure

**Method:** Direct execution (no task-work needed)

**Expected Output:**
- Analysis JSON showing quality scores
- Identified gaps in agent content
- Suggested rules structure
- Enhancement opportunities

**Conductor Workspaces:**
- `self-template-wave1-guardkit`

---

### Wave 2: Rules Structure for Python Library Development (1 task)

Add `.claude/rules/` structure focused on **library development patterns**.

**Tasks:**
- TASK-STE-007: Add rules to GuardKit .claude/

**Method:** `/task-work`

**Rules Structure:**
```
.claude/rules/
├── python-library.md         # paths: installer/core/lib/**/*.py
├── testing.md                # paths: tests/**/*.py
├── task-workflow.md          # paths: tasks/**/*
├── patterns/
│   ├── template.md           # paths: installer/core/templates/**/*
│   ├── pydantic-models.md    # paths: **/models.py, **/schemas.py
│   └── dataclasses.md        # paths: **/*.py (when using dataclasses)
└── guidance/
    └── agent-development.md  # paths: **/agents/**/*.md
```

**Conductor Workspaces:**
- `self-template-wave2-guardkit-rules`

---

### Wave 3: Validation (1 task)

Validate improvements with an actual GuardKit development task.

**Tasks:**
- TASK-STE-008: Validate with GuardKit dev task

**Method:** `/task-work`

**Validation Steps:**
1. Create a Python library task (e.g., add helper to `id_generator.py`)
2. Verify rules load conditionally
3. Verify patterns match actual GuardKit code
4. Verify generated code passes `ruff` and `mypy`
5. Document any remaining gaps

---

## Deferred Tasks

The following tasks are **deferred** because they enhance FastAPI templates for users, not GuardKit development:

| Task | Status | Reason |
|------|--------|--------|
| TASK-STE-002 | DEFERRED | FastAPI template analysis not needed for GuardKit |
| TASK-STE-003 | DEFERRED | FastAPI specialist is for user apps |
| TASK-STE-004 | DEFERRED | FastAPI testing specialist is for user apps |
| TASK-STE-005 | DEFERRED | FastAPI database specialist is for user apps |
| TASK-STE-006 | DEFERRED | FastAPI template rules not needed for GuardKit |

These can be picked up as a **separate initiative** for improving templates that users consume.

---

## Execution Commands (REVISED)

### Wave 1 (Analysis)
```bash
/template-create --name guardkit-analysis --dry-run --save-analysis
```

### Wave 2 (Rules Structure)
```bash
/task-work TASK-STE-007
```

### Wave 3 (Validation)
```bash
/task-work TASK-STE-008
```

---

## Dependencies (REVISED)

```
Wave 1 (Analysis)
    │
    └── TASK-STE-001 ──→ Wave 2 (Rules)
                              │
                              └── TASK-STE-007 ──→ Wave 3 (Validation)
                                                        │
                                                 TASK-STE-008
```

Much simpler than the original 4-wave, 8-task plan.

---

## Estimated Effort (REVISED)

| Wave | Tasks | Effort | Parallel? |
|------|-------|--------|-----------|
| 1 | 1 | 30 min | N/A |
| 2 | 1 | 2-3 hours | N/A |
| 3 | 1 | 1 hour | N/A |
| **Total** | **3** | **3-4 hours** | - |

Reduced from 8 tasks to 3 active tasks by focusing on what GuardKit actually needs.

---

## Python Patterns to Document (Wave 2)

Based on investigation of GuardKit code, these patterns should be in rules:

### From `id_generator.py`
- Module docstring with examples
- `__all__` exports
- Type hints with Optional, Set, Dict, List
- Compiled regex patterns as constants
- Thread-safe caching with locks
- Dataclass for state
- Error message constants
- NumPy-style docstrings with Examples

### From `template_creation/models.py`
- Pydantic v2 BaseModel patterns
- Field with description and defaults
- `model_dump()` for serialization
- Config class with json_schema_extra

### From `tests/unit/test_id_generator.py`
- pytest fixtures with tmp_path
- monkeypatch for patching
- patch.object patterns
- Test class organization
- Coverage summary docstring

---

## Future Work (Deferred)

When ready to improve templates for users:
1. Re-enable TASK-STE-003/004/005/006
2. Run `/agent-enhance` on FastAPI specialists
3. Add rules structure to `fastapi-python` template
4. Validate with a user-facing FastAPI task
