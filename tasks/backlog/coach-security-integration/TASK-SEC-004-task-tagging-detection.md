---
id: TASK-SEC-004
title: Implement task tagging detection
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T14:45:00Z
priority: high
tags: [security, configuration, detection, autobuild]
complexity: 3
parent_review: TASK-REV-SEC1
implementation_mode: task-work
estimated_hours: 1-2
wave: 2
conductor_workspace: coach-security-wave2-2
dependencies: [TASK-SEC-001, TASK-SEC-002]
---

# TASK-SEC-004: Implement Task Tagging Detection

## Description

Implement the logic to determine when a task requires full security-specialist review based on tags, keywords, and configuration. This gates when the more expensive full review runs.

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
SECURITY_TAGS = {
    # Core security
    "authentication", "authorization", "security", "auth",
    # Token/session
    "session", "token", "jwt", "oauth", "oauth2",
    # Sensitive operations
    "payment", "checkout", "billing",
    # Cryptography
    "crypto", "encryption", "hashing",
    # Access control
    "rbac", "acl", "permissions", "roles",
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

- [ ] `SECURITY_TAGS` set defined with 15+ tags
- [ ] `SECURITY_KEYWORDS` list defined with 25+ keywords
- [ ] `should_run_full_review()` implemented
- [ ] Configuration precedence correct (force > level > tags > keywords)
- [ ] Case-insensitive matching
- [ ] Keyword density threshold for descriptions
- [ ] Unit tests for each detection path
- [ ] Edge case handling (empty tags, empty title)

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

```python
# In coach_validator.py

from .security_checker import should_run_full_review

# In validate() method, after quick checks:
if should_run_full_review(task, security_config):
    full_findings = await invoke_security_specialist(...)
```

## Out of Scope

- Quick checks implementation (TASK-SEC-001)
- Configuration schema (TASK-SEC-002)
- Security-specialist invocation (TASK-SEC-003)
