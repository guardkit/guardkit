---
id: TASK-HAI-012-C5F8
title: Update nextjs-fullstack Template Agents with Discovery Metadata
status: completed
priority: medium
tags: [haiku-agents, metadata, template-agents, nextjs, fullstack]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
actual_hours: 1.0
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
completed: 2025-11-25T14:00:00Z
---

# Task: Update nextjs-fullstack Template Agents with Discovery Metadata

## ✅ COMPLETED

**Completion Date**: 2025-11-25
**Duration**: 1 hour
**Status**: All acceptance criteria met

## Completion Summary

Successfully added discovery metadata to all 3 nextjs-fullstack template agents. All agents now support AI-powered discovery for Phase 3 implementation in the Taskwright workflow.

### Deliverables

✅ **3 agents updated with discovery metadata**:
- `nextjs-fullstack-specialist.md`
- `nextjs-server-components-specialist.md`
- `nextjs-server-actions-specialist.md`

✅ **Validation Results**:
- YAML syntax: 3/3 agents passed
- Discovery matching: 3/3 agents found with stack=[nextjs]
- Discovery matching: 3/3 agents found with stack=[react] (inheritance)
- Keyword specialization: Each agent has 6 unique keywords

✅ **Quality Metrics**:
- Files modified: 3
- Lines added: 66
- Lines removed: 3
- All existing content preserved: ✅
- Zero defects introduced: ✅

### Files Modified

```
installer/global/templates/nextjs-fullstack/agents/nextjs-fullstack-specialist.md          (+23/-1)
installer/global/templates/nextjs-fullstack/agents/nextjs-server-actions-specialist.md     (+23/-1)
installer/global/templates/nextjs-fullstack/agents/nextjs-server-components-specialist.md  (+23/-1)
```

### Discovery Metadata Added

All agents now include:
- **Stack**: `[nextjs, react, typescript]`
- **Phase**: `implementation`
- **Model**: `haiku` with clear rationale
- **Capabilities**: 5 per agent
- **Keywords**: 7 per agent (distinct specializations)
- **Collaborates_with**: References to related agents

### Distinct Specializations

**nextjs-fullstack-specialist**:
- Keywords: `fullstack`, `route-handlers`, `layouts`, `routing`, `middleware`, `app-router`
- Focus: App Router architecture (routing, layouts, middleware)

**nextjs-server-components-specialist**:
- Keywords: `server-components`, `streaming`, `data-fetching`, `rsc`, `caching`, `suspense`
- Focus: RSC patterns (server-side data fetching, streaming, Suspense)

**nextjs-server-actions-specialist**:
- Keywords: `optimistic-updates`, `use-server`, `revalidation`, `mutations`, `server-actions`, `forms`
- Focus: Mutation patterns (forms, revalidation, optimistic updates)

---

## Context

Add discovery metadata to 3 agents in the nextjs-fullstack template. These agents specialize in Next.js App Router patterns (server components, server actions) which are distinct from general React patterns.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-010, HAI-011, HAI-013-014)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-H (Conductor workspace - parallel with other template updates)

## Objectives

1. ✅ Add discovery metadata to 3 nextjs-fullstack agents
2. ✅ Validate metadata against HAI-001 schema
3. ✅ Ensure distinct specializations for Next.js App Router patterns
4. ✅ Preserve all existing content

## Agents Updated

### 1. nextjs-fullstack-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-fullstack-specialist
description: Next.js App Router full-stack specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Next.js full-stack implementation follows App Router patterns (layouts, routing, middleware). Haiku provides fast, cost-effective implementation of Next.js conventions."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Next.js App Router structure
  - File-based routing patterns
  - Layout and template components
  - Middleware implementation
  - API route handlers (Route Handlers)
keywords: [nextjs, app-router, routing, layouts, middleware, fullstack, route-handlers]

collaborates_with:
  - nextjs-server-components-specialist
  - nextjs-server-actions-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js App Router architecture and routing patterns

### 2. nextjs-server-components-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-server-components-specialist
description: Next.js Server Components and data fetching specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Server Component implementation follows Next.js patterns (async components, fetch API, caching). Haiku provides fast, cost-effective implementation of RSC patterns."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Server Component patterns
  - Data fetching in Server Components
  - Streaming and Suspense
  - Cache configuration (fetch, unstable_cache)
  - Client vs Server Component boundaries
keywords: [nextjs, server-components, rsc, data-fetching, streaming, suspense, caching]

collaborates_with:
  - nextjs-fullstack-specialist
  - nextjs-server-actions-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js Server Components (RSC) and data fetching patterns

### 3. nextjs-server-actions-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-server-actions-specialist
description: Next.js Server Actions and mutations specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Server Actions implementation follows Next.js patterns ('use server', form actions, revalidation). Haiku provides fast, cost-effective implementation of mutation patterns."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Server Actions implementation ('use server')
  - Form handling with Server Actions
  - Optimistic updates with useOptimistic
  - Revalidation (revalidatePath, revalidateTag)
  - Error handling in Server Actions
keywords: [nextjs, server-actions, mutations, forms, revalidation, use-server, optimistic-updates]

collaborates_with:
  - nextjs-fullstack-specialist
  - nextjs-server-components-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js Server Actions for mutations and form handling

## Specialization Strategy

### Global vs Template Agents

**Global react-state-specialist**:
- General React state management
- Client-side patterns
- Hooks and Context API

**Template-specific specialists**:
- **nextjs-fullstack-specialist**: App Router architecture (routing, layouts, middleware)
- **nextjs-server-components-specialist**: RSC patterns (server-side data fetching, streaming)
- **nextjs-server-actions-specialist**: Mutation patterns (forms, revalidation)

**Discovery behavior**:
- Task keywords "server-component", "rsc", "streaming" → nextjs-server-components-specialist
- Task keywords "server-action", "mutation", "revalidation" → nextjs-server-actions-specialist
- Task keywords "routing", "layout", "middleware" → nextjs-fullstack-specialist
- Default Next.js task → nextjs-fullstack-specialist (most general)

## Acceptance Criteria

- [x] 3 agents updated with discovery metadata
- [x] Stack: [nextjs, react, typescript] for all
- [x] Phase: implementation for all
- [x] Capabilities: Minimum 5 per agent
- [x] Keywords: Minimum 5 per agent, distinct Next.js specializations
- [x] Model: haiku with clear rationale
- [x] All existing content preserved
- [x] YAML syntax valid
- [x] Discovery finds all 3 agents with stack=nextjs
- [x] Discovery finds all 3 agents with stack=react (inheritance)
- [x] Specializations distinct (routing vs RSC vs Server Actions)

## Validation Results

**YAML Syntax Validation**: ✅ All 3 agents passed
```
✅ nextjs-fullstack-specialist.md validated successfully
   Stack: ['nextjs', 'react', 'typescript']
   Phase: implementation
   Capabilities: 5 items
   Keywords: 7 items
   Model: haiku

✅ nextjs-server-components-specialist.md validated successfully
   Stack: ['nextjs', 'react', 'typescript']
   Phase: implementation
   Capabilities: 5 items
   Keywords: 7 items
   Model: haiku

✅ nextjs-server-actions-specialist.md validated successfully
   Stack: ['nextjs', 'react', 'typescript']
   Phase: implementation
   Capabilities: 5 items
   Keywords: 7 items
   Model: haiku
```

**Discovery Testing**: ✅ All tests passed
```
Test 1: Discover agents with stack=[nextjs]
Found 3 agents:
  - nextjs-server-components-specialist
  - nextjs-server-actions-specialist
  - nextjs-fullstack-specialist

Test 2: Discover agents with stack=[react]
Found 3 agents:
  - nextjs-server-components-specialist
  - nextjs-server-actions-specialist
  - nextjs-fullstack-specialist

Test 3: Keyword-based discovery
✅ server-components → nextjs-server-components-specialist
✅ server-actions → nextjs-server-actions-specialist
✅ routing → nextjs-fullstack-specialist
```

**Keyword Specialization**: ✅ Each agent has 6 unique keywords
```
nextjs-server-components-specialist unique:
  {server-components, streaming, data-fetching, rsc, caching, suspense}

nextjs-server-actions-specialist unique:
  {optimistic-updates, use-server, revalidation, mutations, server-actions, forms}

nextjs-fullstack-specialist unique:
  {fullstack, route-handlers, layouts, routing, middleware, app-router}
```

## Risk Assessment

**LOW Risk**:
- Simple metadata addition (3 files)
- Template agents, not global (lower impact)
- Validation script catches errors

**Mitigations**:
- ✅ Batch validation after all updates
- ✅ Git diff review
- ✅ Discovery test ensures matching works

## Reference Materials

- `installer/global/templates/nextjs-fullstack/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-003-45BB-create-react-state-specialist.md` - Global React agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema

## Success Metrics

- ✅ Validation: 3/3 agents pass (100%)
- ✅ Discovery: All 3 found with stack=[nextjs, react, typescript]
- ✅ Keyword targeting: Server Component tasks → nextjs-server-components-specialist
- ✅ Zero disruption: No content changes

## Lessons Learned

**What went well**:
- Simple metadata addition was straightforward
- Validation scripts caught any issues immediately
- Discovery testing confirmed proper agent matching
- Distinct keyword sets ensure proper specialization

**Challenges faced**:
- None - task was low complexity as expected

**Improvements for next time**:
- Consider automating metadata addition for similar template updates
- Create reusable validation script for all template agents

## Risk: LOW | Rollback: Revert files (<30 sec)
