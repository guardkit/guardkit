---
acceptance_criteria:
- SECURITY_TAGS set defined with 25+ tags aligned with 10-category taxonomy
- SECURITY_KEYWORDS list defined with 25+ keywords
- HIGH_RISK_CATEGORIES set defined for always-trigger tags
- should_run_full_review() function implemented in security_detection.py
- Function called from pre_loop.py (NOT Coach)
- Configuration precedence correct (force > level > tags > keywords)
- Case-insensitive matching
- Keyword density threshold for descriptions
- Unit tests for each detection path
- Edge case handling for empty tags and empty title
- Tags aligned with Claude Code 10-category taxonomy
complexity: 3
conductor_workspace: coach-security-wave2-2
created: 2026-01-24 15:00:00+00:00
dependencies:
- TASK-SEC-001
- TASK-SEC-002
estimated_minutes: 90
feature_id: FEAT-SEC
id: TASK-SEC-004
implementation_mode: task-work
parent_review: TASK-REV-SEC1
priority: high
status: in_review
tags:
- security
- pre-loop
- detection
- autobuild
task_type: feature
title: Implement pre-loop security tag detection
updated: 2026-01-24 17:00:00+00:00
wave: 2
---

# TASK-SEC-004: Implement Pre-Loop Security Tag Detection

## Description

**REVISED ARCHITECTURE (from TASK-REV-4B0F)**: Tag detection was originally designed to run in Coach, but this is part of the decision logic that determines whether to run full security review. Since full security review runs in pre-loop (Phase 2.5C), tag detection must also run in pre-loop.

Implement the logic to determine when a task requires full security-specialist review based on tags, keywords, and configuration. This gates when the more expensive full review runs in **pre-loop**, not Coach.

## Requirements

1. Define security-related tags set
2. Define security-related keywords list
3. Implement `should_run_full_review()` function
4. Check explicit configuration first
5. Check task tags
6. Check task title and description for keywords

## Detection Logic

### Security Tags

```python
# [From TASK-REV-SEC2] Aligned with Claude Code 10-category taxonomy
SECURITY_TAGS = {
    # Category: Injection Attacks
    "injection", "sql", "command", "ldap", "xpath", "xxe",
    # Category: Authentication & Authorization
    "authentication", "authorization", "security", "auth",
    "session", "token", "jwt", "oauth", "oauth2",
    "rbac", "acl", "permissions", "roles",
    # Category: Data Exposure
    "secrets", "credentials", "pii", "gdpr",
    # Category: Cryptography
    "crypto", "encryption", "hashing",
    # Category: Input Validation
    "validation", "input", "sanitization",
    # Category: Configuration Security
    "cors", "csrf", "headers",
    # Category: Code Execution
    "deserialization", "pickle",
    # Category: XSS
    "xss",
    # Sensitive operations
    "payment", "checkout", "billing",
}

# [From TASK-REV-SEC2] High-risk categories always trigger full review
HIGH_RISK_CATEGORIES = {
    "authentication", "authorization", "auth",
    "injection", "sql", "command",
    "crypto", "encryption",
    "secrets", "credentials",
}
```

### Security Keywords

```python
SECURITY_KEYWORDS = [
    # Authentication
    "login", "logout", "signup", "signin", "password", "credential",
    # Authorization
    "permission", "access", "role", "privilege", "admin",
    # Tokens
    "jwt", "token", "refresh", "bearer", "api_key", "apikey",
    # Secrets
    "secret", "key", "certificate", "private",
    # Security features
    "rate_limit", "rate-limit", "throttle", "cors", "csrf",
    # Sensitive data
    "pii", "gdpr", "encrypt", "decrypt", "hash",
]
```

### Detection Function

```python
def should_run_full_review(task: dict, config: SecurityConfig) -> bool:
    """
    Determine if task requires full security-specialist review.

    Priority:
    1. Explicit configuration (force or skip)
    2. Security level (strict always, skip never)
    3. Task tags
    4. Task title keywords
    5. Task description keyword density

    Args:
        task: Task dictionary
        config: Security configuration

    Returns:
        True if full review should run
    """
    # 1. Check explicit force/skip
    if config.force_full_review:
        return True

    # 2. Check security level
    if config.level == SecurityLevel.SKIP:
        return False
    if config.level == SecurityLevel.MINIMAL:
        return False
    if config.level == SecurityLevel.STRICT:
        return True

    # 3. Check task tags
    task_tags = {tag.lower() for tag in task.get("tags", [])}
    if task_tags & SECURITY_TAGS:
        return True

    # 4. Check task title
    title = task.get("title", "").lower()
    if any(kw in title for kw in SECURITY_KEYWORDS):
        return True

    # 5. Check description keyword density
    desc = task.get("requirements", "").lower()
    desc += " " + task.get("description", "").lower()
    keyword_count = sum(1 for kw in SECURITY_KEYWORDS if kw in desc)
    if keyword_count >= 2:  # Multiple keywords suggest security focus
        return True

    return False
```

## Acceptance Criteria

- [ ] `SECURITY_TAGS` set defined with 25+ tags (aligned with 10-category taxonomy)
- [ ] `SECURITY_KEYWORDS` list defined with 25+ keywords
- [ ] `HIGH_RISK_CATEGORIES` set defined for always-trigger tags
- [ ] `should_run_full_review()` implemented
- [ ] Configuration precedence correct (force > level > tags > keywords)
- [ ] Case-insensitive matching
- [ ] Keyword density threshold for descriptions
- [ ] Unit tests for each detection path
- [ ] Edge case handling (empty tags, empty title)
- [ ] **[From TASK-REV-SEC2]** Tags aligned with Claude Code 10-category taxonomy

## Test Cases

### Tag Detection
1. Task with `authentication` tag -> True
2. Task with `security` tag -> True
3. Task with `ui-component` tag -> False
4. Task with multiple tags including `auth` -> True

### Keyword Detection
5. Title "Implement login endpoint" -> True
6. Title "Add user profile page" -> False
7. Title "JWT token refresh" -> True
8. Description with "password" and "authentication" -> True
9. Description with single "user" keyword -> False

### Configuration Override
10. `force_full_review: true` -> True (regardless of tags)
11. `level: skip` -> False (regardless of tags)
12. `level: strict` -> True (regardless of tags)
13. `level: minimal` -> False (regardless of tags)
14. `level: standard` with `auth` tag -> True

### Edge Cases
15. Empty tags list -> Use keyword detection
16. Empty title -> Use description only
17. No task metadata -> False
18. Case variations: "Authentication", "AUTHENTICATION" -> True

## Integration

**REVISED ARCHITECTURE (from TASK-REV-4B0F)**: Detection runs in pre-loop, NOT Coach.

```python
# In guardkit/orchestrator/quality_gates/pre_loop.py

from .security_detection import should_run_full_review

class PreLoopQualityGates:
    def _should_run_security_review(self, task: dict) -> bool:
        """Check if task requires full security review."""
        config = self._load_security_config(task)
        return should_run_full_review(task, config)

    async def execute(self, task_id: str, options: Dict[str, Any]) -> PreLoopResult:
        # ... existing gates ...

        # Phase 2.5C: Security Pre-Check (uses detection logic)
        if self._should_run_security_review(task):
            security_result = await self._run_security_review(task)
            self._save_security_review_result(task_id, security_result)

        return self._extract_pre_loop_results(...)
```

**Note**: Coach does NOT call `should_run_full_review()`. Coach only reads the results of security checks from `task_work_results.json`.

## Files Modified

### New Files
- `guardkit/orchestrator/quality_gates/security_detection.py` - Detection logic

### Modified Files
- `guardkit/orchestrator/quality_gates/pre_loop.py` - Import and use detection logic

## Out of Scope

- Quick checks implementation (TASK-SEC-001)
- Configuration schema (TASK-SEC-002)
- Security-specialist invocation (TASK-SEC-003) - but TASK-SEC-003 uses this detection logic

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- Tags aligned with 10-category vulnerability taxonomy
- High-risk categories (auth, injection, crypto, secrets) always trigger full review