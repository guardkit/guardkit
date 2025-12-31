# Implementation Guide: Coach Security Integration

## Wave Execution Strategy

```
Wave 1 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │  TASK-SEC-001   │    │  TASK-SEC-002   │          │
│  │ Quick Checks    │    │ Config Schema   │          │
│  │ (task-work)     │    │ (task-work)     │          │
│  └─────────────────┘    └─────────────────┘          │
│         │                       │                     │
└─────────┼───────────────────────┼─────────────────────
          │                       │
          ▼                       ▼
Wave 2 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │  TASK-SEC-003   │    │  TASK-SEC-004   │          │
│  │ Full Review     │    │ Tag Detection   │          │
│  │ (task-work)     │    │ (task-work)     │          │
│  └─────────────────┘    └─────────────────┘          │
│         │                       │                     │
└─────────┼───────────────────────┼─────────────────────
          │                       │
          ▼                       ▼
Wave 3 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │  TASK-SEC-005   │───▶│  TASK-SEC-006   │          │
│  │ Tests           │    │ Documentation   │          │
│  │ (task-work)     │    │ (direct)        │          │
│  └─────────────────┘    └─────────────────┘          │
│                                                       │
└───────────────────────────────────────────────────────
```

## Conductor Workspace Names

| Task | Workspace Name |
|------|----------------|
| TASK-SEC-001 | `coach-security-wave1-1` |
| TASK-SEC-002 | `coach-security-wave1-2` |
| TASK-SEC-003 | `coach-security-wave2-1` |
| TASK-SEC-004 | `coach-security-wave2-2` |
| TASK-SEC-005 | `coach-security-wave3-1` |
| TASK-SEC-006 | `coach-security-wave3-2` |

## Wave 1: Quick Checks Foundation

### TASK-SEC-001: Add Quick Security Checks

**Objective**: Implement grep/regex-based security checks that run on all tasks.

**Key Implementation Points**:
```python
# guardkit/orchestrator/quality_gates/security_checker.py

QUICK_SECURITY_CHECKS = [
    {
        "id": "hardcoded-secrets",
        "severity": "critical",
        "pattern": r"(API_KEY|PASSWORD|SECRET|TOKEN)\s*=\s*['\"][^'\"]+['\"]",
        "description": "Hardcoded secret detected",
    },
    {
        "id": "sql-injection",
        "severity": "critical",
        "pattern": r"f['\"]SELECT.*\{",
        "description": "Potential SQL injection (string formatting in query)",
    },
    {
        "id": "cors-wildcard",
        "severity": "high",
        "pattern": r"allow_origins.*\[.*['\"\*'\"].*\]",
        "description": "CORS wildcard configuration",
    },
    {
        "id": "debug-mode",
        "severity": "high",
        "pattern": r"DEBUG\s*=\s*True",
        "description": "Debug mode enabled",
    },
    {
        "id": "command-injection",
        "severity": "critical",
        "pattern": r"(subprocess\.run|os\.system)\s*\([^)]*\{",
        "description": "Potential command injection",
    },
]
```

### TASK-SEC-002: Add Security Configuration Schema

**Objective**: Define configuration schema for security validation.

**Key Implementation Points**:
```yaml
# Task frontmatter schema addition
security:
  level: standard  # strict | standard | minimal | skip
  skip_checks: []  # List of check IDs to skip
  force_full_review: false  # Force full security-specialist review

# Feature YAML schema addition
security:
  default_level: standard
  force_full_review: []  # Task IDs
  skip_review: []  # Task IDs
```

## Wave 2: Full Review Integration

### TASK-SEC-003: Implement Security-Specialist Invocation

**Objective**: Add ability to invoke security-specialist agent for comprehensive review.

**Key Implementation Points**:
```python
async def invoke_security_specialist(
    worktree_path: Path,
    task: dict,
    timeout: int = 300
) -> SecurityReviewResult:
    """Invoke security-specialist agent for comprehensive review."""

    # Build prompt with task context
    prompt = f"""
    Perform comprehensive security review of implementation in:
    {worktree_path}

    Task: {task.get('title')}
    Tags: {task.get('tags', [])}

    Focus on:
    - OWASP Top 10 vulnerabilities
    - Authentication/authorization patterns
    - Secret handling
    - Input validation completeness
    - API security
    - Token/session management

    Return structured findings as JSON with:
    - severity: critical | high | medium | low | info
    - category: owasp-category or custom
    - description: detailed description
    - location: file:line if applicable
    - recommendation: fix guidance
    """

    # Invoke via Task tool
    result = await invoke_task(
        subagent_type="security-specialist",
        description=f"Security review for {task.get('id')}",
        prompt=prompt
    )

    return parse_security_findings(result)
```

### TASK-SEC-004: Implement Task Tagging Detection

**Objective**: Determine when full security review should run.

**Key Implementation Points**:
```python
SECURITY_TAGS = {
    "authentication", "authorization", "security", "auth",
    "session", "token", "payment", "crypto", "encryption"
}

SECURITY_KEYWORDS = [
    "login", "password", "jwt", "oauth", "api_key", "secret",
    "credential", "permission", "access", "role"
]

def should_run_full_review(task: dict, config: SecurityConfig) -> bool:
    """Determine if task requires full security-specialist review."""

    # Check explicit configuration
    if config.force_full_review:
        return True
    if config.level == "skip":
        return False
    if config.level == "strict":
        return True

    # Check task tags
    task_tags = set(tag.lower() for tag in task.get("tags", []))
    if task_tags & SECURITY_TAGS:
        return True

    # Check task title for keywords
    title = task.get("title", "").lower()
    if any(kw in title for kw in SECURITY_KEYWORDS):
        return True

    # Check task description for keywords
    desc = task.get("requirements", "").lower()
    keyword_count = sum(1 for kw in SECURITY_KEYWORDS if kw in desc)
    if keyword_count >= 2:  # Multiple security keywords
        return True

    return False
```

## Wave 3: Testing & Documentation

### TASK-SEC-005: Add Security Validation Tests

**Objective**: Comprehensive test coverage for security features.

**Test Categories**:
1. Quick check detection tests
2. Full review triggering logic tests
3. Configuration parsing tests
4. Integration tests with Coach validator
5. Edge case handling

### TASK-SEC-006: Update Coach Agent Documentation

**Objective**: Update documentation with security validation details.

**Files to Update**:
- `.claude/agents/autobuild-coach.md` - Add security validation section
- `installer/core/commands/feature-build.md` - Document security options
- `CLAUDE.md` - Add security configuration reference

## Integration with Coach Validator

```python
# In coach_validator.py validate() method

def validate(self, task_id: str, turn: int, task: dict) -> CoachValidationResult:
    # ... existing validation ...

    # NEW: Security validation
    security_config = self._load_security_config(task)

    if security_config.level != "skip":
        # Always run quick checks
        quick_findings = self.run_quick_security_checks()

        critical = [f for f in quick_findings if f.severity == "critical"]
        if critical:
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                issues=[{
                    "severity": "must_fix",
                    "category": "security",
                    "description": "Critical security issues detected",
                    "findings": [f.to_dict() for f in critical]
                }],
                rationale="Critical security vulnerabilities must be fixed"
            )

        # Conditionally run full review
        if should_run_full_review(task, security_config):
            full_findings = await self.invoke_security_specialist(task)

            blocking = [f for f in full_findings
                       if f.severity in ["critical", "high"]]
            if blocking:
                return self._feedback_result(
                    task_id=task_id,
                    turn=turn,
                    issues=[{
                        "severity": "must_fix",
                        "category": "security",
                        "description": "Security issues require attention",
                        "findings": [f.to_dict() for f in blocking]
                    }],
                    rationale="Security review identified issues"
                )

    # Continue with existing validation...
```

## Rollout Strategy

1. **Phase 1**: Implement behind feature flag (`GUARDKIT_SECURITY_VALIDATION=true`)
2. **Phase 2**: Enable quick checks by default, full review opt-in
3. **Phase 3**: Enable full review for tagged tasks by default
4. **Phase 4**: Remove feature flag, full functionality default
