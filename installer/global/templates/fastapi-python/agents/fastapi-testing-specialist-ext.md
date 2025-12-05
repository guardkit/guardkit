# fastapi-testing-specialist - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the fastapi-testing-specialist agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Code Examples

## Best Practices

1. **Use async fixtures for database operations**
   - Mark fixtures with `async def`
   - Use `await` for database operations
   - Clean up properly in fixtures

2. **Override dependencies, don't modify app state**
   - Use `app.dependency_overrides`
   - Clear overrides after each test
   - Keep tests isolated

3. **Test both success and failure cases**
   - Test happy path
   - Test validation errors
   - Test authentication failures
   - Test not found cases
   - Test permission errors

4. **Use factories for complex test data**
   - Avoid repetitive test data creation
   - Make factories flexible with kwargs
   - Use Faker for realistic data

5. **Parametrize similar tests**
   - Reduce code duplication
   - Test multiple scenarios easily
   - Make test cases explicit

6. **Mock external dependencies**
   - Don't make real API calls in tests
   - Mock email sending
   - Mock payment processing
   - Mock file storage