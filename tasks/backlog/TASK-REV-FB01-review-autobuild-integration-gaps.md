---
id: TASK-REV-FB01
title: "Review AutoBuild Integration Gaps - Player-Coach Feature Build"
status: backlog
created: 2025-12-26T10:00:00Z
updated: 2025-12-26T10:00:00Z
priority: high
tags: [review, autobuild, integration, architecture, feature-build]
task_type: review
review_mode: architectural
review_depth: comprehensive
complexity: 8
parent_feature: feature-build
---

# Review AutoBuild Integration Gaps - Player-Coach Feature Build

## Review Objective

Analyze the current state of the AutoBuild Player-Coach implementation and identify all integration gaps that prevent the `/feature-build` command from working with the full orchestrator (NOT the Task tool fallback).

## Background

The AutoBuild system has multiple components that need to work together:

1. **Bash CLI** (`~/.agentecflow/bin/guardkit autobuild`)
2. **Python Orchestrator** (`guardkit/orchestrator/autobuild.py`)
3. **Python CLI** (`guardkit/cli/autobuild.py`)
4. **Claude Agent SDK Integration** (`guardkit/orchestrator/agent_invoker.py`)
5. **Slash Command** (`/feature-build` → `installer/core/commands/feature-build.md`)

**Current Problem**: The Python orchestrator code exists and the SDK integration is complete, but the Bash CLI cannot invoke the Python CLI because `guardkit` is not installed as a pip package.

## Scope of Review

### 1. Branch Changes Analysis

Review all changes in `autobuild-automation` branch:
- What tasks have been completed?
- What code has been implemented?
- What is the current state of each component?

### 2. Component Integration Analysis

For each seam, identify:
- Current state (working/broken/missing)
- What's blocking integration
- Dependencies and prerequisites

#### Seam A: Bash CLI → Python Orchestrator
- How does `guardkit autobuild` invoke Python code?
- Why does `python3 -m guardkit.cli.main autobuild` fail without pip install?
- How do other Python commands work (e.g., `generate_feature_yaml.py`)?

#### Seam B: Python Orchestrator → Claude Agent SDK
- Is `agent_invoker.py` correctly using `claude_agent_sdk.query()`?
- Are the agent prompts correctly structured?
- Is worktree isolation working?

#### Seam C: Slash Command → Orchestration
- How should `/feature-build` invoke the orchestrator?
- Current fallback uses Task tool - what should the primary path be?
- What triggers the orchestrator vs the fallback?

### 3. Architecture Gap Analysis

Identify fundamental architecture decisions needed:
- Should `guardkit` be a pip-installable package?
- Should the orchestrator be a standalone script instead?
- How do other CLI tools in the ecosystem solve this?

### 4. Implementation Comparison

Compare working vs non-working patterns:
- **Working**: `generate_feature_yaml.py` - standalone script with shebang
- **Not Working**: `guardkit/cli/autobuild.py` - requires package import

## Key Questions to Answer

1. What is the minimal change to make `guardkit autobuild task TASK-XXX` work?
2. Is pip packaging the right solution, or is there a simpler approach?
3. What is the correct invocation path from `/feature-build` to the orchestrator?
4. Are there any SDK-level issues blocking integration?
5. What testing is needed to verify end-to-end flow?

## Artifacts to Review

### Completed Tasks
- [ ] TASK-AB-2D16 - Integration testing and documentation
- [ ] TASK-AB-BD2E - CLI commands implementation
- [ ] TASK-AB-9869 - AutoBuildOrchestrator class
- [ ] TASK-FB-W1 - SDK integration (agent_invoker.py)

### Key Files
- [ ] `~/.agentecflow/bin/guardkit` - Bash CLI wrapper
- [ ] `guardkit/cli/autobuild.py` - Python CLI (416 lines)
- [ ] `guardkit/cli/main.py` - CLI registration
- [ ] `guardkit/orchestrator/autobuild.py` - Orchestrator (1095 lines)
- [ ] `guardkit/orchestrator/agent_invoker.py` - SDK integration
- [ ] `installer/core/commands/feature-build.md` - Slash command spec
- [ ] `installer/core/commands/lib/` - Working standalone scripts

### Branch Commits
- Review recent commits on `autobuild-automation` branch
- Identify what was implemented vs what was planned

## Deliverables

1. **Gap Analysis Report**: Document each integration gap with severity
2. **Architecture Decision**: Recommend packaging vs standalone approach
3. **Implementation Tasks**: Create specific tasks to close each gap
4. **Test Plan**: How to verify end-to-end flow works

## Success Criteria

- [ ] All integration gaps clearly documented
- [ ] Root cause of "ModuleNotFoundError" understood
- [ ] Clear recommendation on packaging approach
- [ ] Actionable implementation tasks created
- [ ] No Task tool fallback dependency in final solution

## Constraints

- Solution must work on any machine with GuardKit installed
- Must not require users to manually set PYTHONPATH
- Must integrate with existing GuardKit installation pattern
- Should leverage existing infrastructure where possible

## Related Tasks

- TASK-AB-CLI (backlog) - Current packaging task (may be superseded by this review)
- TASK-FB-W3 (backlog) - State persistence
- TASK-FB-W4 (backlog) - Testing and docs
