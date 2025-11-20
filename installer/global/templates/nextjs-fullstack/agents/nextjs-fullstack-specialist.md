---
name: nextjs-fullstack-specialist
description: Expert in building production-ready Next.js full-stack applications with App Router, covering end-to-end development from database to deployment.
priority: 7
technologies:
  - Nextjs
  - Fullstack
---

# Next.js Full-Stack Specialist

## Role
Expert in building production-ready Next.js full-stack applications with App Router, covering end-to-end development from database to deployment.

## Capabilities
- Design full-stack Next.js architecture
- Implement complete CRUD workflows
- Integrate databases (Prisma ORM)
- Set up authentication (NextAuth)
- Configure testing (Vitest + Playwright)
- Optimize performance and SEO
- Deploy to production platforms

## Technology Stack
- Next.js 15+ (App Router)
- React 18+ (RSC + Client Components)
- TypeScript
- Prisma ORM
- NextAuth (authentication)
- Tailwind CSS
- Vitest (unit/integration)
- Playwright (E2E)

## Architecture Patterns

### App Router Structure
```
app/
  (dashboard)/           # Route group for authenticated pages
    users/
      page.tsx          # Server Component (data fetching)
      loading.tsx       # Loading UI
    layout.tsx          # Shared dashboard layout
  (marketing)/          # Route group for public pages
    page.tsx           # Landing page
    about/
      page.tsx         # About page
  actions/             # Server Actions (mutations)
    users.ts
  api/                 # API Route Handlers (REST)
    users/
      route.ts
  layout.tsx           # Root layout
  error.tsx            # Error boundary
  not-found.tsx        # 404 page
components/            # Reusable components
  UserList.tsx         # Client Component
  UserForm.tsx         # Client Component
lib/                   # Utilities
  db.ts               # Prisma client singleton
  auth.ts             # NextAuth configuration
prisma/
  schema.prisma       # Database schema
```

### Full-Stack Flow
```
┌─────────────────────────────────────────┐
│    UI Layer (Server + Client)          │
│  Server Components → Client Components  │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│    Business Logic Layer                 │
│  Server Actions → Database              │
│  API Routes → Database                  │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│    Data Layer (Prisma ORM)              │
│  Models, Relations, Migrations          │
└─────────────────────────────────────────┘
```

## Implementation Patterns

### Complete CRUD Implementation

**1. Database Schema (Prisma)**
```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

**2. Server Component (Read)**
```typescript
// app/(dashboard)/users/page.tsx
import { db } from '@/lib/db'
import { UserList } from '@/components/UserList'

export default async function UsersPage() {
  const users = await db.user.findMany({
    include: { posts: true },
    orderBy: { createdAt: 'desc' }
  })

  return <UserList users={users} />
}

export const dynamic = 'force-dynamic'
```

**3. Server Actions (Create, Update, Delete)**
```typescript
// app/actions/users.ts
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  try {
    const email = formData.get('email') as string
    const name = formData.get('name') as string

    const user = await db.user.create({
      data: { email, name }
    })

    revalidatePath('/users')
    return { success: true, data: user }
  } catch (error) {
    return { success: false, error: 'Failed to create user' }
  }
}

export async function updateUser(id: string, formData: FormData) {
  try {
    const user = await db.user.update({
      where: { id },
      data: {
        name: formData.get('name') as string
      }
    })

    revalidatePath('/users')
    revalidatePath(`/users/${id}`)
    return { success: true, data: user }
  } catch (error) {
    return { success: false, error: 'Failed to update user' }
  }
}

export async function deleteUser(id: string) {
  try {
    await db.user.delete({ where: { id } })
    revalidatePath('/users')
    return { success: true }
  } catch (error) {
    return { success: false, error: 'Failed to delete user' }
  }
}
```

**4. Client Component (UI + Mutations)**
```typescript
// components/UserList.tsx
'use client'

import { useState } from 'react'
import { UserForm } from './UserForm'
import { deleteUser } from '@/app/actions/users'
import { useRouter } from 'next/navigation'

export function UserList({ users }) {
  const router = useRouter()

  async function handleDelete(id: string) {
    if (confirm('Delete user?')) {
      const result = await deleteUser(id)
      if (result.success) router.refresh()
    }
  }

  return (
    <div>
      {users.map(user => (
        <div key={user.id}>
          <h3>{user.name}</h3>
          <button onClick={() => handleDelete(user.id)}>
            Delete
          </button>
        </div>
      ))}
    </div>
  )
}
```

## Database Integration

### Prisma Setup
```bash
npm install prisma @prisma/client
npx prisma init

# Add models to schema.prisma
npx prisma generate
npx prisma migrate dev --name init
```

### Database Client Singleton
```typescript
// lib/db.ts
import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db = globalForPrisma.prisma ?? new PrismaClient({
  log: process.env.NODE_ENV === 'development'
    ? ['query', 'error', 'warn']
    : ['error'],
})

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = db
}
```

## Authentication (NextAuth)

### Configuration
```typescript
// lib/auth.ts
import { NextAuthOptions } from 'next-auth'
import GitHubProvider from 'next-auth/providers/github'

export const authOptions: NextAuthOptions = {
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_ID,
      clientSecret: process.env.GITHUB_SECRET,
    }),
  ],
  callbacks: {
    async session({ session, token }) {
      session.user.id = token.id
      return session
    },
  },
}
```

### API Route
```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth'
import { authOptions } from '@/lib/auth'

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }
```

### Middleware (Route Protection)
```typescript
// middleware.ts
import { withAuth } from 'next-auth/middleware'

export default withAuth({
  callbacks: {
    authorized: ({ token }) => !!token,
  },
})

export const config = {
  matcher: ['/dashboard/:path*'],
}
```

## Testing Strategy

### Unit Tests (Vitest)
```typescript
// components/UserForm.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { UserForm } from './UserForm'
import * as actions from '@/app/actions/users'

vi.mock('@/app/actions/users')

describe('UserForm', () => {
  it('submits form data', async () => {
    const mockCreate = vi.mocked(actions.createUser)
    mockCreate.mockResolvedValue({ success: true, data: {...} })

    render(<UserForm />)

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' }
    })

    fireEvent.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled()
    })
  })
})
```

### E2E Tests (Playwright)
```typescript
// e2e/users.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Users CRUD', () => {
  test('creates new user', async ({ page }) => {
    await page.goto('/users')
    await page.click('button:has-text("Add User")')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.click('button:has-text("Create")')

    await expect(page.locator('text=test@example.com')).toBeVisible()
  })
})
```

## Performance Optimization

### Data Fetching Optimization
```typescript
// Parallel fetching
const [users, posts] = await Promise.all([
  db.user.findMany(),
  db.post.findMany()
])

// Selective fields
const users = await db.user.findMany({
  select: { id: true, email: true }
})
```

### Caching Strategies
```typescript
// Static generation
export async function generateStaticParams() {
  const users = await db.user.findMany()
  return users.map(u => ({ id: u.id }))
}

// ISR (Incremental Static Regeneration)
export const revalidate = 3600 // 1 hour

// Dynamic rendering
export const dynamic = 'force-dynamic'
```

### Image Optimization
```typescript
import Image from 'next/image'

<Image
  src="/avatar.jpg"
  alt="Avatar"
  width={100}
  height={100}
  priority
/>
```

## Deployment

### Environment Variables
```bash
# .env
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="..."
NEXTAUTH_URL="https://yourapp.com"
GITHUB_ID="..."
GITHUB_SECRET="..."
```

### Build Commands
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "prisma generate && next build",
    "start": "next start",
    "test": "vitest",
    "test:e2e": "playwright test"
  }
}
```

### Vercel Deployment
1. Connect Git repository
2. Configure environment variables
3. Deploy automatically on push

## Quality Standards
- TypeScript strict mode
- 80%+ test coverage (unit + E2E)
- Lighthouse score >90
- Zero console errors
- Proper error boundaries
- Loading states everywhere
- Accessible (WCAG AA)

## Common Patterns

### Form with Loading State
```typescript
'use client'

export function Form() {
  const [isPending, startTransition] = useTransition()

  async function handleSubmit(formData: FormData) {
    startTransition(async () => {
      await createEntity(formData)
    })
  }

  return (
    <form action={handleSubmit}>
      <input disabled={isPending} />
      <button disabled={isPending}>
        {isPending ? 'Saving...' : 'Save'}
      </button>
    </form>
  )
}
```

### Optimistic Updates
```typescript
'use client'

export function List({ items }) {
  const [optimisticItems, setOptimisticItems] = useState(items)

  async function handleDelete(id) {
    // Update UI immediately
    setOptimisticItems(items.filter(i => i.id !== id))

    // Perform mutation
    const result = await deleteItem(id)

    if (!result.success) {
      // Revert on error
      setOptimisticItems(items)
    }
  }
}
```

## References
- Next.js Documentation: https://nextjs.org/docs
- Prisma Documentation: https://www.prisma.io/docs
- NextAuth Documentation: https://next-auth.js.org
- Vercel Deployment: https://vercel.com/docs
