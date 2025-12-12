---
paths: **/*.test.*, **/e2e/**
---

# Testing Guidelines

## Testing Strategy

### Unit Test Coverage
- **Line Coverage**: ≥80%
- **Branch Coverage**: ≥75%
- **Framework**: Vitest with happy-dom environment

### E2E Test Coverage
- **Critical User Flows**: All major workflows
- **Framework**: Playwright (Chromium)

### Component Testing
- **Framework**: Testing Library React 16.3.0
- **Approach**: Test behavior, not implementation

## Test Structure

### Unit Tests
```typescript
// components/UserList.test.tsx
import { render, screen } from '@testing-library/react'
import { UserList } from './UserList'

describe('UserList', () => {
  it('renders user list correctly', () => {
    const users = [
      { id: '1', email: 'test@example.com', name: 'Test User' }
    ]

    render(<UserList users={users} />)
    expect(screen.getByText('Test User')).toBeInTheDocument()
  })
})
```

### E2E Tests
```typescript
// e2e/users.spec.ts
import { test, expect } from '@playwright/test'

test('user can create and delete user', async ({ page }) => {
  await page.goto('/users')

  // Create user
  await page.click('text=Add User')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.click('button[type="submit"]')

  // Verify creation
  await expect(page.locator('text=test@example.com')).toBeVisible()

  // Delete user
  await page.click('text=Delete')
  await page.click('text=Confirm')

  // Verify deletion
  await expect(page.locator('text=test@example.com')).not.toBeVisible()
})
```

## Running Tests

```bash
npm test              # Unit tests
npm run test:e2e      # E2E tests
npm run type-check    # TypeScript
```

## Quality Gates

- All tests must pass (100%)
- Coverage thresholds must be met
- No TypeScript errors
