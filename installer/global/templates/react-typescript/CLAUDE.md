# React TypeScript Template - Feature-Based Architecture

## Project Context

This template provides a production-ready foundation for React applications using TypeScript, Vite, and feature-based architecture. Based on Bulletproof React (28.5k+ stars), it emphasizes scalability, type safety, and developer experience.

## Core Principles

1. **Feature-Based Organization**: Code organized by domain features, not technical layers
2. **Type Safety First**: Leverage TypeScript for compile-time guarantees
3. **Server State Management**: TanStack Query for efficient data fetching and caching
4. **Component Composition**: Build UIs from small, reusable components
5. **Testing at Every Level**: Unit, integration, and E2E tests co-located with code

## Architecture Overview

### Feature-Based Structure

Features are organized as independent modules containing all related code:

```
features/
  └── {feature-name}/
      ├── api/              # Data fetching and mutations
      ├── components/       # Feature-specific UI
      ├── hooks/            # Custom hooks (optional)
      ├── types/            # Feature types (optional)
      └── __tests__/        # Tests
```

**Benefits:**
- Loose coupling between features
- Easy to locate and modify feature code
- Clear boundaries and responsibilities
- Scalable as application grows

### Layers

1. **Features Layer** (`src/features/`): Domain-specific business logic and UI
2. **Components Layer** (`src/components/`): Shared, reusable UI components
3. **App Layer** (`src/app/`): Application routes and global layout
4. **Lib Layer** (`src/lib/`): Shared utilities and infrastructure

### Data Flow

```
User Interaction
      ↓
  Component
      ↓
Custom Hook (useQuery/useMutation)
      ↓
  API Function
      ↓
API Client (Axios)
      ↓
  Backend
```

## Technology Stack

### Core
- **React 18.3**: UI library with concurrent features
- **TypeScript 5.4+**: Static typing and enhanced IDE support
- **Vite 5.2**: Fast build tool and dev server

### State Management
- **TanStack Query 5.32**: Server state management and caching
- **Zustand 4.5**: Client state management (when needed)

### Routing
- **React Router 7.0**: Declarative routing with data loaders

### Styling
- **Tailwind CSS 3.4**: Utility-first CSS framework
- **Radix UI**: Headless, accessible UI components
- **class-variance-authority**: Variant-based component styling
- **tailwind-merge**: Intelligent Tailwind class merging

### Forms & Validation
- **React Hook Form 7.51**: Performant form state management
- **Zod 3.23**: TypeScript-first schema validation

### Testing
- **Vitest 2.1**: Fast unit testing with Vite
- **Testing Library**: User-centric testing utilities
- **Playwright 1.43**: Reliable E2E testing
- **MSW 2.2**: API mocking for tests and development

### Developer Experience
- **ESLint**: Code linting and style enforcement
- **Prettier**: Opinionated code formatting
- **Husky**: Git hooks for quality checks
- **TypeScript ESLint**: TypeScript-specific linting rules

## Project Structure

```
src/
├── app/                    # Application setup and routing
│   ├── index.tsx          # App entry point
│   ├── provider.tsx       # Global providers
│   ├── router.tsx         # Route definitions
│   └── routes/            # Route components
│       ├── app/           # Protected app routes
│       ├── auth/          # Authentication routes
│       ├── landing.tsx    # Landing page
│       └── not-found.tsx  # 404 page
│
├── features/              # Feature modules
│   ├── auth/             # Authentication feature
│   ├── discussions/      # Discussions feature
│   ├── comments/         # Comments feature
│   ├── users/            # Users feature
│   └── teams/            # Teams feature
│
├── components/           # Shared components
│   ├── ui/              # Design system components
│   │   ├── button/
│   │   ├── form/
│   │   ├── table/
│   │   └── ...
│   └── layouts/         # Layout components
│
├── lib/                 # Shared libraries
│   ├── api-client.ts   # Axios instance and interceptors
│   ├── react-query.ts  # Query client configuration
│   └── authorization.tsx # Authorization utilities
│
├── utils/              # Utility functions
│   ├── cn.ts          # Class name utilities
│   └── format.ts      # Formatting utilities
│
├── types/             # Global type definitions
│   └── api.ts        # API response types
│
├── config/           # Configuration
│   ├── env.ts       # Environment variables
│   └── paths.ts     # Route path definitions
│
├── testing/         # Testing utilities
│   └── mocks/      # MSW mock handlers
│       ├── db.ts
│       ├── utils.ts
│       └── handlers/
│
└── main.tsx        # Application entry point
```

## Naming Conventions

### Files
- **Components**: `kebab-case.tsx` (export: `PascalCase`)
  - Example: `discussions-list.tsx` → `export const DiscussionsList`
- **Hooks**: `use-hook-name.ts` or `useHookName.ts`
  - Example: `use-discussions.ts` → `export const useDiscussions`
- **API Files**: `{action}-{entity}.ts`
  - Example: `get-discussions.ts`, `create-discussion.ts`
- **Types**: `types.ts` or co-located with usage
- **Tests**: `{filename}.test.tsx` in `__tests__/` subdirectory

### Code
- **Components**: `PascalCase`
- **Hooks**: `camelCase` with `use` prefix
- **Functions**: `camelCase`
- **Constants**: `SCREAMING_SNAKE_CASE` or `camelCase`
- **Types/Interfaces**: `PascalCase`

### Features
- **Feature folders**: Singular, lowercase, kebab-case
  - Example: `discussion/`, `comment/`, `user/`
- **API endpoints**: Match feature name (singular or plural based on operation)
  - Example: `/discussions` (list), `/discussions/:id` (single)

## Patterns and Best Practices

### 1. Feature Organization

Each feature is self-contained:

```typescript
// features/discussions/api/get-discussions.ts
export const getDiscussions = (page = 1) => {
  return api.get(`/discussions`, { params: { page } });
};

export const getDiscussionsQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['discussions', { page }] : ['discussions'],
    queryFn: () => getDiscussions(page),
  });
};

export const useDiscussions = ({ page, queryConfig }: Options) => {
  return useQuery({
    ...getDiscussionsQueryOptions({ page }),
    ...queryConfig,
  });
};
```

### 2. Query Options Factory Pattern

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

### 3. Mutations with Cache Invalidation

Invalidate queries after successful mutations:

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

### 4. Form Validation with Zod

Define schemas co-located with API mutations:

```typescript
// API layer
export const createDiscussionInputSchema = z.object({
  title: z.string().min(1, 'Required'),
  body: z.string().min(1, 'Required'),
});

export type CreateDiscussionInput = z.infer<typeof createDiscussionInputSchema>;

// Component layer
<Form
  id="create-discussion"
  onSubmit={(values) => createMutation.mutate({ data: values })}
  schema={createDiscussionInputSchema}
>
  {({ register, formState }) => (
    <>
      <Input
        label="Title"
        error={formState.errors['title']}
        registration={register('title')}
      />
      <Textarea
        label="Body"
        error={formState.errors['body']}
        registration={register('body')}
      />
    </>
  )}
</Form>
```

### 5. Component Variants with CVA

Create flexible, type-safe component variants:

```typescript
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground',
        outline: 'border border-input bg-background hover:bg-accent',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3',
        lg: 'h-10 rounded-md px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;
```

### 6. Authorization Patterns

Role-based and policy-based authorization:

```typescript
// Role-based
<Authorization allowedRoles={[ROLES.ADMIN]}>
  <CreateDiscussion />
</Authorization>

// Policy-based
const canDelete = POLICIES['comment:delete'](user, comment);

<Authorization policyCheck={canDelete}>
  <DeleteComment id={comment.id} />
</Authorization>
```

### 7. API Mocking with MSW

Mock API responses for development and testing:

```typescript
// testing/mocks/handlers/discussions.ts
export const discussionsHandlers = [
  http.get(`${env.API_URL}/discussions`, async ({ cookies, request }) => {
    const { user } = requireAuth(cookies);
    const url = new URL(request.url);
    const page = Number(url.searchParams.get('page') || 1);

    const discussions = db.discussion.findMany({
      where: { teamId: { equals: user?.teamId } },
      take: 10,
      skip: 10 * (page - 1),
    });

    return HttpResponse.json({
      data: discussions,
      meta: { page, total: discussions.length, totalPages: Math.ceil(discussions.length / 10) },
    });
  }),
];
```

### 8. Path Aliases

Use path aliases for clean imports:

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}

// Import usage
import { Button } from '@/components/ui/button';
import { useDiscussions } from '@/features/discussions/api/get-discussions';
import { formatDate } from '@/utils/format';
```

## Code Examples

### Creating a New Feature

1. **Create feature directory structure**:
```bash
mkdir -p src/features/products/{api,components,__tests__}
```

2. **Create API layer** (`api/get-products.ts`):
```typescript
import { queryOptions, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import { QueryConfig } from '@/lib/react-query';
import { Product, Meta } from '@/types/api';

export const getProducts = (page = 1): Promise<{ data: Product[]; meta: Meta }> => {
  return api.get(`/products`, { params: { page } });
};

export const getProductsQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['products', { page }] : ['products'],
    queryFn: () => getProducts(page),
  });
};

export const useProducts = ({ page, queryConfig }: UseProductsOptions) => {
  return useQuery({
    ...getProductsQueryOptions({ page }),
    ...queryConfig,
  });
};
```

3. **Create component** (`components/products-list.tsx`):
```typescript
import { useSearchParams } from 'react-router';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { useProducts } from '../api/get-products';

export const ProductsList = () => {
  const [searchParams] = useSearchParams();
  const productsQuery = useProducts({
    page: +(searchParams.get('page') || 1),
  });

  if (productsQuery.isLoading) {
    return <Spinner size="lg" />;
  }

  const products = productsQuery.data?.data;

  return <Table data={products} columns={[/* ... */]} />;
};
```

4. **Add route** (`app/routes/app/products.tsx`):
```typescript
import { ContentLayout } from '@/components/layouts';
import { ProductsList } from '@/features/products/components/products-list';

const ProductsRoute = () => {
  return (
    <ContentLayout title="Products">
      <ProductsList />
    </ContentLayout>
  );
};

export default ProductsRoute;
```

## Quality Standards

### Code Quality
- **Type Safety**: No `any` types (use `unknown` when necessary)
- **Linting**: Pass all ESLint rules (including TypeScript rules)
- **Formatting**: Prettier-formatted code
- **Naming**: Consistent naming conventions
- **Imports**: Organized imports (built-in → external → internal)

### Testing
- **Unit Tests**: ≥80% line coverage for utilities and hooks
- **Component Tests**: All components have basic render tests
- **Integration Tests**: Feature flows are tested end-to-end
- **E2E Tests**: Critical user journeys are covered

### Performance
- **Bundle Size**: Monitor and optimize bundle size
- **Code Splitting**: Use dynamic imports for routes
- **Query Optimization**: Appropriate stale times and cache strategies
- **Prefetching**: Prefetch data on hover or route transitions

### Accessibility
- **Semantic HTML**: Use appropriate HTML elements
- **ARIA Attributes**: Proper ARIA labels and roles
- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Color Contrast**: Meet WCAG AA standards

## Testing Strategy

### Unit Tests (Vitest)
```typescript
// features/discussions/__tests__/discussions-list.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { DiscussionsList } from '../components/discussions-list';

test('renders discussions list', async () => {
  render(<DiscussionsList />, { wrapper: AppProvider });

  await waitFor(() => {
    expect(screen.getByText('Discussion 1')).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright)
```typescript
// e2e/tests/discussions.spec.ts
import { test, expect } from '@playwright/test';

test('creates a new discussion', async ({ page }) => {
  await page.goto('/app/discussions');
  await page.click('text=Create Discussion');
  await page.fill('[name="title"]', 'Test Discussion');
  await page.fill('[name="body"]', 'Test body');
  await page.click('text=Submit');

  await expect(page.locator('text=Test Discussion')).toBeVisible();
});
```

### Mock Handlers (MSW)
```typescript
// testing/mocks/handlers/discussions.ts
import { http, HttpResponse } from 'msw';
import { env } from '@/config/env';
import { db } from '../db';

export const discussionsHandlers = [
  http.get(`${env.API_URL}/discussions`, async ({ cookies }) => {
    const discussions = db.discussion.findMany();
    return HttpResponse.json({
      data: discussions,
      meta: { page: 1, total: discussions.length, totalPages: 1 },
    });
  }),
];
```

## Specialized Agents

This template includes custom agents for React TypeScript patterns:

### 1. **react-query-specialist**
- Implements TanStack Query patterns
- Query options factory pattern
- Cache invalidation strategies
- Prefetching and optimistic updates

### 2. **feature-architecture-specialist**
- Feature-based organization
- Feature boundaries and isolation
- Code placement decisions
- Cross-feature communication patterns

### 3. **form-validation-specialist**
- React Hook Form integration
- Zod schema validation
- Type-safe forms
- Error handling and display

**Usage**: These agents are automatically available when using the template. Reference them in tasks for specialized guidance.

## Development Workflow

### Starting Development
```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Run tests in watch mode
npm test

# Run E2E tests
npm run test-e2e
```

### Creating New Features
```bash
# Use Plop generator for scaffolding
npm run generate

# Or manually create feature structure
mkdir -p src/features/{feature-name}/{api,components,__tests__}
```

### Code Quality Checks
```bash
# Lint code
npm run lint

# Type check
npm run check-types

# Format code
npx prettier --write .
```

### Building for Production
```bash
# Build
npm run build

# Preview build
npm run preview
```

## Common Tasks

### Adding a New API Endpoint
1. Create API file in `features/{feature}/api/{action}-{entity}.ts`
2. Define function, query options, and custom hook
3. Add Zod schema if it's a mutation
4. Create MSW handler in `testing/mocks/handlers/`

### Adding a New Component
1. Create component file in `features/{feature}/components/` or `components/ui/`
2. Use shared UI components from `components/ui/`
3. Add tests in `__tests__/`
4. Export from feature or component index if needed

### Adding a New Route
1. Create route file in `app/routes/app/` or `app/routes/auth/`
2. Add route definition in `app/router.tsx`
3. Add path helper in `config/paths.ts`
4. Implement route loader for data prefetching

### Adding Form Validation
1. Define Zod schema in API file
2. Export inferred type using `z.infer`
3. Use schema in `<Form>` component
4. Handle validation errors in UI

## Environment Variables

```bash
# .env
VITE_API_URL=http://localhost:3000/api
VITE_APP_URL=http://localhost:5173
```

Access via:
```typescript
import { env } from '@/config/env';

const apiUrl = env.API_URL;
```

## Troubleshooting

### TypeScript Errors
- Run `npm run check-types` to see all type errors
- Check `tsconfig.json` for correct path mappings
- Ensure all dependencies have type definitions

### Query Not Updating
- Check query key is correct and includes all parameters
- Verify cache invalidation is called after mutations
- Use React Query DevTools to inspect cache

### Form Not Submitting
- Ensure form `id` matches submit button `form` attribute
- Check Zod schema is correct
- Verify mutation is properly connected

### MSW Not Mocking
- Ensure MSW is initialized (`mock-server.ts`)
- Check handler matches request URL exactly
- Verify `env.API_URL` is correct in handlers

## Additional Resources

- [Bulletproof React](https://github.com/alan2207/bulletproof-react) - Original inspiration
- [TanStack Query Docs](https://tanstack.com/query/latest) - Query patterns
- [React Hook Form Docs](https://react-hook-form.com/) - Form management
- [Zod Docs](https://zod.dev/) - Schema validation
- [Radix UI Docs](https://www.radix-ui.com/) - UI components
- [Tailwind CSS Docs](https://tailwindcss.com/) - Styling
- [Playwright Docs](https://playwright.dev/) - E2E testing



## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.

## Notes

- This template prioritizes scalability and maintainability over simplicity
- Feature-based architecture scales better than layer-based as apps grow
- Type safety prevents bugs at compile-time, not runtime
- Co-located tests improve discoverability and maintainability
- MSW provides consistent mocking across development and testing
