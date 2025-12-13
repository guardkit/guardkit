---
id: TASK-WC-001
title: Update feature-plan.md to invoke Python orchestrator
status: superseded
created: 2025-12-13T21:00:00Z
updated: 2025-12-13T22:45:00Z
priority: high
tags: [clarification, feature-plan, integration, direct, superseded]
complexity: 3
implementation_mode: direct
conductor_workspace: wire-up-clarification-wave1-1
parent_feature: wire-up-clarification
related_review: TASK-REV-CLQ2
superseded_by: TASK-WC-007
superseded_reason: "TASK-REV-CLQ3 decided to use unified subagent pattern instead of orchestrators"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update feature-plan.md to invoke Python orchestrator

## Description

Modify the `/feature-plan` command specification to invoke the Python orchestrator instead of describing a manual workflow. This will enable clarifying questions to be displayed for ambiguous feature descriptions.

## Background

The current `feature-plan.md` contains "CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE" that tell Claude to manually orchestrate the workflow step-by-step. This bypasses the Python orchestrator that contains the clarification logic.

## Changes Required

### 1. Replace Manual Workflow with Python Invocation

**File**: `installer/core/commands/feature-plan.md`

**Location**: Lines ~954-1012 (CRITICAL EXECUTION INSTRUCTIONS section)

**Current**:
```markdown
## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/feature-plan "description"`, you MUST:

### Execution Steps

1. Parse feature description from command arguments
2. Execute `/task-create` with:
   - Title: "Plan: {description}"
   - Flags: `task_type:review priority:high`
3. Capture task ID from output (regex: `TASK-[A-Z0-9-]+`)
4. Execute `/task-review` with captured task ID:
   - Flags: `--mode=decision --depth=standard`
5. Present decision checkpoint (inherited from `/task-review`)
6. Handle user decision:
   - [A]ccept: Save review, show reference message
   - [R]evise: Re-run review with additional focus
   - [I]mplement: Create subfolder + subtasks + guide
   - [C]ancel: Move to cancelled state
```

**New**:
```markdown
## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/feature-plan "description"`, execute the Python orchestrator:

### Primary Execution Method

Execute the feature-plan orchestrator which handles clarification, review, and implementation:

```bash
python3 ~/.agentecflow/bin/feature-plan-orchestrator "{description}" [flags]
```

**Flag Mapping**:
- `--no-questions`: Pass through to skip clarification
- `--with-questions`: Pass through to force clarification
- `--defaults`: Pass through to use defaults without prompting
- `--mode={mode}`: Pass through for review mode (default: decision)
- `--depth={depth}`: Pass through for review depth (default: standard)

**Example Invocations**:
```bash
# Basic usage
python3 ~/.agentecflow/bin/feature-plan-orchestrator "implement dark mode"

# Skip clarification
python3 ~/.agentecflow/bin/feature-plan-orchestrator "add caching" --no-questions

# Force clarification
python3 ~/.agentecflow/bin/feature-plan-orchestrator "set up infrastructure" --with-questions
```

### What the Orchestrator Handles

1. **Phase 1**: Creates review task automatically
2. **Phase 2**: Executes clarification (Context A - review scope questions)
3. **Phase 3**: Runs architectural/decision review
4. **Phase 4**: Presents decision checkpoint [A/R/I/C]
5. **Phase 5**: If [I]mplement chosen:
   - Executes Context B clarification (implementation preferences)
   - Generates feature folder with subtasks
   - Creates README.md and IMPLEMENTATION-GUIDE.md

### Fallback (If Python Not Available)

If the Python orchestrator fails or is unavailable, fall back to the manual workflow:
1. Execute `/task-create "Plan: {description}" task_type:review priority:high`
2. Execute `/task-review TASK-XXX --mode=decision --depth=standard`
3. Note: Clarification will NOT work in fallback mode

### Error Handling

If the orchestrator exits with non-zero code, display the error and suggest:
- Check that guardkit is installed correctly
- Run `guardkit doctor` to diagnose issues
- Try manual fallback workflow
```

## Acceptance Criteria

- [ ] Python orchestrator invocation replaces manual workflow instructions
- [ ] All flags are documented with proper mapping
- [ ] Fallback workflow documented for error cases
- [ ] Example invocations provided
- [ ] No breaking changes to existing functionality

## Testing

1. Run `/feature-plan "test feature"` and verify Python orchestrator is called
2. Run `/feature-plan "ambiguous input"` and verify clarification questions appear
3. Run `/feature-plan "test" --no-questions` and verify no questions appear

## Implementation Notes

- This is a **direct** change - modify the markdown file directly
- No code changes needed - the Python orchestrator already exists
- Test manually before marking complete
