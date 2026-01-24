# Implementation Guide: Coach Security Integration

**Feature ID**: `FEAT-SEC`
**AutoBuild Command**: `/feature-build FEAT-SEC`
**Architecture Review**: `TASK-REV-4B0F` (Revised architecture approved)

## Architecture Overview (from TASK-REV-4B0F)

**Key Principle**: Coach is READ-ONLY. Security validation runs in pre-loop and task-work.

```
Pre-Loop Quality Gates
    |
    +-- Phase 2.5A: Pattern Suggestions
    +-- Phase 2.5B: Architectural Review
    +-- Phase 2.5C: Security Pre-Check (TASK-SEC-003, TASK-SEC-004)
    |       +-- IF security-tagged: Invoke security-specialist via TaskWorkInterface
    |       +-- Save to security_review_results.json
    |
    v
Player (task-work)
    |
    +-- Phase 3: Implementation
    +-- Phase 4: Testing
    +-- Phase 4.3: Quick Security Scan (TASK-SEC-001)
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
    +-- Approve/Feedback (NO agent invocation - Coach is read-only)
```

## Wave Execution Strategy

```
Wave 1 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │  TASK-SEC-001   │    │  TASK-SEC-002   │          │
│  │ Quick Checks    │    │ Config Schema   │          │
│  │ (task-work)     │    │ (task-work)     │          │
│  │ complexity: 5   │    │ complexity: 3   │          │
│  │ type: feature   │    │ type: feature   │          │
│  │                 │    │                 │          │
│  │ Phase 4.3 impl  │    │ SecurityConfig  │          │
│  └─────────────────┘    └─────────────────┘          │
│         │                       │                     │
└─────────┼───────────────────────┼─────────────────────
          │                       │
          ▼                       ▼
Wave 2 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │  TASK-SEC-003   │    │  TASK-SEC-004   │          │
│  │ Pre-Loop Review │    │ Pre-Loop Detect │          │
│  │ (task-work)     │    │ (task-work)     │          │
│  │ complexity: 6   │    │ complexity: 3   │          │
│  │ type: feature   │    │ type: feature   │          │
│  │                 │    │                 │          │
│  │ Phase 2.5C +    │    │ Detection logic │          │
│  │ TaskWorkIntf    │    │ for pre-loop    │          │
│  └─────────────────┘    └─────────────────┘          │
│         │                       │                     │
└─────────┼───────────────────────┼─────────────────────
          │                       │
          ▼                       ▼
Wave 3 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────────────────────────────────┐     │
│  │              TASK-SEC-005                    │     │
│  │              Tests (Revised Architecture)    │     │
│  │              (task-work)                     │     │
│  │              complexity: 5                   │     │
│  │              type: testing                   │     │
│  │                                              │     │
│  │  - Pre-loop security tests (Phase 2.5C)     │     │
│  │  - Task-work quick scan tests (Phase 4.3)   │     │
│  │  - Coach read-only verification tests       │     │
│  └─────────────────────────────────────────────┘     │
│                        │                              │
└────────────────────────┼──────────────────────────────
                         │
                         ▼
Wave 4 ─────────────────────────────────────────────────
│                                                       │
│  ┌─────────────────────────────────────────────┐     │
│  │              TASK-SEC-006                    │     │
│  │              Documentation (Revised Arch)    │     │
│  │              (direct)                        │     │
│  │              complexity: 2                   │     │
│  │              type: documentation             │     │
│  │                                              │     │
│  │  - Architecture diagram with phases          │     │
│  │  - Coach read-only constraint documented     │     │
│  └─────────────────────────────────────────────┘     │
│                                                       │
└───────────────────────────────────────────────────────
```

## Conductor Workspace Names

| Wave | Task | Workspace Name |
|------|------|----------------|
| 1 | TASK-SEC-001 | `coach-security-wave1-1` |
| 1 | TASK-SEC-002 | `coach-security-wave1-2` |
| 2 | TASK-SEC-003 | `coach-security-wave2-1` |
| 2 | TASK-SEC-004 | `coach-security-wave2-2` |
| 3 | TASK-SEC-005 | `coach-security-wave3-1` |
| 4 | TASK-SEC-006 | `coach-security-wave4-1` |

## Task Type Configuration

Each task has a `task_type` field that determines which quality gates are enforced:

| Task | task_type | Tests Required | Arch Review | Coverage |
|------|-----------|----------------|-------------|----------|
| TASK-SEC-001 | `feature` | Yes | Yes (60+) | Yes (80%) |
| TASK-SEC-002 | `feature` | Yes | Yes (60+) | Yes (80%) |
| TASK-SEC-003 | `feature` | Yes | Yes (60+) | Yes (80%) |
| TASK-SEC-004 | `feature` | Yes | Yes (60+) | Yes (80%) |
| TASK-SEC-005 | `testing` | No | No | No |
| TASK-SEC-006 | `documentation` | No | No | No |

## Wave 1: Quick Checks Foundation

### TASK-SEC-001: Add Quick Security Checks

**Objective**: Implement grep/regex-based security checks that run on all tasks.

**Key Implementation Points**:
```python
# guardkit/orchestrator/quality_gates/security_checker.py

from dataclasses import dataclass
from typing import List, Literal
from pathlib import Path

@dataclass
class SecurityFinding:
    check_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    file_path: str
    line_number: int
    matched_text: str
    recommendation: str

QUICK_SECURITY_CHECKS = [
    {
        "id": "hardcoded-secrets",
        "severity": "critical",
        "pattern": r"(API_KEY|PASSWORD|SECRET|TOKEN)\s*=\s*['\"][^'\"]+['\"]",
        "description": "Hardcoded secret detected",
        "file_types": ["*.py"],
    },
    {
        "id": "sql-injection",
        "severity": "critical",
        "pattern": r"f['\"]SELECT.*\{",
        "description": "Potential SQL injection (string formatting in query)",
        "file_types": ["*.py"],
    },
    {
        "id": "cors-wildcard",
        "severity": "high",
        "pattern": r"allow_origins.*['\"\*'\"]",
        "description": "CORS wildcard configuration",
        "file_types": ["*.py"],
    },
    {
        "id": "debug-mode",
        "severity": "high",
        "pattern": r"DEBUG\s*=\s*True",
        "description": "Debug mode enabled",
        "file_types": ["*.py"],
    },
    {
        "id": "command-injection",
        "severity": "critical",
        "substring": ["subprocess.run(f\"", "os.system(f\""],
        "description": "Potential command injection",
        "file_types": ["*.py"],
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

## Wave 2: Pre-Loop Security Integration (REVISED from TASK-REV-4B0F)

### TASK-SEC-003: Implement Pre-Loop Security Review via TaskWorkInterface

**Objective**: Add Phase 2.5C security pre-check to pre-loop, with security-specialist invocation via TaskWorkInterface.

**Key Implementation Points**:

```python
# In guardkit/orchestrator/quality_gates/pre_loop.py

class PreLoopQualityGates:
    async def execute(self, task_id: str, options: Dict[str, Any]) -> PreLoopResult:
        # Existing gates...
        design_result = await self._interface.execute_design_phase(...)

        # NEW: Phase 2.5C - Security Pre-Check
        if self._should_run_security_review(task):
            security_result = await self._run_security_review(task)
            self._save_security_review_result(task_id, security_result)

        return self._extract_pre_loop_results(...)

    async def _run_security_review(self, task: dict) -> SecurityReviewResult:
        """Invoke security-specialist via TaskWorkInterface (NOT Coach)."""
        return await self._interface.execute_security_review(task)
```

```python
# In guardkit/orchestrator/quality_gates/task_work_interface.py

class TaskWorkInterface:
    async def execute_security_review(self, task: dict) -> SecurityReviewResult:
        """Run full security review - Task tool invocation happens HERE."""
        prompt = self._build_security_review_prompt(task)

        result = await self.invoke_task(
            subagent_type="security-specialist",
            description=f"Security review for {task.get('id')}",
            prompt=prompt,
            timeout=300
        )

        return self._parse_security_review_result(result)
```

### TASK-SEC-004: Implement Pre-Loop Tag Detection

**Objective**: Determine when full security review should run in pre-loop.

**Key Implementation Points**:

```python
# In guardkit/orchestrator/quality_gates/security_detection.py

SECURITY_TAGS = {
    "authentication", "authorization", "security", "auth",
    "session", "token", "payment", "crypto", "encryption"
}

SECURITY_KEYWORDS = [
    "login", "password", "jwt", "oauth", "api_key", "secret",
    "credential", "permission", "access", "role"
]

def should_run_full_review(task: dict, config: SecurityConfig) -> bool:
    """Determine if task requires full security-specialist review in pre-loop."""
    # ... detection logic (unchanged)
```

```python
# In guardkit/orchestrator/quality_gates/pre_loop.py

from .security_detection import should_run_full_review

class PreLoopQualityGates:
    def _should_run_security_review(self, task: dict) -> bool:
        """Called in pre-loop, NOT Coach."""
        config = self._load_security_config(task)
        return should_run_full_review(task, config)
```

**Note**: Detection logic runs in pre-loop. Coach does NOT call `should_run_full_review()`.

## Wave 3: Testing

### TASK-SEC-005: Add Security Validation Tests

**Objective**: Comprehensive test coverage for security features.

**Test Categories**:
1. Quick check detection tests
2. Full review triggering logic tests
3. Configuration parsing tests
4. Integration tests with Coach validator
5. False positive filtering tests
6. Confidence threshold tests
7. Exclusion category tests

## Wave 4: Documentation

### TASK-SEC-006: Update Coach Agent Documentation

**Objective**: Update documentation with security validation details.

**Files to Update**:
- `.claude/agents/autobuild-coach.md` - Add security validation section
- `installer/core/commands/feature-build.md` - Document security options
- `CLAUDE.md` - Add security configuration reference
- `docs/guides/security-validation.md` - Create new guide

## Integration with Coach Validator (REVISED from TASK-REV-4B0F)

**Key Change**: Coach only READS security results. NO agent invocation.

```python
# In coach_validator.py - Coach is READ-ONLY for security

def verify_quality_gates(self, task_work_results: Dict) -> QualityGateStatus:
    """Verify quality gates including security results."""
    # Existing gates...
    tests_passed = ...
    coverage_met = ...

    # NEW: Read security results (Coach does NOT invoke security-specialist)
    security = task_work_results.get("security", {})
    quick_check_passed = security.get("quick_check_passed", True)
    critical_findings = security.get("critical_count", 0)
    high_findings = security.get("high_count", 0)

    # Security gate passes if quick checks passed and no critical issues
    security_passed = quick_check_passed and critical_findings == 0

    return QualityGateStatus(
        tests_passed=tests_passed,
        coverage_met=coverage_met,
        security_passed=security_passed,
        security_warnings=high_findings,  # High findings generate feedback
    )

def validate(self, task_id: str, turn: int, task: dict) -> CoachValidationResult:
    # ... existing validation ...

    # Read task-work results (written by Phase 4.3)
    task_work_results = self._read_task_work_results()

    # Verify quality gates (including security)
    gate_status = self.verify_quality_gates(task_work_results)

    if not gate_status.security_passed:
        return self._feedback_result(
            task_id=task_id,
            turn=turn,
            issues=[{
                "severity": "must_fix",
                "category": "security",
                "description": "Security checks failed",
            }],
            rationale="Critical security vulnerabilities detected by quick scan"
        )

    # Continue with existing validation...
```

**Why This Architecture?**
- Coach has tools [Read, Bash, Grep, Glob] - NO Task tool
- Coach is a "lightweight validator" - reads results, doesn't generate them
- Security-specialist invocation requires Task tool (available in TaskWorkInterface)
- This maintains separation of concerns: task-work runs checks, Coach validates results

## Rollout Strategy

1. **Phase 1**: Implement behind feature flag (`GUARDKIT_SECURITY_VALIDATION=true`)
2. **Phase 2**: Enable quick checks by default, full review opt-in
3. **Phase 3**: Enable full review for tagged tasks by default
4. **Phase 4**: Remove feature flag, full functionality default

## Running with AutoBuild

```bash
# Run the entire feature (all 6 tasks across 4 waves)
/feature-build FEAT-SEC

# Run individual tasks
/feature-build TASK-SEC-001

# Run with verbose output
/feature-build FEAT-SEC --verbose

# Resume after interruption
/feature-build FEAT-SEC --resume
```
