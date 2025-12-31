---
id: TASK-REV-SEC1
title: Evaluate Coach Agent Security Specialist Integration
status: review_complete
created: 2025-12-31T12:00:00Z
updated: 2025-12-31T14:30:00Z
priority: high
task_type: review
tags: [security, feature-build, coach-agent, autobuild, quality-gates]
complexity: 6
decision_required: true
review_results:
  mode: architectural
  depth: standard
  overall_score: 85
  findings_count: 5
  recommendations_count: 6
  recommended_approach: "Option C (Hybrid)"
  report_path: .claude/reviews/TASK-REV-SEC1-review-report.md
  completed_at: 2025-12-31T14:30:00Z
  decision: implement
  decision_timestamp: 2025-12-31T15:00:00Z
  implementation_tasks:
    - TASK-SEC-001
    - TASK-SEC-002
    - TASK-SEC-003
    - TASK-SEC-004
    - TASK-SEC-005
    - TASK-SEC-006
  implementation_path: tasks/backlog/coach-security-integration/
---

# Review Task: Evaluate Coach Agent Security Specialist Integration

## Description

Evaluate the proposal to enhance the Coach agent in the `/feature-build` command workflow to invoke a security specialist agent for automated security reviews. This would integrate security validation directly into the Player-Coach adversarial loop, catching security issues during autonomous implementation rather than requiring separate post-implementation security reviews.

## Background & Context

### The Problem

After implementing FastAPI-Python infrastructure using `/feature-build`, subsequent security reviews (both manual `/task-review --mode=security` and Claude Code's built-in security review) identified significant security deficiencies:

1. **Timing Attack in Password Verification** (MEDIUM) - User enumeration through observable timing differences
2. **Missing JWT Token Revocation** (MEDIUM) - Stolen tokens remain valid until expiration
3. **CORS Wildcard Configuration** (HIGH) - Security anti-pattern allowing credential-bearing requests from any origin
4. **SECRET_KEY Handling Issues** (HIGH) - Predictable/guessable keys in configuration
5. **Missing Rate Limiting Tests** (MEDIUM) - Rate limiting configured but not verified
6. **No Structured Security Logging** (MEDIUM) - Insufficient logging for incident response

### The Observation

The current Coach agent validates:
- ✅ Acceptance criteria met
- ✅ Syntax correctness
- ✅ File structure
- ✅ Test execution (when configured)

But it does NOT validate:
- ❌ Security patterns (OWASP Top 10)
- ❌ Authentication/authorization best practices
- ❌ Secret handling
- ❌ Input validation completeness
- ❌ Rate limiting implementation
- ❌ Token security

### The Proposal

Enhance the Coach agent to invoke `security-specialist` agent during validation, particularly for:
- Authentication implementations
- API endpoints
- Configuration files
- Token/session management
- Database query patterns

## Review Scope

### Primary Questions to Answer

1. **Feasibility**: Can the security-specialist agent be effectively integrated into the Coach workflow without significant performance impact?

2. **Scope Definition**: What security checks should be mandatory vs. optional?
   - Always run: OWASP Top 10 patterns, secret detection
   - Conditionally run: Full security audit for auth/security-tagged tasks
   - Skip: Tasks tagged with `security:skip` or low-risk UI-only changes

3. **Iteration Triggers**: Should security findings trigger Coach FEEDBACK (iteration) or just warnings?
   - Critical (block): Hard-coded secrets, SQL injection, command injection
   - High (feedback): CORS wildcards, missing rate limiting, weak crypto
   - Medium (warn): Missing security headers, excessive permissions
   - Low (note): Best practice suggestions

4. **Integration Architecture**: How should the Coach invoke security-specialist?
   - Option A: Full security-specialist agent invocation (comprehensive, slower)
   - Option B: Security checklist within Coach prompt (faster, less thorough)
   - Option C: Hybrid - quick checks in Coach, full agent for security-tagged tasks

5. **Configuration**: How should users control security strictness?
   - `autobuild.security_level: strict|standard|minimal|skip`
   - Task-level overrides via tags

### Secondary Considerations

6. **Performance Impact**: How much additional time would security validation add?
   - Estimate: 30-60 seconds per task for quick checks
   - Estimate: 2-5 minutes per task for comprehensive checks

7. **False Positive Handling**: How to handle security findings that are intentional design decisions?

8. **AI-Hater Concern**: This addresses the legitimate criticism that AI-generated code often lacks security awareness

## Reference Materials

### Evidence of Security Gaps

1. **TASK-REV-FB01 Execution Analysis**: [.claude/reviews/TASK-REV-FB01-execution-analysis.md](.claude/reviews/TASK-REV-FB01-execution-analysis.md)
   - Lines 465-467: "Not recommended for... High-risk security-critical implementations"
   - This is a limitation, not a feature

2. **Security Review of FastAPI Auth**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/fastapi-auth/.claude/reviews/TASK-3665-security-review.md`
   - 2 MEDIUM severity vulnerabilities found post-implementation
   - Timing attack and JWT revocation issues

3. **Comprehensive Security Audit**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/fastapi-auth/.claude/reviews/TASK-REV-A7B2-review-report_security.md`
   - Overall score: 84/100
   - 2 CRITICAL (P0), 4 HIGH (P1), 4 MEDIUM (P2) findings
   - CORS misconfiguration and SECRET_KEY handling flagged as deployment blockers

### Existing Security Agent

- **security-specialist**: `installer/core/agents/security-specialist.md`
  - Already exists in GuardKit
  - Covers: Application security, threat modeling, OWASP Top 10, compliance
  - Has structured output format for findings

## Acceptance Criteria

### For the Review

- [ ] Assess technical feasibility of Coach/security-specialist integration
- [ ] Recommend integration architecture (Option A, B, or C)
- [ ] Define security check categorization (critical/high/medium/low)
- [ ] Propose configuration schema for security strictness
- [ ] Estimate performance impact
- [ ] Identify implementation tasks if approved

### Decision Options

1. **[A]pprove** - Proceed with security integration implementation
2. **[R]evise** - Request deeper analysis on specific aspects
3. **[I]mplement** - Create implementation tasks from recommendations
4. **[D]efer** - Valid concept but lower priority than other enhancements
5. **[C]ancel** - Reject proposal (with justification)

## Notes

This proposal directly addresses the common criticism that AI-generated code lacks security awareness. By building security validation into the autonomous implementation workflow, GuardKit could differentiate itself as a tool that produces secure code by default, not as an afterthought.

The evidence from the FastAPI authentication implementation shows that even well-structured code with good patterns (Argon2, rate limiting, Pydantic validation) can have security gaps (timing attacks, missing revocation, CORS issues) that only a focused security review catches.

---

*Created from user request to evaluate Coach agent security integration*
*Reference: Feature-build security review findings*
