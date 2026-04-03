---
id: TASK-GMO-005
title: "Document detailed setup instructions for MacBook Graphiti LLM offload"
status: completed
updated: 2026-04-03T15:45:00Z
completed: 2026-04-03T15:45:00Z
created: 2026-04-03T00:00:00Z
priority: medium
tags: [graphiti, macbook, documentation, setup]
task_type: implementation
parent_review: TASK-REV-GMAC
feature_id: FEAT-GMO
implementation_mode: direct
wave: 3
complexity: 2
depends_on:
  - TASK-GMO-004
completed_location: tasks/completed/TASK-GMO-005/
organized_files:
  - TASK-GMO-005.md
---

# Task: Document detailed setup instructions for MacBook Graphiti LLM offload

## Description

Create a reference document with step-by-step instructions for setting up and using
the MacBook Pro M2 Max as an alternative Graphiti LLM host. This should be written
after the setup is validated (TASK-GMO-004) so it reflects actual tested steps.

## Acceptance Criteria

- [x] Document created at `docs/reference/graphiti-macbook-offload.md`
- [x] All commands tested and verified (based on TASK-GMO-004 validated results)
- [x] Cross-referenced from `docs/reference/gb10-vllm-resources.md` (GPU contention section)
- [x] Referenced from `.guardkit/graphiti.yaml` header comments

## Implementation Notes

Document covers all 8 sections from the task spec:
1. Overview (architecture diagram, problem/solution)
2. Prerequisites
3. Quick Start (copy-paste commands for Ollama install, model pull, config)
4. Configuration Reference (all 4 config files, env var overrides)
5. Switching Between GB10 and MacBook (toggle script, restart requirements)
6. Performance Notes (measured data from TASK-GMO-004: 54.7s pipeline, 15-25 tok/s)
7. Troubleshooting (firewall, ports, memory, Tailscale, API compatibility)
8. Memory Budget (component RAM table)

Cross-references added:
- `gb10-vllm-resources.md` Option 2 updated with validated metrics and link
- `graphiti.yaml` header updated with pointer to offload docs
