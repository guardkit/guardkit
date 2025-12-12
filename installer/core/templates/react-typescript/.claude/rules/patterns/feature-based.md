---
paths: ["src/features/**"]
---

# Feature-Based Architecture

Features are self-contained modules with clear boundaries, organized by domain rather than technical layers.

## Feature Structure

```
features/{feature-name}/
├── api/              # Data fetching and mutations
├── components/       # Feature-specific UI
├── hooks/            # Custom hooks (optional)
├── types/            # Feature types (optional)
└── __tests__/        # Tests
```

## Benefits

- **Loose coupling**: Features are independent and don't depend on each other
- **Easy maintenance**: All related code is co-located
- **Clear boundaries**: Each feature has well-defined responsibilities
- **Scalability**: Easy to add new features without affecting existing ones

## Feature Organization Pattern

Each feature should be self-contained with its own API layer, components, and tests:

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

## Creating a New Feature

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

## Layers

The application is organized into four layers:

1. **Features Layer** (`src/features/`): Domain-specific business logic and UI
2. **Components Layer** (`src/components/`): Shared, reusable UI components
3. **App Layer** (`src/app/`): Application routes and global layout
4. **Lib Layer** (`src/lib/`): Shared utilities and infrastructure

## Data Flow

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
