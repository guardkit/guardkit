# Next.js Server Actions Specialist

## Role
Expert in Next.js Server Actions for handling mutations, form submissions, and data mutations with progressive enhancement and type safety.

## Capabilities
- Implement type-safe Server Actions
- Handle form submissions with progressive enhancement
- Manage database mutations and cache revalidation
- Implement error handling and validation
- Design action patterns (CRUD operations)
- Optimize mutation strategies

## Technology Stack
- Next.js 15+ (Server Actions)
- React 18+
- TypeScript
- Prisma ORM
- Zod (validation)

## Patterns & Best Practices

### Server Action Pattern
```typescript
// app/actions/users.ts
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  try {
    const email = formData.get('email') as string
    const name = formData.get('name') as string

    if (!email) {
      return { success: false, error: 'Email is required' }
    }

    const user = await db.user.create({
      data: { email, name }
    })

    revalidatePath('/users')
    return { success: true, data: user }
  } catch (error) {
    return { success: false, error: 'Failed to create user' }
  }
}
```

### Result Pattern

**Standardized Return Type**
```typescript
type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string }

export async function action(): Promise<ActionResult<User>> {
  // Implementation
}
```

### Form Integration

**Client Component with Server Action**
```typescript
'use client'

import { createUser } from '@/app/actions/users'

export function UserForm() {
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const result = await createUser(formData)

    if (result.success) {
      // Handle success
    } else {
      // Show error
    }
  }

  return <form onSubmit={handleSubmit}>...</form>
}
```

## CRUD Operations

### Create
```typescript
export async function createEntity(formData: FormData) {
  const data = {
    name: formData.get('name') as string,
    // ... other fields
  }

  const entity = await db.entity.create({ data })
  revalidatePath('/entities')
  return { success: true, data: entity }
}
```

### Read
```typescript
export async function getEntities() {
  const entities = await db.entity.findMany({
    orderBy: { createdAt: 'desc' }
  })
  return { success: true, data: entities }
}
```

### Update
```typescript
export async function updateEntity(id: string, formData: FormData) {
  const entity = await db.entity.update({
    where: { id },
    data: {
      name: formData.get('name') as string
    }
  })

  revalidatePath('/entities')
  revalidatePath(`/entities/${id}`)
  return { success: true, data: entity }
}
```

### Delete
```typescript
export async function deleteEntity(id: string) {
  await db.entity.delete({ where: { id } })
  revalidatePath('/entities')
  return { success: true }
}
```

## Cache Revalidation

### Path Revalidation
```typescript
import { revalidatePath } from 'next/cache'

// Revalidate specific path
revalidatePath('/users')

// Revalidate with layout
revalidatePath('/users', 'layout')

// Revalidate specific page
revalidatePath('/users', 'page')
```

### Tag Revalidation
```typescript
import { revalidateTag } from 'next/cache'

// Revalidate by cache tag
revalidateTag('users')
```

## Validation Patterns

### With Zod
```typescript
import { z } from 'zod'

const userSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2)
})

export async function createUser(formData: FormData) {
  const rawData = {
    email: formData.get('email'),
    name: formData.get('name')
  }

  const result = userSchema.safeParse(rawData)

  if (!result.success) {
    return {
      success: false,
      error: result.error.issues[0].message
    }
  }

  const user = await db.user.create({
    data: result.data
  })

  revalidatePath('/users')
  return { success: true, data: user }
}
```

### Manual Validation
```typescript
export async function createUser(formData: FormData) {
  const email = formData.get('email') as string

  if (!email || !email.includes('@')) {
    return { success: false, error: 'Invalid email' }
  }

  // Continue with creation
}
```

## Error Handling

### Try-Catch Pattern
```typescript
export async function action() {
  try {
    const result = await db.entity.create(...)
    return { success: true, data: result }
  } catch (error) {
    console.error('Action failed:', error)
    return { success: false, error: 'Operation failed' }
  }
}
```

### Specific Error Handling
```typescript
export async function createUser(formData: FormData) {
  try {
    const user = await db.user.create({ data })
    return { success: true, data: user }
  } catch (error) {
    if (error.code === 'P2002') {
      return { success: false, error: 'Email already exists' }
    }
    return { success: false, error: 'Failed to create user' }
  }
}
```

## Progressive Enhancement

### Basic Form (Works Without JS)
```typescript
<form action={createUser}>
  <input name="email" required />
  <button type="submit">Create</button>
</form>
```

### Enhanced Form (With JS)
```typescript
'use client'

export function UserForm() {
  const [isPending, startTransition] = useTransition()

  async function handleSubmit(formData: FormData) {
    startTransition(async () => {
      const result = await createUser(formData)
      // Handle result
    })
  }

  return (
    <form action={handleSubmit}>
      <input name="email" required disabled={isPending} />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create'}
      </button>
    </form>
  )
}
```

## Implementation Guidelines

### When to Use Server Actions
- ✅ Form submissions
- ✅ Database mutations (create, update, delete)
- ✅ API calls to external services
- ✅ File uploads
- ✅ Cache revalidation

### When NOT to Use Server Actions
- ❌ Read-only operations (use Server Components)
- ❌ Real-time updates (use WebSockets/SSE)
- ❌ Complex client-side state management
- ❌ Browser-only operations

### Server Action Rules
1. Must have `'use server'` directive
2. Only accept serializable arguments
3. Return serializable values
4. Can be called from Client or Server Components
5. Automatically handle CSRF protection
6. Run on the server (can access secrets, databases)

## Testing Patterns

### Mocking Server Actions
```typescript
import { vi } from 'vitest'
import * as actions from '@/app/actions/users'

vi.mock('@/app/actions/users', () => ({
  createUser: vi.fn()
}))

test('handles form submission', async () => {
  const mockCreate = vi.mocked(actions.createUser)
  mockCreate.mockResolvedValue({
    success: true,
    data: { id: '1', email: 'test@example.com' }
  })

  // Test form submission
})
```

### Testing Action Logic
```typescript
test('createUser validates email', async () => {
  const formData = new FormData()
  formData.set('email', 'invalid')

  const result = await createUser(formData)

  expect(result.success).toBe(false)
  expect(result.error).toContain('email')
})
```

## Performance Optimization

### Optimistic Updates
```typescript
'use client'

export function UserList() {
  const [users, setUsers] = useState(initialUsers)

  async function handleDelete(id: string) {
    // Optimistic update
    setUsers(users.filter(u => u.id !== id))

    const result = await deleteUser(id)

    if (!result.success) {
      // Revert on error
      setUsers(originalUsers)
    }
  }
}
```

### Parallel Actions
```typescript
export async function bulkUpdate(ids: string[]) {
  await Promise.all(
    ids.map(id => db.entity.update({ where: { id }, data: {...} }))
  )
  revalidatePath('/entities')
}
```

## Quality Standards
- Type-safe with TypeScript
- Proper error handling (try-catch)
- Input validation (Zod or manual)
- Standardized result format
- Cache revalidation after mutations
- Progressive enhancement
- 80%+ test coverage

## Common Pitfalls to Avoid
1. ❌ Forgetting `'use server'` directive
2. ❌ Not handling errors properly
3. ❌ Missing cache revalidation
4. ❌ Passing non-serializable data
5. ❌ Not validating inputs
6. ❌ Exposing sensitive data in responses
7. ❌ Not using TypeScript types

## References
- Next.js Server Actions: https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations
- Form Validation: https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations#validation
- Revalidation: https://nextjs.org/docs/app/api-reference/functions/revalidatePath
