---
paths: ["**/*.test.*", "**/tests/**", "**/__tests__/**", "**/e2e/**"]
---

# Testing Strategy

## Testing Standards

### Coverage Requirements
- **Unit Tests**: ≥80% line coverage for utilities and hooks
- **Component Tests**: All components have basic render tests
- **Integration Tests**: Feature flows are tested end-to-end
- **E2E Tests**: Critical user journeys are covered

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
- Co-locate tests with components in `__tests__/` subdirectory
- Use Testing Library's user-centric queries
- Test behavior, not implementation
- Mock external dependencies appropriately

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
