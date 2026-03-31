# Feature Build Implementation Guide

## Executive Summary

The `/feature-build` command (alias: `guardkit autobuild`) implements dialectical autocoding using Player-Coach adversarial cooperation. Most of the infrastructure is **already complete** on the `autobuild-automation` branch.

**Key Finding**: Only Wave 1 requires implementation. Waves 2-4 are refinements to existing working code.

## Current State Analysis

### What's Already Complete (DO NOT RECREATE)

| Component | Lines | Status | Notes |
|-----------|-------|--------|-------|
| `AutoBuildOrchestrator` | 1095 | ✅ Complete | Full 3-phase execution loop |
| `AgentInvoker` | 651 | ⚠️ 95% Complete | SDK placeholder at L500-504 |
| `ProgressDisplay` | ~200 | ✅ Complete | Rich console output |
| `WorktreeManager` | ~150 | ✅ Complete | Git worktree management |
| CLI Commands | 400 | ✅ Complete | `guardkit autobuild run/status` |
| Exceptions | ~100 | ✅ Complete | Full error hierarchy |
| Tests | ~500 | ✅ Complete | Unit + integration tests |

### What Needs Implementation

| Task | Scope | Effort |
|------|-------|--------|
| Wave 1: SDK Integration | Replace 20 lines in `AgentInvoker._invoke_with_role()` | 2-3 hours |
| Wave 2: CLI Refinements | Optional enhancements | 1-2 hours |
| Wave 3: State Persistence | Add frontmatter state tracking | 2-3 hours |
| Wave 4: Testing & Docs | Additional tests, CLAUDE.md updates | 2-3 hours |

## Wave Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         WAVE 1 (REQUIRED)                        │
│          SDK Integration in AgentInvoker                        │
│                                                                 │
│  Files: agent_invoker.py (20 lines), pyproject.toml (1 line)   │
│  Mode: Direct Claude Code                                       │
│  Effort: 2-3 hours                                              │
│  Dependencies: None                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WAVES 2-4 (UPDATED STATUS)                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │     Wave 2       │  │     Wave 3       │  │    Wave 4    │  │
│  │ ⚠️ SUPERSEDED    │  │ State Persist.   │  │  Tests/Docs  │  │
│  │                  │  │                  │  │              │  │
│  │ Existing CLI in  │  │ Mode: Direct     │  │ Mode: Direct │  │
│  │ cli/autobuild.py │  │ Effort: 2-3h     │  │ Effort: 2-3h │  │
│  │ covers all needs │  │ Status: DEFER    │  │ Partial w/W1 │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                 │
│  Wave 2: SUPERSEDED by existing guardkit/cli/autobuild.py      │
│  Wave 3: Defer until real-world testing reveals need           │
│  Wave 4: SDK mock tests included with Wave 1                   │
└─────────────────────────────────────────────────────────────────┘
```

### Wave 2 Supersession Note (TASK-REV-FB02)

During architectural review, it was discovered that all Wave 2 functionality already exists in `guardkit/cli/autobuild.py`:

| Wave 2 Proposal | Existing Implementation |
|-----------------|------------------------|
| `guardkit feature-build` command | `guardkit autobuild task` ✅ |
| `--max-turns`, `--model`, `--verbose` | All options exist ✅ |
| Rich progress display | `_display_result()` ✅ |
| Status command | `guardkit autobuild status` ✅ |

**Action**: Wave 2 marked as superseded. No implementation needed.

**Process Improvement**: Created TASK-FP-4F81 to add existing code audit step to `/feature-plan` command to prevent similar duplications in future.

## Implementation Mode Recommendations

### Wave 1: SDK Integration

| Aspect | Recommendation |
|--------|----------------|
| **Mode** | Direct Claude Code |
| **Why** | Single method, 20 lines, clear pattern from SDK docs |
| **Time** | 2-3 hours |
| **Risk** | Low (isolated change) |
| **Rollback** | Git revert single commit |

**Do NOT use `/task-work`** because:
- Scope too narrow for full quality gate workflow
- SDK pattern is well-documented
- Existing tests provide validation
- Single file modification

### Wave 2: CLI Refinements

> **⚠️ SUPERSEDED** - See [TASK-FB-W2](TASK-FB-W2-cli-command.md) for details.

| Aspect | Status |
|--------|--------|
| **Status** | SUPERSEDED |
| **Reason** | All functionality exists in `guardkit/cli/autobuild.py` |
| **Action** | No implementation needed |

The existing CLI provides:
- `guardkit autobuild task TASK-XXX` (equivalent to proposed `feature-build`)
- All proposed options (`--max-turns`, `--model`, `--verbose`)
- Rich progress display with success/failure panels
- Turn history table in verbose mode
- Status command for worktree inspection

### Wave 3: State Persistence

| Aspect | Recommendation |
|--------|----------------|
| **Mode** | Direct Claude Code |
| **Why** | Additive feature to existing orchestrator |
| **Time** | 2-3 hours |
| **Priority** | MEDIUM - useful for interruption recovery |
| **Defer?** | Optional, defer for MVP |

**Scope:**
- Add `feature_build` section to task frontmatter
- Track turn history
- Enable `--resume` continuation

### Wave 4: Testing & Documentation

| Aspect | Recommendation |
|--------|----------------|
| **Mode** | Direct Claude Code |
| **Why** | Standard test/doc additions |
| **Time** | 2-3 hours |
| **Priority** | MEDIUM - needed before v1.0 |
| **Defer?** | Optional, defer for MVP |

**Scope:**
- Add SDK mock tests
- Update CLAUDE.md
- Add usage examples

## Parallel Execution Options

### Option A: Sequential (Safest)

```
Wave 1 → Test → Wave 3 → Test → Wave 2 → Wave 4
  3h      1h      2h       1h     1h       2h

Total: ~10 hours with testing
```

### Option B: Parallel (Fastest)

```
Wave 1 ──┬── Test ──┬── Wave 2 ────┐
         │          │              │
         │          ├── Wave 3 ────┤
         │          │              │
         │          └── Wave 4 ────┴── Final Test
         │
Total: ~6 hours with parallel execution
```

### Option C: MVP First (Recommended)

```
Wave 1 → Test → Real-World Testing → Waves 2-4 as needed
  3h      1h        ongoing              deferred

Total: ~4 hours to functional MVP
```

**Why Option C is recommended:**
1. Feature works immediately after Wave 1
2. Real-world testing reveals actual needs
3. Waves 2-4 may not be necessary
4. Avoids over-engineering

## Quick Start: Wave 1 Implementation

### Prerequisites

1. Verify correct branch:
   ```bash
   git branch --show-current  # Should be: autobuild-automation
   ```

2. Check existing code:
   ```bash
   # Verify placeholder exists
   grep -n "NotImplementedError" guardkit/orchestrator/agent_invoker.py
   ```

3. Install SDK (when available):
   ```bash
   pip install claude-code-sdk  # Or correct package name
   ```

### Implementation Steps

1. **Read the current code** (5 min):
   ```bash
   # Lines 480-516
   cat guardkit/orchestrator/agent_invoker.py | head -520 | tail -40
   ```

2. **Check SDK documentation** (10 min):
   - Verify correct package name
   - Confirm `query()` function signature
   - Confirm `ClaudeCodeOptions` parameters

3. **Replace placeholder** (30 min):
   - Remove `NotImplementedError` block (L500-504)
   - Add SDK import
   - Add `query()` call with options

4. **Add dependency** (5 min):
   - Update `pyproject.toml`

5. **Run existing tests** (10 min):
   ```bash
   pytest tests/unit/orchestrator/ -v
   ```

6. **Manual smoke test** (30 min):
   ```bash
   guardkit autobuild run TASK-TEST-001
   ```

### Code to Replace

**Location**: [agent_invoker.py:480-516](guardkit/orchestrator/agent_invoker.py#L480-L516)

See [TASK-FB-W1-sdk-orchestrator.md](TASK-FB-W1-sdk-orchestrator.md) for exact before/after code.

## Post-Implementation Testing

### Smoke Test Checklist

- [ ] `guardkit autobuild run TASK-TEST-001` executes
- [ ] Player agent runs with file access
- [ ] Coach agent runs with read-only access
- [ ] Reports created in `.guardkit/autobuild/TASK-TEST-001/`
- [ ] Approval workflow terminates correctly
- [ ] Feedback workflow continues to next turn
- [ ] Max turns limit enforced

### Test Task

Use existing test tasks:
- `tasks/backlog/test-simple.md` - Simple hello world
- `tasks/backlog/test-iteration.md` - Requires multiple turns

Or create minimal test:
```bash
cat > tasks/backlog/TASK-TEST-001.md << 'EOF'
---
id: TASK-TEST-001
title: Test SDK Integration
status: backlog
complexity: 1
---

# Test SDK Integration

## Requirements
Create a file `hello.py` with a function that returns "Hello, World!".

## Acceptance Criteria
- [ ] File `hello.py` exists
- [ ] Function returns "Hello, World!"
- [ ] Basic test exists and passes
EOF
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK package name differs | Medium | Low | Check docs before implementing |
| SDK API differs from docs | Low | Medium | Adjust parameters as needed |
| SDK not yet available | Medium | High | Wait for official release |
| Existing tests break | Low | Medium | Run tests before and after |

## Dependencies

### Required
- Claude Agent SDK (pip package)
- Existing branch: `autobuild-automation`

### Already Satisfied
- `AutoBuildOrchestrator` implementation
- `AgentInvoker` structure
- CLI commands
- Exception classes
- Test infrastructure

## Conclusion

**The feature-build command is 95% complete.** Wave 1 (SDK integration) is the only blocking work. It requires replacing ~20 lines of placeholder code with actual SDK calls.

**Recommended approach:**
1. Complete Wave 1 (2-3 hours)
2. Test with real tasks
3. Defer Waves 2-4 unless real-world testing reveals needs

**Do NOT use `/task-work`** for any wave - the scope is too narrow and the existing code provides sufficient quality gates.
