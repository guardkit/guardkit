# react-query-specialist - Extended Reference

This file contains detailed documentation for the `react-query-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/react-query-specialist-ext.md
```


## Code Patterns

### Query Options Factory Pattern

See [Query Options Factory](#query-options-factory-pattern-1) below for the complete pattern with detailed explanation.

### Mutation with Cache Invalidation
```typescript
export const useCreateEntity = ({ mutationConfig }: Options = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getEntitiesQueryOptions().queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: createEntity,
  });
};
```

### Prefetching Pattern

See [Prefetch on Hover for Performance](#-do-prefetch-on-hover-for-performance) below for the complete pattern with detailed explanation.


## Anti-Patterns to Avoid

1. ❌ Hardcoding query keys inline (use query options factory)
2. ❌ Forgetting to invalidate queries after mutations
3. ❌ Over-invalidating queries (be specific with query keys)
4. ❌ Not handling loading/error states
5. ❌ Using useEffect for data fetching (use query loaders instead)


## Technology Stack Context
- TanStack Query v5.32+
- React 18.3+
- TypeScript 5.4+
- React Router 7.0+ (for loader integration)


## Example Implementation

See template files:
- `templates/api/get-entities.ts.template` - Query with pagination
- `templates/api/get-entity.ts.template` - Single entity query
- `templates/api/create-entity.ts.template` - Mutation with invalidation
- `templates/api/update-entity.ts.template` - Mutation with refetch
- `templates/api/delete-entity.ts.template` - Delete mutation


## Related Templates

This specialist works with the following React Query templates:

### Query Templates
- **templates/api/get-entities.ts.template** - List queries with pagination using queryOptions factory pattern
- **templates/api/get-entity.ts.template** - Single entity queries with queryOptions for detail views

### Mutation Templates
- **templates/api/create-entity.ts.template** - Create mutations with Zod validation and cache invalidation
- **templates/api/update-entity.ts.template** - Update mutations with targeted refetch strategies
- **templates/api/delete-entity.ts.template** - Delete mutations with list invalidation patterns

### Component Integration
- **templates/components/entities-list.tsx.template** - List components with prefetching on hover
- **templates/components/create-entity.tsx.template** - Form components with mutation hooks
- **templates/components/update-entity.tsx.template** - Update forms with optimistic updates
- **templates/components/delete-entity.tsx.template** - Delete confirmations with cache management

---


## Template Code Examples

### ✅ DO: Use queryOptions Factory Pattern

```typescript
import { queryOptions, useQuery } from '@tanstack/react-query';

// Define queryOptions factory for reusability
export const getDiscussionsQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['discussions', { page }] : ['discussions'],
    queryFn: () => getDiscussions(page),
  });
};

// Use in hook with config overrides
export const useDiscussions = ({ page, queryConfig }: UseDiscussionsOptions) => {
  return useQuery({
    ...getDiscussionsQueryOptions({ page }),
    ...queryConfig,
  });
};
```

**Why**: queryOptions factories enable type-safe key sharing across queries, mutations, and prefetching.

### ❌ DON'T: Duplicate Query Keys

```typescript
// BAD - Keys can drift out of sync
export const useDiscussions = () => {
  return useQuery({
    queryKey: ['discussions'],
    queryFn: getDiscussions,
  });
};

// Later in mutation - WRONG KEY!
queryClient.invalidateQueries({ queryKey: ['discussion'] });
```

---

### ✅ DO: Cache Invalidation in Mutations

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';

export const useCreateDiscussion = ({ mutationConfig }: Options = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    mutationFn: createDiscussion,
    onSuccess: (...args) => {
      // Invalidate list to show new item
      queryClient.invalidateQueries({
        queryKey: getDiscussionsQueryOptions().queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
  });
};
```

**Why**: Invalidation ensures list queries refetch to include newly created items.

### ❌ DON'T: Forget to Preserve Custom onSuccess

```typescript
// BAD - Overwrites caller's onSuccess callback
return useMutation({
  mutationFn: createDiscussion,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['discussions'] });
    // Custom callback lost!
  },
});
```

---

### ✅ DO: Refetch vs Invalidate for Updates

```typescript
export const useUpdateDiscussion = ({ mutationConfig }: Options = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    mutationFn: updateDiscussion,
    onSuccess: (data, ...args) => {
      // Refetch specific item (we know it changed)
      queryClient.refetchQueries({
        queryKey: getDiscussionQueryOptions(data.id).queryKey,
      });
      onSuccess?.(data, ...args);
    },
    ...restConfig,
  });
};
```

**Why**: `refetchQueries` is more precise than `invalidateQueries` when you know exactly which data changed.

### ❌ DON'T: Invalidate Everything

```typescript
// BAD - Refetches all queries unnecessarily
queryClient.invalidateQueries(); // No queryKey!
```

---

### ✅ DO: Prefetch on Hover for Performance

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { getDiscussionQueryOptions } from '@/features/discussions/api/get-discussion';

export const DiscussionsList = () => {
  const queryClient = useQueryClient();

  return (
    <Link
      onMouseEnter={() => {
        // Prefetch detail view before navigation
        queryClient.prefetchQuery(getDiscussionQueryOptions(discussion.id));
      }}
      to={`/discussions/${discussion.id}`}
    >
      {discussion.title}
    </Link>
  );
};
```

**Why**: Prefetching on hover eliminates loading states when users click, improving perceived performance.

### ❌ DON'T: Prefetch Without queryOptions

```typescript
// BAD - Keys don't match, cache miss on navigation
queryClient.prefetchQuery({
  queryKey: ['discussion', id], // Wrong structure!
  queryFn: () => getDiscussion(id),
});
```

---

### ✅ DO: Validate Input with Zod Before Mutation

```typescript
import { z } from 'zod';

export const createDiscussionInputSchema = z.object({
  title: z.string().min(1, 'Required'),
  body: z.string().min(1, 'Required'),
});

type CreateDiscussionInput = z.infer<typeof createDiscussionInputSchema>;

export const createDiscussion = ({ data }: { data: CreateDiscussionInput }) => {
  return api.post('/discussions', data);
};
```

**Why**: Zod schemas provide type safety and runtime validation, preventing invalid API requests.

---


## Template Best Practices

### Query Key Architecture

✅ **Always use queryOptions factories** for every query to ensure key consistency across:
- Hook definitions (`useDiscussions`)
- Prefetching (`queryClient.prefetchQuery`)
- Cache invalidation (`queryClient.invalidateQueries`)
- Cache updates (`queryClient.setQueryData`)

✅ **Structure keys hierarchically**: `['discussions']` for lists, `['discussion', id]` for details

✅ **Include pagination params in keys**: `['discussions', { page: 2 }]` ensures separate cache entries

### Mutation Patterns

✅ **Create mutations**: Invalidate list queries to trigger refetch
```typescript
queryClient.invalidateQueries({
  queryKey: getDiscussionsQueryOptions().queryKey,
});
```

✅ **Update mutations**: Refetch specific item query (more efficient than invalidation)
```typescript
queryClient.refetchQueries({
  queryKey: getDiscussionQueryOptions(data.id).queryKey,
});
```

✅ **Delete mutations**: Invalidate list queries to remove deleted items from view
```typescript
queryClient.invalidateQueries({
  queryKey: getDiscussionsQueryOptions().queryKey,
});
```

✅ **Preserve caller callbacks**: Destructure and chain `onSuccess`, `onError`, `onSettled`
```typescript
const { onSuccess, ...restConfig } = mutationConfig || {};
onSuccess: (...args) => {
  // Internal cache logic
  onSuccess?.(...args); // Call custom callback
}
```

### Performance Optimization

✅ **Prefetch on hover**: Use `queryClient.prefetchQuery` in `onMouseEnter` handlers

✅ **Share queryOptions**: Export factories from API files, import in components

✅ **Allow query config overrides**: Spread `queryConfig` parameter for custom `staleTime`, `gcTime`, etc.

### Type Safety

✅ **Define input schemas with Zod**: Export schemas and infer types with `z.infer`

✅ **Type API responses**: Use generic types for consistent response shapes

✅ **Export hook options types**: Create `UseDiscussionsOptions` types for better IntelliSense

---


## Template Anti-Patterns

### ❌ NEVER: Hardcode Query Keys

```typescript
// BAD - Keys duplicated across files
const { data } = useQuery({
  queryKey: ['discussions'],
  queryFn: getDiscussions,
});

// Later in another file - typo causes cache miss!
queryClient.invalidateQueries({ queryKey: ['discussion'] });
```

**Fix**: Always use queryOptions factories exported from API files.

### ❌ NEVER: Invalidate Without queryKey

```typescript
// BAD - Refetches ALL queries in the app
queryClient.invalidateQueries();
```

**Fix**: Always specify `queryKey` to target specific queries.

### ❌ NEVER: Mutate Cache Directly Without Type Safety

```typescript
// BAD - No validation, can corrupt cache
queryClient.setQueryData(['discussions'], (old: any) => {
  return [...old, newItem]; // Type error waiting to happen
});
```

**Fix**: Use optimistic updates with proper typing or rely on invalidation/refetch.

### ❌ NEVER: Ignore Mutation Errors

```typescript
// BAD - No error handling
const mutation = useMutation({
  mutationFn: createDiscussion,
});
```

**Fix**: Always handle errors with `onError` callback or error boundaries.

### ❌ NEVER: Prefetch With Different Keys

```typescript
// BAD - Prefetch key doesn't match hook key
queryClient.prefetchQuery({
  queryKey: ['discussion-detail', id],
  queryFn: () => getDiscussion(id),
});

// Hook uses different key - cache miss!
const { data } = useQuery({
  queryKey: ['discussion', id],
  queryFn: () => getDiscussion(id),
});
```

**Fix**: Share queryOptions factory between prefetch and hook.

### ❌ NEVER: Overwrite User Callbacks

```typescript
// BAD - Custom onSuccess lost
export const useCreateDiscussion = () => {
  return useMutation({
    mutationFn: createDiscussion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discussions'] });
      // Component's custom onSuccess ignored!
    },
  });
};
```

**Fix**: Accept `mutationConfig`, destructure callbacks, chain with `?.()` operator.

### ❌ NEVER: Use Stale Closures in Callbacks

```typescript
// BAD - `page` value may be stale
const [page, setPage] = useState(1);

const mutation = useMutation({
  mutationFn: createDiscussion,
  onSuccess: () => {
    queryClient.invalidateQueries({
      queryKey: ['discussions', { page }], // Stale closure!
    });
  },
});
```

**Fix**: Invalidate broader key or use updater function with current state.


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat react-query-specialist-ext.md
```

Or in Claude Code:
```
Please read react-query-specialist-ext.md for detailed examples.
```
