---
id: TASK-LCL-002
title: Add [providers] extras pattern to base pyproject.toml.template
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
state_transition_reason: "Task-complete invoked; acceptance criteria met"
completed_location: tasks/completed/TASK-LCL-002/
organized_files:
  - TASK-LCL-002.md
priority: high
tags: [templates, langchain-deepagents, packaging, les1-provider-parity]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 1
conductor_workspace: langchain-template-lessons-wave1-2
complexity: 2
---

# Task: Add `[providers]` extras pattern to base pyproject.toml.template

## Description

The base template currently lists flat dependencies with no
`[project.optional-dependencies]` block. Neither `langchain-openai` nor
`langchain-google-genai` is declared. Any user who switches from
`provider: "api"` (anthropic) to `provider: "local"` (vLLM / openai-compatible)
will hit `ModuleNotFoundError: langchain_openai`. This is exactly the LES1
§3 LCOI failure mode.

## Evidence

`installer/core/templates/langchain-deepagents/templates/other/other/pyproject.toml.template:6-16`
lists flat `dependencies`. No extras. Coach and Player factories in
`agent-config.yaml.template` both support `provider: "local"` routing through
`init_chat_model(..., model_provider="openai")`, which requires
`langchain-openai`.

## Acceptance Criteria

- [ ] `pyproject.toml.template` adds `[project.optional-dependencies]` with a `providers` key listing `langchain-anthropic>=0.2`, `langchain-openai>=0.2`, `langchain-google-genai>=2.0`.
- [ ] Base `dependencies` retains a default provider (`langchain-anthropic`) so zero-config install still works.
- [ ] `.claude/CLAUDE.md` "Quick Start" block shows `pip install .[providers]` instead of `pip install -r requirements.txt`.
- [ ] If `requirements.txt.template` does not exist (verify), delete the stale reference from docs and keep `pyproject.toml.template` as the single source.
- [ ] LES1 lesson encoded as a comment in the `[providers]` block: `# Every LangChain integration named in code MUST appear here. See TASK-REV-LES1 / LES1 §3 LCOI.`

## Files

- `installer/core/templates/langchain-deepagents/templates/other/other/pyproject.toml.template`
- `installer/core/templates/langchain-deepagents/.claude/CLAUDE.md`

## Implementation Notes

This task's pattern is reused by TASK-LCL-004 for the orchestrator template —
keep the version pins consistent across templates.

## Links

- Review: [TASK-REV-LES1 report §BLOCKER-2](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- LES1 §3 packaging: [cross-agent-lessons-from-specialist-agent.md](../../../../specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md)
