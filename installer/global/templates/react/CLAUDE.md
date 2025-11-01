# React Project Context for Claude Code

This is a React project using the Agentic Flow task workflow system with best practices derived from production implementations.

## Technology Stack
- **Frontend**: React 18+ with TypeScript
- **Build Tool**: Vite 5+
- **Testing**: Vitest + React Testing Library + Playwright
- **Styling**: Tailwind CSS (utility-first) / CSS Modules (component isolation)
- **State Management**: Local state hooks + Context API (simple) / Zustand (complex)
- **Type Safety**: TypeScript with strict mode + runtime validation

## Project Structure
```
.
├── .claude/              # Agentic Flow configuration
├── src/
│   ├── components/       # React components
│   │   ├── ui/          # Reusable UI primitives
│   │   ├── features/    # Feature-specific components
│   │   └── layout/      # Layout components
│   ├── hooks/           # Custom React hooks
│   ├── pages/           # Page/route components
│   ├── services/        # API services & external integrations
│   │   ├── api/         # API client and endpoints
│   │   └── storage/     # Local storage utilities
│   ├── contexts/        # React contexts for global state
│   ├── types/           # TypeScript type definitions
│   ├── utils/           # Utility functions and helpers
│   └── design-tokens/   # Design system tokens
├── tests/
│   ├── unit/           # Component tests
│   ├── integration/    # Integration tests
│   └── e2e/            # Playwright tests
├── tasks/              # Task management
│   ├── backlog/
│   ├── in_progress/
│   ├── in_review/
│   └── completed/
└── docs/               # Documentation
```

## Task Workflow

### Unified 3-Command System
```bash
# 1. Create Task
/task-create "Add user profile component"
/task-create "Implement search functionality" priority:high

# 2. Work on Task (Implementation + Testing Combined)
/task-work TASK-XXX [--mode=standard|tdd|bdd]

# 3. Complete Task
/task-complete TASK-XXX
```

### Development Modes
- **Standard Mode**: Implementation and tests created together
- **TDD Mode**: Red-Green-Refactor cycle for complex logic
- **BDD Mode**: Start from Gherkin scenarios for user-facing features

### Quality Gates (Automatic)
Every task must pass these gates before completion:
- ✅ All tests passing (100%)
- ✅ Code coverage ≥ 80%
- ✅ Performance benchmarks met
- ✅ No security vulnerabilities
- ✅ Accessibility standards met

## Development Standards

### Component Development
- **Functional components** with hooks (no class components)
- **TypeScript interfaces** for all props with JSDoc comments
- **Accessibility-first** development (WCAG 2.1 AA minimum)
- **Error boundaries** for graceful error handling
- **Memoization** for expensive computations and renders
- **Composition over inheritance** for component design

### Code Organization Patterns
```typescript
// Component file structure
ComponentName/
├── index.ts              // Public exports
├── ComponentName.tsx     // Component implementation
├── ComponentName.types.ts // TypeScript interfaces
├── ComponentName.test.tsx // Component tests
├── ComponentName.stories.tsx // Storybook stories (optional)
└── hooks/               // Component-specific hooks
```

### Testing Requirements
- **Unit tests** for all components and utilities (minimum 80% coverage)
- **Integration tests** for data flows and API interactions
- **E2E tests** for critical user journeys (happy paths + edge cases)
- **Accessibility tests** using testing-library and axe-core
- **Performance tests** for components with heavy computation

### Code Quality
- ESLint + Prettier configured
- Pre-commit hooks with Husky
- Conventional commits

## Available Scripts
```bash
# Development
npm run dev          # Start development server with HMR
npm run build        # Build for production with optimization
npm run preview      # Preview production build locally

# Testing
npm run test         # Run unit tests in watch mode
npm run test:ci      # Run tests once with coverage
npm run test:e2e     # Run Playwright E2E tests
npm run test:a11y    # Run accessibility tests

# Code Quality
npm run lint         # Run ESLint with auto-fix
npm run type-check   # Run TypeScript compiler checks
npm run format       # Format code with Prettier
npm run validate     # Run all checks (lint, type-check, test)
```

## React-Specific Commands

### Component Generation
Use `/create-component ComponentName` to generate:
- Component file with TypeScript interfaces
- Test file with unit test cases
- Type definition file
- Index file for clean exports
- Storybook story (if configured)

### Hook Generation
Use `/create-hook useHookName` to generate:
- Custom hook with TypeScript and JSDoc
- Comprehensive test file
- Usage examples in documentation
- Performance considerations

### Service Generation
Use `/create-service ServiceName` to generate:
- Service class/functions with TypeScript
- API integration patterns
- Error handling utilities
- Mock service for testing

## Testing Patterns

### Component Testing
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button Component', () => {
  it('renders with correct text and handles clicks', async () => {
    const handleClick = jest.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toBeEnabled();

    await user.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('respects disabled state', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Hook Testing
```typescript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useApi } from './useApi';

describe('useApi Hook', () => {
  it('handles successful API calls', async () => {
    const { result } = renderHook(() => useApi('/endpoint'));

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.data).toBeDefined();
      expect(result.current.error).toBeNull();
    });
  });
});
```

### E2E Testing
```typescript
import { test, expect } from '@playwright/test';

test.describe('User Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('complete user flow', async ({ page }) => {
    // Wait for app to load
    await expect(page.locator('[data-testid="app-loaded"]')).toBeVisible();

    // Navigate through flow
    await page.click('text=Get Started');
    await expect(page).toHaveURL('/onboarding');

    // Fill form
    await page.fill('[name="email"]', 'test@example.com');
    await page.click('button[type="submit"]');

    // Verify result
    await expect(page.locator('.success-message')).toContainText('Welcome');
  });
});
```

## Performance Requirements

### Core Web Vitals
- **LCP (Largest Contentful Paint)**: < 2.5s
- **FID (First Input Delay)**: < 100ms
- **CLS (Cumulative Layout Shift)**: < 0.1
- **FCP (First Contentful Paint)**: < 1.5s
- **TTI (Time to Interactive)**: < 3.5s

### Bundle Size Targets
- **Initial bundle**: < 150KB (gzipped)
- **Lazy-loaded chunks**: < 50KB each
- **Total application**: < 500KB (gzipped)

### Runtime Performance
- **React render time**: < 16ms (60fps)
- **API response handling**: < 100ms
- **State updates**: Batched and optimized
- **Memory leaks**: Zero tolerance

### Optimization Techniques
```typescript
// Use React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }) => {
  // Component logic
}, (prevProps, nextProps) => {
  // Custom comparison logic
  return prevProps.data.id === nextProps.data.id;
});

// Use useMemo for expensive computations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Use useCallback for stable function references
const handleClick = useCallback(() => {
  // Handler logic
}, [dependency]);
```

## State Management Patterns

### Local State (Simple Cases)
```typescript
const [count, setCount] = useState(0);
const [isLoading, setIsLoading] = useState(false);
```

### Context API (Shared State)
```typescript
// Create context
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Provider component
export const ThemeProvider: React.FC<PropsWithChildren> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>('light');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// Custom hook for consuming context
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};
```

### Zustand (Complex Global State)
```typescript
import { create } from 'zustand';

interface StoreState {
  user: User | null;
  setUser: (user: User) => void;
  clearUser: () => void;
}

export const useStore = create<StoreState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),
}));
```

## Best Practices

1. **Choose the right mode**: TDD for complex logic, BDD for user features, Standard for simple components
2. **Let quality gates guide you**: They ensure consistent quality
3. **Trust the workflow**: Implementation and testing together prevent bugs
4. **Optimize performance**: Use memoization and code splitting
5. **Accessibility first**: Every component should be keyboard and screen reader accessible

Remember: **"Implementation and testing are inseparable"** - this is the core philosophy of the unified workflow.
