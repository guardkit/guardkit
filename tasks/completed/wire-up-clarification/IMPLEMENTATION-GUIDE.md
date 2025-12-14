# Implementation Guide: Wire Up Clarification Python Orchestrators

## Execution Strategy

### Wave 1: Core Changes (Parallel - 3 tasks)

Execute these tasks in parallel using Conductor workspaces:

| Task | Workspace | Description |
|------|-----------|-------------|
| TASK-WC-001 | `wire-up-clarification-wave1-1` | Update feature-plan.md |
| TASK-WC-002 | `wire-up-clarification-wave1-2` | Update task-review.md |
| TASK-WC-003 | `wire-up-clarification-wave1-3` | Add installer symlinks |

**No dependencies** - these can be done simultaneously.

### Wave 2: Verification (Sequential - 1 task)

After Wave 1 completes:

| Task | Description |
|------|-------------|
| TASK-WC-004 | End-to-end smoke test |

**Depends on**: All Wave 1 tasks must be complete and merged.

## Implementation Details

### TASK-WC-001: Update feature-plan.md

**File**: `installer/core/commands/feature-plan.md`

**Current Behavior** (lines 954-1012):
```markdown
## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/feature-plan "description"`, you MUST:
1. Parse feature description from command arguments
2. Execute `/task-create`...
3. Execute `/task-review`...
```

**New Behavior**:
```markdown
## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/feature-plan "description"`, execute the Python orchestrator:

```bash
python3 ~/.agentecflow/bin/feature-plan-orchestrator "{description}" [flags]
```

The orchestrator handles:
- Task creation
- Clarification questions (Context A)
- Review execution
- Decision checkpoint
- Implementation structure (Context B)
```

**Key Points**:
- Replace manual workflow instructions with Python invocation
- Pass through all flags (--no-questions, --with-questions, --defaults)
- Let Python handle the full workflow

### TASK-WC-002: Update task-review.md

**File**: `installer/core/commands/task-review.md`

**Current Behavior**: Describes phases manually but doesn't invoke Python.

**New Behavior**: Add execution section similar to `/agent-enhance`:
```markdown
## EXECUTION INSTRUCTIONS

Execute via Python orchestrator:

```bash
python3 ~/.agentecflow/bin/task-review-orchestrator {task_id} --mode={mode} --depth={depth} [flags]
```

The orchestrator handles all review phases including clarification.
```

### TASK-WC-003: Add Installer Symlinks

**File**: `installer/scripts/install.sh`

**Add symlinks** (similar to existing agent-enhance pattern):
```bash
# Clarification orchestrators
ln -sf "$GUARDKIT_PATH/installer/core/commands/lib/feature_plan_orchestrator.py" "$HOME/.agentecflow/bin/feature-plan-orchestrator"
ln -sf "$GUARDKIT_PATH/installer/core/commands/lib/task_review_orchestrator.py" "$HOME/.agentecflow/bin/task-review-orchestrator"
```

**Make executable**:
```bash
chmod +x "$HOME/.agentecflow/bin/feature-plan-orchestrator"
chmod +x "$HOME/.agentecflow/bin/task-review-orchestrator"
```

### TASK-WC-004: End-to-End Smoke Test

**Create**: `tests/smoke/test_clarification_e2e.py`

**Test Cases**:

1. **feature-plan with ambiguous input shows questions**:
   ```python
   def test_feature_plan_clarification():
       # Run /feature-plan with ambiguous input
       # Verify Context A questions are displayed
       # Verify user input is collected
   ```

2. **task-review with high complexity shows questions**:
   ```python
   def test_task_review_clarification():
       # Create task with complexity >= 5
       # Run /task-review
       # Verify clarification phase executes
   ```

3. **--no-questions flag skips clarification**:
   ```python
   def test_no_questions_flag():
       # Run with --no-questions
       # Verify no questions are asked
   ```

## Verification Checklist

After all tasks complete:

- [ ] Run `/feature-plan "ambiguous description"` - questions should appear
- [ ] Run `/task-review TASK-XXX` with complexity >= 5 - questions should appear
- [ ] Run with `--no-questions` - questions should NOT appear
- [ ] Verify symlinks exist: `ls -la ~/.agentecflow/bin/*orchestrator*`
- [ ] Smoke tests pass: `pytest tests/smoke/test_clarification_e2e.py -v`

## Rollback Plan

If issues arise:
1. Remove Python invocation lines from feature-plan.md and task-review.md
2. Restore manual workflow instructions
3. Remove symlinks from installer

The Python code will remain (not deleted) but simply not be called.

## Estimated Timeline

| Wave | Tasks | Estimated Time |
|------|-------|----------------|
| Wave 1 | 3 tasks (parallel) | 2-3 hours |
| Wave 2 | 1 task | 1-2 hours |
| **Total** | 4 tasks | **3-5 hours** |
