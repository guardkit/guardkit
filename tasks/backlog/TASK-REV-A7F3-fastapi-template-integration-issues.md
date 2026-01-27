---
id: TASK-REV-A7F3
title: Review fastapi-python template integration issues from feature-build testing
status: completed
created: 2026-01-27T10:30:00Z
updated: 2026-01-27T12:45:00Z
decision: implement
priority: high
tags: [template, fastapi-python, integration, quality, review]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 5
source_file: /Users/richardwoollcott/Projects/guardkit_testing/simple-feature_success/integration_issues.md
review_results:
  score: 62
  findings_count: 6
  recommendations_count: 6
  critical_issues: 3
  classification: 5 template-level, 1 documentation
  report_path: .claude/reviews/TASK-REV-A7F3-fastapi-template-review.md
  completed_at: 2026-01-27T12:30:00Z
---

# Task: Review fastapi-python template integration issues from feature-build testing

## Description

Analyze the integration issues encountered during feature-build testing of a FastAPI project and recommend improvements to the GuardKit fastapi-python template to prevent these issues from occurring in future projects.

The issues were discovered during real-world usage of the template and represent common pitfalls that new projects encounter.

## Source Analysis

The following issues were documented in the integration testing:

### Issue 1: Missing Dependencies in pyproject.toml
- **Impact**: ModuleNotFoundError at runtime
- **Root Cause**: Template's pyproject.toml missing common runtime dependencies
- **Affected Packages**: structlog, sqlalchemy[asyncio], asyncpg, alembic, email-validator

### Issue 2: Multiple Python Installations Conflict
- **Impact**: Packages installed but tools can't find them
- **Root Cause**: Documentation doesn't emphasize virtual environment usage
- **Recommendation**: Template should include explicit venv setup instructions

### Issue 3: Alembic Logging Configuration Error
- **Impact**: ValueError when running alembic migrations
- **Root Cause**: alembic.ini missing required `root` logger section
- **Fix Complexity**: Simple configuration fix

### Issue 4: Health Check Schema Validation Error
- **Impact**: Health endpoint returns validation error
- **Root Cause**: Pydantic schema has `ge=0` constraint but SQLAlchemy can report negative overflow
- **Recommendation**: Review all Pydantic schemas for overly strict constraints

### Issue 5: bcrypt/passlib Compatibility Error
- **Impact**: Password hashing fails completely
- **Root Cause**: passlib incompatible with bcrypt 5.x
- **Critical**: This is a security-related issue that blocks authentication

### Issue 6: Database Transactions Not Committing
- **Impact**: Created data doesn't persist
- **Root Cause**: Session dependency uses flush() without commit
- **Critical**: This is a data integrity issue

## Acceptance Criteria

- [ ] Analyze each issue for template impact
- [ ] Determine which issues are template-level vs project-specific
- [ ] Prioritize fixes by severity and frequency
- [ ] Document recommended template changes
- [ ] Consider backward compatibility for existing projects
- [ ] Identify any related issues in other templates

## Review Scope

1. **Template Files to Review**:
   - `installer/core/templates/fastapi-python/`
   - Specifically: pyproject.toml template, alembic.ini, db/session.py pattern

2. **Documentation to Review**:
   - Template README
   - Getting started instructions
   - Troubleshooting section (if exists)

3. **Cross-Template Analysis**:
   - Check if similar issues could affect other templates
   - Identify common patterns that should be standardized

## Decision Checkpoint

After analysis, decide:
- [A]ccept findings and create implementation tasks
- [I]mplement changes directly (if simple fixes)
- [R]evise scope if additional issues discovered
- [C]ancel if issues are project-specific, not template-related

## Implementation Notes

This review should produce:
1. A prioritized list of template improvements
2. Specific code/config changes for each issue
3. Documentation updates needed
4. Test coverage recommendations

## Test Execution Log

[Automatically populated by /task-review]
