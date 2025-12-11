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

## Server vs Client Components

### Server Component
```typescript
// app/(dashboard)/users/page.tsx
import { db } from '@/lib/db'

export default async function UsersPage() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}
```

### Client Component
```typescript
// components/UserList.tsx
'use client'

import { useState } from 'react'

export function UserList({ users }) {
  const [isCreating, setIsCreating] = useState(false)
  // Interactive UI...
}
```

## Rendering Configuration

```typescript
// Force dynamic rendering (always fetch fresh data)
export const dynamic = 'force-dynamic'
export const revalidate = 0

// Or use ISR with revalidation
export const revalidate = 60 // Revalidate every 60 seconds
```

## Suspense and Streaming

```typescript
// app/(dashboard)/users/page.tsx
import { Suspense } from 'react'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'

async function Users() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}

export default function UsersPage() {
  return (
    <div>
      <h1>Users</h1>
      <Suspense fallback={<LoadingSkeleton />}>
        <Users />
      </Suspense>
    </div>
  )
}
```

## Parallel Data Fetching

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'

async function Users() {
  const users = await db.user.findMany()
  return <UserStats users={users} />
}

async function Posts() {
  const posts = await db.post.findMany()
  return <PostStats posts={posts} />
}

export default function Dashboard() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <Suspense fallback={<div>Loading users...</div>}>
        <Users />
      </Suspense>
      <Suspense fallback={<div>Loading posts...</div>}>
        <Posts />
      </Suspense>
    </div>
  )
}
```
