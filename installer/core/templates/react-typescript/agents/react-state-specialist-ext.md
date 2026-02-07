# react-state-specialist - Extended Reference

This file contains detailed documentation for the `react-state-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/react-state-specialist-ext.md
```


## Implementation Patterns

### Custom Hook Pattern

```typescript
// Custom hook encapsulating business logic
export function useCounter(initialValue = 0) {
  const [count, setCount] = useState(initialValue);

  const increment = useCallback(() => setCount((c) => c + 1), []);
  const decrement = useCallback(() => setCount((c) => c - 1), []);
  const reset = useCallback(() => setCount(initialValue), [initialValue]);

  return { count, increment, decrement, reset };
}
```

### Context with Reducer Pattern

```typescript
import { createContext, useContext, useReducer, ReactNode } from 'react';

interface State {
  items: Item[];
  loading: boolean;
}

type Action =
  | { type: 'ADD_ITEM'; payload: Item }
  | { type: 'REMOVE_ITEM'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean };

const initialState: State = { items: [], loading: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'ADD_ITEM':
      return { ...state, items: [...state.items, action.payload] };
    case 'REMOVE_ITEM':
      return { ...state, items: state.items.filter((i) => i.id !== action.payload) };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    default:
      return state;
  }
}

const ItemContext = createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
} | null>(null);

export function ItemProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <ItemContext.Provider value={{ state, dispatch }}>
      {children}
    </ItemContext.Provider>
  );
}

export function useItems() {
  const context = useContext(ItemContext);
  if (!context) {
    throw new Error('useItems must be used within ItemProvider');
  }
  return context;
}
```

### TanStack Query with Prefetching

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

export function UserList() {
  const queryClient = useQueryClient();
  const { data: users } = useUsers();

  return (
    <ul>
      {users?.map((user) => (
        <li key={user.id}>
          <Link
            to={`/users/${user.id}`}
            onMouseEnter={() => {
              // Prefetch user details on hover
              queryClient.prefetchQuery(getUserQueryOptions(user.id));
            }}
          >
            {user.name}
          </Link>
        </li>
      ))}
    </ul>
  );
}
```

### Zustand Store with Actions

```typescript
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface CartState {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  clearCart: () => void;
  totalItems: () => number;
  totalPrice: () => number;
}

export const useCartStore = create<CartState>()(
  immer((set, get) => ({
    items: [],
    addItem: (item) =>
      set((state) => {
        const existing = state.items.find((i) => i.id === item.id);
        if (existing) {
          existing.quantity += item.quantity;
        } else {
          state.items.push(item);
        }
      }),
    removeItem: (id) =>
      set((state) => {
        state.items = state.items.filter((i) => i.id !== id);
      }),
    clearCart: () =>
      set((state) => {
        state.items = [];
      }),
    totalItems: () => get().items.reduce((sum, i) => sum + i.quantity, 0),
    totalPrice: () => get().items.reduce((sum, i) => sum + i.price * i.quantity, 0),
  }))
);
```

### State Location Decision

```
┌────────────────────────────────────────────────────────────┐
│                    State Location Guide                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Server data (async)?  ──────────────▶  TanStack Query    │
│                                                            │
│  Single component?     ──────────────▶  useState/useReducer│
│                                                            │
│  Few components (tree)?──────────────▶  Lift state + props │
│                                                            │
│  Many components?      ──────────────▶  Zustand / Context  │
│                                                            │
│  Complex workflows?    ──────────────▶  XState             │
│                                                            │
│  Form state?           ──────────────▶  React Hook Form    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Dependency Array Rules

```typescript
// ✅ GOOD: All dependencies included
const handleSubmit = useCallback(
  (data: FormData) => {
    onSubmit(data);
    setLoading(true);
  },
  [onSubmit] // setLoading is stable from useState
);

// ❌ BAD: Missing dependency
const handleSubmit = useCallback(
  (data: FormData) => {
    onSubmit(data); // onSubmit missing from deps!
  },
  [] // eslint-disable-next-line
);
```

### Avoiding Stale Closures

```typescript
// ✅ GOOD: Functional update
const increment = useCallback(() => {
  setCount((prev) => prev + 1);
}, []);

// ❌ BAD: Stale closure
const increment = useCallback(() => {
  setCount(count + 1); // count is stale if count changes
}, []); // count missing from deps
```


## Technology Stack Context

- React 18.3+
- TypeScript 5.4+
- TanStack Query v5.32+
- Zustand 4.5+
- React Router 7.0+ (for navigation integration)


## Anti-Patterns to Avoid

### ❌ Using useEffect for Data Fetching

```typescript
// ❌ BAD: Manual data fetching with useEffect
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  fetchData()
    .then(setData)
    .catch(setError)
    .finally(() => setLoading(false));
}, []);

// ✅ GOOD: Use TanStack Query
const { data, isLoading, error } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
});
```

### ❌ Prop Drilling

```typescript
// ❌ BAD: Props passed through many levels
<App user={user}>
  <Layout user={user}>
    <Sidebar user={user}>
      <UserMenu user={user} />
    </Sidebar>
  </Layout>
</App>

// ✅ GOOD: Use Context or Zustand
const UserContext = createContext<User | null>(null);

<UserContext.Provider value={user}>
  <App>
    <Layout>
      <Sidebar>
        <UserMenu /> {/* Access via useContext(UserContext) */}
      </Sidebar>
    </Layout>
  </App>
</UserContext.Provider>
```

### ❌ Mutating State Directly

```typescript
// ❌ BAD: Direct mutation
const addItem = (item: Item) => {
  items.push(item); // Mutation!
  setItems(items);
};

// ✅ GOOD: Immutable update
const addItem = (item: Item) => {
  setItems((prev) => [...prev, item]);
};

// ✅ ALSO GOOD: With Immer (Zustand)
const addItem = (item: Item) =>
  set((state) => {
    state.items.push(item); // Immer handles immutability
  });
```

Remember: Use the right tool for the job - TanStack Query for server state, Zustand for client state, and React's built-in hooks for local component state. Keep state minimal and derived where possible.


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat react-state-specialist-ext.md
```

Or in Claude Code:
```
Please read react-state-specialist-ext.md for detailed examples.
```
