---
id: TASK-WC-002
title: Update task-review.md to invoke Python orchestrator
status: superseded
created: 2025-12-13T21:00:00Z
updated: 2025-12-13T22:45:00Z
priority: high
tags: [clarification, task-review, integration, direct, superseded]
complexity: 3
implementation_mode: direct
conductor_workspace: wire-up-clarification-wave1-2
parent_feature: wire-up-clarification
related_review: TASK-REV-CLQ2
superseded_by: TASK-WC-008
superseded_reason: "TASK-REV-CLQ3 decided to use unified subagent pattern instead of orchestrators"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task-review.md to invoke Python orchestrator

## Description

Modify the `/task-review` command specification to invoke the Python orchestrator instead of relying on Claude to manually follow the workflow phases. This will enable clarifying questions to be displayed for complex review tasks.

## Background

The current `task-review.md` describes the review phases but doesn't explicitly instruct Claude to run the Python orchestrator. The orchestrator at `installer/core/commands/lib/task_review_orchestrator.py` contains fully implemented clarification logic that is never called.

## Changes Required

### 1. Add Execution Instructions Section

**File**: `installer/core/commands/task-review.md`

**Location**: Add after the "Execution Protocol" section (around line 580)

**Add New Section**:
```markdown
## EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/task-review TASK-XXX [flags]`, execute the Python orchestrator:

### Primary Execution Method

```bash
python3 ~/.agentecflow/bin/task-review-orchestrator {task_id} [flags]
```

**Required Parameters**:
- `{task_id}`: The task ID (e.g., TASK-REV-CLQ2)

**Flag Mapping**:
- `--mode={mode}`: Review mode (architectural, code-quality, decision, technical-debt, security)
- `--depth={depth}`: Review depth (quick, standard, comprehensive)
- `--output={format}`: Output format (summary, detailed, presentation)
- `--no-questions`: Skip clarification questions
- `--with-questions`: Force clarification even for simple tasks
- `--defaults`: Use default answers without prompting

**Example Invocations**:
```bash
# Basic architectural review
python3 ~/.agentecflow/bin/task-review-orchestrator TASK-REV-A3F2 --mode=architectural --depth=standard

# Security audit with comprehensive depth
python3 ~/.agentecflow/bin/task-review-orchestrator TASK-SEC-B4C5 --mode=security --depth=comprehensive

# Quick review, skip questions
python3 ~/.agentecflow/bin/task-review-orchestrator TASK-XXX --mode=code-quality --depth=quick --no-questions

# Force clarification
python3 ~/.agentecflow/bin/task-review-orchestrator TASK-XXX --mode=decision --with-questions
```

### What the Orchestrator Handles

1. **Phase 1**: Load review context from task file
2. **Phase 1.5**: Clarification (if complexity >= 4 or --with-questions)
   - Determines clarification mode (SKIP/QUICK/FULL)
   - Generates review scope questions
   - Collects user responses
   - Persists decisions to task frontmatter
3. **Phase 2**: Execute review analysis with appropriate model
4. **Phase 3**: Synthesize recommendations
5. **Phase 4**: Generate review report
6. **Phase 5**: Present decision checkpoint [A/R/I/C]

### Clarification Behavior

The orchestrator automatically determines when to ask clarification questions:

| Complexity | Decision/Architectural | Other Modes |
|------------|----------------------|-------------|
| 0-3 | Skip | Skip |
| 4-6 | Ask (QUICK mode) | Skip (unless --with-questions) |
| 7-10 | Ask (FULL mode) | Ask (FULL mode) |

**Override Flags**:
- `--no-questions`: Always skip clarification
- `--with-questions`: Always ask clarification
- `--defaults`: Apply defaults without prompting

### Fallback (If Python Not Available)

If the orchestrator fails, inform the user:
```
The task-review orchestrator failed to execute.
Clarification questions will not be available.

You can proceed with manual review workflow:
1. Read task file to understand scope
2. Execute review analysis based on mode
3. Present findings and recommendations
4. Offer decision options [A/R/I/C]

Note: Run `guardkit doctor` to diagnose installation issues.
```

### Error Handling

Common errors and solutions:
- **Task not found**: Verify task ID exists in tasks/ directory
- **Permission denied**: Check symlink permissions in ~/.agentecflow/bin/
- **Module import error**: Verify guardkit installation with `guardkit doctor`
```

## Acceptance Criteria

- [ ] Execution instructions section added to task-review.md
- [ ] All flags documented with proper mapping
- [ ] Clarification behavior table included
- [ ] Fallback instructions for error cases
- [ ] Example invocations provided

## Testing

1. Run `/task-review TASK-XXX --mode=decision` with complexity >= 5 task
2. Verify clarification questions appear
3. Run `/task-review TASK-XXX --no-questions` and verify no questions
4. Run `/task-review TASK-XXX --with-questions` on simple task and verify questions appear

## Implementation Notes

- This is a **direct** change - modify the markdown file directly
- The Python orchestrator already exists and is fully implemented
- Just need to add instructions for Claude to invoke it
- Test manually before marking complete
