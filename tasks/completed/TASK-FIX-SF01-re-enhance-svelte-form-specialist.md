---
id: TASK-FIX-SF01
title: Re-enhance svelte-form-specialist agent with AI strategy
status: backlog
task_type: implementation
created: 2025-12-09
priority: high
tags: [agent-enhance, progressive-disclosure, svelte, fix]
related_tasks: [TASK-REV-A36C]
estimated_complexity: 2
source_review: TASK-REV-A36C
---

# TASK-FIX-SF01: Re-enhance svelte-form-specialist Agent

## Summary

The `svelte-form-specialist` agent failed AI enhancement during the kartlog template enhancement process and fell back to static mode. This resulted in:
- Generic placeholder boundaries ("Execute core responsibilities as defined in Purpose section")
- Empty extended file (1.3KB - only template list, no code examples)
- Only 39.4% token reduction vs 73.6% average for other agents

## Root Cause

The AI enhancement likely failed silently or timed out, causing fallback to static enhancement which generates generic content.

## Acceptance Criteria

### AC1: Template-Specific Boundaries
- [ ] ALWAYS section contains 5-7 Svelte form-specific rules
- [ ] NEVER section contains 5-7 Svelte form-specific prohibitions
- [ ] ASK section contains 3-5 decision scenarios specific to form handling
- [ ] No generic phrases like "Execute core responsibilities"

### AC2: Extended File Content
- [ ] Code examples extracted from actual kartlog form templates
- [ ] Minimum 3 detailed code examples with DO/DON'T patterns
- [ ] References to actual template files (e.g., `EditSession.svelte.template`)

### AC3: Token Reduction Target
- [ ] Core file ≤4KB (currently 2.1KB - acceptable)
- [ ] Extended file ≥5KB with real content (currently 1.3KB)
- [ ] Token reduction ≥60% vs monolithic

## Implementation Steps

1. Navigate to kartlog template directory
2. Run AI-powered enhancement:
   ```bash
   /agent-enhance kartlog/svelte-form-specialist --strategy=ai
   ```
3. Verify boundaries are template-specific
4. Verify extended file has code examples
5. Compare against other successfully enhanced agents (e.g., firestore-repository-specialist)

## Files to Modify

- `docs/reviews/progressive-disclosure/kartlog/agents/svelte-form-specialist.md`
- `docs/reviews/progressive-disclosure/kartlog/agents/svelte-form-specialist-ext.md`

## Reference Examples

Compare against successfully enhanced agents:
- `firestore-repository-specialist` - 7/7/5 boundaries, 5 code examples
- `external-api-integration-specialist` - 7/7/5 boundaries, 3 code examples
- `svelte-list-view-specialist` - Complete discovery metadata

## Definition of Done

- [ ] Boundaries are template-specific (not generic)
- [ ] Extended file has ≥3 code examples
- [ ] Extended file size ≥5KB
- [ ] No placeholder text remains
