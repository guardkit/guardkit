---
id: TASK-SEC-003
title: Implement security-specialist invocation
status: backlog
created: 2025-12-31T14:45:00Z
updated: 2025-12-31T14:45:00Z
priority: high
tags: [security, coach-agent, security-specialist, autobuild]
complexity: 6
parent_review: TASK-REV-SEC1
implementation_mode: task-work
estimated_hours: 3-4
wave: 2
conductor_workspace: coach-security-wave2-1
dependencies: [TASK-SEC-001, TASK-SEC-002]
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

## Security-Specialist Invocation

### Prompt Template

```python
SECURITY_REVIEW_PROMPT = """
Perform comprehensive security review of implementation in:
{worktree_path}

Task: {task_title}
Tags: {task_tags}

Focus on:
1. OWASP Top 10 vulnerabilities
2. Authentication patterns (timing attacks, credential handling)
3. Authorization patterns (IDOR, privilege escalation)
4. Secret handling (hardcoded, weak, exposure)
5. Input validation completeness
6. API security (CORS, rate limiting, headers)
7. Token/session management (revocation, expiry)
8. Cryptographic practices

Return findings as JSON array:
[
  {{
    "severity": "critical|high|medium|low|info",
    "category": "owasp-a01|auth|input|crypto|...",
    "description": "Detailed description",
    "location": "file:line",
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

## Technical Notes

### Response Parsing

```python
def parse_security_findings(agent_response: str) -> List[SecurityFinding]:
    """Parse security-specialist response into findings."""
    try:
        # Extract JSON from response (may be wrapped in markdown)
        json_match = re.search(r'\[[\s\S]*\]', agent_response)
        if not json_match:
            return []

        findings_data = json.loads(json_match.group())
        return [
            SecurityFinding(
                check_id=f"security-specialist-{i}",
                severity=f.get("severity", "medium"),
                description=f.get("description", ""),
                file_path=f.get("location", "").split(":")[0],
                line_number=int(f.get("location", "0:0").split(":")[1] or 0),
                matched_text="",
                recommendation=f.get("recommendation", ""),
                category=f.get("category", "unknown")
            )
            for i, f in enumerate(findings_data)
        ]
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
