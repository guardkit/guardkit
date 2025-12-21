# FEATURE-003: Player Agent (SubAgent Definition)

> **Status**: Simplified to use DeepAgents SubAgentMiddleware
> **Effort**: 1 day (down from 1-2 days)
> **Dependencies**: F2 (DeepAgents Infrastructure)
> **Enables**: F5 (Orchestrator)

---

## Overview

The Player Agent is the "implementation-focused" agent in the adversarial cooperation pattern. It receives task requirements, writes code, creates tests, and reports its work for Coach review.

**With DeepAgents**, the Player is defined as a SubAgent configuration rather than a custom agent class. This simplifies implementation while providing context isolation and custom model selection.

---

## SubAgent Definition

```python
# guardkit/agents/player.py
from typing import Sequence
from langchain_core.tools import tool

# Player SubAgent configuration for DeepAgents
PLAYER_SUBAGENT = {
    "name": "player",
    "description": "Implementation-focused agent that writes code to satisfy task requirements",
    "system_prompt": PLAYER_INSTRUCTIONS,  # See below
    "tools": [],  # Player uses filesystem tools from DeepAgents
    "model": "anthropic:claude-3-5-haiku-20241022",  # Cost-efficient
}
```

---

## Player Instructions

```python
# guardkit/agents/player.py

PLAYER_INSTRUCTIONS = """
# Player Agent - Implementation Focus

You are the Player agent in an adversarial cooperation system. Your role is to implement code that satisfies the given requirements.

## Your Responsibilities

1. **Implement** - Write clean, working code that meets requirements
2. **Test** - Create tests that verify your implementation
3. **Document** - Add appropriate comments and docstrings
4. **Report** - Write a structured report of your work

## Working Directory

You are working in an isolated git worktree. All file operations are safe and won't affect the main codebase until approved.

## Coordination Protocol

After completing your implementation:

1. Write your report to: `/coordination/player/turn_{turn}/report.json`
2. Use this exact JSON structure:

```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "files_modified": [
    "path/to/file.py"
  ],
  "tests_written": [
    "tests/test_feature.py"
  ],
  "implementation_notes": "Description of what was implemented and key decisions",
  "concerns": [
    "Any concerns or uncertainties about the implementation"
  ]
}
```

## Guidelines

### Code Quality
- Follow existing project conventions
- Write self-documenting code with clear names
- Keep functions focused and small
- Handle errors appropriately

### Testing
- Write tests BEFORE or ALONGSIDE implementation
- Cover happy path and edge cases
- Use descriptive test names
- Ensure tests actually run and pass

### If You're Stuck
- Document what you tried in your concerns
- Explain what information would help
- Don't guess - be explicit about uncertainties

## What NOT to Do

- Don't modify files outside the task scope
- Don't skip tests to save time
- Don't leave TODO comments without explanation
- Don't assume the Coach will accept incomplete work

## Remember

The Coach will review your work critically. Your goal is to produce implementation that:
1. Fully satisfies the requirements
2. Has passing tests
3. Is well-documented
4. Has no obvious issues

Take pride in your work - incomplete or sloppy implementations will be sent back for revision.
"""
```

---

## Player Tools

The Player uses DeepAgents' built-in filesystem tools plus any project-specific tools:

```python
# guardkit/agents/player.py
from langchain_core.tools import tool

@tool
def run_tests(test_path: str = "tests/") -> str:
    """
    Run tests and return results.
    
    Args:
        test_path: Path to test file or directory
    
    Returns:
        Test output including pass/fail status
    """
    import subprocess
    result = subprocess.run(
        ["pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return f"Exit code: {result.returncode}\n\nOutput:\n{result.stdout}\n\nErrors:\n{result.stderr}"


@tool
def check_syntax(file_path: str) -> str:
    """
    Check Python file for syntax errors.
    
    Args:
        file_path: Path to Python file
    
    Returns:
        "OK" or error message
    """
    import ast
    try:
        with open(file_path) as f:
            ast.parse(f.read())
        return "OK - No syntax errors"
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"


@tool  
def lint_file(file_path: str) -> str:
    """
    Run linter on file and return issues.
    
    Args:
        file_path: Path to file to lint
    
    Returns:
        Linting results
    """
    import subprocess
    result = subprocess.run(
        ["ruff", "check", file_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return "No linting issues found"
    return result.stdout


# Collect all player tools
PLAYER_TOOLS = [run_tests, check_syntax, lint_file]
```

---

## Complete SubAgent Configuration

```python
# guardkit/agents/player.py

from guardkit.agents.player_instructions import PLAYER_INSTRUCTIONS
from guardkit.agents.player_tools import PLAYER_TOOLS

def create_player_subagent(model: str = "anthropic:claude-3-5-haiku-20241022"):
    """
    Create Player SubAgent configuration for DeepAgents.
    
    Args:
        model: Model to use for Player (default: Haiku for cost efficiency)
    
    Returns:
        SubAgent configuration dict
    """
    return {
        "name": "player",
        "description": (
            "Implementation-focused agent that writes code to satisfy task requirements. "
            "Use this agent to implement features, fix bugs, and write tests. "
            "The player works in an isolated environment and reports its work for review."
        ),
        "system_prompt": PLAYER_INSTRUCTIONS,
        "tools": PLAYER_TOOLS,
        "model": model,
    }
```

---

## Integration with Orchestrator

The Player is invoked by the orchestrator via DeepAgents' `task` tool:

```python
# In orchestrator, the task tool delegates to Player:
# agent.invoke({"messages": [{"role": "user", "content": "Use the player agent to implement TASK-001"}]})

# DeepAgents handles:
# 1. Spawning Player with isolated context
# 2. Passing the task to Player
# 3. Returning Player's response to orchestrator
# 4. Context isolation (Player's work doesn't pollute orchestrator context)
```

---

## File Structure

```
guardkit/
├── agents/
│   ├── __init__.py
│   ├── player.py              # SubAgent config + create_player_subagent()
│   ├── player_instructions.py # PLAYER_INSTRUCTIONS constant
│   └── player_tools.py        # run_tests, check_syntax, lint_file
```

---

## Report Format

The Player writes reports to the coordination filesystem:

```json
// /coordination/player/turn_1/report.json
{
  "task_id": "TASK-001",
  "turn": 1,
  "files_modified": [
    "src/auth/oauth.py",
    "src/auth/__init__.py"
  ],
  "tests_written": [
    "tests/auth/test_oauth.py"
  ],
  "implementation_notes": "Implemented OAuth2 authorization code flow with PKCE. Added token refresh logic with exponential backoff. Integrated with existing session management.",
  "concerns": [
    "Token storage uses in-memory cache - may need Redis for production",
    "Error messages expose internal details - should sanitize before release"
  ]
}
```

---

## Testing

### Unit Tests

```python
# tests/unit/agents/test_player.py
import pytest
from guardkit.agents.player import create_player_subagent, PLAYER_INSTRUCTIONS

def test_player_subagent_has_required_fields():
    subagent = create_player_subagent()
    assert subagent["name"] == "player"
    assert "description" in subagent
    assert "system_prompt" in subagent
    assert "tools" in subagent
    assert "model" in subagent

def test_player_instructions_contain_coordination_protocol():
    assert "/coordination/player/" in PLAYER_INSTRUCTIONS
    assert "report.json" in PLAYER_INSTRUCTIONS

def test_player_model_configurable():
    subagent = create_player_subagent(model="anthropic:claude-sonnet-4-5-20250929")
    assert subagent["model"] == "anthropic:claude-sonnet-4-5-20250929"
```

### Integration Tests

```python
# tests/integration/agents/test_player_execution.py
import pytest
from deepagents import create_deep_agent
from guardkit.agents.player import create_player_subagent

@pytest.mark.integration
async def test_player_can_be_invoked():
    """Test that Player subagent can be invoked via task tool."""
    agent = create_deep_agent(
        model="anthropic:claude-3-5-haiku-20241022",
        subagents=[create_player_subagent()],
    )
    
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Use the player agent to create a hello world function in /working/hello.py"
        }]
    })
    
    assert result is not None
    # Check that player was invoked (via task tool)
```

---

## Acceptance Criteria

- [ ] `create_player_subagent()` returns valid SubAgent configuration
- [ ] Player instructions include coordination protocol
- [ ] Player tools (`run_tests`, `check_syntax`, `lint_file`) work correctly
- [ ] Player can be invoked via DeepAgents `task` tool
- [ ] Player writes reports to `/coordination/player/turn_N/report.json`
- [ ] Report format matches schema
- [ ] Unit tests pass
- [ ] Integration test passes

---

## Migration Notes

### What Changed from Original Design

| Original | DeepAgents-Based |
|----------|------------------|
| Custom `PlayerAgent` class | SubAgent configuration dict |
| Custom execution wrapper | DeepAgents `task` tool |
| Custom context management | DeepAgents context isolation |
| 1-2 days effort | 1 day effort |

### What We Keep

- Player instructions (the "soul" of the agent)
- Player tools (run_tests, check_syntax, lint_file)
- Report format specification
- Coordination protocol via filesystem

---

## References

- [DeepAgents SubAgents](https://docs.langchain.com/oss/python/deepagents/middleware#subagentmiddleware)
- [FEATURE-002: DeepAgents Infrastructure](./FEATURE-002-agent-sdk-infrastructure.md)
- [Adversarial Cooperation Paper](../adversarial-cooperation-in-code-synthesis.pdf)
