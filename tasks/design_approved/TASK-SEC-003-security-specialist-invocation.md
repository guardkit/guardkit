---
acceptance_criteria:
- Phase 2.5C security pre-check added to pre_loop.py
- TaskWorkInterface.execute_security_review() async method implemented
- Structured prompt includes task context
- Response parsed into SecurityFinding objects
- Results saved to security_review_results.json
- Phase 4.3 quick security scan added to task-work flow
- Quick scan results written to task_work_results.json["security"]
- Timeout handling with default 300s for full review
- Error handling for agent failures
- 10-category vulnerability taxonomy in prompt
- Confidence scoring in SecurityFinding with filter below 0.8
- Post-filtering for DOS, rate limiting, resource management
- Coach only READS security results (no agent invocation)
- Unit tests for prompt building and response parsing
- Integration test with mock agent response
complexity: 6
conductor_workspace: coach-security-wave2-1
created: 2026-01-24 15:00:00+00:00
dependencies:
- TASK-SEC-001
- TASK-SEC-002
estimated_minutes: 240
feature_id: FEAT-SEC
id: TASK-SEC-003
implementation_mode: task-work
parent_review: TASK-REV-SEC1
priority: high
status: design_approved
tags:
- security
- pre-loop
- task-work-interface
- security-specialist
- autobuild
task_type: feature
title: Implement pre-loop security review via TaskWorkInterface
updated: 2026-01-24 17:00:00+00:00
wave: 2
---

# TASK-SEC-003: Implement Pre-Loop Security Review via TaskWorkInterface

## Description

**REVISED ARCHITECTURE (from TASK-REV-4B0F)**: Security-specialist invocation was originally designed to run in Coach, but this violates Coach's read-only architecture. Coach has tools [Read, Bash, Grep, Glob] - NO Task tool.

This task now implements security review at two points:
1. **Phase 2.5C (Pre-Loop)**: Full security review for security-tagged tasks, invoked via TaskWorkInterface
2. **Phase 4.3 (Task-Work)**: Quick security scan after tests pass

Coach's role is simplified to **reading** security results from `task_work_results.json["security"]`.

## Architecture Overview

```
REVISED ARCHITECTURE (TASK-REV-4B0F):

Pre-Loop Quality Gates (Phase 2.5C - Security Pre-Check)
    |
    +-- Load task metadata (tags, security config)
    +-- IF security-tagged: Run full security review
    |       +-- Invoke security-specialist (via TaskWorkInterface)
    +-- Store security_review_results.json
              |
              v
Player (task-work --implement-only)
    |
    +-- Implementation (Phase 3)
    |
    +-- Quick Security Scan (Phase 4.3 - NEW)
    |       +-- SecurityChecker.run_quick_checks()
    |       +-- Write to task_work_results.json
    |
    +-- Quality Gates (Phase 4-5.5)
              |
              v
Coach (validation)
    |
    +-- Read task-work results (including security findings)
    +-- Verify security gates passed
    |       +-- results["security"]["all_passed"] == true
    |
    +-- Approve/Feedback (NO agent invocation)
```

## Requirements

1. Add Phase 2.5C security pre-check to `pre_loop.py`
2. Implement `TaskWorkInterface.execute_security_review()` method
3. Build structured prompt with task context
4. Parse security-specialist response into findings
5. Save security review results to `security_review_results.json`
6. Add Phase 4.3 quick security scan to task-work flow
7. Write quick scan results to `task_work_results.json["security"]`
8. Update Coach to read (not generate) security results
9. **[From TASK-REV-SEC2]** Use 10-category vulnerability taxonomy from Claude Code
10. **[From TASK-REV-SEC2]** Add confidence scoring (filter below 0.8)
11. **[From TASK-REV-SEC2]** Implement post-filtering for false positives

## Implementation Components

### 1. Pre-Loop Security Review (Phase 2.5C)

```python
# In guardkit/orchestrator/quality_gates/pre_loop.py

class PreLoopQualityGates:
    """Pre-loop quality gates including security pre-check."""

    async def execute(self, task_id: str, options: Dict[str, Any]) -> PreLoopResult:
        """Execute pre-loop quality gates."""
        # Existing gates (Phases 2.5A, 2.5B)...
        design_result = await self._interface.execute_design_phase(...)

        # NEW: Phase 2.5C - Security Pre-Check
        if self._should_run_security_review(task):
            security_result = await self._run_security_review(task)
            self._save_security_review_result(task_id, security_result)

        return self._extract_pre_loop_results(...)

    def _should_run_security_review(self, task: dict) -> bool:
        """Check if task requires full security review (delegates to TASK-SEC-004)."""
        from .security_detection import should_run_full_review
        config = self._load_security_config(task)
        return should_run_full_review(task, config)

    async def _run_security_review(self, task: dict) -> SecurityReviewResult:
        """Invoke security-specialist via TaskWorkInterface."""
        return await self._interface.execute_security_review(task)

    def _save_security_review_result(self, task_id: str, result: SecurityReviewResult) -> None:
        """Save security review results for later consumption."""
        output_path = self.worktree_path / ".guardkit" / "security_review_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result.to_dict(), indent=2))
```

### 2. TaskWorkInterface Security Review Method

```python
# In guardkit/orchestrator/quality_gates/task_work_interface.py

class TaskWorkInterface:
    """Interface for invoking task-work phases."""

    async def execute_security_review(self, task: dict) -> SecurityReviewResult:
        """
        Run full security review for security-tagged tasks.

        This is where the Task tool invocation is appropriate - TaskWorkInterface
        has the Task tool available, unlike Coach which is read-only.

        Args:
            task: Task dictionary with id, title, tags

        Returns:
            SecurityReviewResult with findings
        """
        prompt = self._build_security_review_prompt(task)

        result = await self.invoke_task(
            subagent_type="security-specialist",
            description=f"Security review for {task.get('id')}",
            prompt=prompt,
            timeout=300
        )

        return self._parse_security_review_result(result)
```

### 3. Prompt Template

```python
# [From TASK-REV-SEC2] Structured prompt based on Claude Code security-review
SECURITY_REVIEW_PROMPT = """
Perform comprehensive security review of implementation in:
{worktree_path}

Task: {task_title}
Tags: {task_tags}

Identify HIGH-CONFIDENCE security vulnerabilities with real exploitation potential.
Exclude theoretical issues and false positives.

VULNERABILITY CATEGORIES (10-category taxonomy from Claude Code):
1. Injection Attacks: SQL, command, LDAP, XPath, NoSQL, XXE, template injection
2. Authentication & Authorization: Bypass logic, privilege escalation, IDOR, session flaws, JWT vulnerabilities
3. Data Exposure: Hardcoded secrets, PII violations, sensitive logging, API leakage
4. Cryptographic Issues: Weak algorithms, improper key management, weak RNG
5. Input Validation: Missing validation, improper sanitization, path traversal
6. Business Logic Flaws: Race conditions, TOCTOU issues
7. Configuration Security: Insecure defaults, missing headers, permissive CORS
8. Supply Chain: Vulnerable dependencies, typosquatting risks
9. Code Execution: Deserialization attacks, pickle/YAML injection, eval injection
10. Cross-Site Scripting: Reflected, stored, DOM-based XSS

REQUIREMENTS:
- Confidence must be >80% for each finding
- Provide exploitation scenario for each finding
- EXCLUDE: DOS, rate limiting, resource exhaustion, open redirects

Return findings as JSON array:
[
  {{
    "severity": "critical|high|medium|low|info",
    "confidence": 0.85,
    "category": "injection|auth|data-exposure|crypto|input-validation|business-logic|config|supply-chain|code-execution|xss",
    "description": "Detailed description",
    "location": "file:line",
    "exploitation_scenario": "How this could be exploited",
    "recommendation": "How to fix"
  }}
]

If no issues found, return empty array: []
"""
```

### 4. Phase 4.3 Quick Security Scan (in task-work)

```python
# In task-work execution flow (Phase 4.3)

# Phase 4: Testing
test_results = run_tests()

# Phase 4.3: Quick Security Scan (NEW)
if security_config.level != SecurityLevel.SKIP:
    security_findings = SecurityChecker(worktree).run_quick_checks()
    if has_critical_findings(security_findings):
        return blocked("Critical security vulnerabilities detected")

    task_work_results["security"] = {
        "quick_check_passed": True,
        "findings": [f.to_dict() for f in security_findings],
        "findings_count": len(security_findings),
        "critical_count": len([f for f in security_findings if f.severity == "critical"]),
        "high_count": len([f for f in security_findings if f.severity == "high"]),
    }

# Phase 4.5: Test Enforcement
...
```

### 5. Coach Reads Security Results (No Invocation)

```python
# In guardkit/orchestrator/quality_gates/coach_validator.py

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
        security_warnings=high_findings,  # High findings generate feedback, not blocking
    )
```

## Acceptance Criteria

- [ ] Phase 2.5C security pre-check added to `pre_loop.py`
- [ ] `TaskWorkInterface.execute_security_review()` async method implemented
- [ ] Structured prompt includes task context
- [ ] Response parsed into `SecurityFinding` objects
- [ ] Results saved to `security_review_results.json`
- [ ] Phase 4.3 quick security scan added to task-work flow
- [ ] Quick scan results written to `task_work_results.json["security"]`
- [ ] Timeout handling (default 300s for full review)
- [ ] Error handling for agent failures
- [ ] **[From TASK-REV-SEC2]** 10-category vulnerability taxonomy in prompt
- [ ] **[From TASK-REV-SEC2]** Confidence scoring in SecurityFinding (filter < 0.8)
- [ ] **[From TASK-REV-SEC2]** Post-filtering for DOS, rate limiting, resource management
- [ ] Coach only READS security results from `task_work_results.json`
- [ ] Unit tests for prompt building and response parsing
- [ ] Integration tests for pre-loop and task-work security phases

## Technical Notes

### Response Parsing

```python
# [From TASK-REV-SEC2] Hard exclusion patterns from Claude Code security-review
EXCLUSION_PATTERNS = [
    (r"denial of service|resource exhaustion|infinite loop", "DOS finding"),
    (r"rate limit", "Rate limiting recommendation"),
    (r"memory leak|connection leak|unclosed", "Resource management"),
    (r"open redirect", "Open redirect"),
]

def is_excluded(finding: SecurityFinding) -> bool:
    """Check if finding should be excluded based on hard rules."""
    desc = finding.description.lower()
    for pattern, reason in EXCLUSION_PATTERNS:
        if re.search(pattern, desc):
            logger.debug(f"Excluded finding: {reason}")
            return True
    return False

def parse_security_findings(agent_response: str) -> List[SecurityFinding]:
    """Parse security-specialist response into findings with filtering."""
    try:
        # Extract JSON from response (may be wrapped in markdown)
        json_match = re.search(r'\[[\s\S]*\]', agent_response)
        if not json_match:
            return []

        findings_data = json.loads(json_match.group())
        findings = [
            SecurityFinding(
                check_id=f"security-specialist-{i}",
                severity=f.get("severity", "medium"),
                confidence=f.get("confidence", 0.8),  # [From TASK-REV-SEC2]
                description=f.get("description", ""),
                file_path=f.get("location", "").split(":")[0],
                line_number=int(f.get("location", "0:0").split(":")[1] or 0),
                matched_text="",
                exploitation_scenario=f.get("exploitation_scenario", ""),  # [From TASK-REV-SEC2]
                recommendation=f.get("recommendation", ""),
                category=f.get("category", "unknown")
            )
            for i, f in enumerate(findings_data)
        ]

        # [From TASK-REV-SEC2] Filter low confidence and excluded findings
        filtered = [
            f for f in findings
            if f.confidence >= 0.8 and not is_excluded(f)
        ]
        logger.info(f"Filtered {len(findings) - len(filtered)} findings (confidence/exclusion)")
        return filtered

    except (json.JSONDecodeError, IndexError, ValueError) as e:
        logger.warning(f"Failed to parse security findings: {e}")
        return []
```

### Key Architecture Change

**BEFORE (Violated Coach Architecture)**:
```python
# In coach_validator.py - WRONG: Coach cannot invoke agents
full_findings = await invoke_security_specialist(task)  # Coach lacks Task tool
```

**AFTER (Correct Architecture)**:
```python
# Security invocation happens in pre_loop.py via TaskWorkInterface
# Coach only reads the results:

# In coach_validator.py
security = task_work_results.get("security", {})
security_passed = security.get("quick_check_passed", True)
```

## Test Cases

### Pre-Loop Security Review (Phase 2.5C)
1. Security-tagged task triggers full review in pre-loop
2. Non-security task skips full review
3. Full review results saved to `security_review_results.json`
4. Timeout handling for security-specialist invocation
5. Error handling for agent failures

### Task-Work Quick Scan (Phase 4.3)
6. Quick checks run after tests pass
7. Critical finding blocks task progression
8. Results written to `task_work_results.json["security"]`
9. Non-blocking findings generate warnings

### Response Parsing
10. Successful parsing with findings
11. Successful parsing with no findings
12. Malformed response handling
13. JSON extraction from markdown-wrapped response
14. Correct severity categorization

### Coach Validation (Read-Only)
15. Coach reads security results from task_work_results.json
16. Coach does NOT invoke any agents
17. Security gate passes when quick_check_passed is true
18. Security gate fails on critical findings

## Out of Scope

- Quick checks implementation (TASK-SEC-001)
- Configuration schema (TASK-SEC-002)
- Tag detection logic (TASK-SEC-004) - but this task uses it

## Files Modified

### New Files
- `guardkit/orchestrator/quality_gates/security_review.py` - Security review logic

### Modified Files
- `guardkit/orchestrator/quality_gates/pre_loop.py` - Add Phase 2.5C
- `guardkit/orchestrator/quality_gates/task_work_interface.py` - Add execute_security_review()
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Read-only security verification

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- 10-category vulnerability taxonomy for comprehensive coverage
- Confidence scoring (>80%) to reduce false positives
- Hard exclusion patterns for DOS, rate limiting, resource management
- Structured prompt requiring exploitation scenarios