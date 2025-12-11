---
paths: **/tests/**, **/test_*.py, **/*_test.py, **/conftest.py
---

# Testing Specialist Agent

## Purpose

Specialized guidance for pytest testing patterns, async test clients, and test fixtures.

## Technologies

pytest, pytest-asyncio, httpx, pytest-cov

## Boundaries

### ALWAYS
- ✅ Use async test client for API tests (matches async FastAPI routes)
- ✅ Override dependencies in tests (isolated test environment)
- ✅ Use factory fixtures for test data (reusable test objects)
- ✅ Test both success and error cases (comprehensive coverage)
- ✅ Clean up test database after tests (test isolation)

### NEVER
- ❌ Never test against production database (data corruption risk)
- ❌ Never skip cleanup in fixtures (test pollution)
- ❌ Never hardcode test data (brittle tests)
- ❌ Never ignore failing tests (technical debt accumulation)
- ❌ Never mock database in integration tests (false confidence)

### ASK
- ⚠️ Test coverage below 80% (acceptable for low-risk code)
- ⚠️ Performance test thresholds (depends on requirements)
- ⚠️ Mock vs real database (integration vs unit test trade-offs)
- ⚠️ Flaky test handling (quarantine vs immediate fix)

## When This Agent Is Used

This agent provides guidance when working with:
- Test files (`test_*.py`, `*_test.py`)
- Test fixtures (`conftest.py`)
- API integration tests
- Database test setup

## Capabilities

1. **Async test client** setup for API testing
2. **Database fixtures** with proper cleanup
3. **Factory fixtures** for test data generation
4. **Dependency override patterns** for isolated tests
5. **Coverage reporting** and test organization

## Integration with Other Rules

- **Testing**: Uses patterns from `testing.md`
- **API**: Tests endpoints from `api/routing.md`
- **Database**: Tests CRUD operations from `database/crud.md`
- **Schemas**: Validates with schemas from `api/schemas.md`

## See Also

- `.claude/rules/testing.md` - Testing patterns and fixtures
- `.claude/rules/api/routing.md` - API endpoints to test
- `.claude/rules/database/crud.md` - Database operations to test
