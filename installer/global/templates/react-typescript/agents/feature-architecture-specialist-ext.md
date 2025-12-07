# feature-architecture-specialist - Extended Reference

This file contains detailed documentation for the `feature-architecture-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/feature-architecture-specialist-ext.md
```


## Code Patterns

### Feature API Layer
```typescript
// features/discussions/api/get-discussions.ts
export const getDiscussions = (...) => { ... };
export const getDiscussionsQueryOptions = (...) => { ... };
export const useDiscussions = (...) => { ... };
```

### Feature Component Layer
```typescript
// features/discussions/components/discussions-list.tsx
export const DiscussionsList = () => {
  // Uses API from same feature
  const discussions = useDiscussions();
  // Uses shared UI components
  return <Table data={discussions} />;
};
```

### Cross-Feature Communication
```typescript
// ❌ DON'T: Import components from other features
import { UserAvatar } from '@/features/users/components/user-avatar';

// ✅ DO: Extract shared component
import { Avatar } from '@/components/ui/avatar';

// ❌ DON'T: Import API from other features
import { useUser } from '@/features/users/api/get-user';

// ✅ DO: Use shared context or pass as prop
const user = useAuth(); // from lib/auth
```

### 1. Feature Boundaries
- Each feature represents a distinct domain capability
- Features should be independently testable
- Feature code should be loosely coupled
- Features communicate through well-defined interfaces

### 2. Naming Conventions
- Feature names: singular, lowercase, kebab-case (e.g., `discussion`)
- API files: `{action}-{entity}.ts` (e.g., `get-discussions.ts`)
- Component files: `{entity}-{purpose}.tsx` (e.g., `discussions-list.tsx`)
- Test files: co-located in `__tests__/` subdirectory

### 3. Feature Size Guidelines
- Small feature: 1-5 files (< 500 LOC total)
- Medium feature: 5-15 files (500-2000 LOC)
- Large feature: 15+ files (consider splitting)

If a feature grows too large, consider:
- Splitting into multiple features
- Extracting shared sub-features
- Creating feature sub-modules

### 4. Testing Strategy
- Unit tests: Co-located in feature `__tests__/` folder
- Integration tests: Test feature as a whole
- E2E tests: Test feature in context of full app


## Anti-Patterns to Avoid

1. ❌ Organizing by technical layer (all APIs together, all components together)
2. ❌ Circular dependencies between features
3. ❌ Leaking feature implementation details
4. ❌ Creating "kitchen sink" utils features
5. ❌ Mixing feature code with infrastructure code
6. ❌ Creating dependencies on other features' internal structure


## Technology Stack Context
- React 18.3+ (component architecture)
- TypeScript 5.4+ (strong typing for boundaries)
- React Router 7.0+ (feature-based routes)
- Feature-based folder structure


## Example Structure

```
src/
  ├── features/
  │   ├── discussions/        # Discussion feature
  │   │   ├── api/
  │   │   │   ├── get-discussions.ts
  │   │   │   ├── get-discussion.ts
  │   │   │   ├── create-discussion.ts
  │   │   │   ├── update-discussion.ts
  │   │   │   └── delete-discussion.ts
  │   │   ├── components/
  │   │   │   ├── discussions-list.tsx
  │   │   │   ├── discussion-view.tsx
  │   │   │   ├── create-discussion.tsx
  │   │   │   ├── update-discussion.tsx
  │   │   │   └── delete-discussion.tsx
  │   │   └── __tests__/
  │   │       ├── discussions.test.tsx
  │   │       └── discussion.test.tsx
  │   ├── comments/           # Comments feature
  │   │   └── ... (similar structure)
  │   └── auth/               # Auth feature
  │       └── ... (similar structure)
  ├── components/             # Shared components
  │   ├── ui/                 # Design system components
  │   └── layouts/            # Layout components
  ├── lib/                    # Shared libraries
  │   ├── api-client.ts
  │   ├── react-query.ts
  │   └── authorization.tsx
  └── app/                    # App routes
      └── routes/
          └── app/
              └── discussions/  # Feature routes
                  ├── discussions.tsx
                  └── discussion.tsx
```


## Related Templates

This agent works with the following templates organized by feature layer:

### API Layer Templates
- **`templates/api/get-entities.ts.template`** - TanStack Query hook for fetching entity lists with pagination, filtering, and caching
- **`templates/api/get-entity.ts.template`** - Single entity fetch hook with error handling and stale-while-revalidate
- **`templates/api/create-entity.ts.template`** - Mutation hook with Zod validation, optimistic updates, and cache invalidation
- **`templates/api/update-entity.ts.template`** - Update mutation with partial data support and query cache management
- **`templates/api/delete-entity.ts.template`** - Delete mutation with confirmation patterns and list cache updates

### Component Layer Templates
- **`templates/components/entities-list.tsx.template`** - List component with Table, loading states, empty states, and prefetching on row hover
- **`templates/components/create-entity.tsx.template`** - Creation form with FormDrawer, validation, and submission handling
- **`templates/components/update-entity.tsx.template`** - Update form with pre-filled data and optimistic UI updates
- **`templates/components/delete-entity.tsx.template`** - Delete confirmation modal with undo patterns

### Route Layer Templates
- **`templates/routes/entities.tsx.template`** - Route component with React Router data loader, suspense boundaries, and error handling

### Testing Layer Templates
- **`templates/mocks/entity-handlers.ts.template`** - MSW (Mock Service Worker) HTTP handlers for feature testing with realistic data

Each template demonstrates proper feature isolation, ensuring API hooks, components, and tests stay within feature boundaries.

---


## Template-Driven Code Examples

### Example 1: Complete Feature API Layer

```typescript
// features/products/api/get-products.ts
import { useQuery, queryOptions } from '@tanstack/react-query';
import { z } from 'zod';

const productSchema = z.object({
  id: z.string(),
  name: z.string(),
  price: z.number(),
  category: z.string(),
});

export type Product = z.infer<typeof productSchema>;

export const getProductsQueryOptions = () =>
  queryOptions({
    queryKey: ['products'],
    queryFn: async () => {
      const response = await fetch('/api/products');
      if (!response.ok) throw new Error('Failed to fetch products');
      const data = await response.json();
      return z.array(productSchema).parse(data);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

export const useProducts = () => useQuery(getProductsQueryOptions());
```

```typescript
// features/products/api/create-product.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

const createProductSchema = z.object({
  name: z.string().min(1, 'Name required'),
  price: z.number().positive('Price must be positive'),
  category: z.string().min(1, 'Category required'),
});

export type CreateProductInput = z.infer<typeof createProductSchema>;

export const useCreateProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateProductInput) => {
      const validated = createProductSchema.parse(input);
      const response = await fetch('/api/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(validated),
      });
      if (!response.ok) throw new Error('Failed to create product');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
};
```

**Why this works**: API layer stays within feature boundary, exports query options factory for route loaders, uses Zod for runtime validation.

---

### Example 2: List Component with Prefetching

```typescript
// features/products/components/products-list.tsx
import { useQueryClient } from '@tanstack/react-query';
import { Table } from '@/components/ui/table'; // ✅ Shared UI import OK
import { useProducts } from '../api/get-products';
import { getProductQueryOptions } from '../api/get-product';
import type { Product } from '../api/get-products';

export function ProductsList() {
  const { data: products, isLoading } = useProducts();
  const queryClient = useQueryClient();

  const prefetchProduct = (id: string) => {
    queryClient.prefetchQuery(getProductQueryOptions(id));
  };

  if (isLoading) return <div>Loading products...</div>;

  return (
    <Table>
      <Table.Header>
        <Table.Row>
          <Table.Head>Name</Table.Head>
          <Table.Head>Price</Table.Head>
          <Table.Head>Category</Table.Head>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {products?.map((product) => (
          <Table.Row
            key={product.id}
            onMouseEnter={() => prefetchProduct(product.id)}
          >
            <Table.Cell>{product.name}</Table.Cell>
            <Table.Cell>${product.price}</Table.Cell>
            <Table.Cell>{product.category}</Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table>
  );
}
```

**Why this works**: Component imports from feature's own API layer, uses shared UI components, implements prefetching for better UX.

---

### Example 3: Route with Data Loader

```typescript
// features/products/routes/products.tsx
import { useLoaderData } from 'react-router-dom';
import { queryClient } from '@/lib/query-client';
import { getProductsQueryOptions } from '../api/get-products';
import { ProductsList } from '../components/products-list';
import { CreateProduct } from '../components/create-product';

export const productsLoader = async () => {
  const query = getProductsQueryOptions();
  return queryClient.ensureQueryData(query);
};

export function ProductsRoute() {
  useLoaderData(); // Triggers suspense boundary

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Products</h1>
        <CreateProduct />
      </div>
      <ProductsList />
    </div>
  );
}
```

**Why this works**: Route exports loader using query options factory, ensures data before component renders, keeps route concerns within feature.

---

### Example 4: Cross-Feature Communication (Proper Pattern)

**❌ DON'T: Direct feature imports**
```typescript
// features/orders/components/order-details.tsx
import { Product } from '../../products/api/get-products'; // ❌ Cross-feature import
import { ProductCard } from '../../products/components/product-card'; // ❌ Cross-feature import
```

**✅ DO: Use shared types and components**
```typescript
// lib/types/product.ts (Shared location)
export interface ProductReference {
  id: string;
  name: string;
  price: number;
}

// features/orders/components/order-details.tsx
import { ProductReference } from '@/lib/types/product'; // ✅ Shared type
import { ProductCard } from '@/components/product-card'; // ✅ Shared component

export function OrderDetails({ order }: OrderDetailsProps) {
  const productRefs: ProductReference[] = order.items.map(item => ({
    id: item.productId,
    name: item.productName,
    price: item.price,
  }));

  return (
    <div>
      <h2>Order #{order.id}</h2>
      {productRefs.map(product => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
```

**Why this works**: Shared types live in `/lib`, shared components in `/components`, features remain independent and testable in isolation.

---

### Example 5: MSW Mock Handlers for Feature Testing

```typescript
// features/products/mocks/product-handlers.ts
import { http, HttpResponse } from 'msw';
import type { Product } from '../api/get-products';

const mockProducts: Product[] = [
  { id: '1', name: 'Widget', price: 29.99, category: 'Tools' },
  { id: '2', name: 'Gadget', price: 49.99, category: 'Electronics' },
];

export const productHandlers = [
  http.get('/api/products', () => {
    return HttpResponse.json(mockProducts);
  }),

  http.get('/api/products/:id', ({ params }) => {
    const product = mockProducts.find(p => p.id === params.id);
    if (!product) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(product);
  }),

  http.post('/api/products', async ({ request }) => {
    const body = await request.json();
    const newProduct: Product = {
      id: Math.random().toString(),
      ...body,
    };
    return HttpResponse.json(newProduct, { status: 201 });
  }),
];
```

```typescript
// features/products/__tests__/products-list.test.tsx
import { render, screen } from '@/test/utils';
import { setupServer } from 'msw/node';
import { productHandlers } from '../mocks/product-handlers';
import { ProductsList } from '../components/products-list';

const server = setupServer(...productHandlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('renders product list', async () => {
  render(<ProductsList />);
  expect(await screen.findByText('Widget')).toBeInTheDocument();
  expect(await screen.findByText('$29.99')).toBeInTheDocument();
});
```

**Why this works**: Mock handlers co-located with feature, use feature types, enable testing without backend, handlers can be composed in integration tests.

---


## Feature Creation Checklist

When creating a new feature from scratch, follow this checklist:

### 1. Create Directory Structure
```bash
features/
  your-feature/
    api/
    components/
    hooks/
    types/
    utils/
    mocks/
    __tests__/
    index.ts
```

### 2. Create API Layer Files
- [ ] **GET list hook** - Use `templates/api/get-entities.ts.template`
  - Define Zod schema for entity shape
  - Export `getYourEntitiesQueryOptions()` factory
  - Export `useYourEntities()` hook
  - Set appropriate `staleTime` based on data volatility

- [ ] **GET single hook** - Use `templates/api/get-entity.ts.template`
  - Add ID parameter handling
  - Include error handling for 404s
  - Export query options for route loaders

- [ ] **POST mutation** - Use `templates/api/create-entity.ts.template`
  - Define input Zod schema with validation rules
  - Implement cache invalidation in `onSuccess`
  - Add optimistic update if needed

- [ ] **PATCH mutation** - Use `templates/api/update-entity.ts.template`
  - Support partial updates
  - Update cache with `queryClient.setQueryData`

- [ ] **DELETE mutation** - Use `templates/api/delete-entity.ts.template`
  - Add confirmation logic
  - Remove from list cache in `onSuccess`

### 3. Create Component Files
- [ ] **List component** - Use `templates/components/entities-list.tsx.template`
  - Import from feature's API layer only
  - Add loading/empty/error states
  - Implement prefetching on hover
  - Use shared UI components from `/components/ui`

- [ ] **Create form** - Use `templates/components/create-entity.tsx.template`
  - Use FormDrawer or Dialog for modal UX
  - Connect to mutation hook
  - Handle submission states (loading, error, success)

- [ ] **Update form** - Use `templates/components/update-entity.tsx.template`
  - Pre-fill form with existing data
  - Show optimistic updates

- [ ] **Delete confirmation** - Use `templates/components/delete-entity.tsx.template`
  - Add confirmation dialog
  - Show deletion in progress state

### 4. Create Route File
- [ ] **Route component** - Use `templates/routes/entities.tsx.template`
  - Export loader function using query options factory
  - Compose feature components
  - Add suspense boundaries
  - Add error boundaries

### 5. Create Mock Handlers
- [ ] **MSW handlers** - Use `templates/mocks/entity-handlers.ts.template`
  - Define mock data using feature types
  - Handle all CRUD endpoints
  - Add realistic delays with `delay()` if needed
  - Export handlers array

### 6. Add Tests
- [ ] **Component tests** - Co-locate in `__tests__/` directory
  - Test list rendering with mock data
  - Test create/update/delete flows
  - Test loading and error states
  - Use feature's mock handlers

### 7. Export Public API
```typescript
// features/your-feature/index.ts
export { YourFeatureRoute } from './routes/your-feature';
export { yourFeatureLoader } from './routes/your-feature';
// Only export types/utils needed by other features
```

### 8. Register Route
```typescript
// app/router.tsx
import { YourFeatureRoute, yourFeatureLoader } from '@/features/your-feature';

const router = createBrowserRouter([
  {
    path: '/your-feature',
    element: <YourFeatureRoute />,
    loader: yourFeatureLoader,
  },
]);
```

---


## Feature Architecture Anti-Patterns

### 1. Cross-Feature Component Imports

**NEVER import components directly from other features:**

```typescript
// features/orders/components/order-details.tsx
// ❌ BAD: Direct cross-feature import
import { ProductImage } from '../../products/components/product-image';
import { useProduct } from '../../products/api/get-product';
```

**ALWAYS use shared components or duplicate:**

```typescript
// components/product-image.tsx (Shared location)
export function ProductImage({ src, alt }: Props) {
  return <img src={src} alt={alt} className="rounded-md" />;
}

// features/orders/components/order-details.tsx
// ✅ GOOD: Import from shared location
import { ProductImage } from '@/components/product-image';
```

### 2. Cross-Feature API Hook Imports

**NEVER import API hooks from other features:**

```typescript
// ❌ BAD: Using products feature's API hook
import { useProduct } from '../../products/api/get-product';
```

**ALWAYS pass data down or use shared API layer:**

```typescript
// ✅ GOOD: Feature's own API returns all needed data
export const useCart = () =>
  useQuery({
    queryKey: ['cart'],
    queryFn: async () => {
      const response = await fetch('/api/cart');
      return response.json(); // Returns products with items
    },
  });
```

### 3. Kitchen Sink Features

**NEVER create catch-all features:**

```typescript
// ❌ BAD: "common" feature with unrelated concerns
features/
  common/
    components/
      user-avatar.tsx
      product-card.tsx
      order-status.tsx
```

**ALWAYS create focused features or truly shared locations:**

```typescript
// ✅ GOOD: Domain-specific features
features/
  auth/
    components/user-avatar.tsx
  products/
    components/product-card.tsx
```

### 4. Circular Feature Dependencies

**NEVER create circular dependencies between features:**

```typescript
// ❌ BAD: Circular dependency
// products imports from orders
import { OrdersForProduct } from '../../orders';

// orders imports from products
import { ProductsForOrder } from '../../products';
```

**ALWAYS use unidirectional data flow or shared state.**

### 5. Exporting Everything

**NEVER export internal implementation details:**

```typescript
// ❌ BAD: Exporting internals
export * from './components/product-list';
export * from './hooks/use-product-form-state';
```

**ALWAYS export only public API:**

```typescript
// ✅ GOOD: Minimal public API
export { ProductsRoute, productsLoader } from './routes/products';
export type { Product } from './api/get-products';
```

---


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat feature-architecture-specialist-ext.md
```

Or in Claude Code:
```
Please read feature-architecture-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat feature-architecture-specialist-ext.md
```

Or in Claude Code:
```
Please read feature-architecture-specialist-ext.md for detailed examples.
```
