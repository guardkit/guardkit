---
acceptance_criteria:
- SecurityChecker class created with run_quick_checks() method
- All 12+ quick checks implemented with hybrid detection (substring + regex)
- Path-based filtering limits checks to relevant file types
- Checks scan Python, JavaScript/TypeScript, and YAML files in worktree
- Findings returned as structured SecurityFinding dataclass
- Critical findings categorized correctly
- Execution time less than 30 seconds for typical project
- Unit tests for each check pattern
complexity: 5
conductor_workspace: coach-security-wave1-1
created: 2026-01-24 15:00:00+00:00
dependencies: []
estimated_minutes: 150
feature_id: FEAT-SEC
id: TASK-SEC-001
implementation_mode: task-work
parent_review: TASK-REV-SEC1
priority: high
status: in_review
tags:
- security
- coach-agent
- autobuild
- quality-gates
task_type: feature
title: Add quick security checks to Coach agent
updated: 2026-01-25T22:30:00+00:00
wave: 1
---

# TASK-SEC-001: Add Quick Security Checks to Coach Agent

## Description

Implement grep/regex-based security checks that run on ALL tasks during Coach validation. These quick checks (~30 seconds) detect critical and high-severity security issues without invoking a full security-specialist agent.

## Requirements

1. Create `SecurityChecker` class in `guardkit/orchestrator/quality_gates/security_checker.py`
2. Implement 10-12 quick security checks using hybrid detection (substring + regex)
3. Integrate with `CoachValidator.validate()` method
4. Return structured findings with severity levels
5. **[From TASK-REV-SEC2]** Use substring matching for simple patterns (10x faster than regex)
6. **[From TASK-REV-SEC2]** Add path-based filtering to limit checks to relevant file types

## Quick Checks to Implement

### Python Checks (*.py files)

| Check ID | Severity | Detection | Pattern | Description |
|----------|----------|-----------|---------|-------------|
| `hardcoded-secrets` | critical | regex | `(API_KEY\|PASSWORD\|SECRET)\s*=\s*["'][^"']+` | Hardcoded credentials |
| `sql-injection` | critical | regex | `f["']SELECT.*\{` | SQL string formatting |
| `command-injection` | critical | substring | `subprocess.run(f"`, `os.system(f"` | Shell command injection |
| `pickle-load` | critical | substring | `pickle.load` | Deserialization attacks |
| `eval-exec` | high | substring | `eval(`, `exec(` | Dynamic code execution |
| `debug-mode` | high | regex | `DEBUG\s*=\s*True` | Debug enabled |

### JavaScript/TypeScript Checks (*.js, *.ts, *.jsx, *.tsx)

| Check ID | Severity | Detection | Pattern | Description |
|----------|----------|-----------|---------|-------------|
| `dangerous-inner-html` | high | substring | `dangerouslySetInnerHTML` | React XSS risk |
| `document-write` | high | substring | `document.write` | DOM XSS |
| `inner-html` | medium | substring | `.innerHTML` | DOM manipulation XSS |
| `new-function` | high | substring | `new Function(` | Dynamic code generation |
| `js-eval` | high | substring | `eval(` | JavaScript eval |

### Universal Checks (all files)

| Check ID | Severity | Detection | Pattern | Description |
|----------|----------|-----------|---------|-------------|
| `cors-wildcard` | high | regex | `allow_origins.*["']\*["']` | CORS wildcard |

### GitHub Actions Checks (.github/workflows/*.yml)

| Check ID | Severity | Detection | Pattern | Description |
|----------|----------|-----------|---------|-------------|
| `gha-injection` | critical | regex | `run:.*\$\{\{.*github\.event` | Workflow injection |

## Acceptance Criteria

- [ ] `SecurityChecker` class created with `run_quick_checks()` method
- [ ] All 12+ quick checks implemented with hybrid detection (substring + regex)
- [ ] Path-based filtering limits checks to relevant file types
- [ ] Checks scan Python, JavaScript/TypeScript, and YAML files in worktree
- [ ] Findings returned as structured `SecurityFinding` dataclass
- [ ] Critical findings categorized correctly
- [ ] Execution time < 30 seconds for typical project
- [ ] Unit tests for each check pattern
- [ ] **[From TASK-REV-SEC2]** Substring matching used for simple patterns

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

### Python Detection
1. Detect hardcoded API key: `API_KEY = "sk-1234567890"`
2. Detect SQL injection: `f"SELECT * FROM users WHERE id = {user_id}"`
3. Detect command injection: `subprocess.run(f"ls {path}", shell=True)`
4. Detect pickle load: `pickle.load(open("data.pkl", "rb"))`
5. Detect eval: `eval(user_input)`
6. Detect debug mode: `DEBUG = True`

### JavaScript/TypeScript Detection
7. Detect dangerouslySetInnerHTML: `<div dangerouslySetInnerHTML={{__html: content}} />`
8. Detect document.write: `document.write(userInput)`
9. Detect innerHTML: `element.innerHTML = userInput`
10. Detect new Function: `new Function("return " + code)()`
11. Detect eval: `eval(userCode)`

### Universal Detection
12. Detect CORS wildcard: `allow_origins=["*"]`

### GitHub Actions Detection
13. Detect workflow injection: `run: echo "${{ github.event.issue.title }}"`

### False Positive Prevention
14. No false positives on safe patterns
15. Comments mentioning patterns should not trigger (from Claude Code)
16. Path filtering prevents wrong file type matches

### Performance
17. Performance < 30s on 100-file project

## Out of Scope

- Full security-specialist agent invocation (TASK-SEC-003)
- Configuration schema (TASK-SEC-002)
- Tag-based detection (TASK-SEC-004)

## Claude Code Reference

Techniques adopted from [security-guidance plugin](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance):
- Substring matching for simple patterns (faster than regex)
- Path-based filtering to limit checks to relevant file types
- Expanded pattern list covering JavaScript/TypeScript and GitHub Actions