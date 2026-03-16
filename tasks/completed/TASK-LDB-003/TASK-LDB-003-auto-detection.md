---
id: TASK-LDB-003
title: "Add auto-detection for Python+DeepAgents projects in init-project.sh"
status: completed
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T12:05:00Z
completed: 2026-03-16T12:05:00Z
completed_location: tasks/completed/TASK-LDB-003/
priority: low
complexity: 3
tags: [installer, auto-detection, langchain-deepagents]
task_type: implementation
parent_review: TASK-REV-38D7
feature_id: FEAT-LDB
wave: 2
implementation_mode: task-work
dependencies: [TASK-LDB-001]
---

# Task: Add auto-detection for Python+DeepAgents projects

## Description

When a user runs `guardkit init` without specifying a template, init-project.sh
auto-detects the project type and suggests a template. Currently it maps:

- React projects -> `react-typescript`
- Python projects -> `fastapi-python`
- Node projects -> `nextjs-fullstack`

Add detection for Python projects that use DeepAgents + LangChain, mapping them to
`langchain-deepagents` instead of `fastapi-python`.

## Detection Logic

Check `pyproject.toml` (or `requirements.txt`) for both `deepagents` and `langchain`
as dependencies. If found, suggest `langchain-deepagents`. This check should run
**before** the generic Python detection, since it's more specific.

```bash
# In the detection section (~line 245 and ~line 722)
# Check for DeepAgents+LangChain before generic Python
if [ -f "pyproject.toml" ]; then
    if grep -q "deepagents" pyproject.toml && grep -q "langchain" pyproject.toml; then
        detected_type="deepagents"
    fi
fi

# In the case statement:
deepagents) effective_template="langchain-deepagents" ;;
```

## Acceptance Criteria

- [x] Projects with deepagents+langchain in pyproject.toml auto-detect as langchain-deepagents
- [x] Projects with only langchain (no deepagents) still detect as fastapi-python
- [x] Projects with neither still use default detection
- [x] Detection works with both pyproject.toml and requirements.txt
- [x] Existing auto-detection for react/node/python unchanged
