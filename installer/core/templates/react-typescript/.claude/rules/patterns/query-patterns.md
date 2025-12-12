---
paths: ["**/*query*", "**/*api*", "**/*fetch*", "**/api/**"]
---

# TanStack Query Patterns

Server state management patterns using TanStack Query for efficient data fetching, caching, and synchronization.

## Query Options Factory Pattern

Create reusable query options for prefetching and sharing:

```typescript
// API layer
export const getDiscussionQueryOptions = (id: string) => {
  return queryOptions({
    queryKey: ['discussion', id],
    queryFn: () => getDiscussion({ discussionId: id }),
  });
};

// Component layer - prefetching
queryClient.prefetchQuery(getDiscussionQueryOptions(id));

// Hook layer - using
const discussion = useQuery(getDiscussionQueryOptions(id));
```

## Mutations with Cache Invalidation

Invalidate queries after successful mutations to keep cache fresh:

```typescript
export const useCreateDiscussion = ({ mutationConfig }: Options = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getDiscussionsQueryOptions().queryKey,
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: createDiscussion,
  });
};
```

## Query Key Structure

Organize query keys hierarchically for efficient invalidation:

```typescript
// ✅ Good - hierarchical structure
['discussions']                    // All discussions
['discussions', { page: 1 }]       // Paginated discussions
['discussion', discussionId]       // Single discussion
['discussion', discussionId, 'comments']  // Discussion's comments

// ❌ Bad - flat structure
['discussions-page-1']
['discussion-123']
['discussion-123-comments']
```

### Benefits of Hierarchical Keys
- Invalidate all discussions: `queryKey: ['discussions']`
- Invalidate specific discussion: `queryKey: ['discussion', id]`
- Invalidate discussion and comments: `queryKey: ['discussion', id]`

## Optimistic Updates

Update UI immediately for better UX:

```typescript
export const useUpdateDiscussion = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateDiscussion,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ['discussion', variables.discussionId]
      });

      // Snapshot previous value
      const previous = queryClient.getQueryData([
        'discussion',
        variables.discussionId,
      ]);

      // Optimistically update
      queryClient.setQueryData(
        ['discussion', variables.discussionId],
        variables.data
      );

      return { previous };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      queryClient.setQueryData(
        ['discussion', variables.discussionId],
        context?.previous
      );
    },
    onSettled: (data, error, variables) => {
      // Refetch after mutation
      queryClient.invalidateQueries({
        queryKey: ['discussion', variables.discussionId],
      });
    },
  });
};
```

## Prefetching

Prefetch data on hover or route transitions:

```typescript
// Hover prefetching
<Link
  to={`/discussions/${discussion.id}`}
  onMouseEnter={() => {
    queryClient.prefetchQuery(
      getDiscussionQueryOptions(discussion.id)
    );
  }}
>
  {discussion.title}
</Link>

// Route loader prefetching (React Router 7)
export const loader = async ({ params }: LoaderFunctionArgs) => {
  const queryClient = getQueryClient();

  await queryClient.ensureQueryData(
    getDiscussionQueryOptions(params.id!)
  );

  return null;
};
```

## Stale Time Configuration

Configure appropriate stale times based on data volatility:

```typescript
// Fast-changing data (notifications, messages)
export const useNotifications = () => {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: getNotifications,
    staleTime: 30 * 1000, // 30 seconds
  });
};

// Slow-changing data (user profile, settings)
export const useUserProfile = () => {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: getUserProfile,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Static data (country list, categories)
export const useCountries = () => {
  return useQuery({
    queryKey: ['countries'],
    queryFn: getCountries,
    staleTime: Infinity, // Never stale
  });
};
```

## Error Handling

Handle errors gracefully with fallbacks:

```typescript
export const DiscussionView = () => {
  const { data, isLoading, error } = useDiscussion({ id });

  if (isLoading) {
    return <Spinner />;
  }

  if (error) {
    return (
      <ErrorFallback
        error={error}
        reset={() => queryClient.invalidateQueries(['discussion', id])}
      />
    );
  }

  return <DiscussionContent discussion={data} />;
};
```

## Common Patterns

### Pagination
```typescript
export const useDiscussions = ({ page }: { page: number }) => {
  return useQuery({
    queryKey: ['discussions', { page }],
    queryFn: () => getDiscussions(page),
    placeholderData: keepPreviousData, // Keep previous data while fetching
  });
};
```

### Infinite Scroll
```typescript
export const useInfiniteDiscussions = () => {
  return useInfiniteQuery({
    queryKey: ['discussions', 'infinite'],
    queryFn: ({ pageParam = 1 }) => getDiscussions(pageParam),
    getNextPageParam: (lastPage) => lastPage.meta.nextPage,
    initialPageParam: 1,
  });
};
```

### Dependent Queries
```typescript
export const useDiscussionComments = ({ discussionId }: { discussionId?: string }) => {
  return useQuery({
    queryKey: ['discussion', discussionId, 'comments'],
    queryFn: () => getComments(discussionId!),
    enabled: !!discussionId, // Only run when discussionId exists
  });
};
```

## Performance Optimization

- Use appropriate `staleTime` to reduce unnecessary refetches
- Implement prefetching for predictable navigation
- Use `placeholderData` for smoother transitions
- Configure `gcTime` to control cache retention
- Use React Query DevTools to inspect cache behavior
