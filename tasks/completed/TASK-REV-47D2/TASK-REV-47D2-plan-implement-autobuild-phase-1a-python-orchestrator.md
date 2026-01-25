---
id: TASK-REV-47D2
title: Plan: Implement AutoBuild Phase 1a Python orchestrator for adversarial cooperation
status: completed
task_type: review
created: 2025-12-23T07:14:46Z
updated: 2025-12-23T07:20:00Z
completed: 2025-12-23T07:25:00Z
completed_location: tasks/completed/TASK-REV-47D2/
priority: high
tags: [autobuild, orchestration, adversarial-cooperation, architecture]
complexity: 0
review_results:
  mode: decision
  depth: standard
  score: 90
  findings_count: 15
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-47D2-review-report.md
  completed_at: 2025-12-23T07:20:00Z
organized_files:
  - TASK-REV-47D2-plan-implement-autobuild-phase-1a-python-orchestrator.md
  - review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Implement AutoBuild Phase 1a Python orchestrator for adversarial cooperation

## Description

Plan and architect the implementation of the AutoBuild Phase 1a feature - a Python orchestrator that enables autonomous feature implementation through adversarial cooperation between Player and Coach agents.

This feature extends GuardKit with a `/autobuild` capability implementing the dialectical autocoding pattern from Block AI Research, achieving higher completion rates than single-agent approaches.

## Feature Context

**Feature Spec**: `docs/research/guardkit-agent/Phase1a_Feature_Spec.md`

**Agent Definitions**:
- `.claude/agents/autobuild-player.md` - Implementation-focused agent
- `.claude/agents/autobuild-coach.md` - Validation-focused agent

**Core Pattern**: Two specialized agents in bounded adversarial cooperation:
- **Player**: Implements code, writes tests, responds to feedback
- **Coach**: Validates independently, runs tests, approves or provides feedback
- **Orchestrator**: Manages the loop, enforces bounds, handles approval/escalation

## Key Requirements

### FR-3: Python Orchestrator (Primary Focus)

The orchestrator manages the adversarial loop with these responsibilities:

1. **Task Management**
   - Load task from `.guardkit/tasks/` (existing GuardKit format)
   - Parse requirements and acceptance criteria
   - Track turn count and enforce max turns (default: 5)

2. **Git Worktree Isolation**
   - Create isolated git worktree: `.guardkit/worktrees/{task_id}/`
   - Create branch: `autobuild/{task_id}`
   - All modifications happen in isolation
   - Merge on approval, preserve on failure

3. **Agent Invocation**
   - Invoke Player via Claude Agents SDK with fresh context
   - Pass requirements + previous Coach feedback
   - Invoke Coach via Claude Agents SDK with fresh context
   - Pass requirements + Player report for validation

4. **Loop Management**
   ```
   FOR turn = 1 to max_turns:
     a. Invoke Player with requirements + feedback
     b. Wait for Player report
     c. Invoke Coach with requirements + Player report
     d. Read Coach decision
     e. IF decision == "approve":
          - Prompt user to merge
          - Merge worktree to main
          - RETURN success
     f. ELSE:
          - Extract feedback for next turn
          - CONTINUE
   IF max_turns reached without approval:
     - RETURN failure (escalate to human)
   ```

5. **Progress Display**
   - Real-time feedback using Rich library
   - Show turn-by-turn progress
   - Display Player/Coach status per turn

## Agent Review Requirements

Before implementation, we should review the existing agent definitions to ensure they match GuardKit's template standards:

**Files to Review**:
- `.claude/agents/autobuild-player.md`
- `.claude/agents/autobuild-coach.md`

**Review Criteria**:
1. Frontmatter compliance (required fields, metadata structure)
2. Section structure (capabilities, boundaries, phase integration)
3. Tool usage patterns (Read, Write, Edit, Bash permissions)
4. Integration with GuardKit workflow
5. Progressive disclosure format (core + extended split)

## Technical Architecture

### Component Structure

```
guardkit/
├── cli/
│   ├── main.py              # Add autobuild group
│   └── autobuild.py         # [NEW] AutoBuild CLI commands
├── orchestrator/
│   ├── __init__.py          # [NEW]
│   ├── autobuild.py         # [NEW] AutoBuildOrchestrator
│   └── worktrees.py         # [NEW] WorktreeManager
└── ...

.claude/
├── agents/
│   ├── autobuild-player.md  # ✅ EXISTS - Review needed
│   └── autobuild-coach.md   # ✅ EXISTS - Review needed
└── commands/
    └── autobuild.md         # [NEW] Optional slash command

.guardkit/
├── tasks/                   # Existing task files
├── autobuild/               # [NEW] AutoBuild working directory
│   └── TASK-XXX/
│       ├── player_turn_1.json
│       ├── coach_turn_1.json
│       └── ...
└── worktrees/               # [NEW] Git worktrees
    └── TASK-XXX/            # Isolated worktree
```

### Key Dependencies

```toml
[project.dependencies]
claude-code-sdk = ">=0.1.0"
rich = ">=13.0"
click = ">=8.0"
```

## Acceptance Criteria

### AC-1: Agent Definition Review
- [ ] Review autobuild-player.md against GuardKit template standards
- [ ] Review autobuild-coach.md against GuardKit template standards
- [ ] Identify any template compliance issues
- [ ] Document required agent definition updates

### AC-2: Architecture Design
- [ ] Design orchestrator class structure (AutoBuildOrchestrator)
- [ ] Design worktree management (WorktreeManager)
- [ ] Define CLI command interface (`guardkit autobuild task TASK-XXX`)
- [ ] Design agent invocation patterns (Claude Agents SDK integration)
- [ ] Define turn-based feedback loop structure

### AC-3: Integration Planning
- [ ] Plan integration with existing GuardKit task format
- [ ] Plan git worktree creation and cleanup
- [ ] Plan agent invocation via Claude Agents SDK
- [ ] Plan progress display using Rich library
- [ ] Plan error handling and graceful failure

### AC-4: Implementation Breakdown
- [ ] Break implementation into subtasks
- [ ] Estimate complexity for each subtask
- [ ] Identify dependencies and execution order
- [ ] Recommend parallel vs sequential execution

## Review Focus Areas

### 1. Agent Definition Compliance
- Frontmatter structure and required fields
- Section organization (capabilities, boundaries, examples)
- Tool permission specifications
- Integration with GuardKit workflow phases

### 2. Orchestration Architecture
- Fresh context per turn (no context pollution)
- Bounded execution (max turns, timeouts)
- Requirements as single source of truth
- Coach read-only enforcement

### 3. Git Worktree Strategy
- Worktree creation and naming conventions
- Branch management (autobuild/{task_id})
- Merge strategy on approval
- Cleanup strategy on failure
- Conflict prevention

### 4. SDK Integration Patterns
- Agent invocation via `query()` function
- Permission mode configuration (acceptEdits vs default)
- Allowed tools per agent (Player: Read/Write/Edit/Bash, Coach: Read/Bash)
- Progress message handling

### 5. Error Handling
- SDK errors and timeouts
- Agent failures and retries
- Worktree conflicts
- Max turns exceeded
- Graceful degradation

## Success Metrics

| Metric | Target |
|--------|--------|
| Agent template compliance | 100% |
| Architecture clarity | Clear class structure, responsibilities |
| Implementation breakdown | 5-8 subtasks, <8 hours each |
| Integration risk | Low (clear interfaces defined) |
| Documentation quality | Complete implementation guide |

## Related Documents

- **Feature Spec**: `docs/research/guardkit-agent/Phase1a_Feature_Spec.md`
- **Player Agent**: `.claude/agents/autobuild-player.md`
- **Coach Agent**: `.claude/agents/autobuild-coach.md`
- **Block AI Research**: https://github.com/dhanji/g3

## Implementation Notes

This is a review task. The output will be:
1. Agent definition review findings and recommendations
2. Detailed architecture design
3. Implementation breakdown with subtasks
4. Risk assessment and mitigation strategies

After review approval, implementation tasks will be created based on the recommendations.
