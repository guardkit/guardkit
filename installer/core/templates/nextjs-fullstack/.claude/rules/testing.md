---
paths: **/*.test.*, **/e2e/**
---

# Testing Guidelines

## Trophy Testing Model

This template follows **Kent C. Dodds' Trophy testing model** for fullstack applications:

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
- **50% Feature/Integration Tests**: User scenarios across frontend + backend (Server Actions, API routes)
- **30% Unit Tests**: Complex business logic (calculations, validations, server utilities)
- **10% E2E Tests**: Critical user journeys only (login, checkout, core workflow)
- **10% Static Analysis**: TypeScript strict mode, ESLint

**Key Principle:** Test through Server Actions and API routes (application boundaries at HTTP/network level), not internal implementation. Framework seams (Next.js routing, React Server Components) are reliable — test your business logic and user flows.

## Testing Strategy

### Coverage Requirements
- **Line Coverage**: ≥80%
- **Branch Coverage**: ≥75%
- **Feature Tests**: Every user story has integration test
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

## Testing Checklist

For every feature/user story, ensure:
- [ ] **Feature/Integration Test**: Test through Server Actions or API routes (application boundary)
- [ ] **Unit Tests**: Only for complex business logic (calculations, validators, utilities)
- [ ] **Contract Tests**: For third-party integrations (database, external APIs)
- [ ] **E2E Test**: Only for critical user journeys (login, checkout, payment)
- [ ] **Static Analysis**: TypeScript strict mode enabled

**What to Test:**
- Server Actions and API routes (50% of tests)
- Complex business logic in server utilities (30% of tests)
- User interactions via Testing Library
- Critical workflows end-to-end (10% of tests)

**What NOT to Mock:**
- Internal components/functions (test real implementations)
- Server Components (test through their APIs)
- Server Actions (test through HTTP calls)

**What NOT to Test:**
- Next.js routing logic (framework-tested)
- React Server Components rendering (framework-tested)
- Simple data fetching without transformation
- Database ORM behavior (Prisma/Drizzle-tested)

**When Seam Tests ARE Needed:**
- Third-party API integrations (Stripe, Auth0, external services)
- Database adapters (when you write custom data access layer)
- Microservice boundaries (rare in monolithic Next.js apps)

## Quality Gates

- All tests must pass (100%)
- Coverage thresholds must be met
- No TypeScript errors
