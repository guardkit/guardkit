---
id: TASK-STE-008
title: Validate improvements with Python test task
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [validation, python, testing, integration]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 4
complexity: 4
depends_on:
  - TASK-STE-006
  - TASK-STE-007
---

# Task: Validate improvements with Python test task

## Description

Create and execute a Python/FastAPI test task to validate that all improvements from Waves 1-3 are working correctly.

## Validation Steps

### 1. Agent Discovery Validation

Create a Python task and verify:
- [ ] fastapi-specialist is discovered for `.py` files
- [ ] fastapi-testing-specialist is discovered for `test_*.py` files
- [ ] fastapi-database-specialist is discovered for `models/*.py` files

### 2. Rules Loading Validation

Verify conditional loading:
- [ ] `python-style.md` loads when editing Python files
- [ ] `testing.md` loads when editing test files
- [ ] `database.md` loads when editing model files

### 3. Content Quality Validation

Verify enhanced content:
- [ ] Agent boundaries are clear and actionable
- [ ] Code examples are relevant and correct
- [ ] Best practices include rationale
- [ ] Anti-patterns help avoid common mistakes

### 4. Workflow Integration

Execute a complete workflow:
```bash
/task-create "Add sample FastAPI endpoint with tests" tags:[python,fastapi,testing]
/task-work TASK-XXX
```

Verify:
- [ ] Planning phase uses Python patterns
- [ ] Implementation follows FastAPI best practices
- [ ] Tests are generated with correct fixtures
- [ ] Coverage thresholds are enforced

## Acceptance Criteria

- [ ] All 4 validation areas pass
- [ ] No regressions in existing functionality
- [ ] Context usage improved (measure before/after)
- [ ] Documentation updated if gaps found

## Success Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Context usage (Python files) | TBD | TBD | -40% |
| Agent discovery rate | TBD | TBD | 100% |
| Rules loading rate | TBD | TBD | 100% |
| Test pass rate | N/A | TBD | 100% |

## Notes

- This task cannot run in parallel - requires all previous waves complete
- Document any remaining gaps for future improvement
- Update README.md with validation results
