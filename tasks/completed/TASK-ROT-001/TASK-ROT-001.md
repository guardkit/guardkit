---
id: TASK-ROT-001
title: Fix manifest.json metadata for orchestrator template
status: completed
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T12:00:00Z
completed: 2026-04-02T12:05:00Z
completed_location: tasks/completed/TASK-ROT-001/
priority: high
tags: [template, manifest, metadata]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: task-work
wave: 1
complexity: 2
---

# Task: Fix manifest.json metadata for orchestrator template

## Description

Update the `manifest.json` in `~/.agentecflow/templates/langchain-deepagents-orchestrator/` to have accurate, orchestrator-specific metadata before copying to the installer.

## Changes Required

### display_name
- FROM: `"Python Standard Structure"`
- TO: `"LangChain DeepAgents Orchestrator"`

### description
- FROM: `"Python template using Standard Structure architecture"`
- TO: `"Pipeline orchestrator template using DeepAgents two-model architecture (reasoning model orchestrates, implementation model executes) with LangGraph deployment"`

### source_project
- FROM: `"/Users/richardwoollcott/Projects/appmilla_github/deepagents-orchestrator-exemplar"`
- TO: `"deepagents-orchestrator-exemplar"` (relative reference only)

### Author placeholder default
- FROM: `"default_value": "Richard Woollcott"`
- TO: `"default_value": null`

### frameworks
- FROM: only `pytest`
- TO: Add DeepAgents, LangChain, LangChain-Core, LangGraph, LangChain-Community (match base template versions)

### tags
- Add: `deepagents`, `langchain`, `langgraph`, `orchestrator`, `pipeline`, `two-model`
- Remove generic: `standard-structure`

### category
- FROM: `"general"`
- TO: `"agent"`

### requires
- FROM: `["agent:python-domain-specialist"]`
- TO: `[]` or reference actual template agents

## Acceptance Criteria

- [x] `display_name` is "LangChain DeepAgents Orchestrator"
- [x] `description` mentions pipeline orchestrator, two-model architecture, DeepAgents
- [x] `source_project` has no absolute paths
- [x] `Author` placeholder default is null
- [x] `frameworks` includes DeepAgents, LangChain, LangGraph
- [x] No hardcoded user-specific values remain
