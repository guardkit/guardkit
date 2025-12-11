---
id: TASK-CRS-008
title: Refactor nextjs-fullstack Template to Rules Structure
status: completed
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T13:35:00Z
completed: 2025-12-11T13:35:00Z
priority: medium
tags: [template-refactor, nextjs-fullstack, rules-structure]
complexity: 5
parent_feature: claude-rules-structure
wave: 4
implementation_mode: task-work
conductor_workspace: melbourne
estimated_hours: 5-7
actual_hours: 1
dependencies:
  - TASK-CRS-002
  - TASK-CRS-003
---

# Task: Refactor nextjs-fullstack Template to Rules Structure

## Description

Refactor the `nextjs-fullstack` template (currently 19.4KB) to use the modular `.claude/rules/` structure.

## Current Structure

```
installer/core/templates/nextjs-fullstack/
├── CLAUDE.md                    (19.4 KB)
├── agents/
│   ├── nextjs-server-components-specialist.md
│   ├── nextjs-server-components-specialist-ext.md
│   ├── nextjs-server-actions-specialist.md
│   ├── nextjs-server-actions-specialist-ext.md
│   ├── nextjs-fullstack-specialist.md
│   ├── nextjs-fullstack-specialist-ext.md
│   ├── react-state-specialist.md
│   └── react-state-specialist-ext.md
└── templates/
```

## Target Structure

```
installer/core/templates/nextjs-fullstack/
├── .claude/
│   ├── CLAUDE.md                     (~5KB core)
│   └── rules/
│       ├── code-style.md             # paths: **/*.{ts,tsx}
│       ├── testing.md                # paths: **/*.test.*, **/e2e/**
│       ├── server/
│       │   ├── components.md         # paths: **/app/**/*.tsx, !**/components/**
│       │   ├── actions.md            # paths: **/actions/*.ts, **/actions/**/*.ts
│       │   └── streaming.md          # paths: **/loading.tsx, **/error.tsx
│       ├── api/
│       │   └── routes.md             # paths: **/api/**/route.ts
│       ├── database/
│       │   └── prisma.md             # paths: **/prisma/**, **/lib/db.ts
│       ├── auth/
│       │   └── nextauth.md           # paths: **/auth/**, **/api/auth/**
│       └── agents/
│           ├── server-components.md  # paths: **/app/**/*.tsx
│           ├── server-actions.md     # paths: **/actions/**
│           ├── fullstack.md          # (no paths - always load)
│           └── react-state.md        # paths: **/*use*.ts, **/hooks/**
├── agents/
└── templates/
```

## Content Breakdown

### rules/server/components.md

```markdown
---
paths: **/app/**/*.tsx, !**/components/**
---

# React Server Components

## Key Principles

Server Components execute on the server with zero client JavaScript.

## Data Fetching Pattern

```typescript
// Server Component - async function, direct DB access
export default async function UsersPage() {
  const users = await db.user.findMany({
    include: { posts: { take: 5 } }
  })

  return <UserList users={users} />
}

export const dynamic = 'force-dynamic'
```

## When to Use Server Components

- Data fetching from database
- Accessing backend resources
- Keeping sensitive info on server
- Reducing client bundle size
```

### rules/server/actions.md

```markdown
---
paths: **/actions/*.ts, **/actions/**/*.ts
---

# Server Actions

## Purpose

Type-safe mutations callable from client components.

## Pattern

```typescript
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  try {
    const email = formData.get('email') as string

    if (!email) {
      return { success: false, error: 'Email is required' }
    }

    const user = await db.user.create({
      data: { email }
    })

    revalidatePath('/users')
    return { success: true, data: user }
  } catch (_error) {
    return { success: false, error: 'Failed to create user' }
  }
}
```

## Best Practices

- Always use 'use server' directive
- Return typed responses (success/error)
- Call revalidatePath after mutations
- Handle errors gracefully
```

### rules/agents/server-components.md

```markdown
---
paths: **/app/**/*.tsx, **/app/**/page.tsx, **/app/**/layout.tsx
---

# Server Components Specialist

## Purpose

React Server Components and data fetching patterns for Next.js App Router.

## Technologies

Next.js 15, React Server Components, Prisma

## Boundaries

### ALWAYS
- Use async/await for data fetching
- Export dynamic and revalidate configs
- Handle loading and error states
- Use Suspense for streaming
- Keep server components in app/ directory

### NEVER
- Import 'use client' components at top level
- Use useState/useEffect in server components
- Expose sensitive data to client
- Skip error boundaries
- Mix server and client logic

### ASK
- Rendering strategy (SSG/SSR/ISR)
- Parallel vs sequential data fetching
- Caching and revalidation strategies
- Component boundary decisions
```

## Acceptance Criteria

- [x] Core CLAUDE.md reduced to ~5KB (5.7KB - 70% reduction from 19.4KB)
- [x] Server component patterns well-documented
- [x] Server actions patterns comprehensive
- [x] Prisma integration rules included
- [x] NextAuth rules included
- [x] Template structure verified

## Notes

- This is Wave 4 (parallel with other templates)
- Use `/task-work` for full quality gates
- Complex due to server/client boundaries

## Completion Summary

**Status**: ✅ Completed
**Date**: 2025-12-11
**Actual Time**: ~1 hour

### Implementation Details

Successfully refactored nextjs-fullstack template to use modular `.claude/rules/` structure:

1. **Core CLAUDE.md**: Reduced from 19.4KB to 5.7KB (70% reduction)
2. **Rules Structure Created**:
   - `rules/code-style.md` - TypeScript/Next.js conventions
   - `rules/testing.md` - Vitest and Playwright patterns
   - `rules/server/components.md` - Server Component patterns
   - `rules/server/actions.md` - Server Actions patterns
   - `rules/server/streaming.md` - Loading and streaming UI
   - `rules/api/routes.md` - API route handlers
   - `rules/database/prisma.md` - Prisma ORM integration
   - `rules/auth/nextauth.md` - NextAuth configuration
   - `rules/agents/server-components.md` - Agent guidance
   - `rules/agents/server-actions.md` - Agent guidance
   - `rules/agents/fullstack.md` - Agent guidance
   - `rules/agents/react-state.md` - Agent guidance

### Files Created

- 13 new rules files with path-specific frontmatter
- All rules include practical code examples
- Agent rules reference extended documentation in `agents/` directory

### Benefits

- **70% size reduction** in core CLAUDE.md
- **Path-specific loading** - Only load relevant rules
- **Better organization** - Clear separation by concern
- **Easier maintenance** - Update rules independently
- **Faster context loading** - Smaller memory footprint

### Template Structure

```
installer/core/templates/nextjs-fullstack/
├── .claude/
│   ├── CLAUDE.md                     (5.7KB - core guide)
│   └── rules/
│       ├── code-style.md
│       ├── testing.md
│       ├── server/
│       │   ├── components.md
│       │   ├── actions.md
│       │   └── streaming.md
│       ├── api/
│       │   └── routes.md
│       ├── database/
│       │   └── prisma.md
│       ├── auth/
│       │   └── nextauth.md
│       └── agents/
│           ├── server-components.md
│           ├── server-actions.md
│           ├── fullstack.md
│           └── react-state.md
├── agents/                           (existing agent files preserved)
├── templates/                        (template files)
└── CLAUDE.md.old                     (original 19.4KB file)
```

### Next Steps

Ready for testing with `guardkit init nextjs-fullstack`.
