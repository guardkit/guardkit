---
id: TASK-GI-DOC-002
title: Write Graphiti Setup Guide
status: in_review
created: 2026-01-29 11:00:00+00:00
updated: 2026-01-29 11:00:00+00:00
priority: high
tags:
- documentation
- graphiti
- setup
- installation
complexity: 3
feature_id: FEAT-GI-DOC
parent_review: TASK-GI-DOC
implementation_mode: direct
wave: 1
parallel_group: wave1-2
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GI-DOC
  base_branch: main
  started_at: '2026-01-29T16:53:46.197109'
  last_updated: '2026-01-29T16:58:35.130114'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-29T16:53:46.197109'
    player_summary: "Created comprehensive Graphiti setup guide at docs/setup/graphiti-setup.md\
      \ with:\n\n1. Prerequisites section covering Docker Desktop, Python 3.10+, OpenAI\
      \ API key, and recommended hardware\n2. Five detailed installation steps:\n\
      \   - Step 1: Start Graphiti Services with docker compose\n   - Step 2: Configure\
      \ environment with OPENAI_API_KEY and optional overrides\n   - Step 3: Verify\
      \ connection using 'guardkit graphiti status'\n   - Step 4: Seed knowledge using\
      \ 'guardkit graphiti seed'\n   - Step 5: Verif"
    player_success: true
    coach_success: true
---

# Task: Write Graphiti Setup Guide

## Description

Create detailed installation and configuration documentation at `docs/setup/graphiti-setup.md`. This guide helps users set up Graphiti from scratch with comprehensive troubleshooting.

## Requirements

### Content Structure

1. **Prerequisites**
   - Docker Desktop (or Docker Engine + Compose)
   - Python 3.10+ with async support
   - OpenAI API Key for embeddings
   - Recommended: 4GB RAM, SSD storage

2. **Installation Steps**
   - Step 1: Start Graphiti Services (docker compose command)
   - Step 2: Configure Environment (OPENAI_API_KEY, optional overrides)
   - Step 3: Verify Connection (`guardkit graphiti status`)
   - Step 4: Seed Knowledge (`guardkit graphiti seed`)
   - Step 5: Verify Seeding (`guardkit graphiti verify --verbose`)

3. **Configuration File**
   - Full `.guardkit/graphiti.yaml` example with comments
   - Explanation of each setting
   - Environment variable override patterns

4. **Troubleshooting**
   - Connection Failed (docker ps, logs, restart)
   - Seeding Errors (--force flag, API key check)
   - No Context in Sessions (verification code)
   - Common error messages and solutions

5. **Docker Compose Reference**
   - Services started (FalkorDB, Graphiti API)
   - Port mappings
   - Volume persistence

### Source Materials

- `guardkit/cli/graphiti.py` - CLI implementation and help text
- `.guardkit/graphiti.yaml` - Default configuration
- `docker/docker-compose.graphiti.yml` - Docker setup (if exists)
- `guardkit/knowledge/config.py` - Configuration loading logic

### Style Guidelines

- Step-by-step numbered instructions
- Show expected output for verification commands
- Include troubleshooting for each potential failure point
- Keep to ~250 lines

## Acceptance Criteria

- [ ] File created at `docs/setup/graphiti-setup.md`
- [ ] All 5 installation steps documented
- [ ] Complete configuration file example
- [ ] Troubleshooting section covers common issues
- [ ] Docker commands are copy-paste ready
- [ ] Environment variable documentation complete
- [ ] Expected output shown for status/verify commands

## Implementation Notes

Verify commands against actual CLI implementation in `guardkit/cli/graphiti.py`.

**Note**: The setup guide is less affected by FEAT-GE enhancements since setup steps remain the same. However, if new CLI commands or configuration options were added, include them.

## Test Requirements

- [ ] Markdown lints without errors
- [ ] Docker commands are valid
- [ ] All links valid
