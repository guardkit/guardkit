# Feature: Coach Agent Security Integration

**Feature ID**: `FEAT-SEC`
**Feature File**: [.guardkit/features/FEAT-SEC.yaml](../../../.guardkit/features/FEAT-SEC.yaml)
**Source Review**: [TASK-REV-SEC1](./../TASK-REV-SEC1-coach-security-integration.md)
**Architecture Review**: [TASK-REV-4B0F](../../../.claude/reviews/TASK-REV-4B0F-review-report.md) (Revised architecture)

## AutoBuild Ready

This feature is configured for autonomous implementation via `/feature-build`:

```bash
# Run the full feature
/feature-build FEAT-SEC

# Or run individual tasks
/feature-build TASK-SEC-001
```

## Problem Statement

The current Coach agent in `/feature-build` validates functional correctness but cannot detect security vulnerabilities. Evidence from FastAPI authentication implementation showed 6 security issues (CORS wildcards, timing attacks, missing token revocation) that passed Coach validation but were caught by manual security review.

## Solution: Revised Architecture (from TASK-REV-4B0F)

**Key Constraint**: Coach is READ-ONLY. Coach has tools [Read, Bash, Grep, Glob] - NO Task tool.

The original design (Option C) proposed Coach invoke security-specialist agent, but this violates Coach's read-only architecture. The revised solution:

### Architecture Diagram

```
Pre-Loop Quality Gates
    |
    +-- Phase 2.5A: Pattern Suggestions
    +-- Phase 2.5B: Architectural Review
    +-- Phase 2.5C: Security Pre-Check (NEW)
    |       +-- IF security-tagged: Invoke security-specialist
    |       +-- Via TaskWorkInterface (NOT Coach)
    |       +-- Save to security_review_results.json
    |
    v
Player (task-work)
    |
    +-- Phase 3: Implementation
    +-- Phase 4: Testing
    +-- Phase 4.3: Quick Security Scan (NEW)
    |       +-- Run SecurityChecker.run_quick_checks()
    |       +-- Write to task_work_results.json["security"]
    +-- Phase 4.5: Test Enforcement
    +-- Phase 5: Code Review
    |
    v
Coach (validation)
    |
    +-- READ task_work_results.json (including security)
    +-- Verify all quality gates passed
    +-- Approve/Feedback (NO agent invocation)
```

### Two-Tier Security Validation

1. **Quick Security Checks (Phase 4.3)** - ~30 seconds
   - Runs in task-work, NOT Coach
   - Hardcoded secrets detection
   - SQL injection patterns
   - CORS wildcard configuration
   - Debug mode detection
   - Command injection patterns
   - Results written to `task_work_results.json["security"]`

2. **Full Security-Specialist Review (Phase 2.5C)** - ~2-5 minutes
   - Runs in pre-loop via TaskWorkInterface
   - Triggered for tasks tagged with: `authentication`, `authorization`, `security`, `auth`, `token`, `payment`
   - Or tasks with security keywords in title
   - Comprehensive OWASP Top 10 analysis
   - Auth pattern review
   - Results saved to `security_review_results.json`

3. **Coach Validation (Read-Only)**
   - Coach ONLY reads security results
   - Verifies `task_work_results["security"]["quick_check_passed"]`
   - Does NOT invoke security-specialist agent

## Task Summary (Revised from TASK-REV-4B0F)

| Wave | Task ID | Title | Type | Mode | Complexity | Est. Minutes |
|------|---------|-------|------|------|------------|--------------|
| 1 | TASK-SEC-001 | Add quick security checks (Phase 4.3) | feature | task-work | 5 | 150 |
| 1 | TASK-SEC-002 | Add security configuration schema | feature | task-work | 3 | 90 |
| 2 | TASK-SEC-003 | Implement pre-loop security review via TaskWorkInterface | feature | task-work | 6 | 240 |
| 2 | TASK-SEC-004 | Implement pre-loop tag detection | feature | task-work | 3 | 90 |
| 3 | TASK-SEC-005 | Add security validation tests (revised architecture) | testing | task-work | 5 | 180 |
| 4 | TASK-SEC-006 | Update documentation (revised architecture) | documentation | direct | 2 | 120 |

**Total Estimated Duration**: ~14.5 hours (870 minutes)

## Wave Breakdown (Revised from TASK-REV-4B0F)

### Wave 1: Foundation (Parallel)
- `TASK-SEC-001`: Quick checks implementation for Phase 4.3
- `TASK-SEC-002`: Security configuration schema
- Can run in parallel, no dependencies

### Wave 2: Pre-Loop Integration (Parallel)
- `TASK-SEC-003`: Phase 2.5C security review via TaskWorkInterface
- `TASK-SEC-004`: Detection logic for pre-loop decision
- Depends on Wave 1 completion
- **Key Change**: Security invocation in pre-loop, NOT Coach

### Wave 3: Testing (Sequential)
- `TASK-SEC-005`: Tests for revised architecture
- Tests pre-loop (Phase 2.5C), task-work (Phase 4.3), and Coach (read-only)
- Depends on all Wave 2 tasks

### Wave 4: Documentation (Sequential)
- `TASK-SEC-006`: Documentation reflecting revised architecture
- Includes architecture diagrams showing phase execution
- Documents Coach read-only constraint

## Success Criteria

- [ ] Quick security checks run on all tasks (~30s overhead)
- [ ] Full security review runs on auth-tagged tasks
- [ ] Critical findings block Coach approval
- [ ] High findings generate FEEDBACK (iteration)
- [ ] User can configure security level (strict/standard/minimal/skip)
- [ ] All existing tests continue to pass
- [ ] Documentation updated

## Files Affected (Revised from TASK-REV-4B0F)

### New Files
- `guardkit/orchestrator/quality_gates/security_checker.py` - Quick checks implementation
- `guardkit/orchestrator/quality_gates/security_detection.py` - Tag/keyword detection for pre-loop
- `guardkit/orchestrator/quality_gates/security_review.py` - Full review response parsing
- `docs/guides/security-validation.md` - User guide with revised architecture
- `tests/unit/test_security_checker.py` - Quick checks tests
- `tests/unit/test_security_config.py` - Configuration tests
- `tests/unit/test_security_detection.py` - Detection logic tests (pre-loop)
- `tests/unit/test_security_review.py` - Response parsing tests
- `tests/unit/test_security_filtering.py` - False positive filtering tests
- `tests/integration/test_pre_loop_security.py` - Pre-loop Phase 2.5C tests
- `tests/integration/test_task_work_security.py` - Task-work Phase 4.3 tests
- `tests/integration/test_coach_security.py` - Coach read-only verification tests
- `tests/fixtures/security/vulnerable_code/` - Test fixtures
- `tests/fixtures/security/safe_code/` - Test fixtures

### Modified Files
- `guardkit/orchestrator/quality_gates/__init__.py` - Export security modules
- `guardkit/orchestrator/quality_gates/pre_loop.py` - Add Phase 2.5C security pre-check
- `guardkit/orchestrator/quality_gates/task_work_interface.py` - Add execute_security_review()
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Read-only security verification
- `.claude/agents/autobuild-coach.md` - Clarify Coach reads security results
- `installer/core/commands/feature-build.md` - Document security phases
- `CLAUDE.md` - Add security validation summary

## Key Techniques (from Claude Code Security Review)

- **Substring matching** for simple patterns (10x faster than regex)
- **Path-based filtering** to limit checks to relevant file types
- **10-category vulnerability taxonomy** for comprehensive coverage
- **Confidence scoring** (filter below 0.8) to reduce false positives
- **Hard exclusion categories** (DOS, rate limiting, resource management)
- **Environment variable override** (`GUARDKIT_SECURITY_SKIP`) for CI/CD
