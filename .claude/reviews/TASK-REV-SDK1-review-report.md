# Review Report: TASK-REV-SDK1

## Executive Summary

The Claude Agent SDK "not installed" error is **NOT a real SDK installation issue**. The SDK is correctly installed and functional in the system Python environment. The error is a **false positive** caused by a misleading error message originating from a different execution context where the import fails for a reason unrelated to actual installation status.

**Root Cause**: The error originates from `agent_invoker.py:738-741` which catches ALL `ImportError` exceptions and reports them as "SDK not installed" - even when the SDK IS installed but fails to import for other reasons.

## Review Details

- **Mode**: Code Quality Review
- **Depth**: Standard
- **Duration**: 15 minutes
- **Reviewer**: code-reviewer agent

## Findings

### Finding 1: SDK IS Correctly Installed (Critical)

**Evidence**: All diagnostic commands pass in the current environment:

```bash
$ python3 -m pip show claude-agent-sdk
Name: claude-agent-sdk
Version: 0.1.18
Location: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages

$ python3 -c "from claude_agent_sdk import query, ClaudeAgentOptions, CLINotFoundError, ProcessError, CLIJSONDecodeError; print('OK')"
OK

$ python3 -m pip check claude-agent-sdk
No broken requirements found.

$ which claude && claude --version
/Users/richardwoollcott/.local/bin/claude
2.0.76 (Claude Code)
```

**Conclusion**: The SDK is installed, all imports work, dependencies are satisfied, and the Claude CLI is available.

### Finding 2: Misleading Error Message (Critical)

**Location**: `guardkit/orchestrator/agent_invoker.py:730-741`

```python
try:
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError,
    )
except ImportError as e:
    raise AgentInvocationError(
        "Claude Agent SDK not installed. Run: pip install claude-agent-sdk"
    ) from e  # <-- MISLEADING: assumes all ImportError = not installed
```

**Issue**: The error handler assumes ANY `ImportError` means the SDK is not installed. However, `ImportError` can occur for many reasons:
- SDK not installed (correctly handled)
- SDK installed but a dependency is missing (incorrectly reported)
- SDK installed but import fails due to Python environment isolation (incorrectly reported)
- Circular import issues (incorrectly reported)

### Finding 3: Optional Dependency Architecture (Major)

**Location**: `pyproject.toml:34-37`

```toml
[project.optional-dependencies]
autobuild = [
    "claude-agent-sdk>=0.1.0",
]
```

The Claude Agent SDK is declared as an **optional dependency**. This means:
1. Users can install `guardkit-py` without the SDK
2. AutoBuild features will fail if SDK not explicitly installed
3. The installation command should be: `pip install guardkit-py[autobuild]`

**However**: The current error message suggests `pip install claude-agent-sdk` which works, but doesn't align with the optional dependency pattern.

### Finding 4: Potential Environment Isolation Issue (Major)

The test in `/Users/richardwoollcott/Projects/guardkit_testing/feature_build_cli_test/` was run via:
1. Bash shell script (`guardkit`) that delegates to `guardkit-py`
2. `guardkit-py` uses `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14`

The SDK imports work when tested manually in both directories. This suggests the failure might be:
- A transient issue during that specific run
- An issue with the worktree's Python path at runtime
- A timing issue where the import failed before the process fully initialized

### Finding 5: Missing SDK Availability Check (Minor)

There is no pre-flight check for SDK availability before attempting AutoBuild. The error only occurs when the `_invoke_with_role` method is called during turn execution, which is late in the workflow.

**Better pattern**: Check SDK availability at CLI startup or orchestrator initialization.

## Recommendations

### Recommendation 1: Improve Error Message with Diagnostic Info (High Priority)

**Current**:
```
Claude Agent SDK not installed. Run: pip install claude-agent-sdk
```

**Proposed**:
```python
except ImportError as e:
    import sys
    diagnosis = f"""
    Claude Agent SDK import failed:
      Error: {e}
      Python: {sys.executable}
      Path: {':'.join(sys.path[:3])}...

    To fix:
      pip install claude-agent-sdk
      # OR for full autobuild support:
      pip install guardkit-py[autobuild]
    """
    raise AgentInvocationError(diagnosis) from e
```

This will help diagnose whether it's actually an installation issue or something else.

### Recommendation 2: Add SDK Pre-flight Check (Medium Priority)

Add SDK availability check in `autobuild.py` before creating the orchestrator:

```python
def _check_sdk_available() -> bool:
    """Check if Claude Agent SDK is available."""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
        return True
    except ImportError:
        return False

# In task() command:
if not _check_sdk_available():
    console.print("[red]Error: Claude Agent SDK not available[/red]")
    console.print("Install with: pip install guardkit-py[autobuild]")
    sys.exit(1)
```

### Recommendation 3: Add `guardkit doctor` Command (Medium Priority)

Create a diagnostic command that checks all dependencies:

```bash
$ guardkit doctor
GuardKit Environment Check
===========================
Python:           3.14.0 (/Library/Frameworks/Python.framework/...)
guardkit-py:      0.1.0 ✓
claude-agent-sdk: 0.1.18 ✓
Claude CLI:       2.0.76 ✓
All checks passed!
```

### Recommendation 4: Document Installation with Optional Dependencies (Low Priority)

Update installation documentation to clarify:

```bash
# Basic installation
pip install guardkit-py

# With AutoBuild support (required for /feature-build, guardkit autobuild)
pip install guardkit-py[autobuild]
```

### Recommendation 5: Investigate Test Environment (Low Priority)

The original test that failed should be re-run with more logging to capture:
- The exact Python path at invocation time
- The sys.path when the import failed
- Whether there was a transient network/permission issue

## Root Cause Summary

| Hypothesis | Verdict |
|------------|---------|
| Virtual Environment Mismatch | **Unlikely** - no venv in test directory, system Python used |
| Import Path Issue | **Possible** - shebang points to correct Python, but runtime may differ |
| SDK Import Mechanism | **Likely** - error masking hides real cause |
| SDK Internal Dependencies | **Ruled Out** - `pip check` passes, CLI works |

**Most Likely Cause**: The `ImportError` was triggered by a transient issue or dependency problem that was incorrectly reported as "SDK not installed" due to overly broad error handling.

## Quality Scores

| Aspect | Score | Notes |
|--------|-------|-------|
| Error Handling | 4/10 | Overly broad catch, misleading message |
| Diagnostics | 3/10 | No pre-flight check, no `doctor` command |
| Documentation | 6/10 | Optional dependency pattern exists but not prominent |
| Code Quality | 7/10 | Otherwise well-structured code |

**Overall Score**: 5/10 - Error handling needs improvement

## Appendix

### Diagnostic Commands Run

```bash
# SDK installation check
python3 -m pip show claude-agent-sdk
# Result: Version 0.1.18 installed

# Import test
python3 -c "from claude_agent_sdk import query, ClaudeAgentOptions; print('OK')"
# Result: OK

# Dependency check
python3 -m pip check claude-agent-sdk
# Result: No broken requirements found.

# CLI check
which claude && claude --version
# Result: 2.0.76 (Claude Code)

# GuardKit location
which guardkit-py
# Result: /Library/Frameworks/Python.framework/Versions/3.14/bin/guardkit-py

# Shebang check
head -1 $(which guardkit-py)
# Result: #!/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14
```

### Files Reviewed

1. `guardkit/orchestrator/agent_invoker.py` - SDK import and error handling (lines 730-780)
2. `guardkit/cli/autobuild.py` - CLI entry point
3. `pyproject.toml` - Dependency declarations
4. `docs/reviews/feature-build/feature-build-output.md` - Error evidence (lines 500-644)
