# Security Validation Guide

## Overview

GuardKit's AutoBuild workflow includes automatic security validation to catch vulnerabilities during autonomous implementation.

## Architecture

**[From TASK-REV-4B0F]** Security validation runs at specific phases:

```
Pre-Loop Quality Gates
    |
    +-- Phase 2.5A: Pattern Suggestions
    +-- Phase 2.5B: Architectural Review
    +-- Phase 2.5C: Security Pre-Check (NEW)
    |       +-- IF security-tagged: Invoke security-specialist
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

**Key Principle**: Coach is READ-ONLY. Security checks run in pre-loop and task-work, not Coach.

## How It Works

### Two-Tier Security

1. **Quick Checks** (Always, ~30s) - Phase 4.3
   - Run on every task in task-work
   - Detect critical issues via regex
   - Block on: hardcoded secrets, injection patterns

2. **Full Review** (Conditional, ~2-5min) - Phase 2.5C
   - Run on security-tagged tasks in pre-loop
   - Uses security-specialist agent via TaskWorkInterface
   - Comprehensive OWASP analysis

### Security Levels

| Level | Description |
|-------|-------------|
| `strict` | Full review on all tasks |
| `standard` | Quick checks + tagged review |
| `minimal` | Quick checks only |
| `skip` | No security validation |

### Triggering Full Review

Full review runs in **pre-loop** when:
- Task has security tags: `authentication`, `auth`, `security`, `token`, `payment`
- Task title contains: `login`, `password`, `jwt`, `oauth`
- Configuration: `security.force_full_review: true`
- Level: `strict`

### Configuration Examples

**Task-level (strictest)**:
```yaml
security:
  level: strict
  force_full_review: true
```

**Feature-level**:
```yaml
security:
  default_level: standard
  force_full_review: [TASK-AUTH-001, TASK-AUTH-002]
  skip_review: [TASK-UI-001]
```

**Global**:
```yaml
# .guardkit/config.yaml
autobuild:
  security:
    enabled: true
    default_level: standard
```

### Quick Checks Reference

| Check | Severity | Pattern |
|-------|----------|---------|
| Hardcoded secrets | Critical | `API_KEY = "..."` |
| SQL injection | Critical | `f"SELECT {var}"` |
| Command injection | Critical | `subprocess.run(f"...")` |
| CORS wildcard | High | `allow_origins=["*"]` |
| Debug mode | High | `DEBUG = True` |
| Eval/exec | High | `eval(...)` |

### Skipping Checks

Skip specific checks:
```yaml
security:
  skip_checks: [debug-mode, cors-wildcard]
```

Or use inline comments:
```python
DEBUG = True  # nosec - only enabled in test environment
```

### Troubleshooting

**False Positive**: Add to `skip_checks` or use `# nosec` comment

**Performance**: Use `minimal` level for UI-only tasks

**Missing Detection**: Upgrade to `strict` level

### Excluded Finding Types

[From TASK-REV-SEC2] The following finding types are automatically excluded as low-value:
- Denial of Service / resource exhaustion
- Rate limiting recommendations
- Memory leaks / resource management
- Open redirect vulnerabilities
- Findings in documentation files (*.md)

### Confidence Scoring

[From TASK-REV-SEC2] Security findings include a confidence score (0.0-1.0).
Only findings with confidence >= 0.8 are reported.

This ensures high signal-to-noise ratio and reduces false positives in automated workflows.

## Integration with AutoBuild

### Phase Execution

1. **Pre-Loop (Phase 2.5C)**: Full security review for tagged tasks
   - Runs BEFORE Player implementation
   - Uses security-specialist agent
   - Results saved to `security_review_results.json`
   - Blocks task if critical vulnerabilities found

2. **Task-Work (Phase 4.3)**: Quick security scan for all tasks
   - Runs AFTER tests pass (Phase 4)
   - Runs BEFORE test enforcement (Phase 4.5)
   - Results written to `task_work_results.json["security"]`
   - Lightweight regex-based checks

3. **Coach Validation**: Reads security results
   - Coach ONLY reads `task_work_results.json["security"]`
   - Coach does NOT invoke security-specialist agent
   - Coach has tools [Read, Bash, Grep, Glob] - NO Task tool
   - Security gate: `security.quick_check_passed == true && security.critical_count == 0`

### Coach Security Gate Logic

```python
# Coach only READS, never invokes
security = task_work_results.get("security", {})
security_passed = security.get("quick_check_passed", True) and \
                  security.get("critical_count", 0) == 0

if not security_passed:
    return feedback("Security checks failed")
```

### Security Results Format

```json
{
  "security": {
    "quick_check_passed": true,
    "findings_count": 0,
    "critical_count": 0,
    "high_count": 0,
    "findings": []
  }
}
```

## Best Practices

1. **Tag Security Tasks**: Use tags like `authentication`, `auth`, `security` to trigger full review
2. **Use Standard Level**: Default to `standard` level for balanced security and performance
3. **Skip UI Tasks**: Use `minimal` or `skip` for pure UI tasks with no backend logic
4. **Review Findings**: Always review security findings before suppressing
5. **Document Suppressions**: Add comments explaining why checks are skipped

## Example Workflows

### High-Security Task

```yaml
---
id: TASK-AUTH-001
title: "Implement JWT authentication"
tags: [authentication, security, jwt]
security:
  level: strict
  force_full_review: true
acceptance_criteria:
  - JWT tokens generated securely
  - Token expiry enforced
  - Refresh token rotation implemented
---
```

**Result**:
- Phase 2.5C: Full security review runs in pre-loop
- Phase 4.3: Quick checks run after tests
- Coach: Reads security results and validates

### Low-Risk UI Task

```yaml
---
id: TASK-UI-001
title: "Update button colors"
tags: [ui, frontend]
security:
  level: minimal
acceptance_criteria:
  - Button colors match design system
---
```

**Result**:
- Phase 2.5C: No full review (not tagged)
- Phase 4.3: Quick checks run (minimal level)
- Coach: Reads security results (likely all pass)

## Reference

**Related Documentation**:
- [AutoBuild Workflow](autobuild-workflow.md)
- [Feature Build Command](../../installer/core/commands/feature-build.md)
- [Coach Agent Specification](../../.claude/agents/autobuild-coach.md)

**Source Code**:
- Security Checker: `guardkit/security/security_checker.py`
- Task Work Interface: `guardkit/orchestrator/task_work_interface.py`
- Coach Validator: `guardkit/orchestrator/quality_gates/coach_validator.py`

**Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review)**:
- Excluded finding types (DOS, rate limiting, resource management)
- Confidence threshold (0.8) for findings
- Read-only Coach architecture for security validation
