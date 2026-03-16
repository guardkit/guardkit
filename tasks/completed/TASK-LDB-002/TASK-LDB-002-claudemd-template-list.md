---
id: TASK-LDB-002
title: "Update default template CLAUDE.md to list langchain-deepagents"
status: completed
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
completed: 2026-03-16T00:00:00Z
previous_state: in_review
priority: high
complexity: 1
tags: [documentation, claude-md, langchain-deepagents]
task_type: implementation
parent_review: TASK-REV-38D7
feature_id: FEAT-LDB
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Update default template CLAUDE.md to list langchain-deepagents

## Description

The default template's CLAUDE.md (used by `guardkit init default`) lists 4 specialized
templates under "Use Specialized Templates Instead". Add `langchain-deepagents` to
this list so users know it exists.

## File to Modify

`installer/core/templates/default/.claude/CLAUDE.md` (the template source)

**Note**: The deepagents-tutor-exemplar repo's `.claude/CLAUDE.md` is a copy from this
template. It will be updated next time `guardkit init` is run, or can be updated
manually in that repo separately.

## Change Required

In the "Use Specialized Templates Instead" section, add:

```markdown
- **LangChain/DeepAgents** -> `langchain-deepagents` template
```

After the existing entries (react-typescript, fastapi-python, nextjs-fullstack,
react-fastapi-monorepo).

## Acceptance Criteria

- [ ] Default template CLAUDE.md lists langchain-deepagents as a specialized option
- [ ] Existing template references unchanged
- [ ] Markdown formatting consistent with other entries
