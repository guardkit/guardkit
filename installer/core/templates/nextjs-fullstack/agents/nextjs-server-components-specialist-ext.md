# nextjs-server-components-specialist - Extended Reference

This file contains detailed documentation for the `nextjs-server-components-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/nextjs-server-components-specialist-ext.md
```


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


## Related Templates

This specialist works with these Next.js App Router templates:

### Primary Templates

1. **`templates/app/page-server-component.tsx.template`** - Server Component page pattern with async data fetching, dynamic rendering, and Prisma integration

2. **`templates/components/EntityList.tsx.template`** - Client Component for interactive lists with state management and Server Action integration

3. **`templates/components/EntityForm.tsx.template`** - Client Component for form handling with validation and submission

4. **`templates/actions/entity-actions.ts.template`** - Server Actions for CRUD operations with revalidation

### Supporting Templates

5. **`templates/lib/db.ts.template`** - Prisma singleton pattern for Server Components

6. **`templates/api/entity-route.ts.template`** - API Route Handlers (alternative to Server Actions)

---


## Template Code Examples

### Example 1: Server Component with Async Data Fetching

✅ **DO: Use Server Components for data fetching**

```typescript
// app/products/page.tsx - Server Component
import { db } from '@/lib/db'
import { ProductList } from '@/components/ProductList'

export default async function ProductsPage() {
  // Direct database access in Server Component
  const products = await db.product.findMany({
    orderBy: { createdAt: 'desc' },
    take: 50
  })

  return (
    <div>
      <h1>Products</h1>
      <ProductList products={products} />
    </div>
  )
}

// Force dynamic rendering (no static cache)
export const dynamic = 'force-dynamic'
```

❌ **DON'T: Fetch data in Client Components**

```typescript
// ❌ ANTI-PATTERN: Client Component fetching data
'use client'
import { useEffect, useState } from 'react'

export default function ProductsPage() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    fetch('/api/products')
      .then(res => res.json())
      .then(setProducts)
  }, [])

  return <div>{/* ... */}</div>
}
```

**Why**: Server Components eliminate client-side waterfalls, reduce bundle size, and enable direct database access.

---

### Example 2: Client Component Boundary with Server Actions

✅ **DO: Mark Client Components explicitly and use Server Actions**

```typescript
// components/ProductList.tsx - Client Component
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { deleteProduct } from '@/actions/product-actions'

interface ProductListProps {
  products: Array<{ id: string; name: string }>
}

export function ProductList({ products }: ProductListProps) {
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const router = useRouter()

  async function handleDelete(id: string) {
    setIsDeleting(id)
    try {
      await deleteProduct(id)
      router.refresh() // Revalidate Server Component data
    } catch (error) {
      console.error('Delete failed:', error)
    } finally {
      setIsDeleting(null)
    }
  }

  return (
    <ul>
      {products.map(product => (
        <li key={product.id}>
          {product.name}
          <button
            onClick={() => handleDelete(product.id)}
            disabled={isDeleting === product.id}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
```

❌ **DON'T: Mix server and client code in same component**

```typescript
// ❌ ANTI-PATTERN: Mixing concerns
'use client'
import { db } from '@/lib/db' // ❌ Server-only module in Client Component

export function ProductList() {
  // ❌ Can't use async in Client Component root
  const products = await db.product.findMany()
  return <div>{/* ... */}</div>
}
```

**Why**: Clear boundaries prevent "server-only" module errors and enable optimal code splitting.

---

### Example 3: Prisma Singleton Pattern for Development

✅ **DO: Use singleton pattern to prevent connection pool exhaustion**

```typescript
// lib/db.ts - Prisma singleton
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db = globalForPrisma.prisma ?? new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
})

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = db
}
```

❌ **DON'T: Create new PrismaClient instances per file**

```typescript
// ❌ ANTI-PATTERN: Multiple instances
import { PrismaClient } from '@prisma/client'

// New instance every time this file is imported
export const db = new PrismaClient()
```

**Why**: Next.js hot module reload creates multiple Prisma instances in development, exhausting database connections.

---

### Example 4: Streaming with Suspense Boundaries

✅ **DO: Stream expensive content with Suspense**

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'
import { RecentOrders } from '@/components/RecentOrders'
import { Analytics } from '@/components/Analytics'

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>

      {/* Fast content renders immediately */}
      <Suspense fallback={<div>Loading orders...</div>}>
        <RecentOrders />
      </Suspense>

      {/* Slow content streams in later */}
      <Suspense fallback={<div>Loading analytics...</div>}>
        <Analytics />
      </Suspense>
    </div>
  )
}

// components/Analytics.tsx - Expensive async component
export async function Analytics() {
  const data = await fetchExpensiveAnalytics() // 2-3 seconds
  return <div>{/* charts */}</div>
}
```

❌ **DON'T: Block entire page on slow queries**

```typescript
// ❌ ANTI-PATTERN: Sequential blocking
export default async function DashboardPage() {
  const orders = await db.order.findMany() // 200ms
  const analytics = await fetchExpensiveAnalytics() // 3 seconds

  // User waits 3.2 seconds for anything to render
  return <div>{/* ... */}</div>
}
```

**Why**: Suspense enables progressive rendering and perceived performance improvements.

---


## Template Best Practices

### Server Component Patterns

1. **Always mark Client Components with `'use client'` directive**
   - Place at the very first line of the file
   - Server Components are the default (no directive needed)
   - Use Client Components only when you need interactivity (useState, useEffect, event handlers)

2. **Fetch data directly in Server Components**
   ```typescript
   // ✅ Direct database access
   const data = await db.entity.findMany()
   ```
   - No API route needed for your own data
   - Automatic request deduplication in Next.js 14+
   - Better type safety with Prisma

3. **Use dynamic rendering for real-time data**
   ```typescript
   export const dynamic = 'force-dynamic'
   ```
   - Add to page.tsx for always-fresh data
   - Prevents static generation during build

4. **Pass serializable props to Client Components**
   - Only plain objects, arrays, primitives
   - No functions, class instances, or Date objects
   - Convert dates to ISO strings: `date.toISOString()`

### Server Action Patterns

5. **Use Server Actions for mutations**
   ```typescript
   'use server'

   export async function createProduct(formData: FormData) {
     const name = formData.get('name')
     await db.product.create({ data: { name } })
     revalidatePath('/products')
   }
   ```
   - Mark files or functions with `'use server'`
   - Call from Client Components
   - Use `revalidatePath()` to refresh Server Component data

6. **Handle errors gracefully in Server Actions**
   - Wrap database operations in try/catch
   - Return error objects instead of throwing
   - Use `redirect()` after successful mutations

### Database Connection Patterns

7. **Always use Prisma singleton pattern**
   - Prevents connection pool exhaustion in development
   - See `templates/lib/db.ts.template` for reference
   - Import as `import { db } from '@/lib/db'`

8. **Configure Prisma logging based on environment**
   ```typescript
   log: process.env.NODE_ENV === 'development'
     ? ['query', 'error', 'warn']
     : ['error']
   ```

### Performance Patterns

9. **Minimize Client Component scope**
   - Keep `'use client'` boundary as low as possible in component tree
   - Prefer passing Server Components as children to Client Components
   ```typescript
   <ClientWrapper>
     <ServerComponent /> {/* Rendered on server */}
   </ClientWrapper>
   ```

10. **Use Suspense for parallel data fetching**
    - Wrap independent async components in separate Suspense boundaries
    - Enables streaming and progressive rendering
    - Improves Time to First Byte (TTFB)

---


## Template Anti-Patterns

### Server/Client Boundary Violations

❌ **Importing server-only modules in Client Components**
```typescript
'use client'
import { db } from '@/lib/db' // ❌ ERROR: PrismaClient can't run in browser
```
**Fix**: Keep database access in Server Components or Server Actions.

❌ **Using async/await in Client Component root**
```typescript
'use client'
export default async function ClientPage() { // ❌ Not allowed
  const data = await fetch('/api/data')
}
```
**Fix**: Use useEffect with state, or move to Server Component.

❌ **Passing non-serializable props**
```typescript
// Server Component
<ClientComponent
  onSubmit={() => {}} // ❌ Functions not serializable
  date={new Date()}     // ❌ Date objects lose prototype
/>
```
**Fix**: Pass serializable data only, define handlers in Client Component.

### Data Fetching Anti-Patterns

❌ **Creating API routes for your own data fetching**
```typescript
// app/api/products/route.ts - ❌ UNNECESSARY
export async function GET() {
  const products = await db.product.findMany()
  return Response.json(products)
}

// app/products/page.tsx - ❌ WASTEFUL
export default async function Page() {
  const res = await fetch('http://localhost:3000/api/products')
  const products = await res.json()
}
```
**Fix**: Fetch directly in Server Component:
```typescript
export default async function Page() {
  const products = await db.product.findMany()
}
```

❌ **Forgetting to revalidate after mutations**
```typescript
'use server'
export async function deleteProduct(id: string) {
  await db.product.delete({ where: { id } })
  // ❌ Page still shows stale data
}
```
**Fix**: Add revalidation:
```typescript
import { revalidatePath } from 'next/cache'

export async function deleteProduct(id: string) {
  await db.product.delete({ where: { id } })
  revalidatePath('/products') // ✅ Refresh Server Component
}
```

### Database Connection Anti-Patterns

❌ **Creating new PrismaClient per file**
```typescript
// ❌ Multiple instances exhaust connections
import { PrismaClient } from '@prisma/client'
export const db = new PrismaClient()
```
**Fix**: Use singleton pattern from `templates/lib/db.ts.template`.

❌ **Not closing Prisma connections in serverless**
```typescript
// api/route.ts
export async function GET() {
  const db = new PrismaClient()
  const data = await db.entity.findMany()
  // ❌ Connection leaked
  return Response.json(data)
}
```
**Fix**: Import singleton, or call `db.$disconnect()` in finally block.

### Rendering Strategy Anti-Patterns

❌ **Using `'use client'` everywhere "just to be safe"**
```typescript
'use client' // ❌ Unnecessarily large bundle

export function StaticHeader() {
  return <header>My App</header> // No interactivity needed
}
```
**Fix**: Remove `'use client'` unless component needs state/effects/event handlers.

❌ **Not using Suspense for slow queries**
```typescript
export default async function Page() {
  const fast = await db.entity.findMany() // 100ms
  const slow = await expensiveQuery()      // 5 seconds
  // ❌ User waits 5.1 seconds for blank screen
}
```
**Fix**: Split into separate components with Suspense boundaries.

❌ **Forgetting `export const dynamic = 'force-dynamic'`**
```typescript
export default async function DashboardPage() {
  const latestOrders = await db.order.findMany({
    orderBy: { createdAt: 'desc' },
    take: 10
  })
  // ❌ Page statically generated at build time, shows stale data
}
```
**Fix**: Add `export const dynamic = 'force-dynamic'` for real-time data.


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-server-components-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-server-components-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-server-components-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-server-components-specialist-ext.md for detailed examples.
```
