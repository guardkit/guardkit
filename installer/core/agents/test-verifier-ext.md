# test-verifier - Extended Reference

This file contains detailed documentation for the `test-verifier` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/test-verifier-ext.md
```


## Documentation Level Awareness (TASK-035)

You receive `documentation_level` parameter via `<AGENT_CONTEXT>` block:

```markdown
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|etc
phase: 4.5
</AGENT_CONTEXT>
```

### Behavior by Documentation Level

**Key Principle**: Test execution, auto-fix loop, and quality gate enforcement **ALWAYS RUN** in all modes (quality gate preserved). Only the **output format** changes.

**Minimal Mode** (simple tasks, 1-3 complexity):
- Execute all tests (100% of test suite)
- Run auto-fix loop (up to 3 attempts on failures)
- Enforce all quality gates (100% pass rate required)
- Return **test verification status as structured data**
- Output: Pass/fail JSON for embedding
- Example: `{"status": "passed", "attempts": 1, "final_pass_rate": "100%"}`

**Standard Mode** (medium tasks, 4-10 complexity, DEFAULT):
- Execute all tests (100% of test suite)
- Run auto-fix loop (up to 3 attempts on failures)
- Enforce all quality gates (100% pass rate required)
- Return **detailed test verification report**
- Output: Full test results with fix attempt details
- Current default behavior (unchanged)

**Comprehensive Mode** (explicit request or force triggers):
- Execute all tests (100% of test suite)
- Run auto-fix loop (up to 3 attempts on failures)
- Enforce all quality gates (100% pass rate required)
- Generate **enhanced verification report** with failure pattern analysis
- Create supporting documents (test logs, fix history, flaky test detection)
- Output: Comprehensive test verification documentation

### Output Format Examples

**Minimal Mode Output** (for embedding):
```json
{
  "phase": "4.5",
  "status": "passed",
  "auto_fix_attempts": 2,
  "final_result": {
    "total_tests": 15,
    "passed": 15,
    "failed": 0,
    "pass_rate": "100%"
  },
  "quality_gates": {
    "test_pass_rate": "passed",
    "build_compilation": "passed"
  },
  "fix_summary": "Fixed 3 failing tests in 2 attempts"
}
```

**Standard Mode Output** (embedded section):
```markdown

## Test Enforcement Loop (Phase 4.5)

**Final Status**: ✅ ALL TESTS PASSING (100%)

### Auto-Fix Attempts

**Attempt 1**:
- Tests: 12/15 passed (80%)
- Failed: 3 tests
- Analysis: Import errors in test files
- Fix Applied: Corrected import paths
- Re-run: PENDING

**Attempt 2**:
- Tests: 15/15 passed (100%) ✅
- Failed: 0 tests
- Result: ALL TESTS PASSING
- Auto-fix: SUCCESS

### Final Results
- Total Tests: 15
- Passed: 15 ✅
- Failed: 0
- Pass Rate: 100% (required: 100%)

### Quality Gates
✅ Build compilation: PASSED
✅ Test execution: 100% pass rate
✅ Auto-fix loop: Converged in 2 attempts

**Next**: Proceed to Phase 5 (Code Review)
```

**Comprehensive Mode Output** (standalone files):
- Full test verification report saved to `docs/testing/{task_id}-verification-report.md`
- Auto-fix attempt logs for each iteration
- Failure pattern analysis (common causes across attempts)
- Flaky test detection (tests that passed after retry)
- Test execution timeline and performance metrics
- Recommendations for test stability improvements

### Quality Gate Preservation

**CRITICAL**: The following quality checks run in ALL modes (minimal/standard/comprehensive):
- Test execution (100% of test suite runs)
- Auto-fix loop execution (up to 3 attempts on failures)
- Test pass rate enforcement (100% required - ZERO tolerance)
- Build compilation verification (must succeed before tests)
- Task blocking on persistent failures (after 3 failed fix attempts)

**What NEVER Changes**:
- Quality gate execution (all modes: 100%)
- Test pass rate requirement (100% - no exceptions)
- Auto-fix attempt limit (3 attempts maximum)
- Build verification rigor (comprehensive always)
- Failure blocking behavior (task → BLOCKED if unfixable)

**What Changes**:
- Output format (JSON vs embedded markdown vs standalone document)
- Documentation verbosity (concise vs balanced vs exhaustive)
- Supporting artifacts (none vs embedded vs standalone files)
- Failure analysis depth (essential vs detailed vs comprehensive pattern analysis)

### Auto-Fix Loop Behavior (All Modes)

**Loop Execution** (IDENTICAL in all modes):
1. Run tests
2. If failures detected:
   a. Analyze failure causes
   b. Generate fixes
   c. Apply fixes
   d. Re-run tests
   e. Repeat up to 3 attempts total
3. If all tests pass: SUCCESS → proceed to Phase 5
4. If still failing after 3 attempts: BLOCK TASK → state = BLOCKED

**Only Output Format Changes**:
- Minimal: `{"attempts": 3, "final_status": "blocked", "reason": "Persistent test failures"}`
- Standard: Full attempt-by-attempt report with fix details
- Comprehensive: Enhanced report + failure patterns + test logs

### Agent Collaboration

**Markdown Plan**: This agent writes test verification results to the implementation plan at `.claude/task-plans/{TASK_ID}-implementation-plan.md`.

**Plan Format**: YAML frontmatter + structured markdown (always generated, all modes)

**Context Passing**: Uses `<AGENT_CONTEXT>` blocks for documentation_level parameter passing

**Backward Compatible**: Gracefully handles agents without context parameter support (defaults to standard)

**Coordination with test-orchestrator**:
- test-orchestrator (Phase 4) executes initial test run and reports results
- test-verifier (Phase 4.5) runs auto-fix loop if failures detected
- Both agents enforce same quality gates (100% pass rate)


## Test Execution by Technology

### Python Projects
```bash

# Using pytest
pytest tests/ -v --cov=src --cov-report=term --cov-report=json

# Using MCP Code Checker
mcp-code-checker:run_pytest_check --verbosity 2

# Parse results
cat coverage.json | extract_coverage_metrics
```

### TypeScript/React Projects
```bash

# Using Jest
npm test -- --coverage --json --outputFile=test-results.json

# Using Vitest
npm run test:coverage -- --reporter=json

# Using Playwright for E2E
npx playwright test --reporter=json
playwright:browser_snapshot
playwright:browser_take_screenshot
```

### .NET Projects
```bash

# Using dotnet test
dotnet test --collect:"XPlat Code Coverage" --logger:"json;LogFileName=test-results.json"

# For specific test categories
dotnet test --filter "Category=Integration"
```


## Quality Gates Configuration

```yaml
quality_gates:
  coverage:
    minimum: 80
    target: 90
    branches_minimum: 75
    
  performance:
    max_test_duration: 30s
    max_single_test: 5s
    
  reliability:
    max_flaky_tests: 0
    required_pass_rate: 100
    
  categories:
    critical: must_pass
    integration: must_pass
    unit: must_pass
    e2e: should_pass
```


## Test Verification Workflow

### 1. Pre-Test Validation
```python
def validate_test_environment():
    # Check test files exist
    if not os.path.exists("tests/"):
        return "ERROR: No tests directory found"
    
    # Check for test configuration
    if not has_test_config():
        return "WARNING: No test configuration found"
    
    # Check dependencies
    if not check_test_dependencies():
        return "ERROR: Test dependencies not installed"
    
    return "OK"
```

### 2. Execute Tests
```python
def execute_tests(task_id, technology):
    if technology == "python":
        result = run_pytest()
    elif technology == "typescript":
        result = run_jest()
    elif technology == "dotnet":
        result = run_dotnet_test()
    else:
        result = run_generic_tests()
    
    return parse_test_output(result)
```

### 3. Parse Results
```python
def parse_test_output(output):
    metrics = {
        "passed": extract_passed_count(output),
        "failed": extract_failed_count(output),
        "coverage": extract_coverage(output),
        "duration": extract_duration(output),
        "failures": extract_failure_details(output)
    }
    return metrics
```

### 4. Evaluate Gates
```python
def evaluate_quality_gates(metrics):
    failures = []
    
    if metrics["coverage"] < 80:
        failures.append(f"Coverage {metrics['coverage']}% below 80% threshold")
    
    if metrics["failed"] > 0:
        failures.append(f"{metrics['failed']} tests failing")
    
    if metrics["duration"] > 30:
        failures.append(f"Tests took {metrics['duration']}s, exceeding 30s limit")
    
    return {
        "passed": len(failures) == 0,
        "failures": failures
    }
```

### 5. Update Task
```python
def update_task_with_results(task_id, metrics, gate_results):
    task = load_task(task_id)
    
    task["test_results"] = {
        "status": "passed" if gate_results["passed"] else "failed",
        "last_run": datetime.now().isoformat(),
        "coverage": metrics["coverage"],
        "passed": metrics["passed"],
        "failed": metrics["failed"],
        "execution_log": format_test_log(metrics)
    }
    
    if not gate_results["passed"]:
        task["status"] = "blocked"
        task["blocked_reason"] = "\n".join(gate_results["failures"])
    
    save_task(task)
```


## Related Templates

This specialist works with testing templates across multiple technology stacks:

### React/TypeScript Testing Templates
- **nextjs-fullstack/templates/tests/ComponentTest.test.tsx.template** - Vitest component tests with Testing Library
- **nextjs-fullstack/templates/tests/e2e.spec.ts.template** - Playwright E2E tests for Next.js applications
- **react-typescript/templates/components/__tests__/*.template** - Unit tests for React components

### Python/FastAPI Testing Templates
- **fastapi-python/templates/testing/test_router.py.template** - Pytest router tests with TestClient
- **fastapi-python/templates/testing/conftest.py.template** - Pytest fixtures and configuration

### .NET/MAUI Testing Templates
- **dotnet-maui/templates/tests/*.template** - xUnit tests for .NET MAUI applications

---


## Template Code Examples

### ✅ DO: Structure Tests with Arrange-Act-Assert Pattern

**React/Vitest Example:**
```typescript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { DiscussionsList } from '../discussions-list';

describe('DiscussionsList', () => {
  it('displays loading state initially', () => {
    // Arrange
    render(<DiscussionsList />, { wrapper: AppProvider });

    // Assert
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders discussions after loading', async () => {
    // Arrange
    render(<DiscussionsList />, { wrapper: AppProvider });

    // Act - wait for data to load
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // Assert
    expect(screen.getByText('Discussion 1')).toBeInTheDocument();
  });

  it('handles user interaction correctly', async () => {
    // Arrange
    const user = userEvent.setup();
    render(<DiscussionsList />, { wrapper: AppProvider });
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    // Act
    await user.click(screen.getByRole('button', { name: /create/i }));

    // Assert
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
```

**Why**: AAA pattern makes tests readable and maintainable. Each section has a clear purpose.

### ✅ DO: Use Fixtures for Test Data (Python/pytest)

```python

# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.db import Base
from app.models import User, Team

@pytest.fixture
async def db_session():
    """Create a fresh database session for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    await engine.dispose()

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user fixture."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def authenticated_client(test_user: User):
    """Create an authenticated test client."""
    from app.main import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Set auth header
        client.headers["Authorization"] = f"Bearer {create_token(test_user)}"
        yield client
```

**Why**: Fixtures reduce duplication, ensure consistent test data, and handle setup/teardown automatically.

### ✅ DO: Mock External Dependencies

**React/MSW Example:**
```typescript
// testing/mocks/handlers/discussions.ts
import { http, HttpResponse } from 'msw';
import { env } from '@/config/env';
import { db } from '../db';

export const discussionsHandlers = [
  http.get(`${env.API_URL}/discussions`, async ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get('page') || 1);

    const discussions = db.discussion.findMany({
      take: 10,
      skip: 10 * (page - 1),
    });

    return HttpResponse.json({
      data: discussions,
      meta: { page, total: discussions.length },
    });
  }),

  http.post(`${env.API_URL}/discussions`, async ({ request }) => {
    const data = await request.json();
    const discussion = db.discussion.create(data);
    return HttpResponse.json({ data: discussion }, { status: 201 });
  }),
];
```

**Python/pytest-mock Example:**
```python

# test_external_service.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_sends_email_on_registration(db_session, mocker):
    # Arrange
    mock_send = mocker.patch(
        'app.services.email.send_welcome_email',
        new_callable=AsyncMock
    )

    # Act
    user = await register_user(db_session, "new@example.com", "password")

    # Assert
    mock_send.assert_called_once_with(user.email)
```

**Why**: Mocking prevents flaky tests from network issues and allows testing edge cases.

### ✅ DO: Write E2E Tests for Critical User Journeys

**Playwright Example:**
```typescript
// e2e/tests/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('user can register, login, and access protected content', async ({ page }) => {
    // Register
    await page.goto('/auth/register');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.fill('[name="confirmPassword"]', 'SecurePass123!');
    await page.click('button[type="submit"]');

    // Verify redirect to login
    await expect(page).toHaveURL('/auth/login');
    await expect(page.locator('text=Registration successful')).toBeVisible();

    // Login
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.click('button[type="submit"]');

    // Verify access to protected content
    await expect(page).toHaveURL('/app/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('shows validation errors for invalid input', async ({ page }) => {
    await page.goto('/auth/login');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });
});
```

**Why**: E2E tests verify the entire system works together from the user's perspective.

### ❌ DON'T: Write Tests Without Assertions

```typescript
// BAD - Test passes but verifies nothing
it('renders component', () => {
  render(<MyComponent />);
  // No assertions!
});

// GOOD - Verify expected behavior
it('renders component with correct content', () => {
  render(<MyComponent title="Hello" />);
  expect(screen.getByRole('heading')).toHaveTextContent('Hello');
});
```

### ❌ DON'T: Use Hardcoded Test Data Everywhere

```python

# BAD - Hardcoded values repeated across tests
async def test_create_user():
    response = await client.post("/users", json={
        "email": "test@example.com",  # Duplicated everywhere
        "password": "password123"
    })

# GOOD - Use fixtures or factories
async def test_create_user(user_factory):
    user_data = user_factory.build()
    response = await client.post("/users", json=user_data)
```

---


## Template Best Practices

### Test Organization

✅ **Co-locate tests with source code**: Place `__tests__/` directories inside feature folders
```
features/
  └── discussions/
      ├── api/
      ├── components/
      └── __tests__/
          ├── discussions-list.test.tsx
          └── create-discussion.test.tsx
```

✅ **Use descriptive test names**: Test names should read like documentation
```typescript
// Good
it('displays error message when form submission fails')
it('redirects to dashboard after successful login')
it('disables submit button while request is pending')

// Bad
it('test1')
it('handles error')
it('works correctly')
```

✅ **Group related tests with describe blocks**:
```typescript
describe('DiscussionsList', () => {
  describe('when loading', () => {
    it('shows loading spinner');
    it('disables pagination');
  });

  describe('when loaded successfully', () => {
    it('displays discussions');
    it('enables pagination');
  });

  describe('when error occurs', () => {
    it('shows error message');
    it('offers retry option');
  });
});
```

### Test Isolation

✅ **Each test should be independent**: Tests should not depend on execution order
```python

# Good - Each test creates its own data
async def test_delete_user(db_session, test_user):
    await delete_user(db_session, test_user.id)
    assert await get_user(db_session, test_user.id) is None

# Bad - Depends on previous test's state
async def test_user_exists():
    user = await get_user(db, 1)  # Assumes user 1 exists from previous test
```

✅ **Clean up after tests**: Use fixtures with proper teardown
```python
@pytest.fixture
async def temp_file():
    path = Path("/tmp/test_file.txt")
    path.write_text("test content")
    yield path
    path.unlink(missing_ok=True)  # Cleanup
```

### Coverage Strategy

✅ **Focus on behavior, not implementation details**:
```typescript
// Good - Tests behavior
it('shows success message after saving', async () => {
  await user.click(saveButton);
  expect(screen.getByText('Saved successfully')).toBeVisible();
});

// Bad - Tests implementation
it('calls setState with correct value', () => {
  // Testing internal state changes
});
```

✅ **Prioritize coverage by risk**: Critical paths need more tests
- Authentication: 100% coverage
- Payment processing: 100% coverage
- UI components: 80%+ coverage
- Utilities: 90%+ coverage

### Performance

✅ **Run fast tests frequently, slow tests on CI**:
```json
// package.json
{
  "scripts": {
    "test": "vitest",
    "test:e2e": "playwright test",
    "test:ci": "vitest run && playwright test"
  }
}
```

✅ **Parallelize tests when possible**:
```python

# pytest.ini
[pytest]
addopts = -n auto  # Run tests in parallel with pytest-xdist
```

---


## Template Anti-Patterns

### ❌ NEVER: Skip Tests Without Documentation

```typescript
// BAD - No reason given
it.skip('handles edge case', () => {});

// ACCEPTABLE - Documented skip
it.skip('handles edge case - TODO: Fix after API v2 migration', () => {});
```

### ❌ NEVER: Use Sleep/Wait for Timing

```typescript
// BAD - Flaky and slow
await page.click('button');
await page.waitForTimeout(2000);  // Hope data loaded
expect(screen.getByText('Success')).toBeVisible();

// GOOD - Wait for specific condition
await page.click('button');
await expect(page.locator('text=Success')).toBeVisible({ timeout: 5000 });
```

### ❌ NEVER: Test Implementation Instead of Behavior

```typescript
// BAD - Tests internal implementation
it('updates state correctly', () => {
  const { result } = renderHook(() => useState(0));
  act(() => result.current[1](1));
  expect(result.current[0]).toBe(1);  // Testing React internals
});

// GOOD - Tests user-visible behavior
it('increments counter when button clicked', async () => {
  render(<Counter />);
  await user.click(screen.getByRole('button', { name: 'Increment' }));
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});
```

### ❌ NEVER: Ignore Test Failures in CI

```yaml

# BAD - Ignores failures
- name: Run tests
  run: npm test || true  # Always passes!

# GOOD - Fail the build on test failures
- name: Run tests
  run: npm test  # Fails build if tests fail
```

### ❌ NEVER: Write Tests That Pass for Wrong Reasons

```python

# BAD - Always passes regardless of actual behavior
def test_user_created():
    response = create_user({"email": "test@example.com"})
    assert response is not None  # Too weak!

# GOOD - Verify specific expected state
def test_user_created():
    response = create_user({"email": "test@example.com"})
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert "id" in response.json()
```

### ❌ NEVER: Mock Everything

```typescript
// BAD - Mocking so much that test proves nothing
it('creates user', () => {
  const mockDb = { create: vi.fn().mockResolvedValue({ id: 1 }) };
  const mockValidator = { validate: vi.fn().mockReturnValue(true) };
  const mockLogger = { log: vi.fn() };
  // ... more mocks

  // What are we even testing at this point?
});

// GOOD - Only mock external boundaries
it('creates user in database', async () => {
  // Use real validation, real business logic
  // Only mock external services (email, payment, etc.)
  const user = await createUser(db, validUserData);
  expect(await db.user.findById(user.id)).toBeDefined();
});
```

### ❌ NEVER: Commit Flaky Tests

```typescript
// BAD - Test that sometimes fails
it('fetches data', async () => {
  const data = await fetchData();
  expect(data.length).toBeGreaterThan(0);  // Depends on external API state
});

// GOOD - Deterministic test with controlled data
it('fetches data', async () => {
  server.use(
    http.get('/api/data', () => HttpResponse.json([{ id: 1 }]))
  );
  const data = await fetchData();
  expect(data.length).toBe(1);
});
```

---


## Cross-Stack Testing Checklist

When verifying tests across different technology stacks:

### React/TypeScript (Vitest + Playwright)
- [ ] Unit tests run: `npm test`
- [ ] E2E tests run: `npm run test:e2e`
- [ ] Coverage meets threshold (80%+)
- [ ] No console errors in test output
- [ ] All async operations properly awaited

### Python/FastAPI (pytest)
- [ ] Tests run: `pytest tests/ -v`
- [ ] Coverage report: `pytest --cov=src --cov-report=term`
- [ ] Async fixtures use `@pytest.fixture` with `async def`
- [ ] Database fixtures properly clean up

### .NET/MAUI (xUnit)
- [ ] Tests run: `dotnet test`
- [ ] Coverage: `dotnet test --collect:"XPlat Code Coverage"`
- [ ] Integration tests use proper test fixtures
- [ ] Platform-specific tests are properly categorized


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat test-verifier-ext.md
```

Or in Claude Code:
```
Please read test-verifier-ext.md for detailed examples.
```
