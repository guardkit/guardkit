---
id: TASK-FMT-008
title: Validate fastmcp-python template with /template-validate
status: backlog
task_type: implementation
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: medium
tags: [template, mcp, fastmcp, validation, qa]
complexity: 2
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 3
parallel_group: wave3
implementation_mode: direct
conductor_workspace: null
dependencies: [TASK-FMT-007]
---

# Task: Validate fastmcp-python template with /template-validate

## Description

Run `/template-validate` on the completed `fastmcp-python` template to ensure it meets GuardKit quality standards. Fix any issues identified.

## Acceptance Criteria

- [ ] Run `/template-validate installer/core/templates/fastmcp-python/`
- [ ] Template passes with 0 errors
- [ ] Quality score 8+/10
- [ ] All critical components present:
  - [ ] manifest.json valid
  - [ ] settings.json valid
  - [ ] At least 2 agents
  - [ ] At least 6 templates
  - [ ] At least 3 rules
  - [ ] CLAUDE.md files present
  - [ ] README.md present
- [ ] Fix any issues identified by validator

## Quality Targets

| Metric | Target | Weight |
|--------|--------|--------|
| manifest.json completeness | 100% | 15% |
| settings.json completeness | 100% | 15% |
| Agent quality (boundaries, capabilities) | 8+/10 | 25% |
| Template file coverage | 8+ files | 20% |
| Rules coverage | 4+ rules | 15% |
| Documentation quality | 8+/10 | 10% |

## Validation Command

```bash
/template-validate installer/core/templates/fastmcp-python/
```

## Expected Output

```
================================================================================
TEMPLATE VALIDATION: fastmcp-python
================================================================================

✅ manifest.json: Valid (100%)
✅ settings.json: Valid (100%)
✅ Agents: 3 found (fastmcp-specialist, fastmcp-testing-specialist, ...)
✅ Templates: 8 found
✅ Rules: 4 found
✅ CLAUDE.md: Present (top-level and nested)
✅ README.md: Present

Quality Score: 8.5/10

✅ Template validation PASSED
================================================================================
```

## If Validation Fails

1. Review validation output for specific errors
2. Fix issues in corresponding files
3. Re-run validation
4. Repeat until all checks pass

## Test Execution Log

[Direct implementation - no /task-work quality gates]
