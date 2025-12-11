---
paths: **/api/**/route.ts
---

# API Route Handlers

## Purpose

RESTful endpoints for external clients (mobile apps, third-party services).

## Pattern

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

## HTTP Methods

- `GET` - Retrieve resources
- `POST` - Create resources
- `PUT` - Update resources (full replacement)
- `PATCH` - Update resources (partial update)
- `DELETE` - Delete resources

## Dynamic Routes

```typescript
// app/api/users/[id]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const user = await db.user.findUnique({
    where: { id: params.id }
  })

  if (!user) {
    return NextResponse.json(
      { error: 'User not found' },
      { status: 404 }
    )
  }

  return NextResponse.json({ user })
}
```

## Response Helpers

```typescript
// Success responses
return NextResponse.json({ data }, { status: 200 })
return NextResponse.json({ data }, { status: 201 }) // Created
return NextResponse.json({ message: 'Deleted' }, { status: 204 })

// Error responses
return NextResponse.json({ error: 'Bad request' }, { status: 400 })
return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
return NextResponse.json({ error: 'Not found' }, { status: 404 })
return NextResponse.json({ error: 'Server error' }, { status: 500 })
```

## When to Use API Routes vs Server Actions

**Use Server Actions** (preferred):
- Internal mutations from your Next.js app
- Form submissions
- Progressive enhancement

**Use API Routes**:
- External clients (mobile apps)
- Third-party integrations
- Webhooks
- Public REST API
