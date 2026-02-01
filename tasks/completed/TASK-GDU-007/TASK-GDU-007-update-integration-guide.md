---
id: TASK-GDU-007
title: Update graphiti-integration-guide.md with Phase 2 features
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T10:55:00Z
completed: 2026-02-02T10:55:00Z
completed_location: tasks/completed/TASK-GDU-007/
priority: medium
tags: [documentation, graphiti]
complexity: 2
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 3
implementation_mode: direct
conductor_workspace: graphiti-docs-wave3-2
organized_files:
  - TASK-GDU-007-update-integration-guide.md
---

# Task: Update graphiti-integration-guide.md with Phase 2 Features

## Description

Update the main integration guide to reference Phase 2 features and link to the new detailed guides.

## Current State

`docs/guides/graphiti-integration-guide.md` currently covers:
- The problem Graphiti solves
- Quick start setup
- Core concepts (knowledge categories, context loading, ADR lifecycle)
- Command integration (/task-work, /feature-build, /template-create)
- Configuration
- FAQ
- Multi-project support

## Required Updates

### 1. Add "What's New in Phase 2" Section

After the Quick Start, add a section highlighting:
- Interactive Knowledge Capture
- Knowledge Query Commands
- Job-Specific Context Retrieval
- Turn State Tracking

### 2. Update "Core Concepts" Section

Add brief mentions of:
- Job-specific context (with link to detailed guide)
- Interactive capture (with link to detailed guide)
- Turn states for AutoBuild (with link to detailed guide)

### 3. Update Context Loading Section

Replace or update the "How Context Loading Works" diagram to show:
- Job-specific context retrieval
- Budget calculation
- Relevance filtering

### 4. Update Command Integration Section

Add mentions of:
- `/feature-plan` integration with feature spec detection
- Enhanced `/feature-build` with turn state tracking
- New query commands

### 5. Update FAQ Section

Add new FAQs:
- "How do I capture project knowledge interactively?"
- "How do I query stored knowledge?"
- "What is job-specific context?"

### 6. Update See Also Section

Add links to new guides:
- graphiti-knowledge-capture.md
- graphiti-query-commands.md
- graphiti-job-context.md
- graphiti-turn-states.md

## Acceptance Criteria

- [x] Phase 2 features mentioned and linked
- [x] Core concepts updated
- [x] FAQ section expanded
- [x] See Also section updated
- [x] No broken links
- [x] MkDocs builds successfully (verified files exist; MkDocs not installed in environment)

## Estimated Effort

1 hour
