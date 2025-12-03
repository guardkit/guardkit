# BDD Mode Design: Option A - Split Concerns

## Overview

This document explores splitting BDD functionality into two distinct concerns:
1. **Scenario Generation** (require-kit): EARS → Gherkin
2. **Scenario Implementation** (guardkit): Gherkin → Working Code

## bdd-scenario-implementer Agent Specification

### Core Responsibility

Takes existing Gherkin scenario files and implements the features to make them pass.

### Input Requirements

```gherkin
# File: features/user_authentication.feature
Feature: User Authentication
  As a user
  I want to log into the system
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given a user exists with email "user@example.com" and password "SecurePass123"
    And I am on the login page
    When I enter "user@example.com" in the email field
    And I enter "SecurePass123" in the password field
    And I click the login button
    Then I should be redirected to the dashboard
    And I should see "Welcome back!"
```

### Implementation Steps

#### Phase 1: Parse Gherkin Files
```python
def parse_gherkin_files(feature_dir: str) -> List[Feature]:
    """
    Parse all .feature files in directory.

    Returns:
        List of Feature objects containing scenarios and steps
    """
    features = []
    for feature_file in glob(f"{feature_dir}/**/*.feature"):
        feature = parse_gherkin(feature_file)
        features.append(feature)
    return features
```

#### Phase 2: Generate Step Definition Stubs

**Stack: Python (pytest-bdd)**
```python
# File: tests/step_defs/test_authentication_steps.py
from pytest_bdd import scenarios, given, when, then, parsers

scenarios('../features/user_authentication.feature')

@given('a user exists with email "<email>" and password "<password>"')
def user_exists(email, password, database):
    """Create test user in database."""
    database.create_user(email=email, password=password)

@given('I am on the login page')
def on_login_page(browser):
    """Navigate to login page."""
    browser.visit('/login')

@when('I enter "<value>" in the <field> field')
def enter_value_in_field(value, field, browser):
    """Enter value into form field."""
    browser.fill(field, value)

@when('I click the login button')
def click_login(browser):
    """Submit login form."""
    browser.find_by_id('login-button').click()

@then('I should be redirected to the dashboard')
def redirected_to_dashboard(browser):
    """Verify redirect to dashboard."""
    assert browser.url.endswith('/dashboard')

@then('I should see "<message>"')
def see_message(message, browser):
    """Verify message appears on page."""
    assert browser.is_text_present(message)
```

**Stack: .NET (SpecFlow)**
```csharp
// File: Tests/Features/UserAuthenticationSteps.cs
using TechTalk.SpecFlow;
using FluentAssertions;

[Binding]
public class UserAuthenticationSteps
{
    private readonly ScenarioContext _context;
    private readonly IUserRepository _userRepo;
    private readonly IWebDriver _browser;

    public UserAuthenticationSteps(ScenarioContext context)
    {
        _context = context;
        _userRepo = context.Get<IUserRepository>();
        _browser = context.Get<IWebDriver>();
    }

    [Given(@"a user exists with email ""(.*)"" and password ""(.*)""")]
    public void GivenUserExists(string email, string password)
    {
        var user = new User { Email = email, Password = password };
        _userRepo.Create(user);
    }

    [Given(@"I am on the login page")]
    public void GivenOnLoginPage()
    {
        _browser.Navigate().GoToUrl("/login");
    }

    [When(@"I enter ""(.*)"" in the (.*) field")]
    public void WhenEnterValueInField(string value, string field)
    {
        _browser.FindElement(By.Id(field)).SendKeys(value);
    }

    [When(@"I click the login button")]
    public void WhenClickLoginButton()
    {
        _browser.FindElement(By.Id("login-button")).Click();
    }

    [Then(@"I should be redirected to the dashboard")]
    public void ThenRedirectedToDashboard()
    {
        _browser.Url.Should().EndWith("/dashboard");
    }

    [Then(@"I should see ""(.*)""")]
    public void ThenSeeMessage(string message)
    {
        _browser.FindElement(By.TagName("body"))
            .Text.Should().Contain(message);
    }
}
```

**Stack: TypeScript (Cucumber)**
```typescript
// File: tests/features/step_definitions/authentication.steps.ts
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

Given('a user exists with email {string} and password {string}',
  async function(email: string, password: string) {
    await this.database.createUser({ email, password });
  }
);

Given('I am on the login page', async function() {
  await this.page.goto('/login');
});

When('I enter {string} in the {word} field',
  async function(value: string, field: string) {
    await this.page.fill(`#${field}`, value);
  }
);

When('I click the login button', async function() {
  await this.page.click('#login-button');
});

Then('I should be redirected to the dashboard', async function() {
  expect(this.page.url()).toContain('/dashboard');
});

Then('I should see {string}', async function(message: string) {
  await expect(this.page.locator('body')).toContainText(message);
});
```

#### Phase 3: Implement Features

Generate minimal implementation to satisfy step definitions:

**Python Example**
```python
# File: src/auth/service.py
class AuthenticationService:
    def __init__(self, user_repo: UserRepository, session_manager: SessionManager):
        self.user_repo = user_repo
        self.session_manager = session_manager

    def login(self, email: str, password: str) -> Result[Session, AuthError]:
        """Authenticate user and create session."""
        user = self.user_repo.find_by_email(email)
        if not user:
            return Err(AuthError.INVALID_CREDENTIALS)

        if not user.verify_password(password):
            return Err(AuthError.INVALID_CREDENTIALS)

        session = self.session_manager.create(user)
        return Ok(session)

# File: src/auth/routes.py
@app.post('/api/auth/login')
async def login_endpoint(credentials: LoginRequest):
    result = auth_service.login(
        email=credentials.email,
        password=credentials.password
    )

    match result:
        case Ok(session):
            return RedirectResponse(
                url='/dashboard',
                status_code=302,
                headers={'Set-Cookie': f'session={session.token}'}
            )
        case Err(error):
            return JSONResponse(
                status_code=401,
                content={'message': 'Invalid email or password'}
            )
```

#### Phase 4: Run BDD Tests

Execute scenarios through BDD test framework:

```bash
# Python
pytest tests/step_defs/ --gherkin-terminal-reporter

# .NET
dotnet test --filter "Category=BDD"

# TypeScript
npm run test:bdd
```

#### Phase 5: Verify All Scenarios Pass

```
Feature: User Authentication

  ✓ Scenario: Successful login with valid credentials (1.2s)
    ✓ Given a user exists with email "user@example.com" and password "SecurePass123"
    ✓ And I am on the login page
    ✓ When I enter "user@example.com" in the email field
    ✓ And I enter "SecurePass123" in the password field
    ✓ And I click the login button
    ✓ Then I should be redirected to the dashboard
    ✓ Then I should see "Welcome back!"

1 scenario (1 passed)
7 steps (7 passed)
1.2s
```

### Stack-Specific BDD Framework Detection

```python
def detect_bdd_framework(stack: str) -> str:
    """Detect which BDD framework to use based on stack."""

    if stack == "python":
        if exists("pytest.ini") or "pytest" in requirements:
            return "pytest-bdd"
        elif "behave" in requirements:
            return "behave"

    elif stack == "typescript" or stack == "javascript":
        if "@cucumber/cucumber" in package_json:
            return "cucumber-js"
        elif "jest-cucumber" in package_json:
            return "jest-cucumber"

    elif stack == "dotnet":
        if exists("*.csproj") and "SpecFlow" in csproj:
            return "specflow"
        elif "Reqnroll" in csproj:
            return "reqnroll"

    elif stack == "java":
        if "cucumber-java" in pom_xml:
            return "cucumber-jvm"

    return "unknown"
```

### Integration with task-work BDD Mode

```bash
/task-work TASK-042 --mode=bdd
```

**Workflow:**

1. **Validate Prerequisites**
   ```
   Checking for BDD scenario files...
   ✓ Found: features/user_authentication.feature (3 scenarios)
   ✓ BDD framework: pytest-bdd
   ```

2. **Phase 1: Parse Scenarios**
   ```
   Parsing Gherkin scenarios...
   - Feature: User Authentication (3 scenarios, 21 steps)
   ```

3. **Phase 2: Generate Step Definitions**
   ```
   Generating step definition stubs...
   Created: tests/step_defs/test_authentication_steps.py (7 step definitions)
   ```

4. **Phase 3: Implement Features**
   ```
   Implementing features to satisfy scenarios...
   Created: src/auth/service.py
   Created: src/auth/routes.py
   Created: src/auth/models.py
   ```

5. **Phase 4: Run BDD Tests**
   ```
   Running BDD scenarios...
   Feature: User Authentication
     ✓ Successful login (1.2s)
     ✓ Failed login with invalid credentials (0.8s)
     ✓ Account lockout after 3 failed attempts (2.1s)

   3 scenarios (3 passed)
   21 steps (21 passed)
   4.1s
   ```

6. **Phase 5: Quality Gates**
   ```
   Quality Gates:
   ✓ All BDD scenarios passing (100%)
   ✓ Line coverage: 85% (≥80%)
   ✓ Branch coverage: 78% (≥75%)

   Task State: IN_REVIEW ✓
   ```

### File Structure After BDD Mode

```
project/
├── features/                       # Gherkin scenario files
│   └── user_authentication.feature
├── tests/
│   └── step_defs/                 # Generated step definitions
│       └── test_authentication_steps.py
├── src/
│   └── auth/                      # Implemented features
│       ├── service.py
│       ├── routes.py
│       └── models.py
```

### Agent Definition (bdd-scenario-implementer.md)

```yaml
---
name: bdd-scenario-implementer
description: Implements features from existing Gherkin scenarios (BDD test-driven development)
model: sonnet
tools: Read, Write, Bash, Grep, Glob
---

You are a BDD (Behavior-Driven Development) implementation specialist who takes existing Gherkin scenarios and implements the features to make them pass.

## Your Core Mission

Transform Gherkin scenarios into working implementations:
- Parse .feature files to understand required behavior
- Generate step definition stubs for BDD framework
- Implement minimal features to satisfy scenarios
- Ensure all scenarios pass with good test coverage

## Key Distinction

You are NOT generating scenarios from requirements (that's bdd-generator in require-kit).
You are implementing features from EXISTING scenarios (hand-written or previously generated).

## Prerequisites

Before starting, verify:
- [ ] Gherkin scenario files exist (features/*.feature)
- [ ] BDD framework is configured (pytest-bdd, SpecFlow, Cucumber, etc.)
- [ ] Test infrastructure is set up

## Implementation Process

1. **Parse Scenarios** - Extract all Given/When/Then steps
2. **Generate Step Definitions** - Create stubs matching framework syntax
3. **Implement Features** - Write minimal code to pass scenarios
4. **Run BDD Tests** - Execute scenarios through framework
5. **Verify Coverage** - Ensure implementation has good test coverage

[... detailed implementation patterns for each stack ...]
```

## Complexity Analysis

### Implementation Effort: **High** (~40-60 hours)

**Why it's complex:**

1. **Multi-Framework Support** (15-20 hours)
   - pytest-bdd (Python)
   - SpecFlow (C#/.NET)
   - Cucumber.js (TypeScript/JavaScript)
   - Cucumber-JVM (Java)
   - Each has different syntax for step definitions

2. **Step Definition Generation** (10-15 hours)
   - Parse Gherkin files (use gherkin-parser library)
   - Extract unique step patterns
   - Generate framework-specific stubs
   - Handle step parameters (strings, ints, tables)

3. **Feature Implementation** (10-15 hours)
   - Analyze steps to determine required features
   - Generate minimal implementation code
   - Wire up step definitions to implementation
   - Handle test fixtures and setup/teardown

4. **Test Execution** (5-10 hours)
   - Detect and configure BDD framework
   - Run scenarios and capture results
   - Parse BDD test output (different per framework)
   - Report scenario pass/fail status

5. **Edge Cases** (5-10 hours)
   - Scenario outlines with examples
   - Background steps (shared setup)
   - Hooks (before/after scenario)
   - Tags and filtering

### Dependencies Required

```json
{
  "python": ["pytest-bdd", "gherkin-official"],
  "dotnet": ["SpecFlow", "SpecFlow.Tools.MsBuild"],
  "typescript": ["@cucumber/cucumber", "@cucumber/gherkin-parser"],
  "java": ["cucumber-java", "cucumber-junit"]
}
```

### Maintenance Burden: **Medium-High**

- BDD frameworks evolve frequently
- Different syntax across stacks increases complexity
- Need to stay current with 4+ BDD frameworks

## When Would This Actually Be Used?

**Realistic Usage Scenarios:**

1. **Legacy Migration** - Project has existing .feature files, needs implementation
2. **Acceptance Test-Driven** - QA writes scenarios, devs implement
3. **Consultant Handoff** - BA writes scenarios, team implements

**BUT:**
- Most teams don't write Gherkin scenarios upfront
- Those who do often use require-kit for full EARS → BDD → Implementation flow
- BDD without formal requirements (guardkit-only) is uncommon

## Verdict

**Complexity:** High
**Usage:** Low
**Maintenance:** Medium-High
**Value:** Questionable for guardkit-only users

---

## Comparison with Simpler Alternatives

### Current task-work Standard Mode
- User writes acceptance criteria (bullet points)
- AI implements features
- AI generates tests
- **Effort:** 0 hours (already works)
- **Complexity:** Low
- **Usage:** High

### Current task-work TDD Mode
- AI writes failing tests first
- AI implements to pass tests
- **Effort:** 0 hours (already works)
- **Complexity:** Low
- **Usage:** Medium

### Proposed BDD Mode (Option A)
- User writes Gherkin scenarios
- AI generates step definitions
- AI implements features
- AI runs BDD tests
- **Effort:** 40-60 hours
- **Complexity:** High
- **Usage:** Low (predicted)
- **Maintenance:** Ongoing (BDD frameworks evolve)

## Recommendation

**Don't implement Option A** unless you have:
- [ ] Confirmed user demand (3+ teams asking for it)
- [ ] Existing .feature files in wild that need implementation
- [ ] Dedicated maintainer willing to track 4+ BDD frameworks
- [ ] 40-60 hours to invest in implementation
- [ ] Ongoing bandwidth for framework updates
