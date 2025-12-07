---
id: TASK-EXT-C7C1
title: Create extended files for pwa-vite-specialist and openai-function-calling-specialist
status: backlog
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T11:45:00Z
priority: medium
tags: [progressive-disclosure, agent-enhance, consistency]
complexity: 3
related_tasks: [TASK-REV-7C49]
---

# Task: Create Extended Files for PWA and OpenAI Agents

## Description

Split `pwa-vite-specialist.md` and `openai-function-calling-specialist.md` into core + extended files to maintain consistency with other agents in the `javascript-standard-structure-template`.

**Source**: Review finding from TASK-REV-7C49

## Current State

Both agents currently have all content in a single file:
- `agents/pwa-vite-specialist.md` (~518 lines, comprehensive)
- `agents/openai-function-calling-specialist.md` (~736 lines, comprehensive)

## Target State

Each agent should have:
1. **Core file** (`{name}.md`): ~200-250 lines
   - Frontmatter with discovery metadata
   - Quick Start (5-10 examples)
   - Boundaries (ALWAYS/NEVER/ASK)
   - Capabilities summary
   - Loading instructions for extended content

2. **Extended file** (`{name}-ext.md`): ~400-600 lines
   - Detailed code examples (30+)
   - Best practices with explanations
   - Anti-patterns with code samples
   - Troubleshooting scenarios

## Acceptance Criteria

- [ ] `pwa-vite-specialist-ext.md` created with detailed content
- [ ] `pwa-vite-specialist.md` trimmed to core content only
- [ ] `openai-function-calling-specialist-ext.md` created with detailed content
- [ ] `openai-function-calling-specialist.md` trimmed to core content only
- [ ] Both core files include loading instructions: `cat agents/{name}-ext.md`
- [ ] Token reduction achieved (~55-70% for core files)

## Implementation Notes

Location: `~/.agentecflow/templates/javascript-standard-structure-template/agents/`

Use existing agents as reference:
- `external-api-integration-specialist.md` + `-ext.md`
- `firebase-firestore-specialist.md` + `-ext.md`

## Estimated Effort

Simple (1-3 complexity) - Content reorganization, no new content generation needed.
