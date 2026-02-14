# Completion Report: TASK-FIX-STUB-B

## Summary

Created `.claude/rules/anti-stub.md` — a rules file that defines stub patterns and establishes enforcement rules for the Coach agent in the AutoBuild adversarial cooperation workflow.

## Deliverable

**File created**: `.claude/rules/anti-stub.md` (153 lines)

### Content

| Section | Purpose |
|---------|---------|
| Stub Definition | 6 concrete stub patterns (pass, NotImplementedError, TODO-only, hardcoded defaults, logging-only, ellipsis) |
| Enforcement by Task Type | FEATURE/REFACTOR: rejected. SCAFFOLDING/INFRASTRUCTURE: permitted with explicit AC. INTEGRATION: rejected. |
| Primary Deliverable Function | 4-point definition with thin-wrapper exception |
| Concrete Examples | 4 stub examples + 4 non-stub examples (including real `run_system_plan()` case from TASK-SP-006) |
| Coach Verification Checklist | 4-step verification process |
| Feedback Template | Structured rejection format |

### Path-Based Loading

The rule uses `paths: guardkit/**/*.py, src/**/*.py, src/**/*.ts, src/**/*.cs` frontmatter, ensuring it loads automatically when Claude Code reviews implementation files. No manual Coach agent update needed.

## Acceptance Criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC-001 | PASS | File exists at `.claude/rules/anti-stub.md` with 6 pattern definitions |
| AC-002 | PASS | "FEATURE and REFACTOR Tasks: Stubs are REJECTED" section |
| AC-003 | PASS | "SCAFFOLDING and INFRASTRUCTURE Tasks: Stubs are PERMITTED" section with "only when" condition |
| AC-004 | PASS | 8 total examples (4 stub, 4 non-stub) with code blocks |
| AC-005 | PASS | "Primary Deliverable Function" section with 4-point definition |

## Context

- **Parent review**: TASK-REV-STUB (RC-4: No stub detection gate)
- **Feature**: FEAT-STUB-QG (Stub Quality Gates)
- **Wave**: 1
- **Duration**: ~2 minutes (documentation-only task)
