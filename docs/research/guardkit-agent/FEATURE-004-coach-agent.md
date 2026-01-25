# FEATURE-004: Coach Agent (SubAgent Definition)

> **Status**: Simplified to use DeepAgents SubAgentMiddleware
> **Effort**: 1 day (down from 1-2 days)
> **Dependencies**: F2 (DeepAgents Infrastructure)
> **Enables**: F5 (Orchestrator)

---

## Overview

The Coach Agent is the "validation-focused" agent in the adversarial cooperation pattern. It reviews the Player's implementation against requirements, runs validation checks, and either approves or provides specific feedback.

**With DeepAgents**, the Coach is defined as a SubAgent configuration. This provides context isolation from the orchestrator while allowing custom model selection (Sonnet for better reasoning).

---

## SubAgent Definition

```python
# guardkit/agents/coach.py
from typing import Sequence
from langchain_core.tools import tool

# Coach SubAgent configuration for DeepAgents
COACH_SUBAGENT = {
    "name": "coach",
    "description": "Validation-focused agent that reviews implementation against requirements",
    "system_prompt": COACH_INSTRUCTIONS,  # See below
    "tools": COACH_TOOLS,
    "model": "anthropic:claude-sonnet-4-5-20250929",  # Better reasoning
}
```

---

## Coach Instructions

```python
# guardkit/agents/coach.py

COACH_INSTRUCTIONS = """
# Coach Agent - Validation Focus

You are the Coach agent in an adversarial cooperation system. Your role is to critically review the Player's implementation and ensure it meets requirements.

## Your Responsibilities

1. **Review** - Examine all code changes critically
2. **Validate** - Run tests and verify functionality
3. **Assess** - Compare implementation against requirements
4. **Decide** - Approve or provide specific feedback

## Reading Player's Report

First, read the Player's report from:
`/coordination/player/turn_{turn}/report.json`

This tells you:
- Which files were modified
- Which tests were written
- The Player's implementation notes
- Any concerns the Player flagged

## Validation Checklist

Before making your decision, verify:

### Code Quality
- [ ] Code follows project conventions
- [ ] Functions are well-named and focused
- [ ] Error handling is appropriate
- [ ] No obvious security issues

### Testing
- [ ] Tests exist for new functionality
- [ ] Tests actually pass (run them!)
- [ ] Tests cover edge cases
- [ ] Test names are descriptive

### Requirements
- [ ] All acceptance criteria are met
- [ ] No requirements were missed
- [ ] No scope creep (extra unrequested features)

### Integration
- [ ] Changes don't break existing functionality
- [ ] Dependencies are properly declared
- [ ] No hardcoded values that should be config

## Making Your Decision

After validation, write your decision to:
`/coordination/coach/turn_{turn}/decision.json`

### If APPROVING:

```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "approve",
  "rationale": "Clear explanation of why the implementation is acceptable",
  "feedback_items": [],
  "severity": "minor"
}
```

### If Providing FEEDBACK:

```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "feedback",
  "rationale": "Overall assessment of what needs improvement",
  "feedback_items": [
    "Specific issue #1 with actionable fix",
    "Specific issue #2 with actionable fix"
  ],
  "severity": "major"
}
```

## Feedback Guidelines

When providing feedback:

1. **Be Specific** - Point to exact files and line numbers
2. **Be Actionable** - Explain HOW to fix, not just WHAT is wrong
3. **Prioritize** - List most important issues first
4. **Be Fair** - Don't nitpick if the implementation is fundamentally sound

### Severity Levels

- **minor**: Small issues, mostly style or minor improvements
- **major**: Significant issues that affect functionality or maintainability
- **critical**: Blocking issues like failing tests, security problems, or missing core functionality

## What NOT to Do

- Don't approve incomplete implementations
- Don't fail work for subjective style preferences
- Don't add new requirements not in the original spec
- Don't provide vague feedback like "needs improvement"

## The Adversarial Mindset

Your job is to be a helpful critic, not an antagonist:
- **Goal**: Help produce quality code, not block progress
- **Approach**: Specific, actionable, fair criticism
- **Standard**: Would you approve this for production?

## Escalation

If you encounter:
- Security vulnerabilities
- Fundamental misunderstanding of requirements
- Issues that can't be fixed in remaining turns

Set severity to "critical" and explain clearly in your rationale.

## Remember

The Player is trying their best. Your feedback should help them succeed, not demoralize them. Be critical but constructive.
"""
```

---

## Coach Tools

```python
# guardkit/agents/coach_tools.py
from langchain_core.tools import tool
import subprocess
import json

@tool
def run_all_tests() -> str:
    """
    Run the full test suite and return results.
    
    Returns:
        Test output with pass/fail counts
    """
    result = subprocess.run(
        ["pytest", "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}"


@tool
def run_specific_tests(test_paths: list[str]) -> str:
    """
    Run specific test files.
    
    Args:
        test_paths: List of test file paths to run
    
    Returns:
        Test results
    """
    result = subprocess.run(
        ["pytest", "-v", "--tb=short"] + test_paths,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return f"Exit code: {result.returncode}\n\n{result.stdout}\n{result.stderr}"


@tool
def check_coverage(source_path: str) -> str:
    """
    Check test coverage for a source file.
    
    Args:
        source_path: Path to source file
    
    Returns:
        Coverage percentage and uncovered lines
    """
    result = subprocess.run(
        ["pytest", "--cov=" + source_path, "--cov-report=term-missing", "-q"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout


@tool
def diff_changes() -> str:
    """
    Show git diff of all changes made by Player.
    
    Returns:
        Git diff output
    """
    result = subprocess.run(
        ["git", "diff", "--stat"],
        capture_output=True,
        text=True,
    )
    summary = result.stdout
    
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
    )
    
    if len(result.stdout) > 10000:
        return f"Summary:\n{summary}\n\n(Full diff truncated - {len(result.stdout)} chars)"
    
    return f"Summary:\n{summary}\n\nFull diff:\n{result.stdout}"


@tool
def validate_json_schema(file_path: str, expected_keys: list[str]) -> str:
    """
    Validate that a JSON file has expected structure.
    
    Args:
        file_path: Path to JSON file
        expected_keys: List of keys that must be present
    
    Returns:
        Validation result
    """
    try:
        with open(file_path) as f:
            data = json.load(f)
        
        missing = [k for k in expected_keys if k not in data]
        if missing:
            return f"INVALID: Missing keys: {missing}"
        return "VALID: All expected keys present"
    except json.JSONDecodeError as e:
        return f"INVALID: JSON parse error: {e}"
    except FileNotFoundError:
        return f"INVALID: File not found: {file_path}"


# Collect all coach tools
COACH_TOOLS = [
    run_all_tests,
    run_specific_tests,
    check_coverage,
    diff_changes,
    validate_json_schema,
]
```

---

## Complete SubAgent Configuration

```python
# guardkit/agents/coach.py

from guardkit.agents.coach_instructions import COACH_INSTRUCTIONS
from guardkit.agents.coach_tools import COACH_TOOLS

def create_coach_subagent(model: str = "anthropic:claude-sonnet-4-5-20250929"):
    """
    Create Coach SubAgent configuration for DeepAgents.
    
    Args:
        model: Model to use for Coach (default: Sonnet for better reasoning)
    
    Returns:
        SubAgent configuration dict
    """
    return {
        "name": "coach",
        "description": (
            "Validation-focused agent that reviews implementation against requirements. "
            "Use this agent to validate code changes, run tests, and provide feedback. "
            "The coach either approves work or provides specific, actionable feedback."
        ),
        "system_prompt": COACH_INSTRUCTIONS,
        "tools": COACH_TOOLS,
        "model": model,
    }
```

---

## Decision Format

The Coach writes decisions to the coordination filesystem:

### Approval Decision

```json
// /coordination/coach/turn_1/decision.json
{
  "task_id": "TASK-001",
  "turn": 1,
  "decision": "approve",
  "rationale": "Implementation correctly handles OAuth2 authorization code flow with PKCE. All tests pass (12/12). Code follows project conventions. Token refresh logic is well-implemented with appropriate error handling.",
  "feedback_items": [],
  "severity": "minor"
}
```

### Feedback Decision

```json
// /coordination/coach/turn_1/decision.json
{
  "task_id": "TASK-001",
  "turn": 1,
  "decision": "feedback",
  "rationale": "Core OAuth flow is implemented but several issues need attention before approval.",
  "feedback_items": [
    "CRITICAL: Token storage in memory will be lost on restart. Use Redis or database storage (src/auth/oauth.py:45)",
    "MAJOR: Missing test for token expiration handling - add test case for expired token refresh",
    "MINOR: Consider extracting magic number 3600 to TOKEN_LIFETIME_SECONDS constant"
  ],
  "severity": "major"
}
```

---

## File Structure

```
guardkit/
├── agents/
│   ├── __init__.py
│   ├── coach.py                # SubAgent config + create_coach_subagent()
│   ├── coach_instructions.py   # COACH_INSTRUCTIONS constant
│   └── coach_tools.py          # run_all_tests, diff_changes, etc.
```

---

## Integration with Orchestrator

The Coach is invoked by the orchestrator after Player completes:

```python
# In orchestrator flow:
# 1. Player writes report to /coordination/player/turn_N/report.json
# 2. Orchestrator invokes Coach via task tool
# 3. Coach reads Player's report, validates, writes decision
# 4. Orchestrator reads decision and routes accordingly

# DeepAgents handles context isolation automatically
```

---

## Testing

### Unit Tests

```python
# tests/unit/agents/test_coach.py
import pytest
from guardkit.agents.coach import create_coach_subagent, COACH_INSTRUCTIONS

def test_coach_subagent_has_required_fields():
    subagent = create_coach_subagent()
    assert subagent["name"] == "coach"
    assert "description" in subagent
    assert "system_prompt" in subagent
    assert "tools" in subagent
    assert "model" in subagent

def test_coach_instructions_contain_decision_protocol():
    assert "/coordination/coach/" in COACH_INSTRUCTIONS
    assert "decision.json" in COACH_INSTRUCTIONS
    assert "approve" in COACH_INSTRUCTIONS
    assert "feedback" in COACH_INSTRUCTIONS

def test_coach_uses_sonnet_by_default():
    subagent = create_coach_subagent()
    assert "sonnet" in subagent["model"]

def test_coach_model_configurable():
    subagent = create_coach_subagent(model="anthropic:claude-3-opus-20240229")
    assert "opus" in subagent["model"]
```

### Integration Tests

```python
# tests/integration/agents/test_coach_execution.py
import pytest
from deepagents import create_deep_agent
from guardkit.agents.coach import create_coach_subagent

@pytest.mark.integration
async def test_coach_can_be_invoked():
    """Test that Coach subagent can be invoked via task tool."""
    agent = create_deep_agent(
        model="anthropic:claude-3-5-haiku-20241022",
        subagents=[create_coach_subagent()],
    )
    
    # First write a mock player report
    setup_result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": 'Write this to /coordination/player/turn_1/report.json: {"task_id": "TEST-001", "turn": 1, "files_modified": ["test.py"], "tests_written": [], "implementation_notes": "test", "concerns": []}'
        }]
    })
    
    # Then invoke coach
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Use the coach agent to review the player's work for turn 1"
        }]
    })
    
    assert result is not None
```

---

## Acceptance Criteria

- [ ] `create_coach_subagent()` returns valid SubAgent configuration
- [ ] Coach instructions include decision protocol
- [ ] Coach tools (`run_all_tests`, `diff_changes`, etc.) work correctly
- [ ] Coach can be invoked via DeepAgents `task` tool
- [ ] Coach reads Player reports from `/coordination/player/turn_N/report.json`
- [ ] Coach writes decisions to `/coordination/coach/turn_N/decision.json`
- [ ] Decision format matches schema (approve/feedback)
- [ ] Unit tests pass
- [ ] Integration test passes

---

## Migration Notes

### What Changed from Original Design

| Original | DeepAgents-Based |
|----------|------------------|
| Custom `CoachAgent` class | SubAgent configuration dict |
| Custom execution wrapper | DeepAgents `task` tool |
| Custom context management | DeepAgents context isolation |
| Complex decision logic | Simplified via instructions |
| 1-2 days effort | 1 day effort |

### What We Keep

- Coach instructions (the "soul" of the agent)
- Coach tools (run_all_tests, diff_changes, etc.)
- Decision format specification
- Coordination protocol via filesystem
- Different model from Player (Sonnet vs Haiku)

---

## References

- [DeepAgents SubAgents](https://docs.langchain.com/oss/python/deepagents/middleware#subagentmiddleware)
- [FEATURE-002: DeepAgents Infrastructure](./FEATURE-002-agent-sdk-infrastructure.md)
- [FEATURE-003: Player Agent](./FEATURE-003-player-agent.md)
- [Adversarial Cooperation Paper](../adversarial-cooperation-in-code-synthesis.pdf)
