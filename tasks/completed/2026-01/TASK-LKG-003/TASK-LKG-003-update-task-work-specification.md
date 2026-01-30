---
id: TASK-LKG-003
title: Update task-work.md specification with Phase 2.1
status: completed
updated: 2026-01-30T12:15:00Z
completed: 2026-01-30T12:15:00Z
created: 2026-01-30
priority: high
complexity: 3
tags: [documentation, task-work, specification]
parent_review: TASK-REV-668B
feature_id: library-knowledge-gap
implementation_mode: direct
wave: 2
conductor_workspace: library-knowledge-gap-wave2-spec
depends_on:
  - TASK-LKG-001
  - TASK-LKG-002
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met, specification updated"
completed_location: tasks/completed/2026-01/TASK-LKG-003/
organized_files:
  - TASK-LKG-003-update-task-work-specification.md
  - completion-report.md
---

# TASK-LKG-003: Update task-work.md Specification

## Description

Update the `/task-work` command specification to document the new Phase 2.1 (Library Context Gathering). This ensures the workflow is properly documented and AI agents follow the updated protocol.

## Acceptance Criteria

- [x] Phase 2.1 documented in execution protocol section
- [x] Library detection triggers documented
- [x] Context7 integration flow documented
- [x] Display format specified
- [x] Skip conditions documented (--no-library-context flag)
- [x] Error handling documented

## Implementation Notes

### File to Update

```
installer/core/commands/task-work.md
```

### Location in Document

Insert Phase 2.1 between:
- Phase 1.6 (Clarifying Questions)
- Phase 2 (Implementation Planning)

### Content to Add

```markdown
#### Phase 2.1: Library Context Gathering (NEW)

**PURPOSE**: Proactively fetch library documentation for detected libraries before implementation planning. This prevents stub implementations by ensuring the AI has concrete API knowledge.

**TRIGGER**: Always execute (detection is fast, no-op if no libraries found)

**SKIP CONDITIONS**:
- `--no-library-context` flag is set
- `--implement-only` flag is set (uses saved design)

**WORKFLOW**:

**STEP 1: Detect Libraries**

```python
from installer.core.commands.lib.library_detector import detect_library_mentions

libraries = detect_library_mentions(
    task_context.get("title", ""),
    task_context.get("description", "")
)
```

**IF** no libraries detected:
```
DISPLAY: "📚 No library dependencies detected"
PROCEED to Phase 2
```

**STEP 2: Resolve and Fetch**

**IF** libraries detected:

```python
from installer.core.commands.lib.library_context import gather_library_context

library_context = gather_library_context(libraries)
task_context["library_context"] = library_context
```

**DISPLAY**:
```
📚 Library Context Gathered:
  • graphiti-core
    Import: from graphiti_core import Graphiti
    Methods: search(), add_episode(), build_indices()

Proceed with planning? [Y/n]:
```

**WAIT** for user confirmation (default: Yes after 5 seconds)

**STEP 3: Inject into Planning Context**

Add `library_context` to Phase 2 agent prompt. The planning agent receives:

```
LIBRARY CONTEXT (from Phase 2.1):
The following libraries were detected in this task. Use this documentation
to write WORKING code, not stubs:

### graphiti-core
Import: `from graphiti_core import Graphiti`
Initialization:
```python
graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
await graphiti.build_indices()
```
Key Methods: search(), add_episode(), build_indices()

[Context7 documentation snippets...]

IMPORTANT: Use the actual API calls shown above. Do NOT write placeholder
comments like "# In production, this would call..."
```

**PROCEED** to Phase 2 with enhanced context

**ERROR HANDLING**:

If Context7 resolution fails for a library:
```
⚠️  Could not resolve: graphiti-core
    Error: Not found in Context7 registry
    Proceeding with training data for this library.
```
Continue workflow - do not block on resolution failures.

**FLAG: --no-library-context**

Skip Phase 2.1 entirely:

```bash
/task-work TASK-XXX --no-library-context
```

Use when:
- Libraries are well-known (training data sufficient)
- Context7 is unavailable
- Faster iteration needed
```

### Update Phase 2 Prompt Section

Update Phase 2 (Implementation Planning) to include library context injection:

```markdown
**INVOKE** Task tool with documentation context, clarification decisions, AND library context:
```
subagent_type: "{selected_planning_agent_from_table}"
description: "Plan implementation for TASK-XXX"
prompt: "<AGENT_CONTEXT>
...existing context fields...
</AGENT_CONTEXT>

{if task_context.library_context:}
LIBRARY CONTEXT (from Phase 2.1):
{for lib_name, ctx in task_context.library_context.items():}
{ctx.to_prompt_section()}
{endfor}

IMPORTANT: Use the actual API calls shown above. Do NOT write stubs.
{endif}

...rest of existing prompt...
"
```

### Update Available Flags Table

Add to flags table:

| Flag | Description |
|------|-------------|
| `--no-library-context` | Skip Phase 2.1 library context gathering |

## Notes

- This is a documentation task (direct mode, no code changes)
- Depends on TASK-LKG-001 and TASK-LKG-002 being complete
- Update should be consistent with existing task-work.md style
