---
id: TASK-REV-5842
title: Review vLLM profiling project setup and Graphiti naming
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
completed: 2026-03-03T00:00:00Z
completed_location: tasks/completed/TASK-REV-5842/
priority: high
tags: [review, vllm, graphiti, project-setup, knowledge-graph]
complexity: 0
task_type: review
decision_required: true
review_results:
  mode: architectural
  depth: standard
  score: 92
  findings_count: 6
  recommendations_count: 6
  decision: accept
  report_path: .claude/reviews/TASK-REV-5842-review-report.md
  completed_at: 2026-03-03T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review vLLM Profiling Project Setup and Graphiti Naming

## Description

Review the setup requirements for a new project dedicated to local vLLM profiling and tuning. The project will be initialized using `guardkit init fastapi-python` but requires careful consideration of project naming/ID conventions to ensure correct Graphiti knowledge graph namespace isolation.

## Context

- **Intent**: Create a separate project for local vLLM profiling and model tuning workflows
- **Template**: `fastapi-python` (available in `installer/core/templates/fastapi-python/`)
- **Key Concern**: The `project_id` in `.guardkit/graphiti.yaml` must be set correctly so that knowledge captured in this new project remains isolated from the existing `guardkit` project namespace

## Review Areas

### 1. Project ID / Name for Graphiti Isolation
- [x] Review how `normalize_project_id()` works in `guardkit/knowledge/graphiti_client.py` (lowercase, hyphens, no special chars, max 50 chars)
- [x] Determine the correct `project_id` value for the new vLLM profiling project
- [x] Confirm that `group_id` prefixing via `client.get_group_id()` properly isolates namespaces in FalkorDB
- [x] Check current GuardKit project uses `project_id: guardkit` in `.guardkit/graphiti.yaml`

### 2. Template Initialization Process
- [x] Review what `guardkit init fastapi-python` creates (directory structure, config files)
- [x] Verify the init process creates `.guardkit/graphiti.yaml` with a placeholder or prompt for `project_id`
- [x] Check if init auto-detects project name from directory name or requires manual input

### 3. Graphiti Configuration for New Project
- [x] Determine if the new project should share the same FalkorDB instance (whitestocks:6379) or use a separate one
- [x] Review `group_ids` configuration — does the new project need custom groups beyond defaults?
- [x] Confirm vLLM LLM/embedding provider settings should be carried over or configured independently

### 4. Multi-Project Coexistence
- [x] Review `/context-switch` command compatibility with the new project
- [x] Verify knowledge isolation — queries in one project must not leak into another
- [x] Check if `guardkit graphiti status` correctly reports per-project namespace

## Acceptance Criteria

- [x] Clear recommendation on project name/ID (e.g., `vllm-profiling`, `vllm-tuning`)
- [x] Step-by-step setup instructions for the new project
- [x] Confirmation of Graphiti namespace isolation approach
- [x] Any gotchas or prerequisites documented

## Key Files to Review

| File | Purpose |
|------|---------|
| `guardkit/knowledge/graphiti_client.py` | `normalize_project_id()`, `GraphitiConfig`, `GraphitiClient` |
| `.guardkit/graphiti.yaml` | Current project Graphiti config (reference) |
| `installer/scripts/install.sh` | `guardkit init` implementation |
| `installer/core/templates/fastapi-python/` | Template contents |
| `installer/core/commands/context-switch.md` | Multi-project navigation |
| `.claude/rules/graphiti-knowledge.md` | Graphiti integration rules |

## Implementation Notes

Review completed. Key findings:
- Recommended project_id: `vllm-profiling`
- Share FalkorDB instance (`whitestocks:6379`) — namespace isolation via `{project_id}__` prefixing is sufficient
- Copy LLM/embedding provider settings from existing config
- Gap identified: `guardkit init` only writes `project_id` to graphiti.yaml, not full config

Follow-up task created: **TASK-4B7F** — Add `--copy-graphiti` flag to `guardkit init` CLI to auto-discover and copy an existing project's full Graphiti config.

Full review report: `.claude/reviews/TASK-REV-5842-review-report.md`
