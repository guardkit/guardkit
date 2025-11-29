# TaskWright Pre-Launch Test Plan - macOS Parallels VM

**Created**: 2025-11-29
**Platform**: macOS Parallels Virtual Machine (clean slate)
**Duration**: 2-3 hours
**Goal**: Validate complete workflow before public launch

---

## Test Environment Setup

### VM Configuration

**Recommended VM Settings**:
- **OS**: macOS Sonoma (latest)
- **RAM**: 8GB minimum
- **Disk**: 50GB
- **Network**: Shared network (for GitHub access)

**Why Parallels VM?**
- ✅ Clean slate (no contamination from dev environment)
- ✅ Reproducible (can snapshot and rollback)
- ✅ Realistic user experience
- ✅ Easy to screenshot/record for demos

### Pre-Test Snapshot

```bash
# Before starting tests, create VM snapshot
# Name: "Pre-TaskWright-Install"
# This allows rollback if needed
```

---

## Test Plan Overview

### Phase 1: Installation & Template Init (45 min)
1. Install TaskWright
2. Install RequireKit
3. Initialize greenfield project with fastapi-python template
4. Validate /gather-requirements Q&A workflow

### Phase 2: Task Workflow & Subagent Validation (45 min)
5. Create tasks with hash-based IDs
6. Validate subagent discovery and routing
7. Test quality gates (Phase 2.5, Phase 4.5)
8. Complete task workflow

### Phase 3: BDD Integration (45 min)
9. Create EARS requirements in RequireKit
10. Generate Gherkin scenarios
11. Run /task-work --mode=bdd
12. Validate BDD test execution

### Phase 4: Bonus - KartLog Demo Setup (30 min, optional)
13. Clone KartLog
14. Use /gather-requirements with two Claude instances
15. Implement weather tracking feature

---

## Phase 1: Installation & Template Init (45 min)

### Step 1.1: Install TaskWright (10 min)

```bash
# Open Terminal in VM

# 1. Install prerequisites
xcode-select --install  # If not already installed
brew --version || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python 3.11+
brew install python@3.11
python3 --version  # Should be 3.11+

# 3. Clone TaskWright
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright

# 4. Run installer
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# 5. Verify installation
taskwright --version
which taskwright  # Should show ~/.agentecflow/bin/taskwright
```

**Expected Output**:
```
✅ TaskWright installed to ~/.agentecflow/
✅ Commands symlinked to ~/.agentecflow/bin/
✅ Agents installed to ~/.agentecflow/agents/
✅ Templates available: react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, default
```

**Test Checklist**:
- [ ] Installation completes without errors
- [ ] `taskwright --version` works
- [ ] `~/.agentecflow/` directory created
- [ ] Symlinks in `~/.agentecflow/bin/` point to correct scripts

**Screenshot**: Installation success message

---

### Step 1.2: Install RequireKit (10 min)

```bash
# 1. Clone RequireKit
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit

# 2. Run installer
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# 3. Verify installation
ls ~/.agentecflow/require-kit.marker  # Should exist
which /req-create  # Should resolve
```

**Expected Output**:
```
✅ RequireKit installed
✅ Marker file created: ~/.agentecflow/require-kit.marker
✅ BDD mode available in TaskWright
```

**Test Checklist**:
- [ ] Installation completes without errors
- [ ] Marker file exists at `~/.agentecflow/require-kit.marker`
- [ ] RequireKit commands available

**Screenshot**: RequireKit installation success

---

### Step 1.3: Initialize Greenfield Project with FastAPI Template (15 min)

**Why FastAPI?**
- Minimal dev environment setup (just Python)
- Built-in template (no custom template needed)
- Good for testing subagent routing (python-api-specialist)

```bash
# 1. Create new project directory
mkdir -p ~/Projects/test-api-service
cd ~/Projects/test-api-service

# 2. Initialize git (required for TaskWright)
git init
git config user.name "Test User"
git config user.email "test@example.com"

# 3. Initialize with fastapi-python template
taskwright init fastapi-python
```

**Expected Q&A Session** (Template init greenfield questions):

The system should ask questions like:
```
Gathering requirements for template initialization...

Q: What is the primary purpose of this API?
   (e.g., User management, E-commerce, IoT data processing)

Q: What authentication method will you use?
   - JWT (recommended)
   - OAuth2
   - API Keys
   - Session-based
   - None (public API)

Q: What database will you use?
   - PostgreSQL (recommended)
   - MySQL
   - SQLite
   - MongoDB
   - None (in-memory)

Q: Do you need async database support?
   - Yes (recommended for FastAPI)
   - No

Q: What testing framework?
   - pytest (recommended)
   - unittest

Q: Do you need Celery for background tasks?
   - Yes
   - No (not yet)

Q: Do you need Docker configuration?
   - Yes (recommended)
   - No

Q: Project name? (for pyproject.toml)
```

**Your Answers** (for test consistency):
- Purpose: **User management API**
- Auth: **JWT**
- Database: **PostgreSQL**
- Async: **Yes**
- Testing: **pytest**
- Celery: **No**
- Docker: **Yes**
- Project name: **test-api-service**

**Expected Output After Init**:
```
✅ Template initialized: fastapi-python
✅ Project structure created
✅ Configuration generated based on your answers
✅ Agents installed to .claude/agents/
✅ Ready to create tasks

Next steps:
  /task-create "Your first task"
```

**Verify File Structure**:
```bash
ls -la

Expected:
.claude/
├── agents/           # Template-specific agents
├── commands/         # Symlinked commands
└── settings.json     # Template settings

src/
├── api/
├── auth/             # Since we chose JWT
├── database/         # Since we chose PostgreSQL
├── models/
└── main.py

tests/
├── conftest.py
└── test_api/

pyproject.toml        # With project name "test-api-service"
Dockerfile            # Since we chose Docker
docker-compose.yml
.gitignore
README.md
```

**Test Checklist**:
- [ ] Q&A session completes
- [ ] Template files copied
- [ ] Configuration matches answers (JWT, PostgreSQL, pytest, Docker)
- [ ] `.claude/agents/` contains template agents
- [ ] `pyproject.toml` has correct project name
- [ ] Git repository initialized

**Screenshots**:
- Q&A session in progress
- Final file structure
- Sample configuration file (e.g., `src/config.py`)

---

### Step 1.4: Validate /gather-requirements Q&A Workflow (10 min)

**Objective**: Test the greenfield Q&A workflow separately from template init

```bash
# Create a simple task to test gather-requirements
/task-create "Add user registration endpoint"
```

**Expected**: Task created with hash ID (e.g., `TASK-a3f8`)

```bash
# Now test gather-requirements (if it's a separate command)
# Note: This might be integrated into /task-work Phase 1
/task-work TASK-a3f8 --mode=standard
```

**Expected Q&A During Phase 1** (if implemented):
```
Phase 1: Requirements Analysis

Q: What fields should the registration form include?
   (e.g., email, password, username, full name)

Q: What validation rules for password?
   (e.g., min length, special characters, uppercase)

Q: Should email verification be required?
   - Yes (send confirmation email)
   - No (activate immediately)

Q: What should happen on duplicate email?
   - Return 409 Conflict
   - Return 400 Bad Request
   - Silent failure

Q: Should we return JWT on successful registration?
   - Yes (auto-login)
   - No (require separate login)
```

**Test Checklist**:
- [ ] Q&A session triggers
- [ ] Questions are relevant to task
- [ ] Answers stored in task context
- [ ] Implementation plan uses answers

**Note**: If `/gather-requirements` is not a separate command, validate that Phase 1 of `/task-work` asks appropriate questions.

---

## Phase 2: Task Workflow & Subagent Validation (45 min)

### Step 2.1: Create Tasks with Hash-Based IDs (10 min)

```bash
cd ~/Projects/test-api-service

# Test 1: Simple task (no prefix)
/task-create "Add health check endpoint"
# Expected: TASK-XXXX (4-6 char hash)

# Test 2: Task with prefix
/task-create "Fix authentication bug" prefix:FIX
# Expected: TASK-FIX-XXXX

# Test 3: Epic-related task
/task-create "Implement user management" prefix:E01
# Expected: TASK-E01-XXXX

# Test 4: Subtask
/task-create "Add unit tests for auth" parent:TASK-E01-XXXX
# Expected: TASK-E01-XXXX.1

# Verify tasks created
/task-status
```

**Expected Output**:
```
BACKLOG:
  TASK-a3f8 - Add health check endpoint
  TASK-FIX-b2c4 - Fix authentication bug
  TASK-E01-d5e6 - Implement user management
  TASK-E01-d5e6.1 - Add unit tests for auth
```

**Test Checklist**:
- [ ] All task IDs use hash format
- [ ] Prefixes applied correctly (FIX, E01)
- [ ] Subtask format correct (TASK-E01-XXXX.1)
- [ ] `/task-status` shows all tasks
- [ ] Task files created in `tasks/backlog/`

**Screenshot**: `/task-status` output showing hash-based IDs

---

### Step 2.2: Validate Subagent Discovery & Routing (15 min)

**Objective**: Verify that task-work routes to appropriate stack-specific agents

```bash
# Work on a Python API task
/task-work TASK-a3f8  # Health check endpoint task
```

**Expected Behavior**:

**Phase 1: Requirements Analysis**
```
Loading task context...
Task: Add health check endpoint
Stack detected: Python (FastAPI)
```

**Phase 2: Implementation Planning**
```
Analyzing task complexity...
Complexity score: 2/10 (Simple)
Routing decision: AUTO_PROCEED (no checkpoint needed)

Creating implementation plan...
```

**Phase 3: Implementation**
```
Selecting implementation agent...

Agent Discovery Results:
✅ python-api-specialist selected
   Source: global
   Reason: Stack match (python), Phase match (implementation)
   Capabilities: fastapi, async-patterns, pydantic

Invoking python-api-specialist...
```

**Expected Agent Usage**:
- **python-api-specialist** for FastAPI endpoint implementation
- **test-orchestrator** for running pytest
- **code-reviewer** for Phase 5 review

**Test Checklist**:
- [ ] Stack detected as Python/FastAPI
- [ ] `python-api-specialist` selected for Phase 3
- [ ] Agent discovery shows source (global/user/local)
- [ ] Implementation completes
- [ ] Tests generated and run

**Screenshot**: Agent discovery output showing `python-api-specialist` selection

---

### Step 2.3: Test Quality Gates (Phase 2.5, Phase 4.5) (10 min)

**Phase 2.5: Architectural Review**

```bash
# Create a complex task to trigger architectural review
/task-create "Implement OAuth2 authentication flow with refresh tokens"

/task-work TASK-XXXX
```

**Expected During Phase 2.5**:
```
Phase 2.5: Architectural Review

Analyzing implementation plan...

SOLID Principles Analysis:
  Single Responsibility: 8/10
  Open/Closed: 7/10
  Liskov Substitution: 9/10
  Interface Segregation: 8/10
  Dependency Inversion: 9/10

DRY Analysis: 8/10
YAGNI Analysis: 7/10

Overall Score: 67/100 (Grade: C+ - APPROVE WITH MODIFICATIONS)

Recommendations:
  - Separate token generation from endpoint logic
  - Use dependency injection for token service
  - Add refresh token rotation

Proceed to implementation? (This task scored above 60/100)
```

**Phase 4.5: Test Enforcement**

After implementation, tests should run automatically:

```
Phase 4.5: Test Enforcement

Running build verification...
✅ Build successful

Running tests...
pytest tests/ -v --cov=src

Collected 12 items

tests/test_auth.py::test_login ✅ PASSED
tests/test_auth.py::test_refresh ❌ FAILED

Test Results:
  Passed: 11/12
  Failed: 1/12
  Coverage: 78%

Fix attempt 1/3...
Analyzing failure: AssertionError in test_refresh
Re-implementing token refresh logic...
Re-running tests...

Test Results:
  Passed: 12/12 ✅
  Failed: 0/12
  Coverage: 82%

✅ All tests passing
✅ Coverage above threshold (80%)

Proceeding to Phase 5...
```

**Test Checklist**:
- [ ] Phase 2.5 triggers on complex tasks
- [ ] Architectural score calculated
- [ ] Recommendations provided
- [ ] Phase 4.5 runs tests automatically
- [ ] Fix loop attempts on failures (up to 3)
- [ ] Task proceeds only if tests pass

**Screenshots**:
- Architectural review output
- Test enforcement with fix loop

---

### Step 2.4: Complete Task Workflow (10 min)

```bash
# After Phase 5 (Code Review) completes
# Task should be in IN_REVIEW state

/task-status
# Expected: TASK-XXXX in IN_REVIEW

# Complete the task
/task-complete TASK-XXXX

# Verify completion
ls tasks/completed/
# Expected: TASK-XXXX directory exists

cat tasks/completed/TASK-XXXX/COMPLETION-REPORT.md
```

**Expected Completion Report**:
```markdown
# Task Completion Report

**Task ID**: TASK-a3f8
**Title**: Add health check endpoint
**Status**: COMPLETED
**Completed**: 2025-11-29T14:32:00Z

## Summary
Successfully implemented health check endpoint with tests.

## Implementation Details
- Endpoint: GET /health
- Response: JSON with status and timestamp
- Tests: 3 unit tests, 1 integration test
- Coverage: 92%

## Quality Gates
✅ Architectural Review: 78/100 (Approve)
✅ Build: Success
✅ Tests: 12/12 passed
✅ Coverage: 82% (above 80% threshold)
✅ Code Review: Approved

## Files Changed
- src/api/health.py (new)
- tests/test_health.py (new)
- src/main.py (modified)
```

**Test Checklist**:
- [ ] Task moved to `tasks/completed/`
- [ ] Completion report generated
- [ ] Git commit created (if configured)
- [ ] Task state cleaned up

**Screenshot**: Completion report

---

## Phase 3: BDD Integration (45 min)

### Step 3.1: Create EARS Requirements in RequireKit (10 min)

```bash
cd ~/Projects/require-kit

# Create an epic for authentication features
/req-create "User Authentication System" type:epic

# Expected: REQ-001 created

# Create a specific requirement using EARS notation
/req-create "Login Functionality" parent:REQ-001 type:requirement

# Now formalize with EARS
/formalize-ears REQ-002
```

**Expected EARS Formalization Session**:
```
Formalizing requirement REQ-002: Login Functionality

Current description: "Login Functionality"

Let's formalize this using EARS notation.

What trigger initiates this behavior?
> User submits login form with email and password

What should the system do?
> Authenticate credentials and return JWT token

Are there any constraints or conditions?
> Only allow login if account is active

Let me formalize this:

WHEN user submits login form with email and password,
WHERE account status is active,
SYSTEM SHALL authenticate credentials,
AND system SHALL return JWT token with 24-hour expiration.

Does this capture the requirement correctly? (y/n)
> y

✅ REQ-002 formalized with EARS notation
```

**Test Checklist**:
- [ ] Epic created (REQ-001)
- [ ] Requirement created (REQ-002)
- [ ] EARS formalization session works
- [ ] Formalized requirement saved

**Screenshot**: EARS formalization output

---

### Step 3.2: Generate Gherkin Scenarios (10 min)

```bash
# Generate BDD scenarios from EARS requirement
/generate-bdd REQ-002
```

**Expected Gherkin Output**:
```gherkin
Feature: User Login
  As a registered user
  I want to log in with my email and password
  So that I can access my account

  Background:
    Given the system has an active user account
      | email           | password    | status |
      | user@test.com   | Password123 | active |

  Scenario: Successful login with valid credentials
    Given a user with email "user@test.com" and password "Password123"
    When the user submits the login form
    Then the system should authenticate the credentials
    And the system should return a JWT token
    And the token should expire in 24 hours

  Scenario: Failed login with invalid password
    Given a user with email "user@test.com"
    When the user submits the login form with password "WrongPassword"
    Then the system should return 401 Unauthorized
    And the system should not return a JWT token

  Scenario: Failed login for inactive account
    Given a user with email "inactive@test.com" and status "inactive"
    When the user submits the login form
    Then the system should return 403 Forbidden
    And the error message should be "Account is not active"
```

**Expected Output**:
```
✅ BDD scenarios generated: BDD-001
✅ Feature file created: scenarios/bdd-001-user-login.feature
✅ 3 scenarios generated
✅ Linked to requirement REQ-002

Next steps:
  1. Review scenarios in scenarios/bdd-001-user-login.feature
  2. Link to TaskWright task: Add 'bdd_scenarios: [BDD-001]' to frontmatter
  3. Run: /task-work TASK-XXX --mode=bdd
```

**Test Checklist**:
- [ ] BDD scenarios generated
- [ ] Feature file created
- [ ] Scenarios linked to requirement
- [ ] Multiple scenarios generated (happy path + edge cases)

**Screenshot**: Generated Gherkin scenarios

---

### Step 3.3: Run /task-work --mode=bdd (15 min)

```bash
cd ~/Projects/test-api-service

# Create task for login implementation
/task-create "Implement login endpoint with JWT" task_type:implementation

# Edit task frontmatter to link BDD scenarios
# In tasks/backlog/TASK-XXXX.md, add:
# bdd_scenarios: [BDD-001]

# Now run with BDD mode
/task-work TASK-XXXX --mode=bdd
```

**Expected Workflow**:

**Phase 1: Load Context**
```
Phase 1: Requirements Analysis

Detected: BDD mode
Validating RequireKit installation...
✅ RequireKit marker found: ~/.agentecflow/require-kit.marker

Loading BDD scenarios: [BDD-001]
✅ Loaded 3 scenarios from scenarios/bdd-001-user-login.feature

Stack detection: Python (FastAPI)
BDD framework: pytest-bdd
```

**Phase 2: Implementation Planning**
```
Phase 2: Implementation Planning

Planning implementation to satisfy scenarios:
  - Successful login with valid credentials
  - Failed login with invalid password
  - Failed login for inactive account

Implementation approach:
  1. Create login endpoint: POST /auth/login
  2. Implement credential verification
  3. Generate JWT token with 24h expiration
  4. Add account status check
  5. Generate pytest-bdd step definitions
```

**Phase 3: Implementation**
```
Phase 3: Implementation

Routing to bdd-generator agent (RequireKit)...
✅ Agent discovered: bdd-generator
   Source: RequireKit (~/.agentecflow/agents/bdd-generator.md)

Generating step definitions...
✅ Created: tests/bdd/steps/test_login_steps.py
✅ Created: tests/bdd/features/login.feature

Implementing to pass scenarios...
✅ Created: src/auth/login.py
✅ Created: src/auth/jwt.py
✅ Updated: src/main.py
```

**Phase 4: Testing**
```
Phase 4: Testing

Running BDD tests...
pytest tests/bdd/features/login.feature --gherkin-terminal-reporter

Feature: User Login
  Scenario: Successful login with valid credentials ✅ PASSED
  Scenario: Failed login with invalid password ✅ PASSED
  Scenario: Failed login for inactive account ✅ PASSED

3 scenarios (3 passed)
9 steps (9 passed)

✅ All BDD scenarios passing
✅ Coverage: 89%

Proceeding to Phase 5...
```

**Test Checklist**:
- [ ] BDD mode validates RequireKit installed
- [ ] Scenarios loaded from RequireKit
- [ ] bdd-generator agent invoked
- [ ] Step definitions generated (pytest-bdd)
- [ ] Implementation passes all scenarios
- [ ] BDD tests run in Phase 4

**Screenshots**:
- BDD mode detection
- Step definition generation
- BDD test execution with all scenarios passing

---

### Step 3.4: Validate BDD Test Execution (10 min)

```bash
# Run BDD tests manually to verify
pytest tests/bdd/features/login.feature -v

# Check step definitions
cat tests/bdd/steps/test_login_steps.py
```

**Expected Step Definitions**:
```python
from pytest_bdd import scenarios, given, when, then, parsers
from httpx import AsyncClient
import pytest

scenarios('../features/login.feature')

@given('a user with email "user@test.com" and password "Password123"')
def user_credentials(db_session):
    # Create test user
    user = User(email="user@test.com", status="active")
    user.set_password("Password123")
    db_session.add(user)
    db_session.commit()
    return user

@when('the user submits the login form')
async def submit_login(async_client: AsyncClient, user_credentials):
    response = await async_client.post(
        "/auth/login",
        json={"email": "user@test.com", "password": "Password123"}
    )
    return response

@then('the system should authenticate the credentials')
def verify_authentication(submit_login):
    assert submit_login.status_code == 200

@then('the system should return a JWT token')
def verify_jwt_token(submit_login):
    assert "access_token" in submit_login.json()
    assert submit_login.json()["token_type"] == "bearer"

@then(parsers.parse('the token should expire in {hours:d} hours'))
def verify_token_expiration(submit_login, hours):
    import jwt
    token = submit_login.json()["access_token"]
    decoded = jwt.decode(token, options={"verify_signature": False})
    # Verify exp claim
    assert "exp" in decoded
```

**Test Checklist**:
- [ ] Step definitions match Gherkin steps
- [ ] Fixtures used appropriately (db_session, async_client)
- [ ] Implementation code passes all steps
- [ ] Tests can run independently with `pytest`

**Screenshot**: BDD test output showing scenario pass/fail

---

## Phase 4: BONUS - KartLog Demo Setup (30 min, optional)

### Step 4.1: Clone KartLog (5 min)

```bash
cd ~/Projects
git clone https://github.com/ColinEberhardt/kartlog.git
cd kartlog

# Install dependencies
npm install

# Run development server
npm run dev
```

**Expected**: Svelte dev server starts on http://localhost:5173

**Test Checklist**:
- [ ] KartLog clones successfully
- [ ] Dependencies install without errors
- [ ] Dev server starts
- [ ] Can view app in browser

---

### Step 4.2: Two Claude Instances for /gather-requirements (10 min)

**Setup**: Open two instances of Claude Code

**Instance 1 (Interrogator)**: Asks questions about KartLog codebase

**Instance 2 (Answerer)**: Has access to KartLog source and answers

**Workflow**:

**Claude Instance 1** (in TaskWright project):
```bash
cd ~/Projects/test-api-service

# Create task for weather tracking feature
/task-create "Add weather conditions tracking to KartLog"

# Start gather-requirements
/gather-requirements TASK-XXXX
```

**Expected Questions from Instance 1**:
```
Q: What is the current data model for karting sessions?
Q: Where are session forms defined in the codebase?
Q: What database is used and how is data stored?
Q: Are there existing validation patterns we should follow?
Q: What UI component library is used?
```

**Claude Instance 2** (in KartLog project):
```bash
cd ~/Projects/kartlog

# Instance 2 reads source and answers
cat src/lib/types.ts  # Session data model
cat src/components/SessionForm.svelte  # Form component
cat src/lib/firebase.ts  # Firestore configuration
grep -r "validation" src/  # Validation patterns
cat package.json  # UI library (if any)
```

**Instance 2 provides answers**:
```
A: Session data model includes: id, date, circuit, lapTimes[], equipment, notes
   See: src/lib/types.ts, interface Session

A: Session forms use Svelte components with bind:value for two-way binding
   See: src/components/SessionForm.svelte

A: Database is Firestore (Firebase), collections: /users/{uid}/sessions/{id}
   See: src/lib/firebase.ts

A: Validation uses browser built-in (required, min, max) + custom validators
   See: src/lib/validators.ts

A: No UI component library - uses vanilla Svelte + custom CSS
   See: package.json (no UI deps besides Svelte)
```

**Test Checklist**:
- [ ] Two Claude instances can collaborate
- [ ] Interrogator asks relevant questions
- [ ] Answerer provides accurate source-based answers
- [ ] Answers inform implementation plan

**Screenshot**: Split screen showing both Claude instances

---

### Step 4.3: Implement Weather Tracking Feature (15 min)

```bash
# Back in Instance 1 (TaskWright)
/task-work TASK-XXXX --mode=standard
```

**Expected Implementation** (based on gathered requirements):

**Phase 2: Implementation Planning**
```
Implementation Plan:

1. Update Session Type (src/lib/types.ts)
   - Add weather fields: temperature, humidity, conditions

2. Update Session Form (src/components/SessionForm.svelte)
   - Add temperature input (number, celsius)
   - Add humidity input (number, percentage)
   - Add conditions dropdown (Dry, Damp, Wet)

3. Update Firestore Schema
   - Add weather object to session documents
   - Update security rules to validate weather fields

4. Update Session Display
   - Show weather badges in SessionCard.svelte
   - Add weather section to SessionDetail.svelte

5. Add Validation
   - Temperature: -10 to 50 celsius
   - Humidity: 0 to 100 percent
   - Conditions: enum validation
```

**Expected Files Changed**:
```
Modified:
  src/lib/types.ts
  src/components/SessionForm.svelte
  src/components/SessionCard.svelte
  src/components/SessionDetail.svelte
  firestore.rules

Added:
  tests/weather-validation.test.ts
```

**Test Checklist**:
- [ ] Implementation matches KartLog code style
- [ ] Uses Svelte patterns (bind:value, etc.)
- [ ] Firestore integration correct
- [ ] Validation added
- [ ] Tests generated

**Screenshot**: Weather tracking feature implemented in KartLog

---

## Test Results Documentation

### Create Test Results Document

```bash
cd ~/Projects/taskwright

cat > PARALLELS-VM-TEST-RESULTS.md << 'EOF'
# TaskWright Parallels VM Test Results

**Date**: 2025-11-29
**Tester**: [Your Name]
**VM**: macOS Sonoma, 8GB RAM
**Duration**: 2h 45min

## Phase 1: Installation & Template Init

### ✅ Step 1.1: Install TaskWright
- Status: PASSED
- Duration: 12 minutes
- Notes: Installation smooth, no errors
- Screenshot: [installation-success.png]

### ✅ Step 1.2: Install RequireKit
- Status: PASSED
- Duration: 8 minutes
- Notes: Marker file created correctly
- Screenshot: [requirekit-installed.png]

### ✅ Step 1.3: Initialize Greenfield Project
- Status: PASSED
- Duration: 18 minutes
- Notes: Q&A session worked well, template files copied
- Issues: None
- Screenshot: [template-init-qa.png, file-structure.png]

### ✅ Step 1.4: Validate /gather-requirements
- Status: PASSED
- Duration: 10 minutes
- Notes: Questions relevant and helpful
- Screenshot: [gather-requirements-qa.png]

## Phase 2: Task Workflow & Subagent Validation

### ✅ Step 2.1: Create Tasks with Hash IDs
- Status: PASSED
- Duration: 8 minutes
- Notes: All hash formats worked (simple, prefix, subtask)
- Screenshot: [hash-based-ids.png]

### ✅ Step 2.2: Validate Subagent Discovery
- Status: PASSED
- Duration: 15 minutes
- Notes: python-api-specialist correctly selected
- Screenshot: [subagent-discovery.png]

### ✅ Step 2.3: Test Quality Gates
- Status: PASSED
- Duration: 12 minutes
- Notes: Architectural review triggered, test fix loop worked
- Screenshot: [architectural-review.png, test-enforcement.png]

### ✅ Step 2.4: Complete Task Workflow
- Status: PASSED
- Duration: 8 minutes
- Notes: Completion report generated correctly
- Screenshot: [completion-report.png]

## Phase 3: BDD Integration

### ✅ Step 3.1: Create EARS Requirements
- Status: PASSED
- Duration: 10 minutes
- Notes: EARS formalization worked well
- Screenshot: [ears-formalization.png]

### ✅ Step 3.2: Generate Gherkin Scenarios
- Status: PASSED
- Duration: 10 minutes
- Notes: 3 scenarios generated, good coverage
- Screenshot: [gherkin-scenarios.png]

### ✅ Step 3.3: Run BDD Mode
- Status: PASSED
- Duration: 18 minutes
- Notes: Full workflow worked, step definitions generated
- Screenshot: [bdd-mode-execution.png]

### ✅ Step 3.4: Validate BDD Tests
- Status: PASSED
- Duration: 8 minutes
- Notes: All scenarios passed
- Screenshot: [bdd-tests-passing.png]

## Phase 4: KartLog Demo (BONUS)

### ✅ Step 4.1: Clone KartLog
- Status: PASSED
- Duration: 5 minutes

### ✅ Step 4.2: Two Claude Instances
- Status: PASSED
- Duration: 12 minutes
- Notes: Collaboration workflow effective

### ✅ Step 4.3: Implement Weather Feature
- Status: PASSED
- Duration: 20 minutes
- Notes: Implementation matched KartLog patterns

## Overall Results

**Total Duration**: 2h 45min
**Tests Passed**: 14/14
**Tests Failed**: 0/14
**Critical Issues**: 0
**Medium Issues**: 0
**Minor Issues**: 0

## Recommendations

1. ✅ Ready for public launch
2. ✅ BDD integration working perfectly
3. ✅ Template init Q&A is smooth
4. ✅ Subagent routing validated
5. ✅ Quality gates functioning

## Known Issues

None found during testing.

## Demo Content Ready

- ✅ Installation walkthrough validated
- ✅ Template init can be demoed
- ✅ BDD workflow ready for blog post
- ✅ KartLog feature implementation ready
EOF
```

---

## Success Criteria

### Must Pass (Critical)

- [ ] TaskWright installs without errors
- [ ] RequireKit installs and marker file created
- [ ] Template init Q&A session works
- [ ] Hash-based task IDs generated correctly
- [ ] Subagent discovery routes to correct agents
- [ ] BDD mode validates RequireKit installation
- [ ] BDD scenarios load and execute
- [ ] All quality gates function (Phase 2.5, 4.5)

### Should Pass (High Priority)

- [ ] Template init generates correct project structure
- [ ] Configuration matches Q&A answers
- [ ] Architectural review scores calculated
- [ ] Test enforcement fix loop works
- [ ] Completion reports generated
- [ ] EARS formalization session smooth

### Nice to Have (Medium Priority)

- [ ] KartLog demo setup works
- [ ] Two Claude instance workflow functional
- [ ] Weather feature implementation quality

---

## Troubleshooting Guide

### Issue: TaskWright command not found

**Solution**:
```bash
# Check symlink exists
ls -l ~/.agentecflow/bin/taskwright

# If missing, re-run installer
cd ~/Projects/taskwright
./installer/scripts/install.sh

# Add to PATH if needed
echo 'export PATH="$HOME/.agentecflow/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: RequireKit marker file not found

**Solution**:
```bash
# Check marker file
ls ~/.agentecflow/require-kit.marker

# If missing, re-run RequireKit installer
cd ~/Projects/require-kit
./installer/scripts/install.sh
```

### Issue: BDD mode fails with RequireKit not installed

**Expected Behavior**: This is correct! BDD mode should fail gracefully with helpful error message.

**Verify Error Message**:
```
ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Alternative modes:
    /task-work TASK-XXX --mode=tdd
    /task-work TASK-XXX --mode=standard
```

### Issue: Template init doesn't ask questions

**Solution**: Check if template has greenfield Q&A configured in `template_config.json`.

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Document Results**
   - Complete PARALLELS-VM-TEST-RESULTS.md
   - Take all screenshots
   - Note any observations

2. **Proceed to Shared Agents**
   - Start TASK-SHA-000 (verification)
   - Execute Phase 0 tasks
   - Baseline established

3. **Prepare Demo Content**
   - Use KartLog weather feature for blog post
   - Create demo video script
   - Prepare LinkedIn post

### If Issues Found ❌

1. **Categorize Issues**
   - Critical: Blocks public launch
   - High: Should fix before launch
   - Medium: Can fix post-launch
   - Low: Future enhancement

2. **Create Fix Tasks**
   - Use `/task-create` for each issue
   - Prioritize critical and high
   - Document workarounds

3. **Re-test After Fixes**
   - Run focused tests on fixed areas
   - Verify no regressions
   - Update test results

---

## Time Estimates

| Phase | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Phase 1: Installation | 45 min | ___ | |
| Phase 2: Task Workflow | 45 min | ___ | |
| Phase 3: BDD Integration | 45 min | ___ | |
| Phase 4: KartLog Demo | 30 min | ___ | Optional |
| **Total** | **2-3 hours** | ___ | |

---

## Final Checklist

**Pre-Test**:
- [ ] Parallels VM created and configured
- [ ] Snapshot created (Pre-TaskWright-Install)
- [ ] Screen recording software ready (optional)
- [ ] Test plan printed/accessible

**During Test**:
- [ ] Follow steps in order
- [ ] Take screenshots at each checkpoint
- [ ] Document any unexpected behavior
- [ ] Note duration of each phase

**Post-Test**:
- [ ] Complete test results document
- [ ] Upload screenshots
- [ ] Create fix tasks if needed
- [ ] Update baseline documentation
- [ ] Share results with team

---

**You're ready to validate TaskWright end-to-end! Good luck! 🚀**
