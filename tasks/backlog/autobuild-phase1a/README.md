# AutoBuild Phase 1a - Adversarial Cooperation for Autonomous Implementation

## Problem Statement

GuardKit currently requires human supervision for every implementation turn (`/task-work`). While this ensures quality through direct human oversight, it creates bottlenecks:
- Developers must babysit each 5-minute turn
- Tasks cannot progress during nights/weekends
- Simple tasks take as long to supervise as complex ones
- Human fatigue leads to approval of suboptimal code

## Solution Approach

Implement the **dialectical autocoding** pattern from Block AI Research, achieving autonomous task execution through adversarial cooperation between two specialized agents:

**Player Agent** (Implementation):
- Implements code based on requirements
- Writes tests alongside implementation
- Responds to Coach feedback iteratively
- Cannot declare success (prevents false claims)

**Coach Agent** (Validation):
- Validates implementation against requirements
- Runs tests independently (doesn't trust Player claims)
- Provides specific, actionable feedback
- Approves only when all requirements met (final authority)

**Python Orchestrator**:
- Manages Player/Coach feedback loop
- Enforces fresh context each turn (prevents pollution)
- Provides git worktree isolation (safe experimentation)
- Bounds execution (max turns, timeouts)
- Displays real-time progress

## Research Foundation

Block AI Research (December 2025): Dialectical autocoding achieves **5/5 completeness** vs **1-4.5/5** for single-agent approaches.

**Why it works**:
1. **Requirements Contract**: Shared goal prevents drift
2. **Fresh Context**: Each turn starts clean (objectivity)
3. **Adversarial Validation**: Coach catches Player's premature success claims
4. **Bounded Process**: Turn limits create terminable workflow

## Architecture

**Option Selected**: **Modular Architecture with Phases**

```
guardkit/orchestrator/
├── autobuild.py         # AutoBuildOrchestrator (phase-based orchestration)
├── worktrees.py         # WorktreeManager (git worktree lifecycle)
├── agent_invoker.py     # AgentInvoker (Claude Agents SDK invocation)
└── progress.py          # ProgressDisplay (Rich-based visualization)
```

**Rationale**:
- ✅ Separation of concerns (testable components)
- ✅ Aligns with GuardKit's phase-based workflow
- ✅ Reusable (WorktreeManager useful elsewhere)
- ✅ Maintainable (6/10 complexity, reasonable for team)

## Implementation Subtasks

### Wave 1: Foundation Components (Parallel - 4 tasks)

**Can run simultaneously via Conductor for 33% time savings**

| Task | Description | Effort | Mode |
|------|-------------|--------|------|
| TASK-AB-6908 | Update agent definitions | 1-2h | direct |
| TASK-AB-F55D | Implement WorktreeManager | 3-4h | task-work |
| TASK-AB-A76A | Implement AgentInvoker | 4-5h | task-work |
| TASK-AB-584A | Implement ProgressDisplay | 2-3h | task-work |

**Total Wave 1**: 10-14 hours sequential, **4-5 hours with Conductor**

### Wave 2: Orchestration (Sequential - 1 task)

| Task | Description | Effort | Mode |
|------|-------------|--------|------|
| TASK-AB-9869 | Implement AutoBuildOrchestrator | 5-6h | task-work |

### Wave 3: CLI Interface (Sequential - 1 task)

| Task | Description | Effort | Mode |
|------|-------------|--------|------|
| TASK-AB-BD2E | Implement CLI commands | 2-3h | task-work |

### Wave 4: Testing & Documentation (Sequential - 1 task)

| Task | Description | Effort | Mode |
|------|-------------|--------|------|
| TASK-AB-2D16 | Integration testing and docs | 3-4h | task-work |

## Total Effort

- **Sequential**: 20-27 hours
- **With Conductor** (Wave 1 parallel): **14-18 hours** (33% faster)

## Success Metrics

| Metric | Target |
|--------|--------|
| Task completion rate | ≥50% (autonomous, no human intervention) |
| Average turns to completion | ≤4 turns |
| Coach catch rate | >80% (catches Player's premature success claims) |
| False approval rate | 0% (no broken code approved) |
| Time to working prototype | ≤2 weeks |

## Usage (After Implementation)

```bash
# Basic usage
guardkit autobuild task TASK-042

# With options
guardkit autobuild task TASK-042 --max-turns 3 --auto-merge

# Check status
guardkit autobuild status TASK-042
```

## Benefits

- **Autonomous execution**: Tasks complete without constant supervision
- **Nights & weekends**: Agents work while humans sleep
- **Higher quality**: Coach validation catches issues humans miss
- **Faster iteration**: 30-60 minute autonomous runs vs 5-minute supervised turns
- **Better testing**: Adversarial review ensures edge cases covered

## Related Documents

- **Feature Spec**: `docs/research/guardkit-agent/Phase1a_Feature_Spec.md`
- **Review Report**: `.claude/reviews/TASK-REV-47D2-review-report.md`
- **Block AI Research**: https://github.com/dhanji/g3
