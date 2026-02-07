# nextjs-fullstack-specialist - Extended Reference

This file contains detailed documentation for the `nextjs-fullstack-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/nextjs-fullstack-specialist-ext.md
```


## Technology Stack
- Next.js 15+ (App Router)
- React 18+ (RSC + Client Components)
- TypeScript
- Prisma ORM
- NextAuth (authentication)
- Tailwind CSS
- Vitest (unit/integration)
- Playwright (E2E)


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

**Server Action Pattern**: See [nextjs-server-actions-specialist-ext.md](nextjs-server-actions-specialist-ext.md) for complete CRUD examples (`createUser`, `updateUser`, `deleteUser`) with validation, error handling, and revalidation patterns.

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


## Related Templates

### Core Application Templates

1. **`templates/app/page-server-component.tsx.template`**
   - Server Component page with data fetching and streaming
   - Use for: Any page that needs to fetch data on the server
   - Best for: SEO-critical pages, initial page loads, database queries

2. **`templates/actions/entity-actions.ts.template`**
   - Server Actions for CRUD operations with validation
   - Use for: Form submissions, mutations, revalidation triggers
   - Best for: Non-GET operations that modify server state

3. **`templates/api/entity-route.ts.template`**
   - API Route Handlers for RESTful endpoints
   - Use for: External API integrations, webhooks, non-form mutations
   - Best for: Third-party service callbacks, complex data transformations

### Component Templates

4. **`templates/components/EntityForm.tsx.template`**
   - Client Component form with useTransition and error handling
   - Use for: Interactive forms that call Server Actions
   - Best for: Create/update forms with optimistic updates

5. **`templates/components/EntityList.tsx.template`**
   - Client Component list with interactivity
   - Use for: Displaying collections with client-side interactions
   - Best for: Lists with filtering, sorting, or real-time updates

### Database & Infrastructure

6. **`templates/prisma/schema.prisma.template`**
   - Prisma schema with best practice configurations
   - Use for: Defining database models and relationships
   - Best for: Starting new database schemas or adding models

7. **`templates/lib/db.ts.template`**
   - Prisma client singleton pattern for development
   - Use for: Database client initialization
   - Best for: Preventing connection exhaustion in dev mode

### Testing Templates

8. **`templates/tests/ComponentTest.test.tsx.template`**
   - Vitest unit test for React components
   - Use for: Testing component logic, rendering, user interactions
   - Best for: Client Components with complex state or user flows

9. **`templates/tests/e2e.spec.ts.template`**
   - Playwright E2E test with full user flows
   - Use for: Testing complete user journeys across pages
   - Best for: Critical paths like checkout, onboarding, auth flows

### DevOps Templates

10. **`templates/workflows-ci.yml.template`**
    - GitHub Actions CI/CD pipeline
    - Use for: Automated testing, building, and deployment
    - Best for: Setting up continuous integration for Next.js apps

---


## Template-Driven Code Examples

### Example 1: Server Component Page with Data Fetching

**From:** `templates/app/page-server-component.tsx.template`

```typescript
import { Suspense } from 'react';
import { db } from '@/lib/db';
import { EntityList } from '@/components/EntityList';
import { EntityListSkeleton } from '@/components/EntityListSkeleton';

// Server Component - runs on server only
export default async function EntitiesPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Entities</h1>

      <Suspense fallback={<EntityListSkeleton />}>
        <EntityListServer />
      </Suspense>
    </div>
  );
}

// Separate async component for data fetching
async function EntityListServer() {
  // Direct database query - no API route needed
  const entities = await db.entity.findMany({
    orderBy: { createdAt: 'desc' },
    take: 50,
  });

  return <EntityList entities={entities} />;
}

// Enable static generation with revalidation
export const revalidate = 60; // Revalidate every 60 seconds
```

**When to use:** Pages that fetch data on initial load. Server Components automatically handle loading states with Suspense and enable streaming for better UX.

---

### Example 2: Server Actions for CRUD Operations

**From:** `templates/actions/entity-actions.ts.template`

```typescript
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { db } from '@/lib/db';

// Input validation schema
const EntitySchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  description: z.string().optional(),
  status: z.enum(['active', 'inactive']),
});

export async function createEntity(formData: FormData) {
  // Validate input
  const validated = EntitySchema.safeParse({
    name: formData.get('name'),
    description: formData.get('description'),
    status: formData.get('status'),
  });

  if (!validated.success) {
    return {
      error: 'Invalid input',
      details: validated.error.flatten().fieldErrors,
    };
  }

  try {
    // Create in database
    const entity = await db.entity.create({
      data: validated.data,
    });

    // Revalidate the entities list page
    revalidatePath('/entities');

    // Redirect to new entity page
    redirect(`/entities/${entity.id}`);
  } catch (error) {
    console.error('Failed to create entity:', error);
    return { error: 'Failed to create entity' };
  }
}

export async function updateEntity(id: string, formData: FormData) {
  const validated = EntitySchema.safeParse({
    name: formData.get('name'),
    description: formData.get('description'),
    status: formData.get('status'),
  });

  if (!validated.success) {
    return { error: 'Invalid input', details: validated.error.flatten() };
  }

  try {
    await db.entity.update({
      where: { id },
      data: validated.data,
    });

    revalidatePath('/entities');
    revalidatePath(`/entities/${id}`);

    return { success: true };
  } catch (error) {
    return { error: 'Failed to update entity' };
  }
}

export async function deleteEntity(id: string) {
  try {
    await db.entity.delete({ where: { id } });
    revalidatePath('/entities');
    return { success: true };
  } catch (error) {
    return { error: 'Failed to delete entity' };
  }
}
```

**When to use:** All form submissions and mutations. Server Actions provide type-safe, progressive enhancement and automatic revalidation. Always include validation with Zod or similar.

---

### Example 3: Client Component Form with Optimistic Updates

**From:** `templates/components/EntityForm.tsx.template`

```typescript
'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { createEntity, updateEntity } from '@/actions/entity-actions';

interface EntityFormProps {
  entity?: {
    id: string;
    name: string;
    description: string | null;
    status: 'active' | 'inactive';
  };
}

export function EntityForm({ entity }: EntityFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(formData: FormData) {
    setError(null);

    startTransition(async () => {
      const result = entity
        ? await updateEntity(entity.id, formData)
        : await createEntity(formData);

      if (result?.error) {
        setError(result.error);
      } else {
        router.refresh(); // Refresh server data
      }
    });
  }

  return (
    <form action={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium">
          Name
        </label>
        <input
          id="name"
          name="name"
          type="text"
          defaultValue={entity?.name}
          required
          disabled={isPending}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          defaultValue={entity?.description ?? ''}
          disabled={isPending}
          className="mt-1 block w-full rounded-md border-gray-300"
        />
      </div>

      <div>
        <label htmlFor="status" className="block text-sm font-medium">
          Status
        </label>
        <select
          id="status"
          name="status"
          defaultValue={entity?.status ?? 'active'}
          disabled={isPending}
          className="mt-1 block w-full rounded-md border-gray-300"
        >
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {isPending ? 'Saving...' : entity ? 'Update' : 'Create'}
      </button>
    </form>
  );
}
```

**When to use:** Forms that need client-side interactivity, loading states, and error handling. Use `useTransition` to show pending state without additional state management. Mark component with `'use client'` directive.

---

### Example 4: API Route Handler for External Integrations

**From:** `templates/api/entity-route.ts.template`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { db } from '@/lib/db';

const EntityQuerySchema = z.object({
  status: z.enum(['active', 'inactive']).optional(),
  limit: z.coerce.number().min(1).max(100).default(20),
  offset: z.coerce.number().min(0).default(0),
});

// GET /api/entities
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const query = EntityQuerySchema.parse({
      status: searchParams.get('status'),
      limit: searchParams.get('limit'),
      offset: searchParams.get('offset'),
    });

    const entities = await db.entity.findMany({
      where: query.status ? { status: query.status } : undefined,
      take: query.limit,
      skip: query.offset,
      orderBy: { createdAt: 'desc' },
    });

    const total = await db.entity.count({
      where: query.status ? { status: query.status } : undefined,
    });

    return NextResponse.json({
      data: entities,
      pagination: {
        total,
        limit: query.limit,
        offset: query.offset,
      },
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid query parameters', details: error.errors },
        { status: 400 }
      );
    }

    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// POST /api/entities
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate with schema
    const validated = EntitySchema.parse(body);

    const entity = await db.entity.create({
      data: validated,
    });

    return NextResponse.json(entity, { status: 201 });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request body', details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to create entity' },
      { status: 500 }
    );
  }
}
```

**When to use:** External webhooks, third-party API integrations, or when you need fine-grained control over HTTP responses. For form submissions, prefer Server Actions instead.

---

### Example 5: E2E Test with Playwright

**From:** `templates/tests/e2e.spec.ts.template`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Entity Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to entities page
    await page.goto('/entities');
  });

  test('should create a new entity', async ({ page }) => {
    // Click "New Entity" button
    await page.click('text=New Entity');

    // Fill out form
    await page.fill('input[name="name"]', 'Test Entity');
    await page.fill('textarea[name="description"]', 'Test description');
    await page.selectOption('select[name="status"]', 'active');

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for redirect and verify success
    await page.waitForURL(/\/entities\/[a-z0-9-]+/);
    await expect(page.locator('h1')).toContainText('Test Entity');
  });

  test('should display validation errors', async ({ page }) => {
    await page.click('text=New Entity');

    // Submit empty form
    await page.click('button[type="submit"]');

    // Verify error message appears
    await expect(page.locator('text=Name is required')).toBeVisible();
  });

  test('should update an existing entity', async ({ page }) => {
    // Click first entity in list
    await page.click('[data-testid="entity-item"]:first-child');

    // Click edit button
    await page.click('text=Edit');

    // Update name
    await page.fill('input[name="name"]', 'Updated Entity Name');
    await page.click('button[type="submit"]');

    // Verify update
    await expect(page.locator('h1')).toContainText('Updated Entity Name');
  });

  test('should delete an entity', async ({ page }) => {
    const entityCount = await page.locator('[data-testid="entity-item"]').count();

    // Click first entity
    await page.click('[data-testid="entity-item"]:first-child');

    // Click delete and confirm
    await page.click('text=Delete');
    await page.click('text=Confirm'); // Confirmation dialog

    // Wait for redirect back to list
    await page.waitForURL('/entities');

    // Verify entity count decreased
    const newCount = await page.locator('[data-testid="entity-item"]').count();
    expect(newCount).toBe(entityCount - 1);
  });
});
```

**When to use:** Testing critical user flows end-to-end. Run with `npm run test:e2e`. E2E tests ensure Server Components, Server Actions, and Client Components work together correctly.

---


## Anti-Patterns to Avoid

1. **NEVER fetch data in Client Components**
   - DON'T: Call API routes or use `useEffect` + `fetch` in Client Components
   - DO: Fetch data in Server Components and pass as props
   - Why: Eliminates waterfalls, reduces bundle size, improves SEO

2. **NEVER create API routes for internal data fetching**
   - DON'T: Create `/api/entities` route just to fetch data for your own pages
   - DO: Query database directly in Server Components
   - Why: API routes add unnecessary latency and complexity for internal use

3. **NEVER skip input validation in Server Actions**
   - DON'T: Trust client-side validation alone
   - DO: Always validate with Zod schema in Server Actions
   - Why: Client-side validation can be bypassed; server validation is mandatory for security

4. **NEVER forget to revalidate after mutations**
   - DON'T: Mutate data without calling `revalidatePath()` or `revalidateTag()`
   - DO: Revalidate all affected paths after create/update/delete operations
   - Why: Stale cached data will be displayed until manual page refresh

5. **NEVER use `'use client'` at the root layout level**
   - DON'T: Add `'use client'` to `app/layout.tsx`
   - DO: Keep layouts as Server Components, push `'use client'` to leaf components
   - Why: Makes entire app client-side, negating Next.js benefits

6. **NEVER expose sensitive environment variables to the client**
   - DON'T: Prefix database URLs with `NEXT_PUBLIC_`
   - DO: Only expose variables needed in browser with `NEXT_PUBLIC_` prefix
   - Why: Client-exposed variables are visible in browser DevTools and source code

---


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-fullstack-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-fullstack-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-fullstack-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-fullstack-specialist-ext.md for detailed examples.
```
