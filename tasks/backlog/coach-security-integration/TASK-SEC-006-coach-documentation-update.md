---
id: TASK-SEC-006
title: Update Coach agent documentation
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T14:45:00Z
priority: medium
tags: [security, documentation, coach-agent, autobuild]
complexity: 2
parent_review: TASK-REV-SEC1
implementation_mode: direct
estimated_hours: 1-2
wave: 3
conductor_workspace: coach-security-wave3-2
dependencies: [TASK-SEC-005]
---

# TASK-SEC-006: Update Coach Agent Documentation

## Description

Update all relevant documentation to reflect the new security validation capabilities in the Coach agent.

## Files to Update

### 1. `.claude/agents/autobuild-coach.md`

Add new section:

```markdown
## Security Validation

The Coach now includes security validation as part of its verification process.

### Quick Security Checks (Always Run)

These checks run on ALL tasks (~30 seconds):
- Hardcoded secrets (API_KEY, PASSWORD, SECRET)
- SQL injection patterns (string formatting in queries)
- Command injection (subprocess with variables)
- CORS wildcard configuration
- Debug mode enabled
- Eval/exec usage

**Severity Levels**:
- **Critical**: Block immediately (hardcoded secrets, injection)
- **High**: Block (CORS wildcard, debug mode)
- **Medium**: Feedback (best practices)
- **Low/Info**: Warning (suggestions)

### Full Security Review (Conditional)

Full security-specialist review runs when:
- Task tagged with: `authentication`, `authorization`, `security`, `auth`, `token`, `payment`
- Task title contains security keywords
- Configuration forces full review (`security.force_full_review: true`)
- Security level is `strict`

### Security Configuration

In task frontmatter:
```yaml
security:
  level: standard  # strict | standard | minimal | skip
  skip_checks: []  # Check IDs to skip
  force_full_review: false
```

### NEVER (Updated)
- ❌ Never approve code with security vulnerabilities **← NOW ENFORCED VIA CHECKS**
```

### 2. `installer/core/commands/feature-build.md`

Add security options section:

```markdown
## Security Validation

`/feature-build` includes automatic security validation:

### Quick Checks (Default)
All tasks receive quick security checks (~30s overhead):
- Hardcoded secrets detection
- SQL/command injection patterns
- CORS misconfiguration
- Debug mode detection

### Full Security Review
Tasks tagged with security-related tags receive full review:
- OWASP Top 10 analysis
- Authentication pattern review
- Authorization logic review

### Configuration

In task frontmatter:
```yaml
security:
  level: strict  # strict | standard | minimal | skip
```

Or via feature YAML:
```yaml
security:
  default_level: standard
  force_full_review: [TASK-AUTH-001]
```

### Security Levels

| Level | Quick Checks | Full Review | Block On |
|-------|--------------|-------------|----------|
| strict | Always | Always | High+ |
| standard | Always | Tagged only | Critical |
| minimal | Always | Never | Critical |
| skip | Never | Never | Never |
```

### 3. `CLAUDE.md`

Add to AutoBuild section:

```markdown
### Security Validation

AutoBuild includes automatic security validation:

**Quick Checks** (all tasks, ~30s):
- Hardcoded secrets, SQL injection, command injection
- CORS misconfiguration, debug mode

**Full Review** (security-tagged tasks, ~2-5min):
- OWASP Top 10 analysis
- Auth pattern review

**Configuration**:
```yaml
# In task frontmatter
security:
  level: standard  # strict | standard | minimal | skip
```

**See**: [Security Validation Guide](docs/guides/security-validation.md)
```

### 4. Create New Guide: `docs/guides/security-validation.md`

```markdown
# Security Validation Guide

## Overview

GuardKit's AutoBuild workflow includes automatic security validation
to catch vulnerabilities during autonomous implementation.

## How It Works

### Two-Tier Security

1. **Quick Checks** (Always, ~30s)
   - Run on every task
   - Detect critical issues via regex
   - Block on: hardcoded secrets, injection patterns

2. **Full Review** (Conditional, ~2-5min)
   - Run on security-tagged tasks
   - Uses security-specialist agent
   - Comprehensive OWASP analysis

### Security Levels

| Level | Description |
|-------|-------------|
| `strict` | Full review on all tasks |
| `standard` | Quick checks + tagged review |
| `minimal` | Quick checks only |
| `skip` | No security validation |

### Triggering Full Review

Full review runs when:
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

### Troubleshooting

**False Positive**: Add to `skip_checks` or use `# nosec` comment
**Performance**: Use `minimal` level for UI-only tasks
**Missing Detection**: Upgrade to `strict` level
```

## Acceptance Criteria

- [ ] `autobuild-coach.md` updated with Security Validation section
- [ ] `feature-build.md` updated with Security Validation section
- [ ] `CLAUDE.md` updated with Security Validation summary
- [ ] `docs/guides/security-validation.md` created
- [ ] All documentation reviewed for accuracy
- [ ] Examples tested for correctness

## Out of Scope

- Implementation changes (Wave 1-2 tasks)
- Test documentation (part of TASK-SEC-005)
