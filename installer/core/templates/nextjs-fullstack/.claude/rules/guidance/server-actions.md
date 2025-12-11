---
paths: **/actions/**, **/actions/**/*.ts
---

# Server Actions Specialist

## Purpose

Server Actions for mutations and form handling in Next.js App Router.

## Technologies

Next.js 15, Server Actions, Prisma, Progressive Enhancement

## Boundaries

### ALWAYS
- Use 'use server' directive
- Return typed responses (success/error)
- Call revalidatePath after mutations
- Handle validation errors
- Support progressive enhancement

### NEVER
- Skip 'use server' directive
- Return raw database errors to client
- Forget cache revalidation
- Ignore input validation
- Expose sensitive data

### ASK
- Optimistic updates strategy
- Form validation approach (Zod, manual)
- Error handling patterns
- Cache revalidation scope

## Quick Start

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

## Extended Documentation

For comprehensive patterns, see:
- `installer/core/templates/nextjs-fullstack/agents/nextjs-server-actions-specialist.md`
- `installer/core/templates/nextjs-fullstack/agents/nextjs-server-actions-specialist-ext.md`
