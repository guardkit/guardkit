# Feature 3: Player Agent

> **Feature ID**: FEATURE-003
> **Priority**: P0 (Core agent)
> **Estimated Effort**: 1-2 days
> **Dependencies**: FEATURE-002 (Agent SDK Infrastructure)

---

## Summary

Create the Player agent - the implementation-focused agent in the adversarial cooperation pattern. The Player reads requirements, implements solutions, and writes tests. Critically, the Player does NOT self-validate success; that's the Coach's job.

---

## The Adversarial Cooperation Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Player                              Coach                 │
│   ──────                              ─────                 │
│   • Implements                        • Validates           │
│   • Writes tests                      • Runs tests          │
│   • Reports what was done             • Checks requirements │
│   • NEVER says "complete"             • ONLY one who can    │
│                                         approve completion  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Definition

### Frontmatter

```yaml
# .claude/agents/autobuild-player.md
---
name: autobuild-player
description: Implementation agent for AutoBuild adversarial loop
model: haiku  # Cost-efficient for implementation tasks
triggers: []  # Only invoked by orchestrator, not by triggers
stack: any    # Works with any technology stack

contracts:
  must_call:
    - guardkit.agents.player.start_implementation
    - guardkit.agents.player.report_progress
  must_not:
    - declare task complete
    - self-validate success
    - claim requirements are met
  must_output:
    - structured JSON report
    - list of files modified
    - list of tests written

collaborates_with:
  - autobuild-coach  # Receives validation from coach
---
```

### Agent Instructions

```markdown
## Your Role: PLAYER (Implementation)

You are the implementation agent in an adversarial cooperation loop. Your job is to implement features based on requirements. You do NOT validate your own work - that's the Coach's job.

## Critical Rules

1. **NEVER say "task complete"** - Only the Coach can declare completion
2. **NEVER self-validate** - Don't claim "all requirements met" or "tests pass"
3. **ALWAYS report factually** - State what you did, not whether it's correct
4. **ALWAYS be specific** - List exact files, functions, and tests created

## Your Workflow

1. **Read Requirements**
   - Understand what needs to be built
   - Note acceptance criteria
   - Identify edge cases

2. **Analyze Codebase**
   - Find relevant patterns
   - Identify files to modify
   - Note dependencies

3. **Implement Solution**
   - Write clean, tested code
   - Follow existing patterns
   - Handle edge cases

4. **Write Tests**
   - Unit tests for new functions
   - Integration tests if needed
   - Cover edge cases

5. **Report Progress**
   - List files modified
   - List tests written
   - Note any concerns (NOT whether it's correct)

## Required Python Calls

You MUST call these functions. Do NOT implement this functionality yourself.

```python
from guardkit.agents.player import start_implementation, report_progress

# At the START of your work (after reading requirements):
start_implementation(
    task_id="TASK-001",
    approach_summary="Creating OAuth service with Google provider"
)

# At the END of your work (before final output):
report_progress(
    task_id="TASK-001",
    files_modified=[
        "src/auth/oauth_service.py",
        "src/auth/google_provider.py",
        "tests/test_oauth_service.py"
    ],
    tests_written=[
        "test_google_auth_flow",
        "test_token_refresh",
        "test_invalid_credentials"
    ],
    implementation_notes="Implemented OAuth2 flow with PKCE. Added token refresh logic."
)
```

## Output Format

End your work with this EXACT JSON structure:

```json
{
  "status": "implementation_complete",
  "task_id": "TASK-001",
  "files_modified": [
    "src/auth/oauth_service.py",
    "src/auth/google_provider.py",
    "tests/test_oauth_service.py"
  ],
  "files_created": [
    "src/auth/google_provider.py"
  ],
  "tests_written": [
    "test_google_auth_flow",
    "test_token_refresh",
    "test_invalid_credentials"
  ],
  "implementation_notes": "What you implemented and any technical decisions",
  "concerns": ["Any edge cases you're unsure about"],
  "ready_for_validation": true,
  "contracts_honored": {
    "start_implementation_called": true,
    "report_progress_called": true,
    "no_completion_claims": true
  }
}
```

## What NOT To Do

❌ "The task is complete and all requirements are met."
❌ "Tests are passing so the implementation is correct."
❌ "I've verified that everything works."
❌ Skipping the Python function calls
❌ Claiming success in any form

## What To Do

✅ "I implemented X, Y, and Z. Files modified: [list]. Tests written: [list]."
✅ "I'm unsure about edge case X - the Coach should verify."
✅ "I added tests for A, B, C. The Coach should verify coverage."
✅ Calling start_implementation() and report_progress()
✅ Factual reporting without success claims

## Handling Coach Feedback

When you receive feedback from the Coach:

1. **Read feedback carefully** - Understand exactly what needs fixing
2. **Address each item** - Don't skip any feedback
3. **Report what you changed** - Be specific about fixes
4. **Don't argue** - Just fix and report

Example response to feedback:

```json
{
  "status": "implementation_complete",
  "task_id": "TASK-001",
  "feedback_addressed": [
    {
      "feedback": "Missing null check in oauth_service.py line 42",
      "fix": "Added null check with appropriate error handling"
    },
    {
      "feedback": "test_invalid_credentials doesn't cover timeout case",
      "fix": "Added test_timeout_handling test case"
    }
  ],
  "files_modified": ["src/auth/oauth_service.py", "tests/test_oauth_service.py"],
  "tests_written": ["test_timeout_handling"],
  "ready_for_validation": true
}
```
```

---

## Python Support Functions

```python
# guardkit/agents/player.py
from typing import List, Optional
from guardkit.sdk.tracing import get_trace
import time

def start_implementation(task_id: str, approach_summary: str) -> dict:
    """
    Log start of implementation for tracing and contract verification.
    
    Must be called at the START of player's work.
    """
    trace = get_trace(task_id)
    trace.log_python_call("start_implementation")
    trace.log_event("player_start", {
        "approach": approach_summary,
        "timestamp": time.time()
    })
    
    return {
        "status": "started",
        "task_id": task_id,
        "approach": approach_summary
    }

def report_progress(
    task_id: str,
    files_modified: List[str],
    tests_written: List[str],
    implementation_notes: str,
    concerns: Optional[List[str]] = None
) -> dict:
    """
    Report implementation progress for coach validation.
    
    Must be called at the END of player's work.
    """
    trace = get_trace(task_id)
    trace.log_python_call("report_progress")
    trace.log_event("player_report", {
        "files_modified": files_modified,
        "tests_written": tests_written,
        "notes": implementation_notes,
        "concerns": concerns or [],
        "timestamp": time.time()
    })
    
    return {
        "status": "reported",
        "task_id": task_id,
        "files_count": len(files_modified),
        "tests_count": len(tests_written)
    }

def get_previous_feedback(task_id: str) -> Optional[dict]:
    """
    Get previous coach feedback for this task (if any).
    
    Called automatically by orchestrator, but available for player use.
    """
    trace = get_trace(task_id)
    
    # Find most recent coach feedback event
    for event in reversed(trace.events):
        if event.event_type == "coach_feedback":
            return event.data
    
    return None
```

---

## File Structure

```
guardkit/
├── agents/
│   ├── __init__.py
│   └── player.py            # Player support functions

.claude/
├── agents/
│   └── autobuild-player.md  # Player agent instructions
```

---

## Acceptance Criteria

- [ ] Player agent instructions created in `.claude/agents/autobuild-player.md`
- [ ] Agent frontmatter includes model selection (`haiku`)
- [ ] Agent frontmatter includes contract requirements
- [ ] Python support functions implemented in `guardkit/agents/player.py`
- [ ] `start_implementation()` logs to trace
- [ ] `report_progress()` logs to trace
- [ ] Player NEVER declares task complete (verified via contract)
- [ ] Player output is structured JSON
- [ ] Player reports are consumable by Coach
- [ ] Trace captures all player actions

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_player.py
from guardkit.agents.player import start_implementation, report_progress
from guardkit.sdk.tracing import get_trace, _traces

def setup_function():
    _traces.clear()

def test_start_implementation_logs_trace():
    result = start_implementation("TASK-001", "Test approach")
    
    assert result["status"] == "started"
    
    trace = get_trace("TASK-001")
    assert "start_implementation" in trace.python_calls
    assert any(e.event_type == "player_start" for e in trace.events)

def test_report_progress_logs_trace():
    result = report_progress(
        task_id="TASK-001",
        files_modified=["src/test.py"],
        tests_written=["test_feature"],
        implementation_notes="Implemented feature"
    )
    
    assert result["status"] == "reported"
    
    trace = get_trace("TASK-001")
    assert "report_progress" in trace.python_calls
    assert any(e.event_type == "player_report" for e in trace.events)

def test_contract_verification():
    start_implementation("TASK-001", "Test")
    report_progress("TASK-001", ["file.py"], ["test"], "notes")
    
    trace = get_trace("TASK-001")
    
    assert trace.verify_contract([
        "start_implementation",
        "report_progress"
    ])
```

### Contract Tests

```python
# tests/contract/test_player_contract.py

def test_player_output_has_required_fields(player_output: dict):
    """Verify player output structure."""
    required_fields = [
        "status",
        "task_id", 
        "files_modified",
        "tests_written",
        "ready_for_validation"
    ]
    
    for field in required_fields:
        assert field in player_output, f"Missing required field: {field}"

def test_player_does_not_claim_completion(player_output: dict):
    """Verify player doesn't claim task completion."""
    forbidden_phrases = [
        "task complete",
        "task completed",
        "requirements met",
        "all requirements",
        "successfully completed",
        "implementation is correct"
    ]
    
    output_text = str(player_output).lower()
    
    for phrase in forbidden_phrases:
        assert phrase not in output_text, f"Player claimed completion: '{phrase}'"
```

---

## Example Player Execution

### Input (from Orchestrator)

```
## Task: TASK-001
Create OAuth2 authentication service with Google provider

## Requirements
1. Implement OAuth2 flow with PKCE
2. Support token refresh
3. Handle invalid credentials gracefully
4. Store tokens securely

## Acceptance Criteria
- [ ] User can authenticate with Google
- [ ] Tokens refresh automatically when expired
- [ ] Invalid credentials show user-friendly error
- [ ] Tokens stored in secure storage (not plain text)
```

### Output (to Coach)

```json
{
  "status": "implementation_complete",
  "task_id": "TASK-001",
  "files_modified": [
    "src/auth/oauth_service.py",
    "src/auth/google_provider.py", 
    "src/auth/token_storage.py",
    "tests/test_oauth.py"
  ],
  "files_created": [
    "src/auth/google_provider.py",
    "src/auth/token_storage.py"
  ],
  "tests_written": [
    "test_google_auth_flow",
    "test_token_refresh_on_expiry",
    "test_invalid_credentials_error",
    "test_secure_token_storage"
  ],
  "implementation_notes": "Implemented OAuth2 with PKCE using authlib. Token storage uses system keyring for security. Added exponential backoff for token refresh failures.",
  "concerns": [
    "Not sure if keyring is available on all platforms - Coach should verify"
  ],
  "ready_for_validation": true,
  "contracts_honored": {
    "start_implementation_called": true,
    "report_progress_called": true,
    "no_completion_claims": true
  }
}
```

---

## References

- Adversarial Cooperation: Block AI Research paper
- Main spec: `AutoBuild_Product_Specification.md`
- Coach agent: `FEATURE-004-coach-agent.md`
