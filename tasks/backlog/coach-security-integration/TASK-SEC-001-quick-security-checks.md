---
id: TASK-SEC-001
title: Add quick security checks to Coach agent
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T14:45:00Z
priority: high
tags: [security, coach-agent, autobuild, quality-gates]
complexity: 5
parent_review: TASK-REV-SEC1
implementation_mode: task-work
estimated_hours: 2-3
wave: 1
conductor_workspace: coach-security-wave1-1
dependencies: []
---

# TASK-SEC-001: Add Quick Security Checks to Coach Agent

## Description

Implement grep/regex-based security checks that run on ALL tasks during Coach validation. These quick checks (~30 seconds) detect critical and high-severity security issues without invoking a full security-specialist agent.

## Requirements

1. Create `SecurityChecker` class in `guardkit/orchestrator/quality_gates/security_checker.py`
2. Implement 5-7 quick security checks using regex patterns
3. Integrate with `CoachValidator.validate()` method
4. Return structured findings with severity levels

## Quick Checks to Implement

| Check ID | Severity | Pattern | Description |
|----------|----------|---------|-------------|
| `hardcoded-secrets` | critical | `(API_KEY\|PASSWORD\|SECRET)=["'][^"']+` | Hardcoded credentials |
| `sql-injection` | critical | `f["']SELECT.*\{` | SQL string formatting |
| `command-injection` | critical | `(subprocess\.run\|os\.system).*\{` | Shell command injection |
| `cors-wildcard` | high | `allow_origins.*["']\*["']` | CORS wildcard |
| `debug-mode` | high | `DEBUG\s*=\s*True` | Debug enabled |
| `eval-exec` | high | `\b(eval\|exec)\s*\(` | Dynamic code execution |

## Acceptance Criteria

- [ ] `SecurityChecker` class created with `run_quick_checks()` method
- [ ] All 6 quick checks implemented with regex patterns
- [ ] Checks scan all Python files in worktree
- [ ] Findings returned as structured `SecurityFinding` dataclass
- [ ] Critical findings categorized correctly
- [ ] Execution time < 30 seconds for typical project
- [ ] Unit tests for each check pattern

## Technical Notes

### File Structure
```
guardkit/orchestrator/quality_gates/
├── __init__.py
├── coach_validator.py  # Existing
└── security_checker.py  # NEW
```

### SecurityChecker Interface
```python
@dataclass
class SecurityFinding:
    check_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    file_path: str
    line_number: int
    matched_text: str
    recommendation: str

class SecurityChecker:
    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path

    def run_quick_checks(self) -> List[SecurityFinding]:
        """Run all quick security checks and return findings."""
        ...
```

### Integration Point
```python
# In coach_validator.py
from .security_checker import SecurityChecker

# In validate() method, after reading task-work results:
checker = SecurityChecker(self.worktree_path)
findings = checker.run_quick_checks()
critical = [f for f in findings if f.severity == "critical"]
if critical:
    return self._feedback_result(...)  # Block on critical
```

## Test Cases

1. Detect hardcoded API key: `API_KEY = "sk-1234567890"`
2. Detect SQL injection: `f"SELECT * FROM users WHERE id = {user_id}"`
3. Detect command injection: `subprocess.run(f"ls {path}", shell=True)`
4. Detect CORS wildcard: `allow_origins=["*"]`
5. Detect debug mode: `DEBUG = True`
6. Detect eval: `eval(user_input)`
7. No false positives on safe patterns
8. Performance < 30s on 100-file project

## Out of Scope

- Full security-specialist agent invocation (TASK-SEC-003)
- Configuration schema (TASK-SEC-002)
- Tag-based detection (TASK-SEC-004)
