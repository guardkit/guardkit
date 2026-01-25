---
id: TASK-SEC-006
title: Update security validation documentation for revised architecture
status: pending
task_type: documentation
created: 2026-01-24T15:00:00Z
updated: 2026-01-24T17:00:00Z
priority: medium
tags: [security, documentation, pre-loop, task-work, coach-agent, autobuild]
complexity: 2
parent_review: TASK-REV-SEC1
feature_id: FEAT-SEC
implementation_mode: direct
estimated_minutes: 120
wave: 4
conductor_workspace: coach-security-wave4-1
dependencies:
  - TASK-SEC-005
acceptance_criteria:
  - autobuild-coach.md updated to clarify Coach READS security results (no agent invocation)
  - feature-build.md updated with Security Validation section (pre-loop + task-work phases)
  - CLAUDE.md updated with Security Validation summary
  - docs/guides/security-validation.md created with revised architecture
  - Architecture diagram shows pre-loop Phase 2.5C and task-work Phase 4.3
  - Documentation clarifies Coach is read-only for security
  - All documentation reviewed for accuracy
  - Examples tested for correctness
  - Document excluded finding types including DOS and rate limiting
  - Document confidence threshold of 0.8
---

# TASK-SEC-006: Update Security Validation Documentation for Revised Architecture

## Description

**REVISED ARCHITECTURE (from TASK-REV-4B0F)**: Documentation must reflect the new architecture where:
- Full security review runs in **pre-loop** (Phase 2.5C) via TaskWorkInterface
- Quick security scan runs in **task-work** (Phase 4.3)
- Coach only **reads** security results (no agent invocation)

Update all relevant documentation to accurately describe security validation capabilities and architecture.

## Files to Update

### 1. `.claude/agents/autobuild-coach.md`

**REVISED (from TASK-REV-4B0F)**: Update to clarify Coach is READ-ONLY for security.

Add new section:

```markdown
## Security Validation (Read-Only)

The Coach **reads** security validation results but does NOT run security checks.

### How It Works

1. **Pre-Loop (Phase 2.5C)**: Full security review runs for security-tagged tasks
   - Invoked via TaskWorkInterface (NOT Coach)
   - Results saved to `security_review_results.json`

2. **Task-Work (Phase 4.3)**: Quick security scan runs after tests
   - Results written to `task_work_results.json["security"]`

3. **Coach Validation**: Reads security results and verifies gates
   - Coach ONLY reads `task_work_results.json["security"]`
   - Coach does NOT invoke security-specialist agent
   - Coach has tools [Read, Bash, Grep, Glob] - NO Task tool

### Security Results Coach Reads

```json
{
  "security": {
    "quick_check_passed": true,
    "findings_count": 0,
    "critical_count": 0,
    "high_count": 0
  }
}
```

### Coach Security Gate Logic

```python
# Coach only READS, never invokes
security = task_work_results.get("security", {})
security_passed = security.get("quick_check_passed", True) and \
                  security.get("critical_count", 0) == 0
```

### NEVER (Updated)
- ❌ Never approve code with security vulnerabilities **← ENFORCED VIA QUALITY GATES**
- ❌ Never invoke agents (Coach is read-only) **← ARCHITECTURAL CONSTRAINT**
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

**REVISED (from TASK-REV-4B0F)**: Include architecture diagram and clarify phase execution.

```markdown
# Security Validation Guide

## Overview

GuardKit's AutoBuild workflow includes automatic security validation
to catch vulnerabilities during autonomous implementation.

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
```

## Acceptance Criteria

- [ ] `autobuild-coach.md` updated to clarify Coach READS security results (no agent invocation)
- [ ] `feature-build.md` updated with Security Validation section (pre-loop + task-work phases)
- [ ] `CLAUDE.md` updated with Security Validation summary
- [ ] `docs/guides/security-validation.md` created with revised architecture
- [ ] Architecture diagram shows pre-loop Phase 2.5C and task-work Phase 4.3
- [ ] Documentation clarifies Coach is read-only for security
- [ ] All documentation reviewed for accuracy
- [ ] Examples tested for correctness
- [ ] **[From TASK-REV-SEC2]** Document excluded finding types (DOS, rate limiting, etc.)
- [ ] **[From TASK-REV-SEC2]** Document confidence threshold (0.8)
- [ ] **[From TASK-REV-4B0F]** Document Coach read-only constraint

## Out of Scope

- Implementation changes (Wave 1-2 tasks)
- Test documentation (part of TASK-SEC-005)

## Key Documentation Points (from TASK-REV-4B0F)

1. **Coach is READ-ONLY**: Coach has tools [Read, Bash, Grep, Glob] - NO Task tool
2. **Security runs in pre-loop**: Phase 2.5C for full review
3. **Quick scan in task-work**: Phase 4.3 for quick checks
4. **Results in JSON**: Coach reads `task_work_results.json["security"]`

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- Document excluded finding types (DOS, rate limiting, resource management)
- Document confidence threshold (0.8) for findings
