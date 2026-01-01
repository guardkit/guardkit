---
id: TASK-SEC-003
title: Implement security-specialist invocation
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T16:15:00Z
priority: high
tags: [security, coach-agent, security-specialist, autobuild]
complexity: 6
parent_review: TASK-REV-SEC1
implementation_mode: task-work
estimated_hours: 3-4
wave: 2
conductor_workspace: coach-security-wave2-1
dependencies: [TASK-SEC-001, TASK-SEC-002]
enhanced_by: TASK-REV-SEC2
claude_code_techniques:
  - ten-category-taxonomy
  - confidence-scoring
  - post-filtering
  - structured-prompt
---

# TASK-SEC-003: Implement Security-Specialist Invocation

## Description

Add the ability for Coach agent to invoke the security-specialist agent for comprehensive security review. This is triggered conditionally based on task tags, keywords, or explicit configuration.

## Requirements

1. Create `invoke_security_specialist()` function
2. Build structured prompt with task context
3. Parse security-specialist response into findings
4. Integrate with Coach validation flow
5. Handle timeout and error cases
6. **[From TASK-REV-SEC2]** Use 10-category vulnerability taxonomy from Claude Code
7. **[From TASK-REV-SEC2]** Add confidence scoring (filter below 0.8)
8. **[From TASK-REV-SEC2]** Implement post-filtering for false positives

## Security-Specialist Invocation

### Prompt Template

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

### Invocation Function

```python
async def invoke_security_specialist(
    worktree_path: Path,
    task: dict,
    timeout: int = 300
) -> List[SecurityFinding]:
    """
    Invoke security-specialist agent for comprehensive review.

    Args:
        worktree_path: Path to git worktree
        task: Task dictionary with id, title, tags
        timeout: Maximum time in seconds

    Returns:
        List of SecurityFinding objects
    """
    prompt = SECURITY_REVIEW_PROMPT.format(
        worktree_path=worktree_path,
        task_title=task.get("title", ""),
        task_tags=task.get("tags", [])
    )

    result = await invoke_task(
        subagent_type="security-specialist",
        description=f"Security review for {task.get('id')}",
        prompt=prompt,
        timeout=timeout
    )

    return parse_security_findings(result)
```

## Acceptance Criteria

- [ ] `invoke_security_specialist()` async function implemented
- [ ] Structured prompt includes task context
- [ ] Response parsed into `SecurityFinding` objects
- [ ] Timeout handling (default 300s)
- [ ] Error handling for agent failures
- [ ] Integration with Coach `validate()` method
- [ ] Findings categorized by severity
- [ ] Unit tests for prompt building
- [ ] Integration test with mock agent response
- [ ] **[From TASK-REV-SEC2]** 10-category vulnerability taxonomy in prompt
- [ ] **[From TASK-REV-SEC2]** Confidence scoring in SecurityFinding (filter < 0.8)
- [ ] **[From TASK-REV-SEC2]** Post-filtering for DOS, rate limiting, resource management

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

### Integration with Coach

```python
# In coach_validator.py validate() method

if should_run_full_review(task, security_config):
    try:
        full_findings = await invoke_security_specialist(
            self.worktree_path,
            task,
            timeout=security_config.full_review_timeout
        )

        blocking = [f for f in full_findings
                   if f.severity in ["critical", "high"]]

        if blocking:
            return self._feedback_result(
                task_id=task_id,
                turn=turn,
                issues=[{
                    "severity": "must_fix",
                    "category": "security",
                    "description": "Security review identified issues",
                    "findings": [f.to_dict() for f in blocking]
                }],
                rationale=f"Security review found {len(blocking)} blocking issues"
            )

    except asyncio.TimeoutError:
        logger.warning(f"Security review timed out for {task_id}")
        # Continue with approval (timeout is not blocking)
```

## Test Cases

1. Successful invocation with findings
2. Successful invocation with no findings
3. Timeout handling
4. Malformed response handling
5. Agent error handling
6. JSON extraction from markdown-wrapped response
7. Correct severity categorization
8. Integration with Coach flow

## Out of Scope

- Quick checks (TASK-SEC-001)
- Configuration schema (TASK-SEC-002)
- Tag detection (TASK-SEC-004)

## Claude Code Reference

Techniques adopted from [claude-code-security-review](https://github.com/anthropics/claude-code-security-review):
- 10-category vulnerability taxonomy for comprehensive coverage
- Confidence scoring (>80%) to reduce false positives
- Hard exclusion patterns for DOS, rate limiting, resource management
- Structured prompt requiring exploitation scenarios
