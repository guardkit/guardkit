---
paths: **/loading.tsx, **/error.tsx
---

# Streaming & Loading UI

## Loading UI

Next.js automatically shows loading UI while Server Components fetch data.

```typescript
// app/(dashboard)/loading.tsx
export default function Loading() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
      <div className="h-64 bg-gray-200 rounded"></div>
    </div>
  )
}
```

## Error Boundaries

```typescript
// app/(dashboard)/error.tsx
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  )
}
```

## Suspense Boundaries

Suspense allows you to stream components independently:

```typescript
// app/(dashboard)/users/page.tsx
import { Suspense } from 'react'

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

## Parallel Streaming

Multiple Suspense boundaries stream in parallel:

```typescript
// app/dashboard/page.tsx
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

## Not Found Pages

```typescript
// app/not-found.tsx
export default function NotFound() {
  return (
    <div>
      <h2>Not Found</h2>
      <p>Could not find requested resource</p>
    </div>
  )
}
```
