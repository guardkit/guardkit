# Implementation Guide: AutoBuild Context Payload Optimization

## Feature Overview

Reduce AutoBuild SDK session preamble from ~1,800s to ~300-400s by eliminating unnecessary context injection. Replace `/task-work` skill invocation with focused autobuild-specific prompts using `setting_sources=["project"]` only.

**Spec**: [FEAT-AUTOBUILD-CONTEXT-OPT-spec.md](../../../docs/features/FEAT-AUTOBUILD-CONTEXT-OPT-spec.md)
**Review**: [TASK-REV-A781-review-report.md](../../../.claude/reviews/TASK-REV-A781-review-report.md)

## Architecture Summary

### Current Flow (slow)

```
AutoBuild → SDK Session (setting_sources=["user", "project"])
         → Loads ALL 25 user commands (758KB)
         → Loads ALL project commands (157KB)
         → Resolves /task-work skill (158KB spec)
         → ~987KB context per session × 2 sessions = ~1,974KB
         → ~1,800s preamble per task
```

### Target Flow (optimized)

```
AutoBuild → SDK Session (setting_sources=["project"])
         → Loads project rules + CLAUDE.md only (~72KB)
         → Inline focused prompt with execution protocol (~15-20KB)
         → ~92KB context per session × 2 sessions = ~184KB
         → ~300-400s preamble per task
```

## Execution Waves

### Wave 1: Protocol Extraction (Foundation)

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-ACO-001 | Extract execution & design protocols | 4 | task-work |

**Rationale**: All prompt builders depend on these protocol files.

### Wave 2: Prompt Builders + Auto-Detection (Parallel)

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-ACO-002 | Build implementation prompt builder | 6 | task-work |
| TASK-ACO-003 | Build design prompt builder | 6 | task-work |
| TASK-ACO-004 | Expand direct mode auto-detection | 4 | task-work |

**Rationale**: These three tasks modify different files and can execute in parallel.
- TASK-ACO-002 modifies `agent_invoker.py` (implementation prompt)
- TASK-ACO-003 modifies `task_work_interface.py` (design prompt)
- TASK-ACO-004 modifies `agent_invoker.py` (but different method than TASK-ACO-002)

**Note**: TASK-ACO-002 and TASK-ACO-004 both modify `agent_invoker.py`. If using Conductor parallel execution, they should be in the same workspace OR executed sequentially to avoid merge conflicts. Otherwise, they can proceed independently.

### Wave 3: Unit Tests

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-ACO-005 | Unit tests for all changes | 5 | task-work |

**Rationale**: Tests require all implementation to be complete.

### Wave 4: Integration Validation

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-ACO-006 | End-to-end validation + measurement | 5 | task-work |

**Rationale**: Integration validation requires unit tests to pass first.

## Key Files

| File | Change | Task |
|------|--------|------|
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | **NEW** | ACO-001 |
| `guardkit/orchestrator/prompts/autobuild_design_protocol.md` | **NEW** | ACO-001 |
| `guardkit/orchestrator/prompts/__init__.py` | **NEW** | ACO-001 |
| `guardkit/orchestrator/agent_invoker.py` | MODIFIED | ACO-002, ACO-004 |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | MODIFIED | ACO-003 |
| `tests/unit/test_autobuild_prompt_builders.py` | **NEW** | ACO-005 |
| `tests/unit/test_direct_mode_detection.py` | **NEW** | ACO-005 |
| `tests/unit/test_sdk_session_config.py` | **NEW** | ACO-005 |
| `tests/integration/test_autobuild_context_opt.py` | **NEW** | ACO-006 |

## Risk Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Prompt quality degradation | Medium | Extract protocol carefully; test on real tasks |
| TaskWorkStreamParser incompatibility | Low | Parser uses regex; prompt instructs same format |
| Coach validation breaks | Low | Coach reads JSON — schema unchanged |
| Interactive /task-work regression | Very Low | Zero changes to interactive path |
| Direct mode false positives | Low | Conservative criteria (complexity ≤3 AND no risk keywords) |

## Expected Savings

| Change | Context Reduction | Time Savings |
|--------|------------------|-------------|
| `setting_sources=["project"]` | 987KB → 72KB/session | ~600-900s |
| Focused prompts (no skill expansion) | Eliminates 158KB spec | ~120-180s |
| Skip unnecessary design phases | 3-5 fewer subagent calls | ~180-300s |
| Direct mode for complexity ≤3 | Avoids problem entirely | Variable |
| **Combined** | | **~1,200-1,500s** |

## Success Criteria

1. Preamble ≤ 600s (down from ~1,800s)
2. No quality regression in Player output
3. All JSON schemas unchanged
4. Interactive `/task-work` works identically
5. 4-task wave completes within 7,200s timeout
