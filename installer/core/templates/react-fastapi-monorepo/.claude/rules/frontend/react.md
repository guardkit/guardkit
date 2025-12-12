---
paths: apps/frontend/**/*.tsx, apps/frontend/**/*.ts
---

# React Frontend Architecture

## Feature-Based Structure

Organize React code by domain features, not technical layers:

```
apps/frontend/src/
├── features/
│   ├── users/
│   │   ├── api/
│   │   │   ├── get-users.ts
│   │   │   └── create-user.ts
│   │   ├── components/
│   │   │   ├── users-list.tsx
│   │   │   └── user-card.tsx
│   │   └── hooks/
│   │       └── use-users.ts
│   └── auth/
│       ├── api/
│       ├── components/
│       └── hooks/
├── components/         # Shared components
├── hooks/             # Shared hooks
└── lib/               # Utilities
```

## API Layer Pattern

### Query Options Pattern
```typescript
// features/users/api/get-users.ts
import { queryOptions, useQuery } from '@tanstack/react-query'
import { api, User } from 'shared-types'

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

### Mutation Pattern
```typescript
// features/users/api/create-user.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, UserCreate, User } from 'shared-types'

export const useCreateUser = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UserCreate) => {
      const response = await api.post<User>('/users', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

## Component Patterns

### Feature Component
```typescript
// features/users/components/users-list.tsx
import { useUsers } from '../hooks/use-users'
import { UserCard } from './user-card'

export const UsersList = () => {
  const { data: users, isLoading, error } = useUsers({})

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <div>
      {users?.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  )
}
```

### Shared Component
```typescript
// components/button.tsx
import { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary'
}

export const Button = ({ variant = 'primary', ...props }: ButtonProps) => {
  return <button {...props} className={`btn-${variant}`} />
}
```

## Naming Conventions

### Files
- **Components**: `kebab-case.tsx` (export: `PascalCase`)
- **Hooks**: `use-hook-name.ts`
- **API files**: `{action}-{entity}.ts` (e.g., `get-users.ts`)
- **Features**: singular, lowercase, kebab-case

### Code
- **Components**: `PascalCase`
- **Hooks**: `camelCase` with `use` prefix
- **Functions**: `camelCase`
- **Types/Interfaces**: `PascalCase`
- **Constants**: `SCREAMING_SNAKE_CASE` or `camelCase`

### Examples
```typescript
// features/discussions/components/discussions-list.tsx
export const DiscussionsList = () => { ... }

// features/discussions/hooks/use-discussions.ts
export const useDiscussions = () => { ... }

// features/discussions/api/get-discussions.ts
export const getDiscussions = () => { ... }
```

## Type Safety with shared-types

### Import Generated Types
```typescript
import { api, User, UserCreate, UserUpdate } from 'shared-types'

// Fully typed API calls
const response = await api.get<User[]>('/users')
const users: User[] = response.data  // Type-safe!
```

### Type Guards
```typescript
function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'email' in data
  )
}
```

## State Management

### Server State (TanStack Query)
```typescript
// For data from API
const { data } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers
})
```

### Client State (React Context)
```typescript
// For UI state, theme, auth
const ThemeContext = createContext<ThemeContextValue>({})

export const ThemeProvider = ({ children }: Props) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}
```

## Error Handling

### API Error Boundaries
```typescript
const { data, error } = useUsers({})

if (error) {
  return <ErrorDisplay message={error.message} />
}
```

### React Error Boundaries
```typescript
class ErrorBoundary extends React.Component<Props, State> {
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />
    }
    return this.props.children
  }
}
```

## Testing

### Component Tests
```typescript
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UsersList } from '../users-list'

test('renders users list', async () => {
  const queryClient = new QueryClient()

  render(
    <QueryClientProvider client={queryClient}>
      <UsersList />
    </QueryClientProvider>
  )

  expect(screen.getByText(/users/i)).toBeInTheDocument()
})
```

### Hook Tests
```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useUsers } from '../use-users'

test('fetches users', async () => {
  const queryClient = new QueryClient()
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  const { result } = renderHook(() => useUsers({}), { wrapper })

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toHaveLength(2)
})
```

## Best Practices

### 1. Co-locate Feature Code
✅ Group by feature (users/, auth/)
❌ Group by type (components/, hooks/, api/)

### 2. Export Query Options
✅ Enables server-side prefetching
```typescript
export const getUsersQueryOptions = () => { ... }
```

### 3. Use Generated Types
✅ Import from `shared-types`
❌ Manually define API types

### 4. Invalidate on Mutation
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['users'] })
}
```

### 5. Handle Loading States
```typescript
if (isLoading) return <Spinner />
if (error) return <Error />
```
