"""Testing rules generator."""

from typing import Dict, Optional


def generate_testing_rules(framework: str) -> str:
    """
    Generate testing framework-specific rules.

    Args:
        framework: Testing framework (e.g., "pytest", "vitest", "jest")

    Returns:
        Markdown content for testing.md with paths frontmatter
    """
    templates = {
        "pytest": _pytest_template,
        "vitest": _vitest_template,
        "jest": _jest_template,
        "xunit": _xunit_template,
        "nunit": _nunit_template,
        "junit": _junit_template,
    }

    template_func = templates.get(framework.lower(), _generic_template)
    return template_func(framework)


def _pytest_template(framework: str) -> str:
    """pytest testing rules template."""
    return """---
paths: **/tests/**/*.py, **/*_test.py, **/test_*.py
---

# Testing with pytest

## Test Organization

- Place tests in `tests/` directory
- Mirror source structure in tests
- Name test files `test_*.py` or `*_test.py`
- Name test functions `test_*`

## Test Structure

```python
def test_feature_name():
    # Arrange
    setup_data = create_test_data()

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result == expected_value
```

## Fixtures

- Use fixtures for common setup
- Scope fixtures appropriately (function, class, module, session)
- Place shared fixtures in `conftest.py`

```python
@pytest.fixture
def sample_data():
    return {"key": "value"}
```

## Parametrization

- Use `@pytest.mark.parametrize` for multiple test cases
- Keep test data close to test function

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
])
def test_double(input, expected):
    assert double(input) == expected
```

## Assertions

- Use plain `assert` statements
- pytest provides detailed failure messages
- Use `pytest.raises()` for exceptions

## Coverage

- Aim for >80% line coverage
- Aim for >75% branch coverage
- Use `pytest --cov=src` for coverage reports

## Best Practices

- One assertion per test (when possible)
- Test edge cases and error conditions
- Use meaningful test names
- Keep tests fast and isolated
- Mock external dependencies
"""


def _vitest_template(framework: str) -> str:
    """vitest testing rules template."""
    return """---
paths: **/*.test.{ts,tsx}, **/*.spec.{ts,tsx}
---

# Testing with Vitest

## Test Organization

- Place tests alongside source files
- Use `.test.ts` or `.spec.ts` extension
- Group related tests in `describe` blocks

## Test Structure

```typescript
import { describe, it, expect } from 'vitest'

describe('FeatureName', () => {
  it('should do something', () => {
    // Arrange
    const input = 'test'

    // Act
    const result = functionUnderTest(input)

    // Assert
    expect(result).toBe('expected')
  })
})
```

## Setup and Teardown

```typescript
import { beforeEach, afterEach } from 'vitest'

beforeEach(() => {
  // Setup
})

afterEach(() => {
  // Cleanup
})
```

## Mocking

```typescript
import { vi } from 'vitest'

const mockFn = vi.fn()
vi.mock('./module', () => ({
  someFunction: mockFn
}))
```

## React Component Testing

```typescript
import { render, screen } from '@testing-library/react'

it('renders component', () => {
  render(<Component />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

## Coverage

- Aim for >80% line coverage
- Aim for >75% branch coverage
- Use `vitest --coverage` for reports

## Best Practices

- Test user behavior, not implementation
- Use Testing Library queries
- Avoid testing internal state
- Keep tests simple and readable
"""


def _jest_template(framework: str) -> str:
    """jest testing rules template."""
    return """---
paths: **/*.test.{js,jsx,ts,tsx}, **/*.spec.{js,jsx,ts,tsx}
---

# Testing with Jest

## Test Organization

- Place tests alongside source files
- Use `.test.js` or `.spec.js` extension
- Group related tests in `describe` blocks

## Test Structure

```javascript
describe('FeatureName', () => {
  it('should do something', () => {
    // Arrange
    const input = 'test'

    // Act
    const result = functionUnderTest(input)

    // Assert
    expect(result).toBe('expected')
  })
})
```

## Setup and Teardown

```javascript
beforeEach(() => {
  // Setup before each test
})

afterEach(() => {
  // Cleanup after each test
})
```

## Mocking

```javascript
jest.mock('./module', () => ({
  someFunction: jest.fn()
}))

const mockFn = jest.fn()
mockFn.mockReturnValue('mocked value')
```

## Async Testing

```javascript
it('handles async operations', async () => {
  const result = await asyncFunction()
  expect(result).toBe('expected')
})
```

## Snapshot Testing

```javascript
it('matches snapshot', () => {
  const component = render(<Component />)
  expect(component).toMatchSnapshot()
})
```

## Coverage

- Aim for >80% line coverage
- Use `jest --coverage` for reports
- Configure coverage thresholds in jest.config.js

## Best Practices

- Clear test descriptions
- One concept per test
- Avoid test interdependence
- Mock external dependencies
"""


def _xunit_template(framework: str) -> str:
    """xUnit testing rules template."""
    return """---
paths: **/tests/**/*.cs, **/*.Tests/**/*.cs
---

# Testing with xUnit

## Test Organization

- Place tests in separate test project
- Use `*.Tests` naming convention
- One test class per production class

## Test Structure

```csharp
public class FeatureTests
{
    [Fact]
    public void TestMethodName()
    {
        // Arrange
        var sut = new SystemUnderTest();

        // Act
        var result = sut.Method();

        // Assert
        Assert.Equal(expected, result);
    }
}
```

## Parameterized Tests

```csharp
[Theory]
[InlineData(1, 2)]
[InlineData(2, 4)]
public void TestWithParameters(int input, int expected)
{
    var result = Double(input);
    Assert.Equal(expected, result);
}
```

## Setup and Cleanup

```csharp
public class TestClass : IDisposable
{
    public TestClass()
    {
        // Setup
    }

    public void Dispose()
    {
        // Cleanup
    }
}
```

## Async Tests

```csharp
[Fact]
public async Task TestAsyncMethod()
{
    var result = await AsyncMethod();
    Assert.NotNull(result);
}
```

## Best Practices

- Use AAA pattern (Arrange, Act, Assert)
- Test one thing per test
- Use descriptive test names
- Prefer `Assert.Equal` over `Assert.True`
"""


def _nunit_template(framework: str) -> str:
    """NUnit testing rules template."""
    return """---
paths: **/tests/**/*.cs, **/*.Tests/**/*.cs
---

# Testing with NUnit

## Test Organization

- Place tests in separate test project
- Use `[TestFixture]` attribute
- Group related tests

## Test Structure

```csharp
[TestFixture]
public class FeatureTests
{
    [Test]
    public void TestMethodName()
    {
        // Arrange
        var sut = new SystemUnderTest();

        // Act
        var result = sut.Method();

        // Assert
        Assert.That(result, Is.EqualTo(expected));
    }
}
```

## Parameterized Tests

```csharp
[TestCase(1, 2)]
[TestCase(2, 4)]
public void TestWithParameters(int input, int expected)
{
    var result = Double(input);
    Assert.That(result, Is.EqualTo(expected));
}
```

## Setup and Teardown

```csharp
[SetUp]
public void Setup()
{
    // Before each test
}

[TearDown]
public void TearDown()
{
    // After each test
}
```

## Best Practices

- Use constraint model for assertions
- Descriptive test names
- Isolate tests
- Test edge cases
"""


def _junit_template(framework: str) -> str:
    """JUnit testing rules template."""
    return """---
paths: **/src/test/**/*.java
---

# Testing with JUnit

## Test Organization

- Place tests in `src/test/java`
- Mirror production package structure
- Use `Test` suffix for test classes

## Test Structure

```java
class FeatureTest {
    @Test
    void testMethodName() {
        // Arrange
        var sut = new SystemUnderTest();

        // Act
        var result = sut.method();

        // Assert
        assertEquals(expected, result);
    }
}
```

## Parameterized Tests

```java
@ParameterizedTest
@ValueSource(ints = {1, 2, 3})
void testWithParameters(int input) {
    assertTrue(input > 0);
}
```

## Setup and Teardown

```java
@BeforeEach
void setUp() {
    // Before each test
}

@AfterEach
void tearDown() {
    // After each test
}
```

## Best Practices

- Use AssertJ for fluent assertions
- Test one behavior per test
- Use meaningful test names
- Isolate tests from each other
"""


def _generic_template(framework: str) -> str:
    """Generic testing template for unknown frameworks."""
    return f"""---
paths: **/tests/**, **/test/**
---

# Testing with {framework.title()}

## Test Organization

- Organize tests logically
- Mirror source structure
- Use consistent naming

## Test Structure

- Arrange: Set up test data
- Act: Execute the code under test
- Assert: Verify the results

## Best Practices

- Write tests that are fast and isolated
- Test edge cases and error conditions
- Use meaningful test names
- Aim for high code coverage (>80%)
- Mock external dependencies
- Keep tests simple and readable
"""
