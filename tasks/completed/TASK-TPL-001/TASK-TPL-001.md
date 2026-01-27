---
id: TASK-TPL-001
title: Replace passlib with direct bcrypt for password hashing
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T13:35:00Z
completed: 2026-01-27T13:35:00Z
priority: critical
tags: [template, fastapi-python, security, bcrypt, password-hashing]
complexity: 3
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 1
implementation_mode: task-work
dependencies: []
conductor_workspace: fastapi-fixes-wave1-1
architectural_review_score: 88
test_coverage: 98
tests_passed: 13
tests_failed: 0
completed_location: tasks/completed/TASK-TPL-001/
organized_files:
  - TASK-TPL-001.md
  - completion-report.md
---

# Task: Replace passlib with direct bcrypt for password hashing

## Description

Replace the unmaintained passlib library with direct bcrypt usage in the fastapi-python template. passlib has been unmaintained since 2020 and is incompatible with bcrypt 5.x, causing complete authentication failures in new projects.

## Problem

- passlib unmaintained since 2020
- Incompatible with bcrypt 5.x (internal bug detection uses >72 byte password)
- Password hashing fails completely, blocking all authentication
- Current workaround (version pinning) is technical debt

## Solution

Replace passlib with direct bcrypt usage:

```python
# src/core/security.py
import bcrypt

BCRYPT_ROUNDS = 12  # Production default

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    if not password:
        raise ValueError("Password cannot be empty")
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False
```

## Acceptance Criteria

- [x] Create `templates/core/security.py.template` with direct bcrypt usage
- [x] Remove passlib from dependencies in pyproject.toml template (not present)
- [x] Add `bcrypt>=4.0.0` as dependency
- [x] Update any agent files that reference passlib patterns (none found)
- [x] Add migration note in README for existing projects
- [x] Test that bcrypt output format is compatible with existing hashes

## Files Modified

1. `installer/core/templates/fastapi-python/templates/core/security.py.template` (NEW)
2. `installer/core/templates/fastapi-python/manifest.json` (updated frameworks)
3. `installer/core/templates/fastapi-python/README.md` (added migration note)

## Implementation Summary

### Phase 2: Planning
- Designed bcrypt-based implementation with BCRYPT_ROUNDS=12
- Planned two functions: get_password_hash(), verify_password()

### Phase 2.5B: Architectural Review
- Score: 88/100 (Approved with recommendations)
- SOLID: 44/50
- DRY: 23/25
- YAGNI: 21/25

### Phase 3: Implementation
- Created security.py.template with comprehensive docstrings
- Added bcrypt to manifest.json frameworks
- Added migration guide to README

### Phase 4: Testing
- 13/13 tests passed
- 98% line coverage
- All edge cases covered (empty, None, unicode, invalid hash)

### Phase 5: Code Review
- Code quality: 9/10
- Approved with migration guide added

### Phase 5.5: Plan Audit
- Implementation matches plan
- No scope creep detected
- All acceptance criteria met

## Notes

- bcrypt output format is identical to passlib[bcrypt], so existing hashes work
- No rehashing needed for migrating projects
- Direct bcrypt is simpler than passlib abstraction layer
