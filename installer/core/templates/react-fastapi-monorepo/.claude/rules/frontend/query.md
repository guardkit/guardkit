---
paths: apps/frontend/**/*query*, apps/frontend/**/*api*
---

# TanStack Query Patterns

## Server State Management

TanStack Query (React Query) manages all server state in the frontend.

## Query Patterns

### Basic Query
```typescript
import { useQuery } from '@tanstack/react-query'
import { api, User } from 'shared-types'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users')
      return response.data
    },
  })
}
```

### Parameterized Query
```typescript
export function useUser(userId: number) {
  return useQuery({
    queryKey: ['users', userId],
    queryFn: async () => {
      const response = await api.get<User>(`/users/${userId}`)
      return response.data
    },
    enabled: !!userId,  // Only run if userId exists
  })
}
```

### Query Options Pattern
```typescript
import { queryOptions, useQuery } from '@tanstack/react-query'

export const getUsersQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['users', { page }] : ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users', {
        params: { page }
      })
      return response.data
    },
  })
}

export const useUsers = ({ page, queryConfig }: Options) => {
  return useQuery({
    ...getUsersQueryOptions({ page }),
    ...queryConfig,
  })
}
```

**Benefits**:
- Enables server-side prefetching
- Reusable query configuration
- Type-safe parameters

## Mutation Patterns

### Basic Mutation
```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, UserCreate, User } from 'shared-types'

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UserCreate) => {
      const response = await api.post<User>('/users', data)
      return response.data
    },
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### Optimistic Updates
```typescript
export function useUpdateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UserUpdate }) => {
      const response = await api.patch<User>(`/users/${id}`, data)
      return response.data
    },
    onMutate: async ({ id, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['users', id] })

      // Snapshot previous value
      const previousUser = queryClient.getQueryData(['users', id])

      // Optimistically update
      queryClient.setQueryData(['users', id], (old: User) => ({
        ...old,
        ...data,
      }))

      return { previousUser }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      queryClient.setQueryData(['users', variables.id], context?.previousUser)
    },
    onSettled: (data, error, variables) => {
      // Refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['users', variables.id] })
    },
  })
}
```

### Delete Mutation
```typescript
export function useDeleteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (userId: number) => {
      await api.delete(`/users/${userId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

## Query Client Configuration

```typescript
// lib/query-client.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      gcTime: 1000 * 60 * 10,     // 10 minutes
      retry: 3,
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 1,
    },
  },
})
```

## Provider Setup

```typescript
// App.tsx
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { queryClient } from './lib/query-client'

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <YourApp />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

## Cache Invalidation

### Invalidate Specific Query
```typescript
queryClient.invalidateQueries({ queryKey: ['users'] })
```

### Invalidate Multiple Queries
```typescript
queryClient.invalidateQueries({ queryKey: ['users'] })
queryClient.invalidateQueries({ queryKey: ['posts'] })
```

### Invalidate with Predicate
```typescript
queryClient.invalidateQueries({
  predicate: (query) => query.queryKey[0] === 'users',
})
```

## Prefetching

### Component-Level Prefetch
```typescript
import { useQueryClient } from '@tanstack/react-query'

export function UsersList() {
  const queryClient = useQueryClient()

  const handleHover = (userId: number) => {
    queryClient.prefetchQuery({
      queryKey: ['users', userId],
      queryFn: () => fetchUser(userId),
    })
  }

  return <div onMouseEnter={() => handleHover(1)}>User 1</div>
}
```

### Server-Side Prefetch (Next.js)
```typescript
export async function getServerSideProps() {
  const queryClient = new QueryClient()

  await queryClient.prefetchQuery(getUsersQueryOptions())

  return {
    props: {
      dehydratedState: dehydrate(queryClient),
    },
  }
}
```

## Error Handling

### Query Errors
```typescript
const { data, error, isError } = useUsers()

if (isError) {
  return <div>Error: {error.message}</div>
}
```

### Mutation Errors
```typescript
const createUser = useCreateUser()

const handleSubmit = async (data: UserCreate) => {
  try {
    await createUser.mutateAsync(data)
    toast.success('User created!')
  } catch (error) {
    toast.error('Failed to create user')
  }
}
```

### Global Error Handling
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error) => {
        toast.error(`Query error: ${error.message}`)
      },
    },
    mutations: {
      onError: (error) => {
        toast.error(`Mutation error: ${error.message}`)
      },
    },
  },
})
```

## Best Practices

### 1. Use Query Keys Consistently
```typescript
// ✅ Good
['users']
['users', userId]
['users', { page: 1 }]

// ❌ Bad
['getUsers']
['user', userId]
['users', page]
```

### 2. Export Query Options
```typescript
// ✅ Enables server-side prefetching
export const getUsersQueryOptions = () => { ... }

// ❌ Hard to reuse
const useUsers = () => useQuery({ ... })
```

### 3. Invalidate After Mutations
```typescript
// ✅ Keeps cache fresh
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['users'] })
}

// ❌ Stale cache
onSuccess: () => {}
```

### 4. Handle Loading States
```typescript
// ✅ Good UX
if (isLoading) return <Spinner />
if (isError) return <Error />

// ❌ No feedback
const { data } = useUsers()
return <div>{data?.map(...)}</div>
```

### 5. Use Optimistic Updates for Better UX
```typescript
// ✅ Instant feedback
onMutate: async (newUser) => {
  queryClient.setQueryData(['users'], (old) => [...old, newUser])
}

// ❌ Slow feedback
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['users'] })
}
```

## Common Patterns

### Dependent Queries
```typescript
const { data: user } = useUser(userId)
const { data: posts } = usePosts(user?.id, {
  enabled: !!user?.id,
})
```

### Pagination
```typescript
const [page, setPage] = useState(1)
const { data } = useUsers({ page })
```

### Infinite Scroll
```typescript
const {
  data,
  fetchNextPage,
  hasNextPage,
} = useInfiniteQuery({
  queryKey: ['users'],
  queryFn: ({ pageParam = 1 }) => fetchUsers(pageParam),
  getNextPageParam: (lastPage, pages) => lastPage.nextPage,
})
```

## Debugging

### React Query Devtools
```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

<ReactQueryDevtools initialIsOpen={false} />
```

### Log Query State
```typescript
const query = useUsers()
console.log({
  data: query.data,
  isLoading: query.isLoading,
  isError: query.isError,
  error: query.error,
})
```
