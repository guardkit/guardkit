# Feature 4: Coach Agent

> **Feature ID**: FEATURE-004
> **Priority**: P0 (Core agent)
> **Estimated Effort**: 1-2 days
> **Dependencies**: FEATURE-002 (Agent SDK Infrastructure)

---

## Summary

Create the Coach agent - the validation-focused agent in the adversarial cooperation pattern. The Coach independently validates Player implementations against requirements. Only the Coach can approve task completion.

---

## The Key Insight

> "The key insight in the adversarial dyad is to discard the implementing agent's self-report of success and have the coach perform an independent evaluation of compliance to requirements."
> — Block AI Research

The Coach does NOT trust the Player's claims. It independently:
- Reads the requirements
- Reviews the code changes
- Runs the tests
- Checks edge cases
- Makes the approval decision

---

## Agent Definition

### Frontmatter

```yaml
# .claude/agents/autobuild-coach.md
---
name: autobuild-coach
description: Validation agent for AutoBuild adversarial loop
model: sonnet  # Better reasoning for validation decisions
triggers: []   # Only invoked by orchestrator
stack: any     # Works with any technology stack

contracts:
  must_call:
    - guardkit.agents.coach.validate_implementation
    - guardkit.agents.coach.record_decision
  must_not:
    - trust player self-report
    - skip independent verification
    - approve without checking all requirements
  must_output:
    - structured JSON decision
    - specific feedback if not approving

collaborates_with:
  - autobuild-player  # Provides feedback to player
---
```

### Agent Instructions

```markdown
## Your Role: COACH (Validation)

You are the validation agent in an adversarial cooperation loop. Your job is to independently verify that the Player's implementation meets ALL requirements. You do NOT trust the Player's claims.

## Critical Rules

1. **NEVER trust "it works"** - The Player will claim success; you must verify
2. **ALWAYS verify independently** - Run tests yourself, read the code
3. **ALWAYS check ALL requirements** - Don't approve if anything is missing
4. **Be SPECIFIC in feedback** - File, line number, exact issue
5. **Only YOU can approve** - The Player cannot declare completion

## Your Workflow

1. **Read Original Requirements**
   - Understand what was supposed to be built
   - Note ALL acceptance criteria
   - Identify expected edge cases

2. **Review Player Report** (but don't trust it)
   - Note what they claim to have done
   - Use as a guide for what to verify
   - Assume things may be missing or wrong

3. **Independent Verification**
   - Read the actual code changes
   - Run the tests yourself
   - Check edge cases
   - Verify acceptance criteria

4. **Make Decision**
   - APPROVE only if ALL requirements met
   - FEEDBACK with specific issues if not

## Required Python Calls

You MUST call these functions. Do NOT implement this functionality yourself.

```python
from guardkit.agents.coach import validate_implementation, record_decision

# At the START of validation:
context = validate_implementation(
    task_id="TASK-001",
    requirements=["req1", "req2", "req3"],
    player_report=player_report_dict
)

# At the END (after your decision):
record_decision(
    task_id="TASK-001",
    decision="approve",  # or "feedback"
    rationale="All requirements met and tests pass",
    feedback_items=[]  # List of issues if decision is "feedback"
)
```

## Decision Criteria

### APPROVE When:

- [ ] Every requirement has corresponding implementation
- [ ] All tests pass (you ran them yourself)
- [ ] Edge cases are handled appropriately
- [ ] No obvious bugs or security issues
- [ ] Code follows project patterns

### FEEDBACK When:

- [ ] Any requirement is not implemented
- [ ] Any test is failing
- [ ] Edge cases are not handled
- [ ] Bugs or issues found in code review
- [ ] Code doesn't follow project patterns

## Output Format

### If APPROVING:

```json
{
  "decision": "approve",
  "task_id": "TASK-001",
  "requirements_verified": [
    {
      "requirement": "OAuth2 flow with PKCE",
      "status": "met",
      "evidence": "Implemented in google_provider.py using authlib PKCE"
    },
    {
      "requirement": "Token refresh",
      "status": "met", 
      "evidence": "test_token_refresh_on_expiry passes"
    }
  ],
  "tests_verified": {
    "total": 4,
    "passed": 4,
    "failed": 0
  },
  "rationale": "All 4 requirements verified. Tests pass. Code follows existing patterns.",
  "contracts_honored": {
    "validate_implementation_called": true,
    "record_decision_called": true,
    "independent_verification": true
  }
}
```

### If Providing FEEDBACK:

```json
{
  "decision": "feedback",
  "task_id": "TASK-001",
  "requirements_verified": [
    {
      "requirement": "OAuth2 flow with PKCE",
      "status": "met",
      "evidence": "Implemented correctly"
    },
    {
      "requirement": "Handle invalid credentials",
      "status": "not_met",
      "issue": "No error handling when credentials are revoked"
    }
  ],
  "tests_verified": {
    "total": 4,
    "passed": 3,
    "failed": 1,
    "failures": ["test_revoked_credentials - no test exists"]
  },
  "feedback_items": [
    {
      "severity": "high",
      "file": "src/auth/google_provider.py",
      "line": 87,
      "issue": "No handling for revoked credentials",
      "suggestion": "Add try/catch for TokenRevokedError"
    },
    {
      "severity": "medium",
      "file": "tests/test_oauth.py",
      "issue": "Missing test for revoked credentials scenario",
      "suggestion": "Add test_revoked_credentials test case"
    }
  ],
  "rationale": "3 of 4 requirements met. Missing error handling for revoked credentials.",
  "contracts_honored": {
    "validate_implementation_called": true,
    "record_decision_called": true,
    "independent_verification": true
  }
}
```

## Feedback Quality Guidelines

### Good Feedback:
✅ "src/auth/google_provider.py line 87: No handling for TokenRevokedError. Add try/catch."
✅ "Missing test: test_revoked_credentials should verify graceful handling of revoked tokens"
✅ "Requirement 'secure token storage' not met: tokens stored in plain text config file"

### Bad Feedback:
❌ "The code has issues" (not specific)
❌ "Tests need improvement" (not actionable)
❌ "Doesn't look right" (not helpful)

## What NOT To Do

❌ Trust the Player's claim that "all tests pass"
❌ Approve without running tests yourself
❌ Skip checking any requirements
❌ Provide vague feedback
❌ Approve because "it looks mostly done"

## What To Do

✅ Run tests independently
✅ Read actual code, not just Player's summary
✅ Check every requirement explicitly
✅ Provide specific, actionable feedback
✅ Only approve when truly complete
```

---

## Python Support Functions

```python
# guardkit/agents/coach.py
from typing import List, Dict, Optional
from enum import Enum
from guardkit.sdk.tracing import get_trace
import time

class CoachDecision(Enum):
    APPROVE = "approve"
    FEEDBACK = "feedback"

def validate_implementation(
    task_id: str,
    requirements: List[str],
    player_report: dict
) -> dict:
    """
    Set up validation context for coach.
    
    Must be called at the START of coach's work.
    
    Returns context dict with requirements and files to review.
    """
    trace = get_trace(task_id)
    trace.log_python_call("validate_implementation")
    trace.log_event("coach_validate_start", {
        "requirements_count": len(requirements),
        "player_files": player_report.get("files_modified", []),
        "player_tests": player_report.get("tests_written", []),
        "timestamp": time.time()
    })
    
    return {
        "task_id": task_id,
        "requirements": requirements,
        "files_to_review": player_report.get("files_modified", []),
        "tests_to_run": player_report.get("tests_written", []),
        "player_notes": player_report.get("implementation_notes", ""),
        "player_concerns": player_report.get("concerns", [])
    }

def record_decision(
    task_id: str,
    decision: str,
    rationale: str,
    feedback_items: Optional[List[dict]] = None,
    requirements_status: Optional[List[dict]] = None
) -> dict:
    """
    Record coach decision for orchestrator.
    
    Must be called at the END of coach's work.
    
    Args:
        task_id: The task being validated
        decision: "approve" or "feedback"
        rationale: Why this decision was made
        feedback_items: List of specific issues (if decision is feedback)
        requirements_status: Status of each requirement checked
    """
    trace = get_trace(task_id)
    trace.log_python_call("record_decision")
    trace.log_event("coach_decision", {
        "decision": decision,
        "rationale": rationale,
        "feedback_count": len(feedback_items) if feedback_items else 0,
        "timestamp": time.time()
    })
    
    # Store feedback for player's next iteration
    if feedback_items:
        trace.log_event("coach_feedback", {
            "items": feedback_items,
            "requirements_status": requirements_status or []
        })
    
    return {
        "task_id": task_id,
        "decision": decision,
        "rationale": rationale,
        "feedback_items": feedback_items or [],
        "is_approved": decision == "approve"
    }

def get_validation_history(task_id: str) -> List[dict]:
    """
    Get history of coach validations for this task.
    
    Useful for seeing how many iterations have occurred.
    """
    trace = get_trace(task_id)
    
    return [
        event.data for event in trace.events
        if event.event_type == "coach_decision"
    ]
```

---

## File Structure

```
guardkit/
├── agents/
│   ├── __init__.py
│   ├── player.py            # Player support functions
│   └── coach.py             # Coach support functions

.claude/
├── agents/
│   ├── autobuild-player.md  # Player agent instructions
│   └── autobuild-coach.md   # Coach agent instructions
```

---

## Acceptance Criteria

- [ ] Coach agent instructions created in `.claude/agents/autobuild-coach.md`
- [ ] Agent frontmatter includes model selection (`sonnet`)
- [ ] Agent frontmatter includes contract requirements
- [ ] Python support functions implemented in `guardkit/agents/coach.py`
- [ ] `validate_implementation()` logs to trace
- [ ] `record_decision()` logs to trace with decision details
- [ ] Coach independently verifies (doesn't trust Player)
- [ ] Coach provides specific, actionable feedback
- [ ] Coach decisions are logged for orchestrator
- [ ] Only Coach can approve task completion
- [ ] Feedback items include file, line, issue, suggestion

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_coach.py
from guardkit.agents.coach import validate_implementation, record_decision
from guardkit.sdk.tracing import get_trace, _traces

def setup_function():
    _traces.clear()

def test_validate_implementation_logs_trace():
    player_report = {
        "files_modified": ["src/test.py"],
        "tests_written": ["test_feature"]
    }
    
    result = validate_implementation(
        task_id="TASK-001",
        requirements=["req1", "req2"],
        player_report=player_report
    )
    
    assert result["task_id"] == "TASK-001"
    assert len(result["requirements"]) == 2
    
    trace = get_trace("TASK-001")
    assert "validate_implementation" in trace.python_calls

def test_record_decision_approve():
    result = record_decision(
        task_id="TASK-001",
        decision="approve",
        rationale="All requirements met"
    )
    
    assert result["is_approved"] == True
    
    trace = get_trace("TASK-001")
    assert "record_decision" in trace.python_calls
    
    decision_events = [e for e in trace.events if e.event_type == "coach_decision"]
    assert len(decision_events) == 1
    assert decision_events[0].data["decision"] == "approve"

def test_record_decision_feedback():
    feedback_items = [
        {"file": "src/test.py", "line": 42, "issue": "Missing null check"}
    ]
    
    result = record_decision(
        task_id="TASK-001",
        decision="feedback",
        rationale="Missing error handling",
        feedback_items=feedback_items
    )
    
    assert result["is_approved"] == False
    assert len(result["feedback_items"]) == 1
    
    trace = get_trace("TASK-001")
    feedback_events = [e for e in trace.events if e.event_type == "coach_feedback"]
    assert len(feedback_events) == 1

def test_contract_verification():
    validate_implementation("TASK-001", ["req"], {"files_modified": []})
    record_decision("TASK-001", "approve", "LGTM")
    
    trace = get_trace("TASK-001")
    
    assert trace.verify_contract([
        "validate_implementation",
        "record_decision"
    ])
```

### Contract Tests

```python
# tests/contract/test_coach_contract.py

def test_coach_output_has_required_fields(coach_output: dict):
    """Verify coach output structure."""
    required_fields = ["decision", "task_id", "rationale"]
    
    for field in required_fields:
        assert field in coach_output

def test_feedback_has_required_fields(feedback_item: dict):
    """Verify feedback item structure."""
    required_fields = ["file", "issue"]
    
    for field in required_fields:
        assert field in feedback_item

def test_coach_provides_specific_feedback(coach_output: dict):
    """Verify feedback is specific, not vague."""
    if coach_output["decision"] == "feedback":
        for item in coach_output.get("feedback_items", []):
            # Must have file reference
            assert "file" in item and item["file"]
            # Must have specific issue
            assert "issue" in item and len(item["issue"]) > 10
```

---

## Example Coach Execution

### Input (from Orchestrator)

```
## Task: TASK-001
Validate Player implementation of OAuth2 authentication

## Original Requirements
1. Implement OAuth2 flow with PKCE
2. Support token refresh
3. Handle invalid credentials gracefully
4. Store tokens securely

## Player Report
{
  "files_modified": ["src/auth/oauth_service.py", "src/auth/google_provider.py"],
  "tests_written": ["test_google_auth_flow", "test_token_refresh"],
  "implementation_notes": "Implemented OAuth2 with authlib",
  "concerns": ["Not sure about keyring availability"]
}
```

### Output (FEEDBACK example)

```json
{
  "decision": "feedback",
  "task_id": "TASK-001",
  "requirements_verified": [
    {
      "requirement": "OAuth2 flow with PKCE",
      "status": "met",
      "evidence": "PKCE implemented correctly in google_provider.py"
    },
    {
      "requirement": "Token refresh",
      "status": "met",
      "evidence": "test_token_refresh passes"
    },
    {
      "requirement": "Handle invalid credentials",
      "status": "not_met",
      "issue": "No error handling for invalid/expired credentials"
    },
    {
      "requirement": "Secure token storage",
      "status": "not_met",
      "issue": "Tokens stored in plain text file, not keyring"
    }
  ],
  "tests_verified": {
    "total": 2,
    "passed": 2,
    "failed": 0,
    "missing": ["test_invalid_credentials", "test_secure_storage"]
  },
  "feedback_items": [
    {
      "severity": "high",
      "file": "src/auth/google_provider.py",
      "line": 45,
      "issue": "No exception handling for invalid credentials",
      "suggestion": "Add try/catch for AuthenticationError and return user-friendly message"
    },
    {
      "severity": "high",
      "file": "src/auth/oauth_service.py",
      "line": 78,
      "issue": "Tokens written to tokens.json in plain text",
      "suggestion": "Use keyring library for secure storage, with fallback for systems without keyring"
    },
    {
      "severity": "medium",
      "file": "tests/test_oauth.py",
      "issue": "Missing test coverage",
      "suggestion": "Add test_invalid_credentials and test_secure_storage tests"
    }
  ],
  "rationale": "2 of 4 requirements met. Missing error handling and secure storage.",
  "contracts_honored": {
    "validate_implementation_called": true,
    "record_decision_called": true,
    "independent_verification": true
  }
}
```

---

## References

- Adversarial Cooperation: Block AI Research paper
- Main spec: `AutoBuild_Product_Specification.md`
- Player agent: `FEATURE-003-player-agent.md`
