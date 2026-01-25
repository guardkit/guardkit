# Review Report: TASK-REV-SEC1

## Evaluate Coach Agent Security Specialist Integration

**Review Mode**: Architectural
**Review Depth**: Standard
**Date**: 2025-12-31
**Reviewer**: Architectural Review Agent

---

## Executive Summary

This architectural review evaluates the proposal to integrate security validation into the Coach agent within the `/feature-build` command workflow. The analysis confirms that security integration is **technically feasible and architecturally sound**, with Option C (Hybrid) emerging as the recommended approach.

| Category | Score | Assessment |
|----------|-------|------------|
| Technical Feasibility | 9/10 | Excellent - Clean integration points exist |
| Architectural Alignment | 8/10 | Strong - Follows existing patterns |
| Risk/Benefit Ratio | 8.5/10 | High benefit, manageable risk |
| Implementation Complexity | Medium | 3-5 tasks over 2-3 waves |
| **Overall Recommendation** | **APPROVE** | Proceed with Option C (Hybrid) |

---

## 1. Current State Analysis

### 1.1 Coach Agent Architecture

The current Coach agent ([autobuild-coach.md](.claude/agents/autobuild-coach.md)) implements a **lightweight validation-focused** design:

**Current Validation Scope**:
- Read task-work quality gate results from `task_work_results.json`
- Verify tests passed (`test_results.all_passed`)
- Verify architectural review score (>= 60)
- Verify plan audit (0 violations)
- Run independent test verification (trust but verify)
- Validate acceptance criteria

**Current Coach Boundaries**:
```
ALWAYS:
  - Read task-work results
  - Verify quality gates passed
  - Run tests independently
  - Check acceptance criteria
  - Provide actionable feedback

NEVER:
  - Reimplement quality gates
  - Write or modify code
  - Approve code with security vulnerabilities  <-- ALREADY STATED
  - Skip independent test verification
```

**Key Observation**: The Coach ALREADY has "Never approve code with security vulnerabilities" in its boundaries, but **lacks the tooling to detect them**.

### 1.2 Security-Specialist Agent Capabilities

The existing `security-specialist` agent ([security-specialist.md](installer/core/agents/security-specialist.md)) provides comprehensive security expertise:

**Core Capabilities**:
- OWASP Top 10 mitigation
- Input validation/sanitization patterns
- Authentication/authorization best practices
- Session/token management
- Secret detection
- SQL injection/XSS protection
- CORS configuration review
- Infrastructure security scanning

**Key Strength**: The security-specialist already has detailed examples for FastAPI, React, and infrastructure patterns - exactly matching the types of implementations `/feature-build` produces.

### 1.3 Evidence of Security Gap

From the task background, the FastAPI authentication implementation by `/feature-build` had:

| Issue | Severity | Coach Detection? |
|-------|----------|------------------|
| Timing Attack in Password Verification | MEDIUM | Could NOT detect |
| Missing JWT Token Revocation | MEDIUM | Could NOT detect |
| CORS Wildcard Configuration | HIGH | Could NOT detect |
| SECRET_KEY Handling Issues | HIGH | Could NOT detect |
| Missing Rate Limiting Tests | MEDIUM | Could NOT detect |
| No Structured Security Logging | MEDIUM | Could NOT detect |

**Conclusion**: The current Coach validates functional correctness but is blind to security patterns.

---

## 2. Integration Architecture Options

### Option A: Full Security-Specialist Agent Invocation

**Description**: Coach invokes security-specialist as a full subagent for every task.

**Implementation**:
```python
# In Coach validation flow
def validate_security(task_id: str, worktree_path: Path):
    # Invoke full security-specialist agent
    result = invoke_task(
        subagent_type="security-specialist",
        prompt=f"""
        Perform comprehensive security review of implementation in:
        {worktree_path}

        Focus on:
        - OWASP Top 10 vulnerabilities
        - Authentication/authorization patterns
        - Secret handling
        - Input validation
        - API security

        Return structured findings with severity levels.
        """
    )
    return parse_security_findings(result)
```

**Pros**:
- Maximum coverage (comprehensive security review)
- Leverages full security-specialist expertise
- Catches edge cases and subtle vulnerabilities

**Cons**:
- **Performance impact: 2-5 minutes per task** (significant for multi-task features)
- Token cost: ~8,000-15,000 tokens per invocation
- Overkill for simple tasks (UI components, utilities)

**Best For**: Security-critical tasks (authentication, authorization, payment processing)

### Option B: Security Checklist Within Coach Prompt

**Description**: Embed a security checklist directly in the Coach agent prompt.

**Implementation**:
```markdown
# In autobuild-coach.md

## Security Validation Checklist

Before approving, verify:
- [ ] No hardcoded secrets (grep for API_KEY, PASSWORD, SECRET)
- [ ] No SQL string concatenation (parameterized queries only)
- [ ] CORS not set to "*" (check allow_origins)
- [ ] Rate limiting implemented for auth endpoints
- [ ] Input validation on all user inputs
- [ ] No sensitive data in error messages
- [ ] HTTPS enforced for sensitive operations
```

**Pros**:
- **Zero performance impact** (runs within existing Coach context)
- Simple implementation (prompt modification only)
- Fast iteration on checklist items

**Cons**:
- Limited depth (checklist vs. comprehensive analysis)
- Misses subtle vulnerabilities (timing attacks, complex injection patterns)
- No specialized security reasoning

**Best For**: Quick sanity checks, low-risk tasks

### Option C: Hybrid Approach (Recommended)

**Description**: Quick security checks by default + full security-specialist for security-tagged tasks.

**Implementation**:
```python
# In Coach validation flow
def validate_security(task: dict, worktree_path: Path):
    # Step 1: Quick checks (always run, ~30 seconds)
    quick_findings = run_quick_security_checks(worktree_path)

    critical_quick = [f for f in quick_findings if f.severity == "critical"]
    if critical_quick:
        return SecurityResult.BLOCK, critical_quick

    # Step 2: Full review if security-tagged or auth implementation
    if should_run_full_review(task):
        full_findings = invoke_security_specialist(worktree_path)
        high_or_above = [f for f in full_findings if f.severity in ["critical", "high"]]
        if high_or_above:
            return SecurityResult.FEEDBACK, full_findings

    return SecurityResult.PASS, quick_findings
```

**Task Tagging Logic**:
```python
def should_run_full_review(task: dict) -> bool:
    # Always run full review for these tags
    security_tags = {"authentication", "authorization", "security",
                     "auth", "session", "token", "payment", "crypto"}

    task_tags = set(task.get("tags", []))
    if task_tags & security_tags:
        return True

    # Check if task implements auth patterns
    keywords = ["login", "password", "jwt", "oauth", "api_key", "secret"]
    title = task.get("title", "").lower()
    if any(kw in title for kw in keywords):
        return True

    return False
```

**Pros**:
- **Balanced performance**: 30 seconds default, 2-5 minutes for security tasks
- Catches critical issues quickly (secrets, SQL injection)
- Deep analysis only when needed
- User control via tags and configuration

**Cons**:
- More complex implementation (two-tier system)
- Requires clear categorization of quick vs. full checks

**Best For**: Production use - right level of security for task type

---

## 3. Security Check Categorization

### 3.1 Quick Checks (Always Run, ~30 seconds)

| Check | Category | Detection Method |
|-------|----------|------------------|
| Hardcoded secrets | Critical | Regex: `API_KEY=`, `PASSWORD=`, `SECRET=` |
| SQL string concatenation | Critical | Regex: `f"SELECT.*{` |
| Command injection | Critical | Regex: `subprocess.run(.*{`, `os.system(.*{` |
| CORS wildcard | High | Regex: `allow_origins.*\["?\*"\]` |
| Debug mode enabled | High | Regex: `DEBUG.*=.*True` |
| Eval/exec usage | High | AST: `eval(`, `exec(` |

**Implementation**: These can be implemented as Bash grep/regex commands, no subagent needed.

### 3.2 Full Review Checks (Security-Tagged Tasks)

| Check | Category | Requires Reasoning |
|-------|----------|-------------------|
| Timing attack patterns | Medium | Yes - constant-time comparison analysis |
| Token revocation logic | Medium | Yes - JWT lifecycle analysis |
| Rate limiting completeness | Medium | Yes - endpoint coverage analysis |
| Input validation gaps | High | Yes - data flow analysis |
| AuthZ bypass patterns | High | Yes - permission logic review |
| OWASP Top 10 | Varies | Yes - comprehensive patterns |

**Implementation**: Requires security-specialist agent's reasoning capabilities.

### 3.3 Iteration Trigger Severity

| Severity | Coach Response | Example |
|----------|----------------|---------|
| **Critical** | BLOCK | Hardcoded API key in code |
| **High** | FEEDBACK | CORS wildcard with credentials |
| **Medium** | FEEDBACK | Missing rate limiting on auth |
| **Low** | WARN (approve) | Missing security headers (non-auth) |
| **Info** | NOTE (approve) | Best practice suggestion |

---

## 4. Performance Impact Assessment

### 4.1 Quick Checks (Option B/C Baseline)

| Metric | Value |
|--------|-------|
| Duration | 15-30 seconds |
| Token Cost | ~500 tokens (grep commands) |
| Impact on /feature-build | Minimal (+30s per task) |

### 4.2 Full Security Review (Option A/C Security Tasks)

| Metric | Value |
|--------|-------|
| Duration | 2-5 minutes |
| Token Cost | 8,000-15,000 tokens |
| Impact on /feature-build | Significant (+2-5 min per task) |

### 4.3 Projected Impact by Task Type

**Standard Feature Build (12 tasks across 4 waves)**:

| Scenario | Option A | Option B | Option C |
|----------|----------|----------|----------|
| All tasks (worst case) | +24-60 min | +6 min | +6 min + 2-5 min (for 1-2 auth tasks) |
| Auth tasks only | +4-10 min | +1 min | +4-10 min |
| **Total overhead** | +24-60 min | +6 min | +8-16 min |

**Recommendation**: Option C provides the best balance - comprehensive security for auth tasks, quick checks for everything else.

---

## 5. Configuration Schema

### 5.1 Task-Level Configuration

```yaml
# In task frontmatter
---
id: TASK-AUTH-001
title: Implement OAuth2 authentication
tags: [authentication, security]  # Triggers full security review
security:
  level: strict  # Override default
  skip_checks: []  # No skipped checks
---
```

### 5.2 Feature-Level Configuration

```yaml
# In .guardkit/features/FEAT-XXX.yaml
security:
  default_level: standard  # standard | strict | minimal | skip
  force_full_review: [TASK-AUTH-001, TASK-AUTH-002]  # Always full review
  skip_review: [TASK-UI-001]  # Skip security review (UI only)
```

### 5.3 Global Configuration

```yaml
# In .guardkit/config.yaml or autobuild section
autobuild:
  security:
    enabled: true
    default_level: standard
    quick_check_timeout: 30  # seconds
    full_review_timeout: 300  # seconds
    block_on_critical: true  # Block vs feedback
    security_agent_model: claude-sonnet-4-5-20250929
```

### 5.4 Security Levels

| Level | Quick Checks | Full Review | Block Severity |
|-------|--------------|-------------|----------------|
| **strict** | Always | Always | High+ |
| **standard** | Always | Tagged tasks only | Critical |
| **minimal** | Always | Never | Critical |
| **skip** | Never | Never | Never |

---

## 6. Implementation Recommendations

### 6.1 Recommended Approach: Option C (Hybrid)

**Why Option C?**

1. **Right-sized security**: Full review for auth tasks, quick checks for others
2. **Performance acceptable**: +8-16 min for 12-task feature (vs. +24-60 min for Option A)
3. **User control**: Tags and configuration allow customization
4. **Incremental adoption**: Can start with quick checks, add full review later

### 6.2 Implementation Tasks

**Wave 1: Quick Checks Integration**
1. **TASK-SEC-001**: Add quick security checks to Coach agent
   - Implement grep/regex checks for critical/high issues
   - Add to Coach validation flow before approval
   - ~2-3 hours

2. **TASK-SEC-002**: Add security configuration schema
   - Add `security` section to task frontmatter schema
   - Add `security` section to feature YAML schema
   - ~1-2 hours

**Wave 2: Full Review Integration**
3. **TASK-SEC-003**: Implement security-specialist invocation
   - Create `invoke_security_specialist()` function
   - Parse and categorize findings
   - ~3-4 hours

4. **TASK-SEC-004**: Implement task tagging detection
   - `should_run_full_review()` logic
   - Keyword and tag-based detection
   - ~1-2 hours

**Wave 3: Testing & Documentation**
5. **TASK-SEC-005**: Add security validation tests
   - Test quick checks detection
   - Test full review triggering
   - Test configuration options
   - ~2-3 hours

6. **TASK-SEC-006**: Update Coach agent documentation
   - Update autobuild-coach.md with security validation
   - Document configuration options
   - ~1-2 hours

**Total Estimated Effort**: 10-16 hours (2-3 days)

### 6.3 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| False positives | Start with high-confidence checks only |
| Performance regression | Measure and monitor execution time |
| User friction | Provide clear override mechanisms |
| Breaking existing workflows | Feature flag for gradual rollout |

---

## 7. SOLID/DRY/YAGNI Assessment

### 7.1 SOLID Compliance

| Principle | Score | Assessment |
|-----------|-------|------------|
| **Single Responsibility** | 9/10 | Security validation is a distinct concern, properly separated |
| **Open/Closed** | 8/10 | New checks can be added without modifying core Coach logic |
| **Liskov Substitution** | N/A | No inheritance hierarchy |
| **Interface Segregation** | 8/10 | Clear interfaces between Coach, quick checks, and full review |
| **Dependency Inversion** | 8/10 | Security-specialist invoked via abstract Task tool interface |

### 7.2 DRY Adherence

| Area | Score | Notes |
|------|-------|-------|
| Check definitions | 9/10 | Centralized in security check registry |
| Configuration | 8/10 | Single schema, multiple levels |
| Agent invocation | 9/10 | Reuses existing Task tool patterns |

### 7.3 YAGNI Compliance

| Proposed Feature | YAGNI Score | Recommendation |
|------------------|-------------|----------------|
| Quick checks | 10/10 | Essential - addresses known gaps |
| Full review for auth | 10/10 | Essential - high-risk area |
| Configuration levels | 8/10 | Needed for flexibility |
| Skip option | 7/10 | Keep for edge cases |
| Custom check definitions | 5/10 | Defer - not immediately needed |

---

## 8. Findings Summary

### 8.1 Key Findings

1. **Gap Confirmed**: Current Coach cannot detect security vulnerabilities despite stating "Never approve code with security vulnerabilities"

2. **Integration Feasible**: Clean integration points exist between Coach validation flow and security-specialist agent

3. **Option C Optimal**: Hybrid approach balances security coverage with performance

4. **Existing Assets**: security-specialist agent already has comprehensive patterns for FastAPI, React, and infrastructure

5. **Configuration Needed**: Task-level and global configuration enables user control

### 8.2 Recommendations

| # | Recommendation | Priority |
|---|----------------|----------|
| 1 | Implement Option C (Hybrid) architecture | High |
| 2 | Start with quick checks (Wave 1) | High |
| 3 | Add full review for security-tagged tasks (Wave 2) | High |
| 4 | Provide feature flag for gradual rollout | Medium |
| 5 | Document security check coverage | Medium |
| 6 | Consider CI/CD integration for security scanning | Low |

---

## 9. Decision Checkpoint

**Review Status**: REVIEW_COMPLETE

**Overall Assessment**: The proposal to integrate security validation into the Coach agent is **technically sound and architecturally aligned** with GuardKit's quality-first principles. Option C (Hybrid) provides the best balance of security coverage and performance.

### Decision Options

| Option | Description |
|--------|-------------|
| **[A]ccept** | Approve findings, archive review (no implementation) |
| **[R]evise** | Request deeper analysis (specify areas) |
| **[I]mplement** | Create implementation tasks from recommendations |
| **[D]efer** | Valid concept but lower priority |
| **[C]ancel** | Reject proposal |

### Recommendation: **[I]mplement**

The security integration directly addresses a critical gap in the autonomous implementation workflow. The evidence from FastAPI authentication implementation shows real security issues that would have been caught with this integration.

**Implementation would create 6 subtasks organized in 3 waves** (see Section 6.2).

---

*Generated by GuardKit Task Review*
*Review Mode: Architectural*
*Depth: Standard*
*Task: TASK-REV-SEC1*
