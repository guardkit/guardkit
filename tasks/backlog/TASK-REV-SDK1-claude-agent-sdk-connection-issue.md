---
id: TASK-REV-SDK1
title: Investigate Claude Agent SDK connection/installation detection failure
status: review_complete
task_type: review
review_mode: code-quality
review_depth: standard
created: 2026-01-06T10:00:00Z
updated: 2026-01-06T15:30:00Z
priority: high
tags: [claude-agent-sdk, feature-build, environment, debugging, blocking]
complexity: 6
decision_required: true
related_tasks:
  - TASK-REV-66B4
source_evidence:
  file: docs/reviews/feature-build/feature-build-output.md
  lines: 502-644
review_results:
  mode: code-quality
  depth: standard
  score: 50
  findings_count: 5
  recommendations_count: 5
  root_cause: "Misleading error message - SDK is installed but ImportError catch is too broad"
  report_path: .claude/reviews/TASK-REV-SDK1-review-report.md
  completed_at: 2026-01-06T15:30:00Z
---

# Task: Investigate Claude Agent SDK connection/installation detection failure

## Description

When running `/feature-build FEAT-1682` via the GuardKit CLI (`guardkit-py autobuild feature`), the system reports "Claude Agent SDK not installed" despite the SDK being correctly installed in the system Python environment.

**Evidence**: User confirmed SDK is installed:
```bash
python3 -m pip list | grep -i claude
claude-agent-sdk          0.1.18
```

Yet the feature build fails with:
```
Error: Unexpected error: Claude Agent SDK not installed. Run: pip install claude-agent-sdk
```

## Root Cause Hypothesis

The issue is likely one of the following:

### Hypothesis 1: Virtual Environment Mismatch
GuardKit may be running in a different virtual environment (venv/conda) than where the SDK is installed.

**Investigation needed**:
- Where is `guardkit-py` installed?
- What Python environment does it use?
- Is there a venv activation step missing?

### Hypothesis 2: Import Path Issue
The `guardkit-py` command may be using a different Python interpreter than `python3`.

**Investigation needed**:
- What does `which guardkit-py` return?
- What Python does the guardkit script use (shebang)?
- Is the script using `#!/usr/bin/env python3` or a specific path?

### Hypothesis 3: SDK Import Mechanism
The SDK detection in `agent_invoker.py:731-741` uses a try/except ImportError:

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
    ) from e
```

**Investigation needed**:
- Is the exception being raised from ImportError or something else?
- Could there be a dependency issue in claude-agent-sdk itself?
- Are all the imported classes available in version 0.1.18?

### Hypothesis 4: SDK Internal Dependencies
The SDK might be installed but one of its dependencies (or the Claude Code CLI it wraps) might not be available.

**Investigation needed**:
- Is `claude` CLI installed globally? (`which claude`)
- What does `claude --version` return?
- Does the SDK require the CLI to be on PATH?

## Source Evidence

From [docs/reviews/feature-build/feature-build-output.md](docs/reviews/feature-build/feature-build-output.md) lines 502-600:

```
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-INFRA-001 (turn 1)
  ✗ Player failed
   Error: Unexpected error: Claude Agent SDK not installed. Run: pip install claude-agent-sdk
```

The error originates in `guardkit/orchestrator/agent_invoker.py:740`.

## Files to Review

1. `guardkit/orchestrator/agent_invoker.py:730-780` - SDK import and invocation
2. `guardkit/cli/autobuild.py` - CLI entry point, Python environment
3. `pyproject.toml` - SDK dependency declaration
4. `installer/scripts/install.sh` - Installation and symlink setup

## Questions to Answer

1. **Environment**: Is GuardKit running in a venv that doesn't have the SDK?
2. **CLI Dependency**: Does the SDK require Claude Code CLI to be installed?
3. **Version Compatibility**: Is version 0.1.18 compatible with our import statements?
4. **Error Masking**: Is the ImportError actually from something else (e.g., a dependency)?

## Diagnostic Commands to Run

```bash
# 1. Find guardkit-py location and Python
which guardkit-py
head -5 $(which guardkit-py)

# 2. Check SDK availability in guardkit's Python
python3 -c "from claude_agent_sdk import query, ClaudeAgentOptions; print('OK')"

# 3. Check if guardkit has a venv
ls -la ~/.agentecflow/

# 4. Check Claude CLI availability
which claude
claude --version

# 5. Check SDK version and dependencies
pip show claude-agent-sdk
pip check claude-agent-sdk
```

## Acceptance Criteria

- [x] Root cause identified and documented
- [x] Diagnostic commands run with results captured
- [x] Fix approach determined (installation docs, venv setup, or code change)
- [x] Implementation tasks created if code changes needed

## Implementation Tasks Created

The following tasks were created from the review recommendations:

| Task ID | Title | Priority | Wave |
|---------|-------|----------|------|
| [TASK-SDK-001](sdk-error-handling/TASK-SDK-001-improve-error-message.md) | Improve SDK error message with diagnostics | HIGH | 1 |
| [TASK-SDK-002](sdk-error-handling/TASK-SDK-002-preflight-check.md) | Add SDK pre-flight check in CLI | MEDIUM | 1 |
| [TASK-SDK-003](sdk-error-handling/TASK-SDK-003-doctor-command.md) | Add guardkit doctor command | MEDIUM | 2 |
| [TASK-SDK-004](sdk-error-handling/TASK-SDK-004-update-documentation.md) | Document optional dependency installation | LOW | 2 |

**Feature Folder**: `tasks/backlog/sdk-error-handling/`

**Next Steps**:
1. Review: `tasks/backlog/sdk-error-handling/IMPLEMENTATION-GUIDE.md`
2. Start with Wave 1 tasks (TASK-SDK-001, TASK-SDK-002)

## Review Mode

Suggested: `--mode=code-quality --depth=standard`

## Related Tasks

- **TASK-REV-66B4**: Feature build schema analysis (predecessor - different issue)
- **TASK-FP-001 through TASK-FP-005**: Schema fix implementation (related)
