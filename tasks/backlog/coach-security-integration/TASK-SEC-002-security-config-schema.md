---
id: TASK-SEC-002
title: Add security configuration schema
status: pending
task_type: feature
created: 2026-01-24T15:00:00Z
updated: 2026-01-24T15:00:00Z
priority: high
tags: [security, configuration, schema, autobuild]
complexity: 3
parent_review: TASK-REV-SEC1
feature_id: FEAT-SEC
implementation_mode: task-work
estimated_minutes: 90
wave: 1
conductor_workspace: coach-security-wave1-2
dependencies: []
acceptance_criteria:
  - SecurityConfig dataclass with all fields
  - SecurityLevel enum with strict, standard, minimal, skip values
  - Task frontmatter security section parsed correctly
  - Feature YAML security section parsed correctly
  - Global config autobuild.security section parsed correctly
  - Configuration merging with correct precedence (task > feature > global)
  - Default values applied correctly
  - Unit tests for configuration loading
  - exclude_categories field with default DOS, rate-limiting, resource-management
  - exclude_patterns field for file pattern exclusions
  - Environment variable override GUARDKIT_SECURITY_SKIP
---

# TASK-SEC-002: Add Security Configuration Schema

## Description

Define and implement the configuration schema for security validation in task frontmatter and feature YAML files. This enables user control over security validation behavior.

## Requirements

1. Define `SecurityConfig` dataclass for parsing configuration
2. Add schema validation for task frontmatter `security` section
3. Add schema validation for feature YAML `security` section
4. Implement configuration loading in Coach validator
5. Document configuration options
6. **[From TASK-REV-SEC2]** Add hard exclusion categories (DOS, rate limiting, resource management)
7. **[From TASK-REV-SEC2]** Add file type/pattern exclusions
8. **[From TASK-REV-SEC2]** Add environment variable override (GUARDKIT_SECURITY_SKIP)

## Configuration Schema

### Task Frontmatter

```yaml
---
id: TASK-XXX
title: Task title
security:
  level: standard        # strict | standard | minimal | skip
  skip_checks: []        # List of check IDs to skip
  force_full_review: false  # Force security-specialist invocation
---
```

### Feature YAML

```yaml
# .guardkit/features/FEAT-XXX.yaml
security:
  default_level: standard
  force_full_review: [TASK-AUTH-001]  # Task IDs requiring full review
  skip_review: [TASK-UI-001]  # Task IDs to skip review
```

### Global Configuration

```yaml
# .guardkit/config.yaml
autobuild:
  security:
    enabled: true
    default_level: standard
    quick_check_timeout: 30
    full_review_timeout: 300
    block_on_critical: true
    # [From TASK-REV-SEC2] Hard exclusion categories
    exclude_categories:
      - dos                    # Denial of Service
      - rate-limiting          # Rate limiting recommendations
      - resource-management    # Memory leaks, connection leaks
      - open-redirect          # Open redirect vulnerabilities
    # [From TASK-REV-SEC2] File pattern exclusions
    exclude_patterns:
      - "*.md"                 # Markdown documentation
      - "*.test.*"             # Test files
      - "docs/**"              # Documentation directory
      - "**/fixtures/**"       # Test fixtures
```

### Environment Variable Override

```bash
# [From TASK-REV-SEC2] Disable security checks entirely (CI/CD use case)
export GUARDKIT_SECURITY_SKIP=1
```

## Security Levels

| Level | Quick Checks | Full Review | Block Severity |
|-------|--------------|-------------|----------------|
| `strict` | Always | Always | High+ |
| `standard` | Always | Tagged only | Critical |
| `minimal` | Always | Never | Critical |
| `skip` | Never | Never | Never |

## Acceptance Criteria

- [ ] `SecurityConfig` dataclass with all fields
- [ ] `SecurityLevel` enum: strict, standard, minimal, skip
- [ ] Task frontmatter `security` section parsed
- [ ] Feature YAML `security` section parsed
- [ ] Global config `autobuild.security` section parsed
- [ ] Configuration merging (task > feature > global)
- [ ] Default values applied correctly
- [ ] Unit tests for configuration loading
- [ ] **[From TASK-REV-SEC2]** `exclude_categories` field with default DOS, rate-limiting, resource-management
- [ ] **[From TASK-REV-SEC2]** `exclude_patterns` field for file pattern exclusions
- [ ] **[From TASK-REV-SEC2]** Environment variable override (`GUARDKIT_SECURITY_SKIP`)

## Technical Notes

### SecurityConfig Dataclass
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import os

class SecurityLevel(Enum):
    STRICT = "strict"
    STANDARD = "standard"
    MINIMAL = "minimal"
    SKIP = "skip"

# [From TASK-REV-SEC2] Default exclusion categories from Claude Code security-review
DEFAULT_EXCLUDE_CATEGORIES = [
    "dos",                  # Denial of Service
    "rate-limiting",        # Rate limiting recommendations
    "resource-management",  # Memory leaks, connection leaks
    "open-redirect",        # Open redirect vulnerabilities
]

# [From TASK-REV-SEC2] Default file pattern exclusions
DEFAULT_EXCLUDE_PATTERNS = [
    "*.md",
    "*.test.*",
    "docs/**",
    "**/fixtures/**",
]

@dataclass
class SecurityConfig:
    level: SecurityLevel = SecurityLevel.STANDARD
    skip_checks: List[str] = field(default_factory=list)
    force_full_review: bool = False
    quick_check_timeout: int = 30
    full_review_timeout: int = 300
    block_on_critical: bool = True
    # [From TASK-REV-SEC2] Hard exclusion categories
    exclude_categories: List[str] = field(default_factory=lambda: DEFAULT_EXCLUDE_CATEGORIES.copy())
    # [From TASK-REV-SEC2] File pattern exclusions
    exclude_patterns: List[str] = field(default_factory=lambda: DEFAULT_EXCLUDE_PATTERNS.copy())

    @classmethod
    def from_task(cls, task: dict) -> "SecurityConfig":
        """Load config from task frontmatter."""
        ...

    @classmethod
    def from_feature(cls, feature: dict, task_id: str) -> "SecurityConfig":
        """Load config from feature YAML."""
        ...

    @classmethod
    def from_global(cls) -> "SecurityConfig":
        """Load config from global config, respecting env override."""
        # [From TASK-REV-SEC2] Environment variable override
        if os.getenv("GUARDKIT_SECURITY_SKIP", "0") == "1":
            return cls(level=SecurityLevel.SKIP)
        ...

    @classmethod
    def merge(cls, task_config, feature_config, global_config) -> "SecurityConfig":
        """Merge configs with precedence: task > feature > global."""
        ...
```

### Configuration Loading
```python
# In coach_validator.py
def _load_security_config(self, task: dict) -> SecurityConfig:
    """Load merged security configuration for task."""
    task_config = SecurityConfig.from_task(task)
    feature_config = SecurityConfig.from_feature(self.feature, task["id"])
    global_config = SecurityConfig.from_global()
    return SecurityConfig.merge(task_config, feature_config, global_config)
```

## Test Cases

1. Parse task-level security config
2. Parse feature-level security config
3. Parse global security config
4. Merge with correct precedence
5. Apply defaults when not specified
6. Handle invalid security level
7. Handle missing security section

## Out of Scope

- Quick check implementation (TASK-SEC-001)
- Full review invocation (TASK-SEC-003)
- Tag detection logic (TASK-SEC-004)

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- Hard exclusion categories (DOS, rate limiting, resource management, open redirect)
- File pattern exclusions (markdown, test files, documentation)
- Environment variable override for CI/CD pipelines
