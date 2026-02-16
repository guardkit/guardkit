---
paths: ["**/*.test.*", "**/tests/**", "**/__tests__/**", "**/e2e/**"]
---

# Testing Strategy

## Trophy Testing Model

This template follows **Kent C. Dodds' Trophy testing model** for client applications:

```
        🏆  E2E (~10%)
      ___________
    /             \
   | Feature/       |
   | Integration    |    ← Primary investment (~50%)
   | Tests          |
    \_____________/
     Unit Tests (~30%)
      ___________
     Static/Types (~10%)
```

**Testing Distribution:**
- **50% Feature/Integration Tests**: User-meaningful scenarios across multiple components
- **30% Unit Tests**: Complex business logic (calculations, validations, state machines)
- **10% E2E Tests**: Critical user journeys only (login, checkout, core workflow)
- **10% Static Analysis**: TypeScript strict mode, ESLint

**Key Principle:** "The more your tests resemble the way your software is used, the more confidence they can give you." Framework seams (React rendering, HTTP routing) are reliable — test the business logic and user behavior, not framework wiring.

## Testing Standards

### Coverage Requirements
- **Line Coverage**: ≥80%
- **Branch Coverage**: ≥75%
- **Feature Tests**: Every user story has at least one feature/integration test
- **Unit Tests**: Complex business logic only (not simple getters/setters)
- **Contract Tests**: Third-party API integrations
- **E2E Tests**: Critical user journeys only
- **Static Analysis**: TypeScript strict mode enabled

## Unit Tests (Vitest)

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

### Best Practices
- **Test behavior, not implementation**: Focus on what users see and do, not internal state
- **Mock at HTTP boundaries only**: Use MSW for API mocking; DO NOT mock internal functions/components
- **Co-locate tests**: Place tests with components in `__tests__/` subdirectory
- **User-centric queries**: Use Testing Library's `getByRole`, `getByLabelText`, not `getByTestId`
- **When to use seam tests**: Third-party integrations, microservice boundaries (rare in client apps)

## E2E Tests (Playwright)

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

### E2E Best Practices
- Test critical user journeys
- Use data-testid for stable selectors
- Handle async operations properly
- Clean up test data after each test

## API Mocking with MSW

Mock API responses for development and testing:

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

### MSW Setup
1. Define handlers in `testing/mocks/handlers/`
2. Initialize MSW in `mock-server.ts`
3. Ensure handlers match request URLs exactly
4. Use `env.API_URL` for consistent URLs

**Why MSW?** Mock APIs at the HTTP level (network boundary), not at the function level. This tests the entire client-side flow while isolating backend dependencies.

## Testing Checklist

For every feature/user story, ensure:
- [ ] **Feature/Integration Test**: At least one test covering the user-facing behavior across multiple components
- [ ] **Unit Tests**: Only for complex business logic (calculations, validations, state machines)
- [ ] **Contract Tests**: For third-party API integrations (mock provider responses)
- [ ] **E2E Test**: Only for critical user journeys (login, checkout, payment)
- [ ] **Static Analysis**: TypeScript strict mode catches type errors

**What NOT to Test:**
- Simple getters/setters
- React rendering logic (framework-tested)
- Styled components (visual regression tests instead)
- Internal component implementation details

## Running Tests

```bash
# Run tests in watch mode
npm test

# Run tests with coverage
npm test -- --coverage

# Run E2E tests
npm run test-e2e

# Run E2E in UI mode
npm run test-e2e:ui
```

## Troubleshooting

### MSW Not Mocking
- Ensure MSW is initialized (`mock-server.ts`)
- Check handler matches request URL exactly
- Verify `env.API_URL` is correct in handlers
- Check browser console for MSW registration messages

### Query Not Updating in Tests
- Use `waitFor` for async operations
- Check query key matches
- Verify mock handlers return expected data
- Use React Query DevTools in development
