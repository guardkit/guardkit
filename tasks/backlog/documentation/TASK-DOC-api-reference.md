# Create API/Command Reference Documentation

**Priority**: Enhancement
**Category**: Documentation - Reference
**Estimated Effort**: 4-5 hours

## Problem

Users need comprehensive reference documentation for all GuardKit commands, their parameters, flags, and behaviors. While command .md files exist in `installer/core/commands/`, they need to be consolidated and presented in a user-friendly format in MkDocs.

## Command Categories

### 1. Core Workflow Commands
- `/task-create`
- `/task-work`
- `/task-complete`
- `/task-status`
- `/task-refine`

### 2. Review Workflow Commands
- `/task-review`

### 3. Design-to-Code Commands
- `/figma-to-react`
- `/zeplin-to-maui`

### 4. Template Management Commands
- `/template-create`
- `/template-validate`

### 5. Agent Management Commands
- `/agent-enhance`
- `/agent-validate`
- `/agent-format`

### 6. Utility Commands
- `/debug`
- `guardkit init`
- `guardkit doctor`

## Acceptance Criteria

1. Create `docs/reference/commands.md` page
2. Add to navigation under "Reference" section
3. For each command, document:
   - Command syntax with all parameters
   - Description and purpose
   - Parameters (required vs optional)
   - Flags with descriptions
   - Usage examples (basic and advanced)
   - Output format
   - Exit codes
   - Related commands
   - Common errors
4. Add searchable index
5. Include quick reference table
6. Add filtering by category

## Command Documentation Format

```markdown
## /task-create

Create a new task in the backlog.

**Syntax:**
```bash
/task-create "<title>" [priority:high|medium|low] [prefix:PREFIX] [task_type:implementation|review]
```

**Parameters:**
- `title` (required): Task description
- `priority` (optional): Task priority (default: medium)
- `prefix` (optional): 2-4 char uppercase prefix for task ID
- `task_type` (optional): implementation or review (default: implementation)

**Examples:**
```bash
# Basic task
/task-create "Add user login"

# High priority with prefix
/task-create "Fix auth bug" priority:high prefix:FIX

# Review task
/task-create "Review auth architecture" task_type:review
```

**Output:**
```
Created: TASK-a3f8
Status: BACKLOG
```

**Related:**
- `/task-work` - Work on the created task
- `/task-status` - Check task status
```

## Implementation Notes

- Extract from existing command .md files
- Add runnable examples (copy-paste ready)
- Include screenshots where helpful
- Add "See Also" cross-references
- Create quick reference cheat sheet

## References

- installer/core/commands/*.md
- Existing command documentation
- README.md command examples
