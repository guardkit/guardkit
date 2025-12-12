---
paths: **/actions/*.ts, **/actions/**/*.ts
---

# Server Actions

## Purpose

Type-safe mutations callable from client components.

## Pattern

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

## Best Practices

- Always use 'use server' directive
- Return typed responses (success/error)
- Call revalidatePath after mutations
- Handle errors gracefully

## Complete CRUD Example

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

## Using in Client Components

```typescript
// components/UserForm.tsx
'use client'

import { createUser } from '@/app/actions/users'
import { useRouter } from 'next/navigation'

export function UserForm() {
  const router = useRouter()

  async function handleSubmit(formData: FormData) {
    const result = await createUser(formData)

    if (result.success) {
      router.refresh() // Refresh Server Component data
    } else {
      alert(result.error)
    }
  }

  return (
    <form action={handleSubmit}>
      <input name="email" type="email" required />
      <button type="submit">Create User</button>
    </form>
  )
}
```

## Progressive Enhancement

Server Actions work without JavaScript:

```typescript
// components/UserForm.tsx
export function UserForm() {
  return (
    <form action={createUser}>
      <input name="email" type="email" required />
      <button type="submit">Create User</button>
    </form>
  )
}
```

## Cache Revalidation

```typescript
import { revalidatePath, revalidateTag } from 'next/cache'

// Revalidate specific path
revalidatePath('/users')

// Revalidate all paths
revalidatePath('/', 'layout')

// Revalidate by cache tag
revalidateTag('users')
```
