# Feature: Coach Agent Security Integration

**Source Review**: [TASK-REV-SEC1](./../TASK-REV-SEC1-coach-security-integration.md)
**Review Report**: [.claude/reviews/TASK-REV-SEC1-review-report.md](../../../.claude/reviews/TASK-REV-SEC1-review-report.md)

## Problem Statement

The current Coach agent in `/feature-build` validates functional correctness but cannot detect security vulnerabilities. Evidence from FastAPI authentication implementation showed 6 security issues (CORS wildcards, timing attacks, missing token revocation) that passed Coach validation but were caught by manual security review.

## Solution: Option C (Hybrid) Architecture

Implement a two-tier security validation:

1. **Quick Security Checks (Always)** - ~30 seconds
   - Hardcoded secrets detection
   - SQL injection patterns
   - CORS wildcard configuration
   - Debug mode detection
   - Command injection patterns

2. **Full Security-Specialist Review (Conditional)** - ~2-5 minutes
   - Triggered for tasks tagged with: `authentication`, `authorization`, `security`, `auth`, `token`, `payment`
   - Or tasks with security keywords in title
   - Comprehensive OWASP Top 10 analysis
   - Auth pattern review

## Subtask Summary

| Wave | Task ID | Title | Mode | Est. Hours |
|------|---------|-------|------|------------|
| 1 | TASK-SEC-001 | Add quick security checks to Coach agent | task-work | 2-3h |
| 1 | TASK-SEC-002 | Add security configuration schema | task-work | 1-2h |
| 2 | TASK-SEC-003 | Implement security-specialist invocation | task-work | 3-4h |
| 2 | TASK-SEC-004 | Implement task tagging detection | task-work | 1-2h |
| 3 | TASK-SEC-005 | Add security validation tests | task-work | 2-3h |
| 3 | TASK-SEC-006 | Update Coach agent documentation | direct | 1-2h |

**Total Estimated Effort**: 10-16 hours

## Wave Breakdown

### Wave 1: Quick Checks Foundation (Parallel)
- TASK-SEC-001 and TASK-SEC-002 can run in parallel
- No dependencies

### Wave 2: Full Review Integration (Parallel)
- TASK-SEC-003 and TASK-SEC-004 can run in parallel
- Depends on Wave 1 completion

### Wave 3: Testing & Documentation (Sequential)
- TASK-SEC-005 depends on Wave 2
- TASK-SEC-006 can run after TASK-SEC-005

## Success Criteria

- [ ] Quick security checks run on all tasks (~30s overhead)
- [ ] Full security review runs on auth-tagged tasks
- [ ] Critical findings block Coach approval
- [ ] High findings generate FEEDBACK (iteration)
- [ ] User can configure security level (strict/standard/minimal/skip)
- [ ] All existing tests continue to pass
- [ ] Documentation updated

## Files Affected

- `.claude/agents/autobuild-coach.md` - Add security validation section
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Add security checks
- `guardkit/orchestrator/quality_gates/security_checker.py` - New file
- Task and feature YAML schemas - Add security configuration
- `installer/core/commands/feature-build.md` - Document security options
