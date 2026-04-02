---
id: TASK-ROT-002
title: Fix CompiledStateGraph import in agents.py.template
status: completed
created: 2026-04-02T00:00:00Z
completed: 2026-04-02T00:00:00Z
priority: high
tags: [template, code-quality, import]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: task-work
wave: 1
complexity: 2
---

# Task: Fix CompiledStateGraph import in agents.py.template

## Description

The `agents.py.template` imports `CompiledStateGraph` from a non-existent module path. Fix the import to use the correct source.

## Current Code

```python
from {{ProjectName}}.graph.state import CompiledStateGraph
```

This assumes a `graph/state.py` module exists in the project, but no such module is provided by the template.

## Fix Options

**Option A (Recommended)**: Import from LangGraph SDK:
```python
from langgraph.graph.state import CompiledStateGraph
```

**Option B**: Use TYPE_CHECKING conditional:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
```

## Acceptance Criteria

- [x] `CompiledStateGraph` import resolves to a real module
- [x] Return type annotations on factory functions are correct
- [x] No references to `{{ProjectName}}.graph.state` remain
