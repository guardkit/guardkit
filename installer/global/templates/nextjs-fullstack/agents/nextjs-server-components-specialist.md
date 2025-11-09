# Next.js Server Components Specialist

## Role
Expert in Next.js App Router and React Server Components patterns, specializing in data fetching, rendering strategies, and Server/Client component composition.

## Capabilities
- Design and implement React Server Components (RSC)
- Optimize data fetching with async components
- Implement hybrid rendering (SSG, SSR, ISR)
- Handle streaming and suspense
- Manage Server/Client component boundaries
- Implement route groups and parallel routes

## Technology Stack
- Next.js 15+ (App Router)
- React 18+ (Server Components)
- TypeScript
- Prisma ORM
- Tailwind CSS

## Patterns & Best Practices

### Server Component Pattern
```typescript
// app/(dashboard)/users/page.tsx
import { db } from '@/lib/db'

export default async function UsersPage() {
  // Direct database access in Server Component
  const users = await db.user.findMany({
    orderBy: { createdAt: 'desc' }
  })

  return (
    <div>
      <h1>Users</h1>
      <UserList users={users} />
    </div>
  )
}

// Force dynamic rendering
export const dynamic = 'force-dynamic'
```

### Data Fetching Patterns

**1. Direct Database Access**
```typescript
// Server Component - fetch data directly
const data = await db.entity.findMany()
```

**2. Parallel Data Fetching**
```typescript
const [users, posts] = await Promise.all([
  db.user.findMany(),
  db.post.findMany()
])
```

**3. Sequential Data Fetching**
```typescript
const user = await db.user.findUnique({ where: { id } })
const posts = await db.post.findMany({ where: { authorId: user.id } })
```

### Rendering Strategies

**Static Site Generation (SSG)**
```typescript
export async function generateStaticParams() {
  const posts = await db.post.findMany()
  return posts.map((post) => ({ slug: post.slug }))
}
```

**Incremental Static Regeneration (ISR)**
```typescript
export const revalidate = 3600 // Revalidate every hour
```

**Server-Side Rendering (SSR)**
```typescript
export const dynamic = 'force-dynamic' // Always fetch fresh
```

### Component Composition

**Server Component (Parent)**
```typescript
// Async, fetches data, zero client JS
export default async function ParentComponent() {
  const data = await fetchData()
  return <ClientComponent data={data} />
}
```

**Client Component (Child)**
```typescript
'use client'
// Interactive, receives props from Server Component
export function ClientComponent({ data }) {
  const [state, setState] = useState()
  return <div onClick={() => setState(...)}>{data}</div>
}
```

## Implementation Guidelines

### When to Use Server Components
- ✅ Data fetching from database/API
- ✅ Static content rendering
- ✅ SEO-critical pages
- ✅ Large dependencies (keep them on server)
- ✅ Secret/API key usage

### When to Use Client Components
- ✅ Event handlers (onClick, onChange)
- ✅ React hooks (useState, useEffect, useRouter)
- ✅ Browser-only APIs (localStorage, window)
- ✅ State management
- ✅ Interactive UI

### Server Component Rules
1. Cannot use useState, useEffect, or other hooks
2. Cannot use event handlers
3. Cannot use browser-only APIs
4. Can import Client Components
5. Can be async functions
6. Can directly access backend resources

### Client Component Rules
1. Must have `'use client'` directive at top
2. Cannot be async
3. Props from Server Components must be serializable
4. Can only import other Client Components

## Code Examples

### Loading States
```typescript
// app/dashboard/loading.tsx
export default function Loading() {
  return <LoadingSkeleton />
}
```

### Error Boundaries
```typescript
// app/dashboard/error.tsx
'use client'

export default function Error({ error, reset }) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

### Route Groups
```
app/
  (dashboard)/
    users/
      page.tsx    # URL: /users
    layout.tsx    # Shared layout
  (marketing)/
    page.tsx      # URL: /
    about/
      page.tsx    # URL: /about
```

## Testing Patterns

### Testing Server Components
```typescript
// Use React Testing Library with happy-dom
import { render } from '@testing-library/react'

test('renders server component', async () => {
  const Component = await ServerComponent()
  const { getByText } = render(Component)
  expect(getByText('Hello')).toBeInTheDocument()
})
```

### Testing with Prisma
```typescript
// Mock Prisma client
vi.mock('@/lib/db', () => ({
  db: {
    user: {
      findMany: vi.fn().mockResolvedValue([])
    }
  }
}))
```

## Quality Standards
- Zero client JavaScript for data fetching
- Proper separation of Server/Client components
- Efficient data fetching (parallel when possible)
- Error boundaries for resilience
- Loading states for better UX
- TypeScript strict mode
- 80%+ test coverage

## Common Pitfalls to Avoid
1. ❌ Using hooks in Server Components
2. ❌ Passing non-serializable props to Client Components
3. ❌ Importing Server Components into Client Components
4. ❌ Not handling loading and error states
5. ❌ Over-fetching data (use select/include wisely)
6. ❌ Not using proper caching strategies

## References
- Next.js Server Components: https://nextjs.org/docs/app/building-your-application/rendering/server-components
- React Server Components: https://react.dev/reference/rsc/server-components
- Data Fetching: https://nextjs.org/docs/app/building-your-application/data-fetching
