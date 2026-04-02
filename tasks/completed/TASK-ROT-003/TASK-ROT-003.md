---
id: TASK-ROT-003
title: Copy orchestrator template to installer/core/templates/
status: completed
completed: 2026-04-02T14:42:00Z
completed_location: tasks/completed/TASK-ROT-003/
created: 2026-04-02T00:00:00Z
priority: high
tags: [template, installer, registration]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: direct
wave: 2
complexity: 1
depends_on:
  - TASK-ROT-001
  - TASK-ROT-002
---

# Task: Copy orchestrator template to installer/core/templates/

## Description

Copy the fixed template from `~/.agentecflow/templates/langchain-deepagents-orchestrator/` to `installer/core/templates/langchain-deepagents-orchestrator/` in the GuardKit repo.

## Steps

1. Copy entire directory:
   ```bash
   cp -r ~/.agentecflow/templates/langchain-deepagents-orchestrator/ \
     installer/core/templates/langchain-deepagents-orchestrator/
   ```

2. Verify directory structure matches conventions:
   - `manifest.json` at root
   - `settings.json` at root
   - `agents/` directory with specialist .md files
   - `.claude/` directory with rules
   - `templates/` directory with .template files

3. Verify no user-specific paths leaked through (grep for absolute paths)

## Acceptance Criteria

- [x] Template directory exists at `installer/core/templates/langchain-deepagents-orchestrator/`
- [x] All 44 files copied successfully
- [x] No absolute paths in any file (grep -r "/Users/" returns nothing)
- [x] Directory structure matches existing langchain-deepagents template conventions
