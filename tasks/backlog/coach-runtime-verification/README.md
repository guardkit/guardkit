# Feature: Coach Runtime Verification

## Overview

Enable the Coach validator to verify acceptance criteria that require runtime execution (commands, API calls, UI verification), addressing the structural gap that caused FEAT-2AAA's UNRECOVERABLE_STALL failure.

**Current Status**: 1/9 tasks complete (criteria classifier POC implemented and tested)

**Source Review**: [TASK-REV-3F40](.claude/reviews/TASK-REV-3F40-review-report.md) — Analysis of FEAT-2AAA failure on Anthropic models

## Problem Statement

The Coach validator can only verify acceptance criteria through file-content analysis (text matching, file-existence promises). When acceptance criteria require runtime verification (`pip install succeeds`, `pytest passes`, `API returns 200`), the Coach cannot verify them, causing infinite feedback loops and UNRECOVERABLE_STALL.

This is not a task authoring problem — it's a verification pipeline gap.

## Architecture

```
                   +----------------------+
                   | Criteria Classifier  |     <-- POC COMPLETE
                   | (criteria_classifier |
                   |  .py)               |
                   +----------+-----------+
                              |
              +---------------+---------------+
              |               |               |
    +---------v------+ +-----v------+ +------v-------+
    | file_content   | | command_   | | manual       |
    |                | | execution  | |              |
    | Existing       | | NEW:       | | Skip/flag    |
    | Path A/B/C     | | Path D     | |              |
    +----------------+ +-----+------+ +--------------+
                             |
                   +---------v----------+
                   | Execute in         |
                   | worktree           |
                   | (subprocess/MCP)   |
                   +--------------------+
```

## Wave Breakdown

| Wave | Task | Status | Effort | Mode |
|------|------|--------|--------|------|
| 1 | [TASK-CRV-412F](TASK-CRV-412F-integrate-criteria-classifier.md) | backlog | 1-2h | task-work |
| 1 | [TASK-CRV-537E](TASK-CRV-537E-orchestrator-command-execution.md) | backlog | 2-3h | task-work |
| 2 | [TASK-CRV-1540](TASK-CRV-1540-cancelederror-partial-data.md) | backlog | 2-3h | task-work |
| 2 | [TASK-CRV-9618](TASK-CRV-9618-carry-forward-best-requirements.md) | backlog | 1-2h | task-work |
| 2 | [TASK-CRV-90FB](TASK-CRV-90FB-align-stall-detector.md) | backlog | 1h | task-work |
| 3 | [TASK-CRV-9914](TASK-CRV-9914-extended-coach-validator.md) | backlog | 3-4h | task-work |
| 3 | [TASK-CRV-B275](TASK-CRV-B275-rate-limit-invoke-with-role.md) | backlog | 1h | direct |
| 4 | [TASK-CRV-7DBC](TASK-CRV-7DBC-mcp-coach-integration.md) | backlog | 4-6h | task-work |
| 4 | [TASK-CRV-3B1A](TASK-CRV-3B1A-sdk-sessions-player-resume.md) | backlog | 4-6h | task-work |

## Prerequisites

- GuardKit Python package installed with `[autobuild]` extras
- Claude Agent SDK (`claude_agent_sdk`) installed
- For Wave 4: Node.js for Playwright MCP server

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `guardkit/orchestrator/quality_gates/criteria_classifier.py` | Criteria classification | Complete |
| `tests/unit/test_criteria_classifier.py` | Classifier tests (21 passing) | Complete |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Coach validation pipeline | To modify |
| `guardkit/orchestrator/agent_invoker.py` | SDK invocation | To modify |
| `guardkit/orchestrator/autobuild.py` | Turn loop orchestrator | To modify |
| `guardkit/orchestrator/synthetic_report.py` | Synthetic report builder | To modify |

## Parent Task

- **Review Task**: [TASK-REV-3F40](../TASK-REV-3F40-analyse-autobuild-feat-2aaa-anthropic-failure.md)
