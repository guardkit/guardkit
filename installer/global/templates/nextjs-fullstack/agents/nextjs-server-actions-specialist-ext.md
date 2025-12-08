# nextjs-server-actions-specialist - Extended Reference

This file contains detailed documentation for the `nextjs-server-actions-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/nextjs-server-actions-specialist-ext.md
```


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


## Related Templates

### Primary Templates

1. **templates/actions/entity-actions.ts.template**
   - Complete CRUD Server Actions implementation
   - Standard result pattern (`{ success, data/error }`)
   - Cache revalidation with `revalidatePath()`
   - Zod validation integration (optional)
   - Error handling patterns

2. **templates/components/EntityForm.tsx.template**
   - Form submission with Server Actions
   - Progressive enhancement support
   - Loading states (`isSubmitting`)
   - Error display patterns
   - Success callback handling

3. **templates/components/EntityList.tsx.template**
   - Server Action integration in lists
   - Delete action patterns
   - `router.refresh()` for optimistic updates
   - Error handling in UI

### Supporting Templates

4. **templates/tests/ComponentTest.test.tsx.template**
   - Server Action mocking patterns with Vitest
   - Form submission testing
   - Error state testing

5. **templates/lib/db.ts.template**
   - Prisma singleton for Server Actions
   - Database connection patterns


## Code Examples from Templates

### Example 1: Complete CRUD Server Actions

```typescript
// ✅ DO: Implement full CRUD with standard patterns
// actions/products.ts
'use server'

import { revalidatePath } from 'next/cache'
import { db } from '@/lib/db'

// GET all
export async function getProducts() {
  try {
    const products = await db.product.findMany()
    return { success: true, data: products }
  } catch (error) {
    return { success: false, error: 'Failed to fetch products' }
  }
}

// GET by ID
export async function getProduct(id: string) {
  try {
    const product = await db.product.findUnique({ where: { id } })
    if (!product) {
      return { success: false, error: 'Product not found' }
    }
    return { success: true, data: product }
  } catch (error) {
    return { success: false, error: 'Failed to fetch product' }
  }
}

// CREATE
export async function createProduct(formData: FormData) {
  try {
    const name = formData.get('name') as string
    const price = parseFloat(formData.get('price') as string)

    // Validation
    if (!name || name.trim().length === 0) {
      return { success: false, error: 'Name is required' }
    }
    if (isNaN(price) || price <= 0) {
      return { success: false, error: 'Valid price is required' }
    }

    const product = await db.product.create({
      data: { name: name.trim(), price }
    })

    revalidatePath('/products')
    return { success: true, data: product }
  } catch (error) {
    return { success: false, error: 'Failed to create product' }
  }
}

// UPDATE
export async function updateProduct(id: string, formData: FormData) {
  try {
    const name = formData.get('name') as string
    const price = parseFloat(formData.get('price') as string)

    if (!name || name.trim().length === 0) {
      return { success: false, error: 'Name is required' }
    }
    if (isNaN(price) || price <= 0) {
      return { success: false, error: 'Valid price is required' }
    }

    const product = await db.product.update({
      where: { id },
      data: { name: name.trim(), price }
    })

    revalidatePath('/products')
    revalidatePath(`/products/${id}`)
    return { success: true, data: product }
  } catch (error) {
    return { success: false, error: 'Failed to update product' }
  }
}

// DELETE
export async function deleteProduct(id: string) {
  try {
    await db.product.delete({ where: { id } })
    revalidatePath('/products')
    return { success: true, data: { id } }
  } catch (error) {
    return { success: false, error: 'Failed to delete product' }
  }
}
```

```typescript
// ❌ DON'T: Mix Server Actions with read operations
'use server'

export async function getAndUpdateProduct(id: string) {
  // DON'T: Server Actions are for mutations only
  const product = await db.product.findUnique({ where: { id } })
  // Fetching should happen in Server Components
}

// ❌ DON'T: Skip revalidation
export async function createProduct(formData: FormData) {
  const product = await db.product.create({ data: { /*...*/ } })
  // Missing: revalidatePath('/products')
  return product // UI will show stale data!
}
```

### Example 2: Form Integration with Progressive Enhancement

```typescript
// ✅ DO: Progressive enhancement with loading states
'use client'

import { createProduct } from '@/actions/products'
import { useState } from 'react'

export function ProductForm({ onSuccess }: { onSuccess?: () => void }) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(formData: FormData) {
    setIsSubmitting(true)
    setError(null)

    const result = await createProduct(formData)

    if (result.success) {
      onSuccess?.()
      // Form reset handled by key remount or ref
    } else {
      setError(result.error)
    }

    setIsSubmitting(false)
  }

  return (
    <form action={handleSubmit}>
      <input type="text" name="name" required disabled={isSubmitting} />
      <input type="number" name="price" step="0.01" required disabled={isSubmitting} />

      {error && <div className="error">{error}</div>}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating...' : 'Create Product'}
      </button>
    </form>
  )
}
```

```typescript
// ❌ DON'T: Forget loading states or error handling
'use client'

export function ProductForm() {
  // Missing: loading state, error handling

  return (
    <form action={async (formData) => {
      await createProduct(formData)
      // No feedback to user!
    }}>
      <input type="text" name="name" />
      <button type="submit">Create</button>
    </form>
  )
}
```

### Example 3: Optimistic UI with Server Actions

```typescript
// ✅ DO: Optimistic updates with rollback
'use client'

import { deleteProduct } from '@/actions/products'
import { useRouter } from 'next/navigation'
import { useState, useTransition } from 'react'

export function ProductList({ initialProducts }: { initialProducts: Product[] }) {
  const [products, setProducts] = useState(initialProducts)
  const [isPending, startTransition] = useTransition()
  const router = useRouter()

  async function handleDelete(id: string) {
    // Optimistic update
    const previousProducts = products
    setProducts(products.filter(p => p.id !== id))

    startTransition(async () => {
      const result = await deleteProduct(id)

      if (result.success) {
        router.refresh() // Sync with server
      } else {
        // Rollback on error
        setProducts(previousProducts)
        alert(result.error)
      }
    })
  }

  return (
    <ul>
      {products.map(product => (
        <li key={product.id}>
          {product.name}
          <button onClick={() => handleDelete(product.id)} disabled={isPending}>
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
```

```typescript
// ❌ DON'T: Skip rollback or error handling in optimistic updates
async function handleDelete(id: string) {
  setProducts(products.filter(p => p.id !== id)) // Optimistic

  await deleteProduct(id)
  // Missing: error handling and rollback
  // Missing: router.refresh() to sync
}
```

### Example 4: Advanced Validation with Zod

```typescript
// ✅ DO: Add Zod validation for complex schemas
'use server'

import { z } from 'zod'
import { revalidatePath } from 'next/cache'

const ProductSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  price: z.number().positive('Price must be positive'),
  category: z.enum(['electronics', 'clothing', 'food']),
  tags: z.array(z.string()).optional()
})

export async function createProduct(formData: FormData) {
  try {
    // Parse FormData to object
    const rawData = {
      name: formData.get('name'),
      price: parseFloat(formData.get('price') as string),
      category: formData.get('category'),
      tags: formData.get('tags')?.toString().split(',').map(t => t.trim())
    }

    // Validate with Zod
    const validated = ProductSchema.parse(rawData)

    const product = await db.product.create({ data: validated })

    revalidatePath('/products')
    return { success: true, data: product }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        success: false,
        error: error.errors.map(e => e.message).join(', ')
      }
    }
    return { success: false, error: 'Failed to create product' }
  }
}
```


## Anti-Patterns to Avoid

### 1. Using Server Actions for Read Operations

```typescript
// ❌ DON'T
'use server'
export async function getProducts() {
  return await db.product.findMany()
}

// ✅ DO: Use Server Components for reads
// app/products/page.tsx
export default async function ProductsPage() {
  const products = await db.product.findMany()
  return <ProductList products={products} />
}
```

**Why**: Server Actions add unnecessary overhead for reads. Server Components are optimized for data fetching.

### 2. Missing Revalidation After Mutations

```typescript
// ❌ DON'T: Forget to revalidate
export async function createProduct(formData: FormData) {
  const product = await db.product.create({ data: { /*...*/ } })
  return { success: true, data: product }
  // UI will show stale data until hard refresh!
}

// ✅ DO: Always revalidate affected paths
export async function createProduct(formData: FormData) {
  const product = await db.product.create({ data: { /*...*/ } })
  revalidatePath('/products') // Invalidate list
  revalidatePath('/') // Invalidate home if needed
  return { success: true, data: product }
}
```

### 3. Redirect Inside Try-Catch

```typescript
// ❌ DON'T: redirect() throws, breaks try-catch
'use server'
import { redirect } from 'next/navigation'

export async function createProduct(formData: FormData) {
  try {
    await db.product.create({ data: { /*...*/ } })
    redirect('/products') // This throws!
  } catch (error) {
    return { success: false, error: 'Failed' } // Never reached
  }
}

// ✅ DO: redirect() outside try-catch
export async function createProduct(formData: FormData) {
  try {
    await db.product.create({ data: { /*...*/ } })
    revalidatePath('/products')
  } catch (error) {
    return { success: false, error: 'Failed' }
  }

  redirect('/products') // Outside try-catch
}
```

### 4. Inconsistent Result Patterns

```typescript
// ❌ DON'T: Mix return patterns
export async function createProduct(formData: FormData) {
  try {
    const product = await db.product.create({ data: { /*...*/ } })
    return product // Sometimes return data directly
  } catch (error) {
    return { error: 'Failed' } // Sometimes return error object
  }
}

// ✅ DO: Consistent result pattern
export async function createProduct(formData: FormData) {
  try {
    const product = await db.product.create({ data: { /*...*/ } })
    return { success: true, data: product } // Always same shape
  } catch (error) {
    return { success: false, error: 'Failed' }
  }
}
```

### 5. Exposing Sensitive Operations

```typescript
// ❌ DON'T: Expose admin operations without auth checks
'use server'
export async function deleteAllProducts() {
  await db.product.deleteMany() // Anyone can call this!
  return { success: true }
}

// ✅ DO: Add authentication and authorization
'use server'
import { auth } from '@/lib/auth'

export async function deleteAllProducts() {
  const session = await auth()

  if (!session?.user?.isAdmin) {
    return { success: false, error: 'Unauthorized' }
  }

  await db.product.deleteMany()
  revalidatePath('/products')
  return { success: true }
}
```


## Common Patterns

### Pattern 1: Multi-Step Mutations

```typescript
// Complex mutation with multiple database operations
'use server'

export async function createOrderWithItems(formData: FormData) {
  try {
    const customerId = formData.get('customerId') as string
    const items = JSON.parse(formData.get('items') as string)

    // Use transaction for atomicity
    const order = await db.$transaction(async (tx) => {
      const order = await tx.order.create({
        data: { customerId, status: 'pending' }
      })

      await tx.orderItem.createMany({
        data: items.map((item: any) => ({
          orderId: order.id,
          productId: item.productId,
          quantity: item.quantity
        }))
      })

      return order
    })

    revalidatePath('/orders')
    revalidatePath(`/customers/${customerId}`)
    return { success: true, data: order }
  } catch (error) {
    return { success: false, error: 'Failed to create order' }
  }
}
```

### Pattern 2: File Upload Actions

```typescript
// Server Action with file upload
'use server'

export async function uploadProductImage(formData: FormData) {
  try {
    const file = formData.get('image') as File
    const productId = formData.get('productId') as string

    if (!file || file.size === 0) {
      return { success: false, error: 'No file provided' }
    }

    if (file.size > 5 * 1024 * 1024) {
      return { success: false, error: 'File too large (max 5MB)' }
    }

    // Save file (simplified - use S3/Cloudinary in production)
    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)
    const path = `/uploads/${productId}-${Date.now()}.${file.name.split('.').pop()}`

    await fs.writeFile(`./public${path}`, buffer)

    // Update database
    await db.product.update({
      where: { id: productId },
      data: { imageUrl: path }
    })

    revalidatePath(`/products/${productId}`)
    return { success: true, data: { path } }
  } catch (error) {
    return { success: false, error: 'Failed to upload image' }
  }
}
```

### Pattern 3: Rate-Limited Actions

```typescript
// Server Action with rate limiting
'use server'

import { ratelimit } from '@/lib/ratelimit'

export async function sendEmail(formData: FormData) {
  const ip = headers().get('x-forwarded-for') ?? 'unknown'

  const { success: rateLimitOk } = await ratelimit.limit(ip)

  if (!rateLimitOk) {
    return {
      success: false,
      error: 'Too many requests. Please try again later.'
    }
  }

  try {
    const email = formData.get('email') as string
    const message = formData.get('message') as string

    await sendEmailService({ to: email, message })

    return { success: true, data: { sent: true } }
  } catch (error) {
    return { success: false, error: 'Failed to send email' }
  }
}
```


## Integration Points

### With Server Components
- Server Components fetch initial data (reads)
- Server Actions handle mutations (writes)
- Pass Server Actions to Client Components as props
- Use `revalidatePath()` to refresh Server Component data

### With Client Components
- Client Components call Server Actions for mutations
- Handle loading states with `useState` or `useTransition`
- Display errors from action results
- Trigger re-renders with `router.refresh()`

### With Database Layer
- Server Actions are the ONLY way Client Components mutate data
- Always use transactions for multi-step mutations
- Include proper error handling for database failures
- Leverage Prisma middleware for common concerns (logging, soft deletes)

### With Authentication
- Check `auth()` or session at action start
- Return `{ success: false, error: 'Unauthorized' }` for auth failures
- Include user ID in audit logs
- Rate-limit sensitive actions


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-server-actions-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-server-actions-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat nextjs-server-actions-specialist-ext.md
```

Or in Claude Code:
```
Please read nextjs-server-actions-specialist-ext.md for detailed examples.
```
