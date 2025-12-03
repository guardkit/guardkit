# CLAUDE.md - Next.js Full-Stack Template

## Template Overview

This is a **production-ready Next.js 15 full-stack template** featuring the App Router with React Server Components, Server Actions, Prisma ORM, and comprehensive testing infrastructure.

**Template Name**: `nextjs-fullstack`
**Display Name**: Next.js Full-Stack (App Router)
**Complexity**: 7/10 (High)
**Confidence Score**: 92/100

### Key Features

- ✅ **Next.js 15** - Latest App Router with React Server Components
- ✅ **TypeScript** - Strict mode for type safety
- ✅ **Prisma ORM** - Type-safe database access with migrations
- ✅ **NextAuth** - Authentication ready (GitHub, credentials)
- ✅ **Server Actions** - Type-safe mutations without API routes
- ✅ **Tailwind CSS** - Utility-first styling
- ✅ **Vitest** - Unit and integration testing
- ✅ **Playwright** - End-to-end testing
- ✅ **Progressive Enhancement** - Forms work without JavaScript

---

## Technology Stack

### Core Framework
- **Next.js**: 15.1.2 (App Router)
- **React**: 18.2.0 (Server Components + Client Components)
- **TypeScript**: 5.x (strict mode)

### Database & ORM
- **Prisma**: 6.19.0 (with Prisma Client)
- **Database**: SQLite (dev), PostgreSQL/MySQL (production)

### Authentication
- **NextAuth**: 4.24.11 (GitHub OAuth, Credentials)

### Styling
- **Tailwind CSS**: 4.x (utility-first CSS)
- **PostCSS**: 4.x (CSS processing)

### Testing
- **Vitest**: 4.0.8 (unit/integration, happy-dom environment)
- **Playwright**: 1.56.1 (E2E testing, Chromium)
- **Testing Library React**: 16.3.0 (component testing)

### Development Tools
- **ESLint**: 9 (linting with Next.js config)
- **TypeScript Compiler**: Type checking
- **Prisma Studio**: Database GUI

---

## Architecture

### Architectural Style
**App Router with React Server Components (RSC)**

This architecture leverages the latest Next.js paradigm with clear separation between server-side and client-side rendering:

```
┌─────────────────────────────────────────┐
│    Presentation Layer (UI)              │
│  - Server Components (data fetching)    │
│  - Client Components (interactivity)    │
│  - Route Groups (organization)          │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│    Application Layer (Business Logic)   │
│  - Server Actions (mutations)           │
│  - API Route Handlers (REST)            │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│    Data Access Layer                    │
│  - Prisma ORM (type-safe queries)      │
│  - Database Client Singleton            │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│    Data Layer                           │
│  - SQLite/PostgreSQL Database           │
│  - Schema Migrations                    │
└─────────────────────────────────────────┘
```

### Key Patterns

1. **React Server Components (RSC)** - Components that execute on the server with zero client JavaScript for data fetching
2. **Server Actions** - Type-safe mutations callable from client components
3. **API Route Handlers** - RESTful endpoints for external clients
4. **Database Singleton** - Prevents multiple Prisma instances during development
5. **Progressive Enhancement** - Forms work without JavaScript
6. **Cache Revalidation** - Automatic cache invalidation after mutations
7. **Route Groups** - Organize routes without affecting URLs

---

## Project Structure

```
nextjs-fullstack/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (dashboard)/          # Route group (authenticated pages)
│   │   │   ├── users/
│   │   │   │   ├── page.tsx     # Server Component (data fetching)
│   │   │   │   └── loading.tsx  # Loading UI
│   │   │   └── layout.tsx       # Dashboard layout
│   │   ├── actions/              # Server Actions (mutations)
│   │   │   └── users.ts         # CRUD operations
│   │   ├── api/                  # API Route Handlers
│   │   │   ├── auth/
│   │   │   │   └── [...nextauth]/
│   │   │   │       └── route.ts # NextAuth handler
│   │   │   └── users/
│   │   │       └── route.ts     # REST API
│   │   ├── layout.tsx            # Root layout
│   │   ├── error.tsx             # Error boundary
│   │   └── not-found.tsx         # 404 page
│   ├── components/               # Reusable components
│   │   ├── UserList.tsx          # Client Component (list)
│   │   └── UserForm.tsx          # Client Component (form)
│   ├── lib/                      # Shared utilities
│   │   ├── db.ts                 # Prisma client singleton
│   │   └── auth.ts               # NextAuth configuration
│   ├── types/                    # TypeScript types
│   │   └── next-auth.d.ts        # NextAuth type extensions
│   └── test/                     # Test configuration
│       └── setup.ts              # Vitest setup
├── prisma/
│   ├── schema.prisma             # Database schema
│   └── migrations/               # Database migrations
├── e2e/                          # Playwright E2E tests
│   └── users.spec.ts
├── public/                       # Static assets
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript config
├── tailwind.config.ts            # Tailwind config
├── vitest.config.ts              # Vitest config
├── playwright.config.ts          # Playwright config
└── .env                          # Environment variables
```

---

## Naming Conventions

### Components
- **Format**: PascalCase
- **Extension**: `.tsx`
- **Examples**: `UserList`, `UserForm`, `DashboardLayout`
- **Location**: `src/components/`

### Pages
- **Format**: `page.tsx` (fixed name)
- **Examples**: `app/users/page.tsx`, `app/(dashboard)/settings/page.tsx`

### Server Actions
- **Format**: camelCase
- **Extension**: `.ts`
- **Examples**: `createUser`, `deletePost`, `updateProfile`
- **Location**: `src/app/actions/`

### API Routes
- **Format**: `route.ts` (fixed name)
- **Examples**: `app/api/users/route.ts`, `app/api/posts/[id]/route.ts`

### Library Files
- **Format**: camelCase
- **Extension**: `.ts`
- **Examples**: `db.ts`, `auth.ts`, `utils.ts`
- **Location**: `src/lib/`

### Test Files
- **Unit Tests**: `ComponentName.test.tsx` (adjacent to source)
- **E2E Tests**: `feature.spec.ts` (in `e2e/` directory)

---

## Code Examples

### 1. Server Component (Data Fetching)

```typescript
// app/(dashboard)/users/page.tsx
import { db } from '@/lib/db'
import { UserList } from '@/components/UserList'

// Server Component - async function, direct DB access
export default async function UsersPage() {
  const users = await db.user.findMany({
    include: {
      posts: {
        take: 5
      }
    },
    orderBy: {
      createdAt: 'desc'
    }
  })

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold">Users</h1>
      <UserList users={users} />
    </div>
  )
}

// Force dynamic rendering (always fetch fresh data)
export const dynamic = 'force-dynamic'
export const revalidate = 0
```

### 2. Client Component (Interactivity)

```typescript
// components/UserList.tsx
'use client'

import { useState } from 'react'
import { UserForm } from './UserForm'
import { deleteUser } from '@/app/actions/users'
import { useRouter } from 'next/navigation'

type User = {
  id: string
  email: string
  name: string | null
}

export function UserList({ users }: { users: User[] }) {
  const router = useRouter()
  const [isCreating, setIsCreating] = useState(false)

  async function handleDelete(id: string) {
    if (confirm('Are you sure?')) {
      const result = await deleteUser(id)
      if (result.success) {
        router.refresh() // Refresh Server Component data
      } else {
        alert(result.error)
      }
    }
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => setIsCreating(!isCreating)}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        {isCreating ? 'Cancel' : 'Add User'}
      </button>

      {isCreating && (
        <UserForm onSuccess={() => {
          setIsCreating(false)
          router.refresh()
        }} />
      )}

      {users.map(user => (
        <div key={user.id} className="border p-4">
          <h3>{user.name || 'Anonymous'}</h3>
          <p>{user.email}</p>
          <button
            onClick={() => handleDelete(user.id)}
            className="text-red-600"
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  )
}
```

### 3. Server Actions (Mutations)

```typescript
// app/actions/users.ts
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  try {
    const email = formData.get('email') as string
    const name = formData.get('name') as string | null

    if (!email) {
      return { success: false, error: 'Email is required' }
    }

    const user = await db.user.create({
      data: {
        email,
        name: name || null
      }
    })

    revalidatePath('/users')
    return { success: true, data: user }
  } catch (_error) {
    return { success: false, error: 'Failed to create user' }
  }
}

export async function deleteUser(id: string) {
  try {
    await db.user.delete({
      where: { id }
    })

    revalidatePath('/users')
    return { success: true }
  } catch (_error) {
    return { success: false, error: 'Failed to delete user' }
  }
}
```

### 4. API Route Handler

```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export const dynamic = 'force-dynamic'

export async function GET(_request: NextRequest) {
  try {
    const users = await db.user.findMany({
      orderBy: {
        createdAt: 'desc'
      }
    })

    return NextResponse.json({ users }, { status: 200 })
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    if (!body.email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      )
    }

    const user = await db.user.create({
      data: {
        email: body.email,
        name: body.name || null
      }
    })

    return NextResponse.json({ user }, { status: 201 })
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to create user' },
      { status: 500 }
    )
  }
}
```

### 5. Database Schema (Prisma)

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  password  String?
  image     String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  posts     Post[]
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

### 6. Suspense and Streaming Patterns

**Streaming with Suspense Boundaries**
```typescript
// app/(dashboard)/users/page.tsx
import { Suspense } from 'react'
import { UserList } from '@/components/UserList'
import { LoadingSkeleton } from '@/components/LoadingSkeleton'

// Slow data fetch
async function Users() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}

export default function UsersPage() {
  return (
    <div>
      <h1>Users</h1>
      {/* Stream this component separately */}
      <Suspense fallback={<LoadingSkeleton />}>
        <Users />
      </Suspense>
    </div>
  )
}
```

**Parallel Data Fetching with Suspense**
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
      {/* These fetch in parallel and stream independently */}
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

**Loading UI with Instant Feedback**
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

### 7. Image Optimization

**Using next/image for Performance**
```typescript
import Image from 'next/image'

export function UserAvatar({ imageUrl, name }) {
  return (
    <Image
      src={imageUrl}
      alt={name}
      width={64}
      height={64}
      className="rounded-full"
      priority={false}
      loading="lazy"
    />
  )
}
```

---

## Quality Standards

### Code Quality
- **TypeScript Strict Mode**: Enabled for maximum type safety
- **Linting**: ESLint with Next.js recommended rules
- **Formatting**: Consistent code style (2 spaces, single quotes)

### Testing Requirements
- **Unit Test Coverage**: ≥80% lines, ≥75% branches
- **E2E Test Coverage**: Critical user flows
- **Test Frameworks**: Vitest (unit), Playwright (E2E)

### Performance
- **First Contentful Paint**: <1.5s
- **Time to Interactive**: <3.5s
- **Lighthouse Score**: ≥90

### Architecture Compliance
- **SOLID Principles**: 75/100
- **DRY Principle**: 80/100
- **YAGNI Principle**: 90/100

---

## AI Agents

This template includes 3 custom AI agents specialized for Next.js full-stack development:

### 1. nextjs-server-components-specialist
**Purpose**: React Server Components and data fetching patterns
**Use When**: Implementing pages, data fetching, rendering strategies
**Capabilities**:
- Design async Server Components
- Optimize data fetching (parallel, sequential)
- Implement rendering strategies (SSG, SSR, ISR)
- Manage Server/Client component boundaries

### 2. nextjs-server-actions-specialist
**Purpose**: Server Actions for mutations and form handling
**Use When**: Implementing CRUD operations, form submissions, mutations
**Capabilities**:
- Implement type-safe Server Actions
- Handle progressive enhancement
- Manage cache revalidation
- Implement validation and error handling

### 3. nextjs-fullstack-specialist
**Purpose**: End-to-end Next.js full-stack application development
**Use When**: Complete CRUD workflows, authentication, deployment
**Capabilities**:
- Design full-stack architecture
- Integrate databases (Prisma)
- Set up authentication (NextAuth)
- Configure testing and deployment

---

## Getting Started

### 1. Initialize Project
```bash
guardkit init nextjs-fullstack --output my-app
cd my-app
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment
```bash
# Create .env file
echo 'DATABASE_URL="file:./dev.db"' > .env
echo 'NEXTAUTH_SECRET="your-secret-key"' >> .env
echo 'NEXTAUTH_URL="http://localhost:3000"' >> .env
```

### 4. Initialize Database
```bash
npx prisma generate
npx prisma migrate dev --name init
```

### 5. Run Development Server
```bash
npm run dev
```

### 6. Run Tests
```bash
npm test              # Unit tests
npm run test:e2e      # E2E tests
npm run type-check    # TypeScript
```

---

## Common Development Tasks

### Adding a New Entity

1. **Update Prisma Schema**
   ```prisma
   model Product {
     id    String @id @default(cuid())
     name  String
     price Float
   }
   ```

2. **Generate Migration**
   ```bash
   npx prisma migrate dev --name add_product
   ```

3. **Create Server Component**
   ```typescript
   // app/(dashboard)/products/page.tsx
   export default async function ProductsPage() {
     const products = await db.product.findMany()
     return <ProductList products={products} />
   }
   ```

4. **Create Server Actions**
   ```typescript
   // app/actions/products.ts
   'use server'
   export async function createProduct(formData: FormData) { ... }
   ```

5. **Create Client Components**
   ```typescript
   // components/ProductList.tsx
   'use client'
   export function ProductList({ products }) { ... }
   ```

### Deployment

#### Vercel (Recommended)
1. Push to Git repository
2. Connect to Vercel
3. Configure environment variables
4. Deploy automatically

#### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npx prisma generate
RUN npm run build
CMD ["npm", "start"]
```

---

## Troubleshooting

### Build Errors
- **Prisma not generated**: Run `npx prisma generate`
- **TypeScript errors**: Run `npm run type-check`
- **Environment variables**: Ensure `.env` file exists

### Runtime Errors
- **Database connection**: Check `DATABASE_URL` in `.env`
- **Auth errors**: Verify `NEXTAUTH_SECRET` and `NEXTAUTH_URL`
- **CORS issues**: Configure Next.js headers in `next.config.js`

---

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [React Server Components](https://react.dev/reference/rsc/server-components)
- [Prisma Documentation](https://www.prisma.io/docs)
- [NextAuth Documentation](https://next-auth.js.org)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

---

**Template Version**: 1.0.0
**Last Updated**: 2025-11-09
**Confidence Score**: 92/100
**Quality**: Production Ready

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.

