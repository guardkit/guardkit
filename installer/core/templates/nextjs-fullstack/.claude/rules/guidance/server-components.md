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

## Quick Start

```typescript
// Server Component with async data fetching
export default async function UsersPage() {
  const users = await db.user.findMany({
    include: { posts: { take: 5 } }
  })

  return <UserList users={users} />
}

export const dynamic = 'force-dynamic'
```

## Extended Documentation

For comprehensive patterns, see:
- `installer/core/templates/nextjs-fullstack/agents/nextjs-server-components-specialist.md`
- `installer/core/templates/nextjs-fullstack/agents/nextjs-server-components-specialist-ext.md`
