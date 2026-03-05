---
id: TASK-ISF-003
title: Fix -ext.md file copying in guardkit init
status: completed
completed: 2026-03-04T12:00:00Z
priority: high
complexity: 3
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 2
implementation_mode: task-work
tags: [init, templates, progressive-disclosure, agents]
---

# TASK-ISF-003: Fix -ext.md File Copying in Init

## Problem

`guardkit init` previously skipped `-ext.md` (extended agent markdown) files during template copying:

```python
# init.py lines 217-220
# Skip extended files (-ext.md) - they stay in ~/.agentecflow/
# for on-demand loading (progressive disclosure pattern)
if agent_file.name.endswith("-ext.md"):
    continue
```

The three affected files in the fastapi-python template:
- `fastapi-database-specialist-ext.md`
- `fastapi-specialist-ext.md`
- `fastapi-testing-specialist-ext.md`

These extended files contain detailed agent knowledge needed for progressive disclosure — the core agent file loads always, and the extended file loads on-demand when that agent is invoked. By not copying them to the project, the progressive disclosure pattern breaks.

## Solution

Removed the `-ext.md` skip logic in `init.py` so extended agent files are copied to the project's `.claude/agents/` directory alongside their core counterparts.

## Files Changed

- `guardkit/cli/init.py` — Lines 217-220: Removed the ext.md skip block
- `tests/cli/test_init.py` — Added `test_copies_ext_md_files` test

## Acceptance Criteria

- [x] `-ext.md` files are copied to project `.claude/agents/` during init
- [x] Core agent files still copied correctly (no regression)
- [x] Tests verify both core and ext files are present after init
- [x] Progressive disclosure pattern works (core loads always, ext loads on-demand)

## Testing

```bash
pytest tests/cli/test_init.py -v
# 90/90 tests passed
```
