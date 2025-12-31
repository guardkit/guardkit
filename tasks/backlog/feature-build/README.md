# Feature: /feature-build Command

## Overview

Implement dialectical autocoding (Player-Coach adversarial cooperation) using Claude Agent SDK for true fresh context per turn.

**Current Status**: 98% complete. SDK integration (Wave 1) and State Persistence (Wave 3) are complete. Only packaging (TASK-AB-CLI) and final testing/docs (Wave 4) remain.

**Architectural Review**: Completed 2025-12-26 (Score: 78/100 - APPROVED)
- Report: [.claude/reviews/TASK-REV-FB01-review-report.md](../../../.claude/reviews/TASK-REV-FB01-review-report.md)

## Quick Start

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for:
- Wave-by-wave breakdown
- Parallel execution options
- Implementation mode recommendations (/task-work vs direct)
- Quick start instructions

## Parent Task

- **Review Task**: [TASK-REV-FB01](../TASK-REV-FB01-plan-feature-build-command.md)

## Architecture

```
guardkit autobuild run TASK-XXX   (or future: guardkit feature-build TASK-XXX)
    │
    ├─→ Setup: Load task, create worktree (✅ WorktreeManager - COMPLETE)
    │
    └─→ Dialectical Loop (✅ AutoBuildOrchestrator - COMPLETE):
          │
          ├─→ PLAYER: query() with full tools → implements + tests
          │   └─→ AgentInvoker.invoke_player() (⚠️ SDK PLACEHOLDER)
          │
          └─→ COACH: query() with read-only tools → validates → approve/feedback
              └─→ AgentInvoker.invoke_coach() (⚠️ SDK PLACEHOLDER)
```

## Wave Breakdown

| Wave | Task | Status | Effort | Mode |
|------|------|--------|--------|------|
| 1 | [TASK-FB-W1](../completed/feature-build/TASK-FB-W1-sdk-orchestrator.md) - SDK Integration | ✅ Complete | 2-3h | Direct |
| 2 | CLI Refinements | ⏭️ Superseded | - | Existing CLI covers all needs |
| 3 | [TASK-FB-W3](TASK-FB-W3-state-persistence.md) - State Persistence | ✅ Complete | 2-3h | Direct |
| 4 | [TASK-FB-W4](TASK-FB-W4-testing-docs.md) - Testing & Docs | 📋 Backlog | 2-3h | Direct |
| - | [TASK-AB-CLI](TASK-AB-CLI-implement-autobuild-command.md) - Packaging | 📋 Backlog | 4h | task-work |

**Remaining to MVP**: Package as pip installable (TASK-AB-CLI)
**Remaining to v1.0**: Testing & docs (Wave 4)

## What's Already Complete

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| `AutoBuildOrchestrator` | `guardkit/orchestrator/autobuild.py` | 1095 | ✅ Complete |
| `AgentInvoker` | `guardkit/orchestrator/agent_invoker.py` | 651 | ✅ SDK integrated |
| `ProgressDisplay` | `guardkit/orchestrator/progress.py` | ~200 | ✅ Complete |
| `WorktreeManager` | `guardkit/orchestrator/worktrees.py` | ~150 | ✅ Complete |
| CLI Commands | `guardkit/cli/autobuild.py` | 400 | ✅ Complete |
| Exceptions | `guardkit/orchestrator/exceptions.py` | ~100 | ✅ Complete |
| Agent Definitions | `.claude/agents/autobuild-*.md` | - | ✅ Complete |

## Prerequisites

```bash
# Install SDK (when available)
pip install claude-code-sdk  # Check official package name

# API key (for SDK)
export ANTHROPIC_API_KEY=your-api-key
```

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `guardkit/orchestrator/autobuild.py` | AutoBuildOrchestrator class | ✅ Complete |
| `guardkit/orchestrator/agent_invoker.py` | SDK invocation (placeholder) | ⚠️ Wave 1 |
| `guardkit/cli/autobuild.py` | CLI commands | ✅ Complete |
| `.claude/agents/autobuild-player.md` | Player agent definition | ✅ Complete |
| `.claude/agents/autobuild-coach.md` | Coach agent definition | ✅ Complete |

## Testing

### After Wave 1 Completion

```bash
# Run existing tests
pytest tests/unit/orchestrator/ -v

# Manual smoke test
guardkit autobuild run TASK-TEST-001

# Check output
cat .guardkit/autobuild/TASK-TEST-001/player_turn_1.json
cat .guardkit/autobuild/TASK-TEST-001/coach_turn_1.json
```

### Test Tasks Available

- `tasks/backlog/test-simple.md` - Simple hello world
- `tasks/backlog/test-iteration.md` - Requires multiple turns

## Related Research

- [Block AI: Adversarial Cooperation in Code Synthesis](https://block.xyz/research)
- [g3 implementation](https://github.com/dhanji/g3)
- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)

## Recommended Approach

1. **Complete Wave 1** (2-3 hours) - Replace SDK placeholder
2. **Test with real tasks** - Use test-simple.md and test-iteration.md
3. **Defer Waves 2-4** - Only implement if real-world testing reveals needs

**See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for detailed instructions.**
