/feature-plan lets build the application infrastructure
I'll help you plan the application infrastructure for this FastAPI project. Let me execute the /feature-plan command workflow. First, let me understand the current state of the codebase to provide context for the planning.
Task:Explore current project structure
IN
Explore this FastAPI project to understand its current state:

1. What files and directories currently exist?
2. Is there already any infrastructure set up (database, config, etc.)?
3. What is the current project structure?

Be thorough but quick - I need to understand what exists before planning infrastructure.
Globpattern: "**/{src,tests,alembic,requirements}/**"
No files found
Bash Display directory tree structure
IN
tree -L 3 /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test 2>/dev/null || find /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test -type d | head -30

OUT
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/migrations
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/completed
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/in_progress
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/backlog
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/in_review
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/blocked
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tests
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tests/unit
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tests/integration
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tests/e2e
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/stacks
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/agents
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/hooks
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/rules
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/rules/database
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/rules/guidance
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/rules/api
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/core
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/dependencies
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/models
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/schemas
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/testing
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/crud
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/db
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/templates/api
/Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/commands
Bash List docs directory
IN
ls -la /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/docs

OUT
total 0
drwxr-xr-x@ 4 richardwoollcott  staff  128 Dec 31 09:27 .
drwxr-xr-x@ 8 richardwoollcott  staff  256 Dec 31 09:27 ..
drwxr-xr-x@ 3 richardwoollcott  staff   96 Dec 31 09:27 adr
drwxr-xr-x@ 3 richardwoollcott  staff   96 Dec 31 09:27 state
Read state
Bash List root-level files
IN
find /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test -maxdepth 1 -type f

OUT
0
Bash List agents directory
IN
ls -la /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.claude/agents/

OUT
total 1504
drwxr-xr-x@ 40 richardwoollcott  staff   1280 Dec 31 09:27 .
drwxr-xr-x@ 13 richardwoollcott  staff    416 Dec 31 09:27 ..
-rw-r--r--@  1 richardwoollcott  staff  27444 Dec 31 09:27 agent-content-enhancer-ext.md
-rw-r--r--@  1 richardwoollcott  staff  17102 Dec 31 09:27 agent-content-enhancer.md
-rw-r--r--@  1 richardwoollcott  staff  38419 Dec 31 09:27 architectural-reviewer-ext.md
-rw-r--r--@  1 richardwoollcott  staff   6222 Dec 31 09:27 architectural-reviewer.md
-rw-r--r--@  1 richardwoollcott  staff  13570 Dec 31 09:27 build-validator-ext.md
-rw-r--r--@  1 richardwoollcott  staff   3522 Dec 31 09:27 build-validator.md
-rw-r--r--@  1 richardwoollcott  staff  19724 Dec 31 09:27 clarification-questioner.md
-rw-r--r--@  1 richardwoollcott  staff  20459 Dec 31 09:27 code-reviewer-ext.md
-rw-r--r--@  1 richardwoollcott  staff   9174 Dec 31 09:27 code-reviewer.md
-rw-r--r--@  1 richardwoollcott  staff   4186 Dec 31 09:27 complexity-evaluator-ext.md
-rw-r--r--@  1 richardwoollcott  staff  14411 Dec 31 09:27 complexity-evaluator.md
-rw-r--r--@  1 richardwoollcott  staff  40725 Dec 31 09:27 database-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   6033 Dec 31 09:27 database-specialist.md
-rw-------@  1 richardwoollcott  staff  22464 Dec 31 09:27 debugging-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   7178 Dec 31 09:27 debugging-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  55076 Dec 31 09:27 devops-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   2984 Dec 31 09:27 devops-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  25389 Dec 31 09:27 fastapi-database-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   3646 Dec 31 09:27 fastapi-database-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  28426 Dec 31 09:27 fastapi-database-specialist.md.bak
-rw-r--r--@  1 richardwoollcott  staff  14948 Dec 31 09:27 fastapi-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   5798 Dec 31 09:27 fastapi-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  20164 Dec 31 09:27 fastapi-specialist.md.bak
-rw-r--r--@  1 richardwoollcott  staff   2564 Dec 31 09:27 fastapi-testing-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff  17249 Dec 31 09:27 fastapi-testing-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  19209 Dec 31 09:27 fastapi-testing-specialist.md.bak
-rw-r--r--@  1 richardwoollcott  staff  32817 Dec 31 09:27 git-workflow-manager-ext.md
-rw-r--r--@  1 richardwoollcott  staff  17365 Dec 31 09:27 git-workflow-manager.md
-rw-r--r--@  1 richardwoollcott  staff  13898 Dec 31 09:27 pattern-advisor-ext.md
-rw-r--r--@  1 richardwoollcott  staff  11302 Dec 31 09:27 pattern-advisor.md
-rw-r--r--@  1 richardwoollcott  staff  46203 Dec 31 09:27 security-specialist-ext.md
-rw-r--r--@  1 richardwoollcott  staff   2898 Dec 31 09:27 security-specialist.md
-rw-r--r--@  1 richardwoollcott  staff  60078 Dec 31 09:27 task-manager-ext.md
-rw-r--r--@  1 richardwoollcott  staff  12601 Dec 31 09:27 task-manager.md
-rw-r--r--@  1 richardwoollcott  staff  10117 Dec 31 09:27 test-orchestrator-ext.md
-rw-r--r--@  1 richardwoollcott  staff  16309 Dec 31 09:27 test-orchestrator.md
-rw-r--r--@  1 richardwoollcott  staff  23732 Dec 31 09:27 test-verifier-ext.md
-rw-r--r--@  1 richardwoollcott  staff   4129 Dec 31 09:27 test-verifier.md
Bash List all task files
IN
find /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks -type f | sort

OUT
0
Bash Show recent git commits
IN
git -C /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test log --oneline -10

OUT
Exit code 128
fatal: your current branch 'main' does not have any commits yet
Read crud_base.py.template
Read router.py.template
This is a greenfield FastAPI project with templates but no actual code yet. Now I'll proceed with the feature planning workflow. Step 1: Review Scope Clarification
AskUserQuestion
OUT
User has answered your questions: "What aspects should the infrastructure analysis focus on?"="All aspects (Recommended)", "What trade-offs are you optimizing for?"="Balanced (Recommended)". You can now continue with the user's answers in mind.
Context A recorded: Focus = All aspects, Priority = Balanced Step 2: Creating review task
Skill
IN
{
  "skill": "task-create",
  "args": "Plan: build application infrastructure task_type:review priority:high"
}
OUT
Launching skill: task-create
# Task Create - Start a New Development Task

Create a new task with requirements, acceptance criteria, and optional BDD scenarios.

## Feature Detection

This command supports **graceful degradation** based on installed packages:

### GuardKit Only (Core Features)
```bash
# Basic task creation
/task-create "Add user authentication"
/task-create "Add user authentication" priority:high tags:[auth,security]
```

Available fields: `title`, `priority`, `tags`, `status`, `complexity`

### GuardKit + Require-Kit (Full Features)
```bash
# Advanced task creation with requirements management
/task-create "Add user authentication" epic:EPIC-001 feature:FEAT-003 requirements:[REQ-001]
/task-create "Add user authentication" epic:EPIC-001 export:jira bdd:[BDD-001]
```

Additional fields: `epic`, `feature`, `requirements`, `bdd_scenarios`, `export`

**Note**: Epic, feature, and requirements functionality requires [require-kit](https://github.com/requirekit/require-kit) to be installed. The command will gracefully skip these fields if require-kit is not available.

## Usage
```bash
/task-create <description> [options]
```

**Description**: A natural language description of what needs to be done (5-500 characters). The system automatically infers a concise title from the description.

**Examples**:
```bash
# Short, action-oriented (used as-is)
/task-create "Fix login bug"

# Detailed explanation (title auto-inferred)
/task-create "We need to add user authentication with JWT tokens and refresh token support for the API"
# → Title: "Add JWT user authentication"

# Problem description (title extracted)
/task-create "The login button styling is broken on mobile devices and needs to be fixed"
# → Title: "Fix mobile login button styling"
```

## Title Inference Algorithm

The system automatically generates concise, actionable titles from your descriptions using this algorithm:

### Inference Rules

**Rule 1: Short action-oriented descriptions (< 50 chars, starts with verb, no trailing punctuation)**
```bash
/task-create "Fix login bug"
# → Title: "Fix login bug" (used as-is)

/task-create "Add dark mode support"
# → Title: "Add dark mode support" (used as-is)
```

**Rule 2: Detailed descriptions (extract main action + object + qualifier)**
```bash
/task-create "We need to add user authentication with JWT tokens and refresh token support"
# → Identifies: Action="Add", Object="user authentication", Qualifier="JWT"
# → Title: "Add JWT user authentication"

/task-create "The login button styling is completely broken on mobile devices and needs immediate attention"
# → Identifies: Action="Fix", Object="login button styling", Qualifier="mobile"
# → Title: "Fix mobile login button styling"

/task-create "Implement a caching layer for API responses to improve performance"
# → Identifies: Action="Implement", Object="caching layer", Qualifier="API response"
# → Title: "Implement API response caching"
```

### Common Transformation Examples

| Description | Inferred Title |
|-------------|----------------|
| "Fix null pointer exception in UserService" | "Fix UserService null pointer" |
| "We need to add user authentication with JWT" | "Add JWT user authentication" |
| "The login button is broken on mobile" | "Fix mobile login button" |
| "Implement caching for API responses" | "Implement API response caching" |
| "Add dark mode" | "Add dark mode" (used as-is) |
| "Create component for user profile display" | "Create user profile component" |
| "Update database schema to support multi-tenancy" | "Update schema for multi-tenancy" |
| "Refactor authentication to use OAuth2" | "Refactor authentication for OAuth2" |

### Edge Cases

**Ambiguous descriptions** (system will ask for clarification):
```bash
/task-create "This needs to be done soon"
# → Error: Cannot infer clear action. Please provide a more specific description.
```

**Multiple actions** (uses first primary action):
```bash
/task-create "Add authentication and fix the logout bug"
# → Title: "Add authentication"
# → Suggestion: Consider creating separate tasks for "fix logout bug"
```

**Very long descriptions** (truncates to 10 words max):
```bash
/task-create "We need to completely redesign and refactor the entire authentication system to support multiple providers including OAuth2, SAML, and custom integrations"
# → Title: "Refactor authentication for multiple providers"
```

## Examples

```bash
# Simple, direct descriptions
/task-create "Fix login bug"
/task-create "Add dark mode support"
/task-create "Implement caching layer"

# Detailed problem descriptions (title auto-inferred)
/task-create "We need to add user authentication with JWT tokens for the API"
/task-create "The login button styling is broken on mobile devices"
/task-create "Implement a caching layer for API responses to improve performance"

# With priority and tags
/task-create "Add user authentication with JWT support" priority:high tags:[auth,security]

# Link to requirements immediately
/task-create "Implement OAuth2 authentication flow" requirements:[REQ-001,REQ-002]

# Link to epic for hierarchy and PM tool integration
/task-create "Add JWT authentication middleware" epic:EPIC-001

# Full specification with epic linking
/task-create "Implement complete authentication system with OAuth2" priority:high epic:EPIC-001 requirements:[REQ-001,REQ-002] bdd:[BDD-001]

# Epic linking with automatic PM tool integration
/task-create "Build authentication API endpoints" epic:EPIC-001 export:jira
```

## Task Structure

Creates a markdown file with metadata. The fields included depend on which packages are installed:

### Core Fields (GuardKit)
```markdown
---
id: TASK-A3F2
title: Add user authentication
status: backlog
created: 2024-01-15T10:00:00Z
updated: 2024-01-15T10:00:00Z
priority: high
tags: [auth, security]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---
```

### Extended Fields (GuardKit + Require-Kit)
```markdown
---
id: TASK-E01-B2C4
title: Add user authentication
status: backlog
created: 2024-01-15T10:00:00Z
updated: 2024-01-15T10:00:00Z
priority: high
tags: [auth, security]
complexity: 0
epic: EPIC-001                    # Requires require-kit
feature: FEAT-003                  # Requires require-kit
requirements: [REQ-001, REQ-002]  # Requires require-kit
external_ids:                      # Requires require-kit
  epic_jira: PROJ-123
  epic_linear: PROJECT-456
  jira: null        # Populated after export
  linear: null      # Populated after export
bdd_scenarios: [BDD-001]          # Requires require-kit
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add user authentication

## Description
[Generated from requirements or provided description]

## Acceptance Criteria
- [ ] User can log in with email/password
- [ ] Session tokens are secure (from REQ-001)
- [ ] Failed attempts are rate-limited (from REQ-002)

## Test Requirements
- [ ] Unit tests for authentication service
- [ ] Integration tests for login endpoint
- [ ] E2E tests for complete login flow

## Implementation Notes
[Space for implementation details]

## Test Execution Log
[Automatically populated by /task-work]
```

## Options

### Priority Levels
- `critical` - Must be done immediately
- `high` - Important, do soon
- `normal` - Standard priority (default)
- `low` - Can wait

### Status Values
- `backlog` - Not started (default)
- `in_progress` - Being worked on
- `in_review` - Implementation complete, under review
- `blocked` - Cannot proceed
- `completed` - Done and verified

### Linking Specifications
```bash
# Link requirements during creation
/task-create "Title" requirements:[REQ-001,REQ-002,REQ-003]

# Link BDD scenarios
/task-create "Title" bdd:[BDD-001,BDD-002]

# Link to epic (automatically inherits external tool configuration)
/task-create "Title" epic:EPIC-001

# Link to both epic and feature for hierarchy
/task-create "Title" epic:EPIC-001 feature:FEAT-003

# Export task directly to PM tool (in addition to epic export)
/task-create "Title" epic:EPIC-001 export:[jira,linear]

# Create task with automatic progress tracking setup
/task-create "Title" epic:EPIC-001 feature:FEAT-003 --track-progress

# Create task with quality gate configuration
/task-create "Title" epic:EPIC-001 --quality-gates coverage:90,security:required

# Create task with Agentecflow Stage 3 integration
/task-create "Title" epic:EPIC-001 --agentecflow-stage3
```

## Automatic Enrichment

When requirements and epics are linked, the task is automatically enriched with:
1. **Acceptance criteria** extracted from EARS requirements
2. **Test scenarios** from linked BDD specifications
3. **Priority inference** based on requirement priorities
4. **Suggested tags** from requirement domains
5. **Epic context** including external tool references and stakeholder information
6. **PM tool integration** inherited from linked epic configuration
7. **Feature hierarchy** if feature is specified or inferred from epic
8. **Progress tracking configuration** for automatic rollup to feature and epic
9. **Quality gate setup** based on epic and feature requirements
10. **Agentecflow Stage 3 integration** for implementation workflow tracking

### Example with Requirements and Epic
```bash
/task-create "User login" epic:EPIC-001 requirements:[REQ-001]
```

If REQ-001 states:
> When a user submits valid credentials, the system shall authenticate within 1 second

And EPIC-001 is configured with Jira (PROJ-123) and Linear (PROJECT-456):

The task will include:
- Acceptance criteria: "Authentication completes within 1 second"
- Test requirement: "Performance test for 1-second response time"
- Tag: "performance"
- Epic context: "Part of User Management System (EPIC-001)"
- External tool references: Inherited from epic configuration
- Stakeholder information: Pulled from epic metadata
- Priority alignment: Matches epic priority if not specified

## Task ID Generation

### Hash-Based ID Generation (Collision-Free)

**CRITICAL**: Task IDs MUST be unique. The system uses SHA-256 hashing to generate collision-free IDs.

```python
from lib.id_generator import generate_task_id, validate_task_id, check_duplicate

# Parse prefix from command args (optional)
prefix = None
for arg in args:
    if arg.startswith('prefix:'):
        prefix = arg.split(':', 1)[1].strip()
        break

# Generate hash-based ID
task_id = generate_task_id(prefix=prefix)

# Validate format (redundant but safe)
if not validate_task_id(task_id):
    raise ValueError(f"Generated invalid task ID: {task_id}")

# Pre-creation duplicate check (should never fail with hash IDs)
duplicate_path = check_duplicate(task_id)
if duplicate_path:
    raise ValueError(f"Duplicate task ID: {task_id}\nExisting: {duplicate_path}")
```

### Task ID Pattern

**Format**: `TASK-{hash}` or `TASK-{prefix}-{hash}`

- **Hash**: 4-6 character uppercase hexadecimal (SHA-256 based)
- **Prefix**: Optional 2-4 character uppercase alphanumeric namespace
- **Length Scaling**: Automatically adjusts based on task count
  - 0-499 tasks: 4 characters (e.g., `TASK-A3F2`)
  - 500-1,499 tasks: 5 characters (e.g., `TASK-A3F2D`)
  - 1,500+ tasks: 6 characters (e.g., `TASK-A3F2D7`)
- **Collision Risk**: <0.01% even at 5,000 tasks
- **Unique**: Cryptographically guaranteed uniqueness

### Examples

```bash
# Simple task (no prefix)
/task-create "Fix login bug"
# Generated: TASK-A3F8

# With epic prefix
/task-create "Add authentication" prefix:E01
# Generated: TASK-E01-B2C4

# With domain prefix
/task-create "Update installation guide" prefix:DOC
# Generated: TASK-DOC-F1A3

# With feature prefix
/task-create "Implement password reset" prefix:AUTH
# Generated: TASK-AUTH-D7E2

# Multiple tasks (each gets unique hash)
/task-create "Task 1"  # TASK-A3F2
/task-create "Task 2"  # TASK-B7D1
/task-create "Task 3"  # TASK-C4E5
```

### Prefix Parameter

**Syntax**: `prefix:{VALUE}`

**Valid Prefixes**:
- 2-4 uppercase alphanumeric characters
- Examples: `E01`, `DOC`, `AUTH`, `FIX`, `FEAT`
- Invalid: `e01` (lowercase), `X` (too short), `EXTRA` (too long)

**Use Cases**:
- **Epic Namespacing**: `prefix:E01`, `prefix:E02`
- **Domain Grouping**: `prefix:DOC`, `prefix:TEST`, `prefix:INFRA`
- **Type Categorization**: `prefix:FIX`, `prefix:FEAT`, `prefix:REFAC`

### Duplication Prevention

✅ **Collision Detection**:
- SHA-256 cryptographic hashing ensures uniqueness
- Pre-creation validation checks all task directories
- Automatic collision resolution (max 10 attempts)
- Clear error messages if duplicate detected

✅ **Directory Scanning**:
- Checks: `backlog/`, `in_progress/`, `in_review/`, `blocked/`, `completed/`
- O(1) lookup with cached registry (5-second TTL)
- Thread-safe with lock protection

✅ **Error Handling**:
```
❌ ERROR: Duplicate task ID: TASK-A3F2
   Existing file: tasks/backlog/TASK-A3F2-fix-login.md
```

### Backward Compatibility

**Reading Old Format Tasks**: ✅ Fully supported
- Can read: `TASK-001`, `TASK-004A`, `TASK-030B-1`
- Old IDs stored in `legacy_id` frontmatter field if needed
- New tasks always use hash format

**Migration**: No migration required - old and new formats coexist

## File Organization

Tasks are organized by status:
```
tasks/
├── backlog/
│   ├── TASK-A3F2-add-login.md
│   └── TASK-B7D1-reset-password.md
├── in_progress/
│   └── TASK-C4E5-user-profile.md
├── in_review/
│   └── TASK-E01-D2F8-notifications.md
├── blocked/
│   └── TASK-AUTH-A1B3-oauth-integration.md
└── completed/
    └── 2024-01/
        └── TASK-DOC-F9E2-data-export.md
```

## Review Task Detection

The system automatically detects when a task is likely a review/analysis task and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if any of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: architecture-review, code-review, decision-point, assessment
4. **Title keywords**: review, analyze, evaluate, assess, audit, investigation

### Detection Behavior

When a review task is detected, the system displays a suggestion:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

### Examples

```bash
# Explicit review task type
/task-create "Architectural review of authentication system" task_type:review

# Decision-making task
/task-create "Should we migrate to microservices?" decision_required:true

# Review tags
/task-create "Code quality assessment" tags:[code-review,assessment]

# Title-based detection
/task-create "Evaluate caching strategy options"
```

**Note**: The suggestion is informational only and doesn't block task creation. Users can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### See Also

- [task-review.md - Automatic Review Task Detection](./task-review.md#automatic-review-task-detection) - Full details on how detection works and what happens after task creation
- [task-review.md - Integration with /task-work](./task-review.md#integration-with-task-work) - Complete review → implementation → verification workflow

## Integration with Workflow

After creation, use the appropriate workflow based on task type:

### Implementation Workflow (Standard)
```bash
# 1. Create the task
/task-create "Implement user authentication" prefix:E01
# Output: Created TASK-E01-B2C4

# 2. Work on it (implementation + testing)
/task-work TASK-E01-B2C4 [--mode=standard|tdd|bdd]
# Automatically moves to appropriate state based on test results

# 3. Complete it (after review)
/task-complete TASK-E01-B2C4
# Archives to completed with timestamp
```

### Review Workflow (Analysis/Decision)
```bash
# 1. Create the review task
/task-create "Architectural review of authentication" task_type:review
# Output: Created TASK-REV-A3F2
# System suggests using /task-review

# 2. Execute review
/task-review TASK-REV-A3F2 --mode=architectural
# Runs analysis, generates report, presents findings

# 3. Make decision at checkpoint
# [A]ccept - Approve findings
# [I]mplement - Create implementation task
# [R]evise - Request deeper analysis
# [C]ancel - Discard review

# 4. (Optional) Implement recommendations
/task-work TASK-IMP-B4D1  # If [I]mplement was chosen

# 5. Complete review task
/task-complete TASK-REV-A3F2
```

## Batch Creation

Create multiple related tasks:
```bash
/task-create-batch epic:USER-MGMT tasks:[
  "Implement login form",
  "Add password reset",
  "Create user profile page",
  "Add session management"
]
```

Creates TASK-XXX through TASK-XXX+3 with shared epic and tags.

## Templates

Use predefined templates for common task types:
```bash
# CRUD operations
/task-create --template=crud entity:Product

# API endpoint
/task-create --template=api-endpoint method:POST path:/api/users

# UI component
/task-create --template=ui-component name:UserProfile
```

## Phase 2.5: Complexity Evaluation (TASK-005)

During task creation, the system automatically evaluates task complexity to detect oversized tasks early and recommend splitting when appropriate.

### Upfront Complexity Estimation

**Purpose**: Prevent oversized tasks from entering backlog by evaluating complexity BEFORE implementation.

**Evaluation Inputs**:
- Task title and description
- Linked requirements (EARS notation analysis)
- Estimated effort (if provided)
- Technology stack context

**Complexity Scoring (0-10 Scale)**:

Tasks are scored based on these factors:

1. **Requirements Complexity (0-3 points)**
   - 1-2 EARS requirements: 1 point
   - 3-4 EARS requirements: 2 points
   - 5+ EARS requirements: 3 points

2. **Architectural Patterns (0-2 points)**
   - Simple CRUD operations: 0 points
   - Moderate patterns (validation, state management): 1 point
   - Complex patterns (event sourcing, CQRS, multi-tenant): 2 points

3. **Risk Indicators (0-3 points)**
   - Low risk (UI updates, simple logic): 0 points
   - Medium risk (external APIs, moderate data changes): 1 point
   - High risk (security, schema changes, breaking changes): 3 points

4. **External Dependencies (0-2 points)**
   - 0 new dependencies: 0 points
   - 1-2 new dependencies: 1 point
   - 3+ new dependencies: 2 points

**Complexity Levels**:
- **1-3 (Simple)**: 🟢 Single developer, <4 hours, straightforward implementation
- **4-6 (Medium)**: 🟡 Single developer, 4-8 hours, may require research
- **7-8 (Complex)**: 🟡 Consider breakdown, >8 hours, multiple sub-systems
- **9-10 (Very Complex)**: 🔴 MUST break down, unclear scope, high risk

### Automatic Split Recommendations

When complexity ≥ 7, the system suggests breaking the task into smaller subtasks:

```bash
/task-create "Implement event sourcing for orders" epic:EPIC-001 feature:FEAT-001.2 requirements:[REQ-042,REQ-043]

# System evaluates:
ESTIMATED COMPLEXITY: 9/10 (Very Complex)

COMPLEXITY FACTORS:
  🔴 Requirements suggest 8+ files (Event Sourcing pattern)
  🔴 New architecture pattern (Event Sourcing unfamiliar)
  🔴 High risk: State consistency, event replay
  🟡 Multiple new dependencies (event store libraries)

⚠️  RECOMMENDATION: Consider splitting this task

SUGGESTED BREAKDOWN:
1. TASK-k3m7.1: Design Event Sourcing architecture (Complexity: 5/10)
2. TASK-k3m7.2: Implement EventStore infrastructure (Complexity: 6/10)
3. TASK-k3m7.3: Implement Order aggregate with events (Complexity: 5/10)
4. TASK-k3m7.4: Implement CQRS handlers (Complexity: 5/10)
5. TASK-k3m7.5: Testing and integration (Complexity: 6/10)

OPTIONS:
1. [C]reate - Create this task as-is (complexity 9/10)
2. [S]plit - Create 5 subtasks instead (recommended)
3. [M]odify - Adjust task scope to reduce complexity
4. [A]bort - Cancel task creation

Your choice [S/C/M/A]:
```

### Interactive Complexity Mode

```bash
# Enable interactive complexity evaluation
/task-create "Title" epic:EPIC-001 feature:FEAT-001.2 --interactive-complexity

# System prompts for confirmation at each complexity threshold
# Allows human override of automatic recommendations
```

### Complexity Metadata

Tasks store complexity evaluation results in frontmatter:

```yaml
---
id: TASK-k3m7.5
complexity_evaluation:
  score: 7
  level: "complex"
  factors:
    - name: "requirements_complexity"
      score: 2
      justification: "3-4 EARS requirements"
    - name: "pattern_complexity"
      score: 1
      justification: "Moderate patterns (validation, state)"
    - name: "risk_level"
      score: 2
      justification: "Medium risk (external API dependencies)"
    - name: "dependencies"
      score: 2
      justification: "3+ new dependencies"
  breakdown_suggested: true
  breakdown_accepted: false
  user_decision: "create_as_is"
  user_justification: "Team has event sourcing experience"
---
```

### Benefits

- **Early Detection**: Identify oversized tasks before they enter workflow
- **Better Planning**: More accurate sprint planning with right-sized tasks
- **Reduced Rework**: Less mid-implementation task splitting
- **Improved Velocity**: Consistent task completion rates
- **Risk Mitigation**: High-risk tasks flagged and decomposed early

## Validation

Tasks are validated before creation:
- ✅ Description must be 5-500 characters
- ✅ Inferred title must be 5-100 characters
- ✅ Description must contain identifiable action (add, fix, implement, etc.)
- ✅ No duplicate titles in active tasks
- ✅ Linked requirements must exist
- ✅ Linked BDD scenarios must exist
- ✅ Epic must be valid if specified
- ✅ Feature must belong to specified epic if both are provided
- ✅ Export tools must be configured and accessible
- ✅ Complexity score calculated (if requirements linked)

### Validation Examples

**✅ Valid descriptions**:
```bash
/task-create "Fix login bug"                                    # Clear action, concise
/task-create "Add user authentication"                          # Clear action, specific
/task-create "We need to implement OAuth2 for the API"         # Detailed, inferable
```

**❌ Invalid descriptions**:
```bash
/task-create "Do it"                                           # Too vague (< 5 chars meaningful)
/task-create "This"                                            # No identifiable action
/task-create "Something something something..."                # No clear action verb
```

**⚠️ Warnings (task created but flagged)**:
```bash
/task-create "Add auth and fix logout and update profile"     # Multiple actions (suggest split)
/task-create "The system is slow"                             # Missing action (inferred: "Fix system performance")
```

## Best Practices

### Writing Good Descriptions

1. **Start with action verbs** when possible:
   - ✅ "Fix login button on mobile"
   - ✅ "Add JWT authentication"
   - ✅ "Implement caching layer"
   - ❌ "Login button issue" (no action)

2. **Be specific** but concise:
   - ✅ "Fix null pointer in UserService.authenticate()"
   - ❌ "Fix bug" (too vague)
   - ❌ "We need to fix the bug where the UserService.authenticate() method throws a null pointer exception when the user object is not properly initialized during the authentication flow" (too verbose)

3. **Focus on one primary action**:
   - ✅ "Add user authentication"
   - ❌ "Add authentication and fix logout and update profile" (multiple actions → split tasks)

4. **Use natural language**:
   - ✅ "The login button is broken on mobile devices"
   - ✅ "We need to implement caching for API responses"
   - System will extract clear title automatically

### Other Best Practices

5. **Link specifications**: Always link to requirements for traceability
6. **Set priority**: Helps with sprint planning
7. **Use tags**: Improves discoverability and filtering

## Troubleshooting

### "Cannot infer clear action from description"

**Problem**: Description is too vague or doesn't contain an identifiable action verb.

```bash
/task-create "This needs work"
# ❌ Error: Cannot infer clear action from description
```

**Solutions**:
- Add an action verb: "Fix this login issue"
- Be more specific: "Refactor authentication module"
- Describe the problem: "The login page is broken on Safari"

### "Inferred title too short/long"

**Problem**: Extracted title doesn't meet 5-100 character requirement.

```bash
/task-create "Fix it"
# ⚠️ Warning: Inferred title too short. Using description as-is.
```

**Solutions**:
- Provide more context: "Fix login validation error"
- Be more specific about what needs fixing

### "Multiple actions detected"

**Problem**: Description contains multiple distinct actions.

```bash
/task-create "Add authentication and fix the logout bug and update the profile page"
# ⚠️ Warning: Multiple actions detected. Consider creating separate tasks.
# Created: "Add authentication"
# Suggestions:
#   - /task-create "Fix logout bug"
#   - /task-create "Update profile page"
```

**Solutions**:
- Split into separate tasks as suggested
- Focus on the primary action
- Accept the inferred title if it covers the main work

### Title differs from expectation

**Problem**: Inferred title doesn't match what you intended.

```bash
/task-create "We really need to get the authentication working properly"
# Inferred: "Fix authentication"
# Expected: "Add authentication"
```

**Solutions**:
- Review the inferred title in the output
- If incorrect, cancel and rephrase:
  ```bash
  /task-create "Add authentication support to the API"
  # Inferred: "Add API authentication"
  ```
- Start with the action verb: "Add authentication..."

## Output Format

### Success
```
✅ Task Created: TASK-E01-B2C4

📋 Task Details
Description: "We need to add user authentication with JWT tokens and refresh token support"
Inferred Title: Add JWT user authentication
ID Format: Hash-based with prefix (E01)
Priority: high
Status: backlog
Tags: [auth, security]
Epic: EPIC-001 (User Management System)
Feature: FEAT-003 (Authentication Module)

📑 Linked Specifications
Requirements: REQ-001, REQ-002
BDD Scenarios: BDD-001

🔗 External Integration
Epic Context: User Management System
Jira Epic: PROJ-123
Linear Initiative: PROJECT-456
Task Export: Will be created in linked tools

📁 File Location
tasks/backlog/TASK-E01-B2C4-add-jwt-user-authentication.md

Next Steps:
1. Review task details
2. When ready: /task-work TASK-E01-B2C4
3. Track progress: /task-status TASK-E01-B2C4 --hierarchy
4. Auto-sync to PM tools: /task-sync TASK-E01-B2C4
5. Complete task: /task-complete TASK-E01-B2C4
```

### With Warnings
```
✅ Task Created: TASK-A3F2

⚠️ Warnings:
- REQ-003 not found, skipped
- No BDD scenarios linked
- Consider adding test requirements

📋 Task Details
[... rest of output ...]
```

## Error Handling

### Duplicate Title
```
❌ Task creation failed

A task with this title already exists:
- TASK-p9r3: Add user authentication (in_progress)

Suggestions:
- Use a more specific title
- Check if you meant to update TASK-p9r3
```

### Invalid Requirements
```
❌ Task creation failed

Requirements not found:
- REQ-999 does not exist
- REQ-1000 does not exist

Available requirements:
- REQ-001: User login
- REQ-002: Password reset
- REQ-003: Session management
```

## PM Tool Integration

### Epic-Level Integration
When linking tasks to epics, the task automatically inherits:
- **External tool configuration** from the epic
- **Project/workspace mappings** to appropriate PM tools
- **Stakeholder assignments** and notification settings
- **Progress tracking** that rolls up to epic metrics

### Automatic Task Export
```bash
# Task will be created in Jira and Linear if epic is configured for both
/task-create "Implement login" epic:EPIC-001

# Explicit export to specific tools
/task-create "Implement login" epic:EPIC-001 export:jira

# Export to multiple tools
/task-create "Implement login" epic:EPIC-001 export:[jira,linear,github]
```

### Task-to-Story Mapping
Tasks created with epic linking are mapped to external tools as:
- **Jira**: Sub-task of epic or story within epic
- **Linear**: Issue linked to initiative (epic)
- **GitHub**: Issue linked to epic project/milestone
- **Azure DevOps**: Task work item linked to epic work item

### Progress Synchronization
Task progress automatically updates epic progress:
- Task status changes trigger epic sync
- Epic progress calculations include task completion
- External tool progress bars reflect task-level progress
- Stakeholder notifications include task-level updates

## Streamlined Workflow

This command is part of the unified 3-command workflow:
1. `/task-create` - Create task with requirements and epic hierarchy
2. `/task-work` - Implement and test together
3. `/task-complete` - Finalize after review and sync progress

The streamlined workflow ensures testing is never skipped and reduces command complexity by 70%.

## Enhanced Phase 3 Integration

### Agentecflow Stage 3 Integration
```bash
# Create task optimized for Stage 3: Engineering
/task-create "Implement authentication API" epic:EPIC-001 feature:FEAT-003 --agentecflow-stage3

# Includes:
# - Automatic quality gate configuration
# - Progress tracking for implementation metrics
# - Integration with AI/human collaboration tracking
# - Stage 3 → Stage 4 transition preparation
```

### Complete Task Lifecycle
```bash
# 1. Create task with full hierarchy context
/task-create "User login implementation" epic:EPIC-001 feature:FEAT-003 requirements:[REQ-001]
# Created: TASK-s4t8

# 2. Begin implementation with context awareness
/task-work TASK-s4t8 --with-context

# 3. Monitor progress with hierarchy visibility
/task-status TASK-s4t8 --hierarchy

# 4. Sync progress to PM tools and rollup to feature/epic
/task-sync TASK-s4t8 --rollup-progress

# 5. Complete with validation and automatic rollup
/task-complete TASK-s4t8
```

### Quality Gates and Progress Tracking
```bash
# Create task with enhanced quality requirements
/task-create "Payment processing" epic:EPIC-002 --quality-gates coverage:95,performance:200ms,security:required

# Progress automatically rolls up:
# Task Progress → Feature Progress → Epic Progress → Portfolio Progress
```

## Integration with Epic Management Commands

### Workflow Integration
```bash
# Create epic first
/epic-create "User Management" export:jira

# Create features for the epic
/feature-create "Authentication" epic:EPIC-001

# Create tasks for features (enhanced with Phase 3 capabilities)
/task-create "Implement login" epic:EPIC-001 feature:FEAT-001 --track-progress
# Created: TASK-u7v2

# Work on task (automatically updates epic progress)
/task-work TASK-u7v2 --sync-progress

# Progress is visible in epic status with full hierarchy
/epic-status EPIC-001 --hierarchy
```

### Cross-Command References
- Tasks link to epics and features for complete hierarchy
- Epic progress automatically calculated from task completion
- Task completion triggers epic sync to external tools
- External tool IDs are preserved throughout the workflow
- Real-time progress rollup across all hierarchy levels

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

**After creating the task, you MUST STOP and wait for the user to invoke `/task-work`.**

### What You Should Do:
1. ✅ Create the task file in `tasks/backlog/TASK-XXX-title.md`
2. ✅ Display the task details and file location
3. ✅ Show "Next Steps" with `/task-work TASK-XXX` command
4. ✅ **STOP HERE - Do not proceed with implementation**

### What You Should NOT Do:
1. ❌ **DO NOT** start implementing the task
2. ❌ **DO NOT** write any code
3. ❌ **DO NOT** create any files beyond the task markdown file
4. ❌ **DO NOT** use the TodoWrite tool to create implementation todos

### Why This Matters:
The `/task-work` command provides:
- **Architectural Review** (Phase 2.5): SOLID/DRY/YAGNI evaluation BEFORE coding
- **Test Enforcement** (Phase 4.5): Automatic test fixing with 100% pass rate guarantee
- **Code Review** (Phase 5): Quality verification after implementation
- **Plan Audit** (Phase 5.5): Scope creep detection

**If you implement directly, you bypass all quality gates and the entire GuardKit workflow!**

### Correct Workflow:
```bash
User: /task-create "Add temperature conversion endpoint"
Claude: ✅ Task Created: TASK-w3x9
        Next Steps: /task-work TASK-w3x9
        [STOPS HERE - WAITS FOR USER]

User: /task-work TASK-w3x9
Claude: [Executes Phases 2-5.5 with all quality gates]
```

### Exception:
Only proceed with implementation if the user explicitly says:
- "Create the task and implement it"
- "Create and work on the task"
- "Create the task and start working"

Otherwise, **ALWAYS STOP** after task creation.


ARGUMENTS: Plan: build application infrastructure task_type:review priority:high
I'll create the review task for planning the application infrastructure.
Write TASK-REV-8A3F-plan-build-application-infrastructure.md
80 lines
---
id: TASK-REV-8A3F
title: "Plan: Build application infrastructure"
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
task_type: review
tags: [infrastructure, planning, architecture]
complexity: 0
clarification:
  context_a:
    timestamp: 2025-12-31T00:00:00Z
    decisions:
      focus: all
      tradeoff: balanced
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan - Build application infrastructure

## Description

Create a comprehensive plan for building the FastAPI application infrastructure from scratch. This is a greenfield project with templates available but no actual implementation yet.

## Current State

- **Templates Available**: 10 production-ready templates in `.claude/templates/`
- **No Source Code**: `src/` directory does not exist
- **No Dependencies**: `requirements/` directory does not exist
- **No Configuration**: `pyproject.toml`, `.env`, `alembic.ini` not created
- **Technology Stack**: FastAPI, SQLAlchemy 2.0, Pydantic 2.0, Alembic, pytest

## Infrastructure Components to Plan

1. **Project Configuration**
   - pyproject.toml with tool configurations
   - requirements/ directory with base.txt, dev.txt, prod.txt
   - .env.example for environment variables

2. **Core Application**
   - src/ directory structure
   - main.py FastAPI application
   - core/config.py settings management

3. **Database Layer**
   - db/session.py async session management
   - db/base.py SQLAlchemy Base
   - Alembic configuration and initial migration

4. **API Infrastructure**
   - Exception handlers
   - Middleware setup
   - Health check endpoints

5. **Testing Infrastructure**
   - conftest.py with fixtures
   - Test database configuration
   - Coverage configuration

## Review Focus

- All aspects (comprehensive analysis)
- Balanced trade-offs (speed, quality, maintainability)

## Acceptance Criteria

- [ ] Complete infrastructure plan with implementation order
- [ ] Clear subtask breakdown for each component
- [ ] Dependency graph for parallel execution opportunities
- [ ] Effort estimation per component
- [ ] Risk assessment for complex areas

## Implementation Notes

This is a REVIEW task. Use `/task-review TASK-REV-8A3F` to execute the analysis.
Step 2 Complete: Review task created: TASK-REV-8A3F

✅ Feature planning task created: TASK-REV-8A3F
📋 Title: Plan: Build application infrastructure
📁 Location: tasks/backlog/TASK-REV-8A3F-plan-build-application-infrastructure.md

Proceeding to review analysis...
Step 3: Executing decision review
Skill
IN
{
  "skill": "task-review",
  "args": "TASK-REV-8A3F --mode=decision --depth=standard"
}
OUT
Launching skill: task-review
# Task Review - Structured Analysis and Decision-Making

Execute structured review and analysis workflows for tasks that require assessment, evaluation, or decision-making rather than implementation.

## Command Syntax

```bash
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT]
```

## Available Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Review mode (architectural, code-quality, decision, technical-debt, security) |
| `--depth=DEPTH` | Review depth (quick, standard, comprehensive) |
| `--output=FORMAT` | Output format (markdown, json, both) |
| `--no-questions` | Skip review scope clarification |
| `--with-questions` | Force clarification even for simple reviews |
| `--defaults` | Use clarification defaults without prompting |

## Overview

The `/task-review` command provides a dedicated workflow for analysis and decision-making tasks, separate from the implementation-focused `/task-work` command.

**Use `/task-review` for**:
- Architectural reviews and assessments
- Code quality evaluations
- Technical decision analysis
- Technical debt assessment
- Security audits
- Root cause analysis

**Use `/task-work` for**:
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if **any** of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. **Title keywords**: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

### Suggestion Behavior

When a review task is detected during `/task-create`, you'll see:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

**Important**: The suggestion is **informational only** and doesn't block task creation. You can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### Detection Examples

**Example 1: Explicit task_type**
```bash
/task-create "Architectural review of authentication system" task_type:review
# ✅ Detected: Explicit task_type field
```

**Example 2: Decision required flag**
```bash
/task-create "Should we migrate to microservices?" decision_required:true
# ✅ Detected: Decision flag indicates review/analysis needed
```

**Example 3: Review tags**
```bash
/task-create "Code quality assessment" tags:[code-review,assessment]
# ✅ Detected: Tags indicate review task
```

**Example 4: Title keywords**
```bash
/task-create "Evaluate caching strategy options"
# ✅ Detected: "Evaluate" keyword in title
```

**Example 5: Not a review task**
```bash
/task-create "Implement user authentication"
# ❌ Not detected: Implementation task, no review indicators
# Suggestion not shown, proceeds normally
```

### Why Detection Helps

1. **Command Selection**: Helps you choose `/task-review` vs `/task-work`
2. **Workflow Efficiency**: Review tasks skip implementation phases
3. **Better Reports**: Review mode generates structured analysis reports
4. **Decision Support**: Review tasks include decision checkpoints ([A]ccept/[R]evise/[I]mplement/[C]ancel)

### Overriding Detection

If you want to use `/task-work` for a task that was detected as review:

```bash
# Task detected as review, but you want implementation workflow
/task-create "Review authentication architecture"
# [Suggestion shown]
# Choose Y to create task

# Use /task-work instead of /task-review
/task-work TASK-XXX
# Works fine, detection is only a suggestion
```

### See Also

- [task-create.md - Review Task Detection](./task-create.md#review-task-detection)
- [CLAUDE.md - Review Workflow](../../CLAUDE.md#review-vs-implementation-workflows)

## Examples

```bash
# Basic architectural review (default mode)
/task-review TASK-042

# Code quality review with comprehensive depth
/task-review TASK-043 --mode=code-quality --depth=comprehensive

# Quick decision analysis with summary output
/task-review TASK-044 --mode=decision --depth=quick --output=summary

# Security audit with detailed report
/task-review TASK-045 --mode=security --output=detailed
```

## Clarification Integration

The `/task-review` command uses the `clarification-questioner` subagent to collect review scope preferences before analysis begins.

### Context A: Review Scope Clarification (Phase 1)

**Purpose**: Clarify what the review should focus on and what trade-offs to prioritize before analysis begins.

**When Triggered**:
- Decision mode tasks (always, unless --no-questions)
- Complexity ≥4 (unless quick depth or --no-questions)
- User specifies --with-questions flag

**When Skipped**:
- User specifies --no-questions flag
- Quick depth reviews (complexity <4)
- Review scope already well-defined in task description

**Example Flow**:

```bash
/task-review TASK-b2c4 --mode=decision --depth=standard

Phase 1: Loading context...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SCOPE CLARIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Review Focus
    What aspects should this analysis focus on?

    [A]ll aspects - Comprehensive analysis
    [T]echnical only - Focus on technical feasibility
    [R]chitecture - Architecture and design patterns
    [P]erformance - Performance and scalability
    [S]ecurity - Security considerations

    Default: [A]ll aspects
    Your choice [A/T/R/P/S]: A

Q2. Analysis Depth
    How deep should the analysis go?

    [Q]uick (surface-level) - 15-30 minutes
    [S]tandard (recommended) - 1-2 hours
    [D]eep (comprehensive) - 4-6 hours

    Default: [S]tandard (recommended)
    Your choice [Q/S/D]: S

Q3. Trade-off Priority
    What trade-offs are you optimizing for?

    [S]peed of delivery
    [Q]uality/reliability
    [C]ost
    [M]aintainability
    [B]alanced

    Default: [B]alanced
    Your choice [S/Q/C/M/B]: Q

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 3 decisions - proceeding with review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Analyzing with focus: All aspects, Quality/reliability priority...
```

**Questions Asked** (Context A):
1. **Review Focus** - What aspects to analyze (all/technical/architecture/performance/security)
2. **Analysis Depth** - How thorough to be (quick/standard/deep)
3. **Trade-off Priority** - What to optimize for (speed/quality/cost/maintainability/balanced)
4. **Specific Concerns** - Any particular areas of concern (free-form, optional)
5. **Extensibility** - Consider future extensibility? (yes/no/default based on complexity)

**Benefits**:
- Focuses analysis on what matters most
- Sets appropriate depth expectations
- Captures user priorities for decision-making
- Reduces back-and-forth clarification during review

### Context B: Implementation Preferences ([I]mplement Handler)

**Purpose**: Clarify how subtasks should be created and executed when user chooses to implement review findings.

**When Triggered**:
- User selects [I]mplement at decision checkpoint
- Multiple subtasks will be created (≥2)
- Unless --no-questions flag specified

**When Skipped**:
- User specifies --no-questions flag
- Single subtask only
- User selects [A]ccept, [R]evise, or [C]ancel instead

**Example Flow**:

```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review Results:
  Architecture Score: 72/100
  Findings: 8
  Recommendations: 5

Key Recommendations:
  1. Migrate to JWT-based authentication (Recommended)
  2. Implement Argon2 password hashing
  3. Add rate limiting middleware
  4. Update session management logic
  5. Add integration tests for auth flow

Decision Options:
  [A]ccept - Approve findings
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation tasks
  [C]ancel - Discard review

Your choice: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Approach Selection
    The review identified 3 approaches. Recommended: JWT with refresh tokens.
    Which should subtasks follow?

    [1] JWT with refresh tokens (Recommended)
    [2] Session-based auth
    [3] OAuth 2.0 integration
    [R]ecommend for me

    Default: [R]ecommend for me
    Your choice [1/2/3/R]: 1

Q2. Execution Preference
    How should 5 subtasks be executed?

    [M]aximize parallel - Use Conductor workspaces
    [S]equential - Simpler execution
    [D]etect automatically (recommended)

    Default: [D]etect automatically (recommended)
    Your choice [M/S/D]: M

Q3. Testing Depth
    What testing depth for subtasks?

    [F]ull TDD (test-first for all subtasks)
    [S]tandard (quality gates only)
    [M]inimal (compilation only)
    [D]efault (based on complexity)

    Default: [D]efault (based on complexity)
    Your choice [F/S/M/D]: S

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Creating 5 subtasks with preferences:
  - Approach: JWT with refresh tokens
  - Execution: Parallel (3 Conductor workspaces)
  - Testing: Standard (quality gates)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Questions Asked** (Context B):
1. **Approach Selection** - Which recommended approach to follow (from review options)
2. **Execution Preference** - Parallel vs sequential execution (Conductor integration)
3. **Testing Depth** - Testing rigor for subtasks (TDD/standard/minimal/default)
4. **Constraints** - Any implementation constraints (time/resource/scope/none)
5. **Workspace Naming** - Conductor workspace naming preference (auto/custom/none)

**Benefits**:
- Eliminates ambiguity about which approach to implement
- Optimizes for Conductor parallel execution when beneficial
- Sets appropriate testing expectations for all subtasks
- Captures constraints upfront to avoid rework

### Complexity-Based Gating

The `clarification-questioner` subagent uses task complexity to determine when clarification is needed.

**Gating Rules**:

| Complexity | Review Mode | Behavior |
|------------|-------------|----------|
| 0-3 | Any | Skip (unless --with-questions) |
| 4-6 | decision, architectural | Ask |
| 4-6 | code-quality, technical-debt, security | Skip (unless --with-questions) |
| 7-10 | Any | Always ask (unless --no-questions) |

**Flags**:
- `--no-questions`: Skip clarification entirely
- `--with-questions`: Force clarification
- `--defaults`: Apply defaults without prompting
- `--answers="..."`: Inline answers for automation

**Examples**:

```bash
# Complexity 3, code-quality → No clarification
/task-review TASK-XXX --mode=code-quality
# Phase 1: Loads context (no questions)
# Phase 5: [I]mplement → Uses auto-detection

# Complexity 5, decision → Context A questions
/task-review TASK-XXX --mode=decision
# Phase 1: Asks focus, depth, tradeoffs
# Phase 5: [I]mplement → Context B questions (if 2+ subtasks)

# Complexity 8, architectural → Both contexts
/task-review TASK-XXX --mode=architectural
# Phase 1: Asks all Context A questions
# Phase 5: [I]mplement → Asks all Context B questions

# Override gating with --with-questions
/task-review TASK-XXX --mode=code-quality --with-questions
# Phase 1: Forces Context A questions
# Phase 5: [I]mplement → Forces Context B questions

# Disable all clarification
/task-review TASK-XXX --mode=decision --no-questions
# Phase 1: Skips Context A
# Phase 5: [I]mplement → Skips Context B
```

**Why Complexity Gating?**

1. **Simple reviews** (0-3): Scope is clear, defaults work fine
2. **Medium reviews** (4-6): Clarification valuable for decision/architectural modes
3. **Complex reviews** (7-10): Clarification essential to focus effort correctly

This ensures clarification adds value without creating unnecessary friction.

## Flags

### --mode=MODE

Specifies the type of review to perform.

**Values**:
- `architectural` (default) - Architecture and design review
- `code-quality` - Code quality and maintainability assessment
- `decision` - Technical decision analysis
- `technical-debt` - Technical debt inventory and prioritization
- `security` - Security audit and vulnerability assessment

**Examples**:
```bash
/task-review TASK-XXX --mode=architectural
/task-review TASK-XXX --mode=code-quality
/task-review TASK-XXX --mode=decision
```

### --depth=DEPTH

Controls the thoroughness of the review.

**Values**:
- `quick` - Surface-level review (15-30 minutes)
- `standard` (default) - Thorough review (1-2 hours)
- `comprehensive` - Exhaustive analysis (4-6 hours)

**Examples**:
```bash
/task-review TASK-XXX --depth=quick
/task-review TASK-XXX --depth=standard
/task-review TASK-XXX --depth=comprehensive
```

### --output=FORMAT

Specifies the output format for the review report.

**Values**:
- `summary` - Executive summary only
- `detailed` (default) - Full analysis report
- `presentation` - Presentation/slide deck format

**Examples**:
```bash
/task-review TASK-XXX --output=summary
/task-review TASK-XXX --output=detailed
/task-review TASK-XXX --output=presentation
```

### --no-questions

Disables all clarification questions (Context A and Context B).

**When to Use**:
- Automated/CI workflows where user input not available
- Well-defined reviews where defaults are acceptable
- Quick iterations where minimal friction desired

**Behavior**:
- Context A: Skipped, uses review mode defaults
- Context B: Skipped, uses auto-detection for all preferences
- No prompts shown during review or [I]mplement

**Examples**:
```bash
# CI/CD pipeline - no user interaction
/task-review TASK-XXX --mode=security --no-questions

# Quick review with defaults
/task-review TASK-XXX --depth=quick --no-questions
```

### --with-questions

Forces clarification questions to be presented, even for simple reviews.

**When to Use**:
- Want explicit control over review scope
- Complex decisions requiring human judgment
- Learning/exploration mode

**Behavior**:
- Context A: Always presented (Phase 1)
- Context B: Always presented (if [I]mplement chosen)
- Overrides complexity-based gating

**Examples**:
```bash
# Force questions for simple review
/task-review TASK-XXX --mode=code-quality --with-questions

# Explicit control over scope
/task-review TASK-XXX --mode=architectural --with-questions
```

### --defaults

Uses default answers for all clarification questions without prompting.

**When to Use**:
- Testing/validation scenarios
- Standard workflows where defaults are well-calibrated
- Batch processing of multiple reviews

**Behavior**:
- Context A: Default values auto-applied (no prompts)
- Context B: Default values auto-applied (no prompts)
- Equivalent to pressing Enter for all questions

**Examples**:
```bash
# Use defaults for all questions
/task-review TASK-XXX --defaults

# Combine with specific mode
/task-review TASK-XXX --mode=decision --defaults
```

### Flag Combinations

**Common Patterns**:

```bash
# Interactive review with full clarification
/task-review TASK-XXX --mode=architectural --with-questions

# Silent automation (no questions, use defaults)
/task-review TASK-XXX --no-questions

# Semi-automated (apply defaults without prompts)
/task-review TASK-XXX --defaults

# Invalid: contradictory flags (--no-questions wins)
/task-review TASK-XXX --no-questions --with-questions
```

**Flag Priority**:
1. `--no-questions` (highest priority - disables all clarification)
2. `--defaults` (auto-applies defaults without prompts)
3. `--with-questions` (forces clarification to be presented)
4. Complexity-based gating (default behavior if no flags)

## Workflow Phases

The `/task-review` command executes these phases automatically:

### Phase 1: Load Review Context (with Optional Clarification)

**READ** task file from: tasks/{state}/TASK-{id}-*.md

**PARSE** task metadata:
- Task ID: {task_id}
- Title: {task_title}
- Complexity: {task_complexity}
- Review mode: {review_mode} (from --mode flag or task frontmatter)

**IF** --no-questions flag is NOT set:

  **INVOKE** Task tool:
  ```
  subagent_type: "clarification-questioner"
  description: "Collect review scope clarifications for {task_id}"
  prompt: "Execute clarification for task review.

  CONTEXT TYPE: review_scope

  TASK CONTEXT:
    Task ID: {task_id}
    Title: {task_title}
    Description: {task_description}
    Review Mode: {review_mode}
    Complexity: {task_complexity}/10

  FLAGS:
    --no-questions: {flags.no_questions}
    --with-questions: {flags.with_questions}
    --defaults: {flags.defaults}
    --answers: {flags.answers}

  Ask about:
  1. Review focus (all/technical/architecture/performance/security)
  2. Analysis depth (quick/standard/deep)
  3. Trade-off priority (speed/quality/cost/maintainability/balanced)
  4. Specific concerns (optional, free-form)
  5. Extensibility consideration (yes/no/default)

  Apply complexity gating:
  - Complexity 0-3: Skip unless --with-questions
  - Complexity 4-6 + decision/architectural mode: Ask
  - Complexity 7+: Always ask

  Return ClarificationContext with review preferences."
  ```

  **WAIT** for agent completion

  **STORE** clarification_context for review analysis

  **DISPLAY**:
  ```
  Phase 1: Review context loaded
    Clarification mode: {clarification_context.mode}
    Focus: {clarification_context.get_decision('focus', 'all')}
    Depth: {clarification_context.get_decision('depth', 'standard')}
    Trade-off Priority: {clarification_context.get_decision('tradeoff', 'balanced')}
  ```

**ELSE**:
  **DISPLAY**: "Review scope clarification skipped (--no-questions)"
  **SET** clarification_context = None

**Continue with context loading**:
- Identify review scope and objectives (using clarification if provided)
- Load relevant codebase files/modules
- Load related design documents and ADRs

### Phase 2: Execute Review Analysis

**INVOKE** appropriate review agent based on --mode flag:

{if clarification_context:}
**REVIEW SCOPE** (from clarification):
  Focus: {clarification_context.get_decision('focus', 'all')}
  Depth: {clarification_context.get_decision('depth', 'standard')}
  Trade-off Priority: {clarification_context.get_decision('tradeoff', 'balanced')}
  Specific Concerns: {clarification_context.get_decision('concerns', 'none')}
  Extensibility: {clarification_context.get_decision('extensibility', 'default')}

Prioritize analysis based on these preferences.
{endif}

- Perform analysis using specialized prompts
- Generate findings with supporting evidence
- Score/rate based on review criteria

### Phase 3: Synthesize Recommendations
- Aggregate findings from multiple agents (if applicable)
- Generate actionable recommendations
- Identify decision options (for decision-making tasks)
- Prioritize recommendations by impact

### Phase 4: Generate Review Report
- Create structured markdown report
- Include executive summary
- Document findings with evidence
- Provide recommendations with rationale
- Attach supporting artifacts (diagrams, metrics)

### Phase 5: Human Decision Checkpoint (with Optional Implementation Preferences)
Present findings to user with decision options:
- **[A]ccept** - Approve findings, mark task as `REVIEW_COMPLETE`
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation task based on recommendation
  - **[NEW]** Presents implementation preferences questions (Context B)
  - Triggered if: user chooses [I]mplement and --no-questions not set
  - Questions help clarify: approach selection, parallelization, testing depth, constraints
- **[C]ancel** - Discard review, return task to backlog

## Model Selection Strategy

The `/task-review` command automatically selects the optimal Claude model based on review mode and depth, balancing cost efficiency with quality requirements.

### When Opus 4.5 Is Used

**Opus 4.5** provides superior reasoning for high-value scenarios:

1. **Security reviews** (all depths) - Security breaches cost $100K-$10M, model costs $1-5
2. **Decision analysis** (standard/comprehensive) - Complex trade-offs require deep reasoning
3. **Comprehensive architectural reviews** - Thorough SOLID/DRY/YAGNI analysis
4. **Comprehensive technical debt** - Nuanced effort vs impact prioritization

**Cost**: $0.45-$1.65 per review (67% premium vs Sonnet)

### When Sonnet 4.5 Is Used

**Sonnet 4.5** provides excellent quality for most scenarios:

1. **Quick reviews** (except security) - Speed matters
2. **Code quality reviews** (all depths) - Metrics are objective
3. **Standard architectural reviews** - Pattern-based analysis sufficient
4. **Standard technical debt** - Straightforward prioritization

**Cost**: $0.09-$0.68 per review

### Cost Transparency

Before each review, you'll see:
```
======================================================================
📊 Review Cost Estimate
======================================================================
Model: claude-opus-4-20250514
Estimated tokens: 150,000
Estimated cost: $1.13
Rationale: comprehensive depth requires deep analysis,
           security reviews always use Opus 4.5
======================================================================
```

This ensures you always know which model will be used and why.

## Review Modes (Detailed)

### Architectural Review Mode

**Purpose**: Evaluate system design against SOLID/DRY/YAGNI principles

**Agents Used**:
- `architectural-reviewer` (primary)
- `pattern-advisor` (if Design Patterns MCP available)
- `software-architect` (for recommendations)

**Output Sections**:
1. Architecture Assessment (scored 0-100)
   - SOLID Compliance (0-10 per principle)
   - DRY Adherence (0-10)
   - YAGNI Compliance (0-10)
2. Design Patterns Analysis
3. Technical Debt Inventory
4. Recommendations (Keep/Refactor/Rewrite)

### Code Quality Review Mode

**Purpose**: Assess code maintainability, complexity, test coverage

**Agents Used**:
- `code-reviewer` (primary)
- `test-orchestrator` (for coverage analysis)

**Output Sections**:
1. Code Metrics (complexity, LOC, duplication, coverage)
2. Quality Issues (code smells, anti-patterns)
3. Maintainability Score (0-10)
4. Refactoring Recommendations

### Decision Analysis Mode

**Purpose**: Evaluate options and provide decision recommendation

**Agents Used**:
- `software-architect` (primary)
- `architectural-reviewer` (for technical assessment)
- Stack-specific specialists (for implementation details)

**Output Sections**:
1. Current Situation Assessment
2. Root Cause Analysis (if applicable)
3. Option Evaluation Matrix
4. Recommended Decision with Rationale

### Technical Debt Mode

**Purpose**: Inventory and prioritize technical debt

**Agents Used**:
- `code-reviewer` (primary)
- `architectural-reviewer` (for architectural debt)

**Output Sections**:
1. Technical Debt Inventory
2. Priority Matrix (effort vs impact)
3. Remediation Roadmap
4. Quick Wins vs Strategic Improvements

### Security Audit Mode

**Purpose**: Security vulnerability assessment

**Agents Used**:
- `security-specialist` (primary)
- `code-reviewer` (for code-level issues)

**Output Sections**:
1. Security Findings (OWASP Top 10 mapping)
2. Vulnerability Severity Ratings
3. Remediation Recommendations
4. Compliance Assessment (if applicable)

## Integration with /task-work

The `/task-review` command integrates seamlessly with `/task-work` to support a complete review → implementation → verification workflow.

### Review → Implementation Workflow

**Step 1: Create Review Task**
```bash
/task-create "Review authentication architecture" task_type:review
# Output: Created TASK-REV-A3F2
```

**Step 2: Execute Review**
```bash
/task-review TASK-REV-A3F2 --mode=architectural --depth=standard
# Review runs, generates report at .claude/reviews/TASK-REV-A3F2-review-report.md
# Task status: BACKLOG → IN_PROGRESS → REVIEW_COMPLETE
```

**Step 3: Decision Checkpoint**

After review completion, you'll see:

```
=========================================================================
REVIEW COMPLETE: TASK-REV-A3F2
=========================================================================

Review Results:
  Architecture Score: 72/100
  Findings: 8
  Recommendations: 5

Key Findings:
  - Authentication uses outdated session management
  - Password hashing needs upgrade to Argon2
  - Missing rate limiting on login endpoint

Recommendations:
  1. Migrate to JWT-based authentication
  2. Implement Argon2 password hashing
  3. Add rate limiting middleware
  4. Update session management logic
  5. Add integration tests for auth flow

Decision Options:
  [A]ccept - Archive review (no implementation needed)
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation task based on recommendations
  [C]ancel - Discard review

Your choice:
```

**Step 4a: Choose [I]mplement**

System executes the enhanced auto-detection pipeline:

```bash
================================================================================
🔄 Enhanced [I]mplement Flow - Auto-Detection Pipeline
================================================================================

Step 1/10: Extracting feature slug...
   ✓ Feature slug: authentication-refactor
   ✓ Feature name: Authentication Architecture

Step 2/10: Parsing subtasks from review recommendations...
   ✓ Found 5 subtasks

Step 3/10: Assigning implementation modes...
   ✓ /task-work: 3, Direct: 2, Manual: 0

Step 4/10: Detecting parallel execution groups...
   ✓ Organized into 2 waves

Step 5/10: Generating Conductor workspace names...
   ✓ Assigned 3 workspace names

Step 6/10: Displaying auto-detected configuration...

================================================================================
✅ Auto-detected Configuration:
================================================================================
   Feature slug: authentication-refactor
   Feature name: Authentication Architecture
   Subtasks: 5 (from review recommendations)
   Parallel groups: 2 waves

   Implementation modes:
     • /task-work: 3 tasks
     • Direct: 2 tasks
     • Manual: 0 tasks
================================================================================

Step 7/10: Creating subfolder structure...
   ✓ Created tasks/backlog/authentication-refactor/

Step 8/10: Generating subtask files...
   ✓ Generated 5 task files

Step 9/10: Generating IMPLEMENTATION-GUIDE.md...
   ✓ Guide generated

Step 10/10: Generating README.md...
   ✓ README generated

================================================================================
✅ Feature Implementation Structure Created
================================================================================

Created: tasks/backlog/authentication-refactor/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-AR-001-migrate-jwt-auth.md
  ├── TASK-AR-002-implement-argon2.md
  ├── TASK-AR-003-rate-limiting.md
  ├── TASK-AR-004-update-session-mgmt.md
  └── TASK-AR-005-add-integration-tests.md

--------------------------------------------------------------------------------
📋 Execution Strategy:
--------------------------------------------------------------------------------

Wave 1: 3 tasks
  ⚡ Parallel execution (Conductor recommended)
     • TASK-AR-001: Migrate to JWT-based authentication
       Workspace: authentication-refactor-wave1-1
       Method: task-work
     • TASK-AR-002: Implement Argon2 password hashing
       Workspace: authentication-refactor-wave1-2
       Method: task-work
     • TASK-AR-003: Add rate limiting middleware
       Workspace: authentication-refactor-wave1-3
       Method: direct

Wave 2: 2 tasks
  ⚡ Parallel execution (Conductor recommended)
     • TASK-AR-004: Update session management logic
       Workspace: authentication-refactor-wave2-1
       Method: task-work
     • TASK-AR-005: Add integration tests for auth flow
       Workspace: authentication-refactor-wave2-2
       Method: direct

================================================================================
🚀 Next Steps:
================================================================================
1. Review: tasks/backlog/authentication-refactor/IMPLEMENTATION-GUIDE.md
2. Review: tasks/backlog/authentication-refactor/README.md
3. Start with Wave 1 tasks
4. Use Conductor for parallel Wave 1 execution
================================================================================
```

### What [I]mplement Does

When you choose [I]mplement, the system automatically:

1. **Extracts feature slug** from review title (e.g., "Authentication Refactor" → "authentication-refactor")
2. **Parses subtasks** from review recommendations section
3. **Assigns implementation modes** (task-work/direct/manual) based on complexity and risk
4. **Detects parallel groups** by analyzing file conflicts between tasks
5. **Generates workspace names** for Conductor parallel execution
6. **Creates subfolder** at `tasks/backlog/{feature-slug}/`
7. **Generates task files** with complete frontmatter and metadata
8. **Generates IMPLEMENTATION-GUIDE.md** with wave breakdowns and execution strategy
9. **Generates README.md** with problem statement, solution approach, and subtask summary
10. **Displays execution plan** with next steps

### Enhanced [I]mplement Benefits

**Before (Manual)**:
- Manually create each implementation task
- Guess at implementation modes
- No parallel execution strategy
- No documentation generated

**After (Auto-Detection)**:
- Zero manual task creation
- Smart mode assignment (task-work/direct/manual)
- Automatic parallel group detection
- Complete documentation generated
- Conductor-ready workspace names

**Step 5: Implement Changes**
```bash
/task-work TASK-IMP-B4D1
# Executes implementation with all quality gates:
# - Phase 2: Planning
# - Phase 2.5: Architectural Review
# - Phase 3: Implementation
# - Phase 4: Testing
# - Phase 4.5: Test Enforcement
# - Phase 5: Code Review
```

**Step 6: Verification Review (Optional)**

After implementation, create verification review:

```bash
/task-create "Verify authentication refactoring from TASK-IMP-B4D1" task_type:review
# Output: Created TASK-VER-C5E3

/task-review TASK-VER-C5E3 --mode=code-quality --depth=quick
# Quick verification that changes meet original recommendations
```

### Task State Flow

```
Review Task:
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED

Implementation Task (created from [I]mplement):
  BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED

Verification Task (optional):
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED
```

### Real-World Example: Security Audit

```bash
# 1. Security audit review
/task-create "Security audit of payment processing" task_type:review
/task-review TASK-SEC-D7E2 --mode=security --depth=comprehensive

# 2. Review identifies 12 vulnerabilities
# Decision: [I]mplement

# 3. System creates implementation task
# TASK-IMP-E8F3: Fix security vulnerabilities from TASK-SEC-D7E2

# 4. Implement fixes
/task-work TASK-IMP-E8F3

# 5. Verification review
/task-create "Verify security fixes from TASK-IMP-E8F3" task_type:review
/task-review TASK-VER-F9G4 --mode=security --depth=standard

# 6. Verification passes, close all tasks
/task-complete TASK-VER-F9G4
/task-complete TASK-IMP-E8F3
/task-complete TASK-SEC-D7E2
```

### Benefits of Integration

1. **Traceability**: Implementation tasks linked to review findings
2. **Context Preservation**: Review report available during implementation
3. **Consistent Quality**: Implementation goes through all quality gates
4. **Verification Loop**: Optional verification review closes the cycle
5. **Automated Task Creation**: [I]mplement option eliminates manual task creation

### See Also

- [CLAUDE.md Review Workflow](../../CLAUDE.md#review-vs-implementation-workflows)
- [Task Review Workflow Guide](../../docs/workflows/task-review-workflow.md)
- [task-create.md](./task-create.md#review-task-detection)

## Task States and Transitions

```
BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → Completed/Implemented
              ↓
           BLOCKED
```

**States**:
- `BACKLOG`: Review task not started
- `IN_PROGRESS`: Review in progress
- `REVIEW_COMPLETE`: Review finished, awaiting human decision
- `BLOCKED`: Review cannot proceed (missing context, access issues)

**After Review**:
- Accept findings → Task archived as completed
- Create implementation task → New task in backlog linked to review

## Task Metadata

Review tasks use extended metadata fields:

```yaml
---
id: TASK-XXX
title: Review authentication architecture
status: in_progress
task_type: review                    # NEW: review | implementation | research | docs
review_mode: architectural           # NEW: architectural | code-quality | decision | etc.
review_depth: standard               # NEW: quick | standard | comprehensive
priority: high
tags: [architecture, security]
---
```

After review completion:

```yaml
---
id: TASK-XXX
status: review_complete
review_results:                      # NEW: Added after review
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
---
```

## Integration with Task States

### Creating Review Tasks

```bash
# Create review task
/task-create "Review authentication architecture" task_type:review

# Task created with task_type=review in frontmatter
```

### Executing Review

```bash
# Execute review (automatically detects task_type=review)
/task-review TASK-XXX --mode=architectural

# Review runs, generates report, updates task metadata
```

### Post-Review Actions

**Option 1: Accept findings (archive task)**
```bash
# User chooses [A]ccept at checkpoint
# Task moved to completed, report archived
```

**Option 2: Create implementation task**
```bash
# User chooses [I]mplement at checkpoint
# New task created in backlog:
# /task-create "Refactor authentication based on TASK-XXX findings" related_to:TASK-XXX
```

**Option 3: Revise review**
```bash
# User chooses [R]evise at checkpoint
# Review re-runs with additional focus areas
/task-review TASK-XXX --mode=architectural --depth=comprehensive
```

## Execution Protocol

### Prerequisites
1. Task must exist in `tasks/` directory
2. Task must have `task_type: review` in frontmatter (optional, defaults to review)
3. Review scope must be defined in task description

### Validation
- Validates `--mode` against allowed values
- Validates `--depth` against allowed values
- Validates `--output` against allowed values
- Checks task exists and is accessible

### Error Handling

**Common Errors**:

```bash
# Invalid review mode
❌ Error: Invalid review mode 'invalid-mode'
   Allowed: architectural, code-quality, decision, technical-debt, security

# Task not found
❌ Error: Task TASK-XXX not found in any task directory

# Missing review scope
❌ Error: Task TASK-XXX missing review scope in description
   Add "Review Scope" section to task description

# Insufficient context
⚠️  Warning: Review scope references non-existent files
   Proceeding with available context
```

## Output Files

### Review Report
**Location**: `.claude/reviews/TASK-XXX-review-report.md`

**Format**:
```markdown
# Review Report: TASK-XXX

## Executive Summary
[Brief overview of findings and recommendations]

## Review Details
- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: 1.5 hours
- **Reviewer**: architectural-reviewer agent

## Findings
1. [Finding 1 with evidence]
2. [Finding 2 with evidence]
...

## Recommendations
1. [Recommendation 1 with rationale]
2. [Recommendation 2 with rationale]
...

## Decision Matrix
| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| ... | ... | ... | ... | ... |

## Appendix
- Supporting diagrams
- Code samples
- Metrics
```

### Task Metadata Update
**Location**: Task file frontmatter

**Added Fields**:
```yaml
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
  completed_at: 2025-01-20T16:30:00Z
```

## Best Practices

### When to Use `/task-review`

**Use for**:
- ✅ "Should we implement X?" (decision analysis)
- ✅ "Review the architecture of X" (architectural review)
- ✅ "Assess code quality of X" (code quality review)
- ✅ "Identify technical debt in X" (technical debt assessment)
- ✅ "Audit security of X" (security audit)

**Don't use for**:
- ❌ "Implement feature X" (use `/task-work`)
- ❌ "Fix bug in X" (use `/task-work`)
- ❌ "Refactor X" (use `/task-work`)

### Review Depth Selection

**Quick** (15-30 min):
- Initial assessment
- Sanity check before major work
- High-level overview for stakeholders

**Standard** (1-2 hours):
- Regular code reviews
- Architecture assessments
- Decision analysis for medium complexity

**Comprehensive** (4-6 hours):
- Security audits
- Critical architectural decisions
- Large-scale refactoring planning
- Compliance assessments

### Output Format Selection

**Summary**:
- Executive presentations
- Quick decision-making
- Stakeholder communication

**Detailed**:
- Technical team consumption
- Implementation planning
- Audit trail

**Presentation**:
- Architecture reviews with stakeholders
- Decision presentations
- Training materials

## Advanced Usage

### Chaining Reviews and Implementation

```bash
# 1. Architectural review
/task-review TASK-001 --mode=architectural

# 2. Based on findings, create implementation task
/task-create "Refactor auth based on TASK-001" related_to:TASK-001

# 3. Implement refactoring
/task-work TASK-002

# 4. Post-implementation review
/task-review TASK-003 --mode=code-quality
```

### Iterative Review Refinement

```bash
# 1. Quick initial assessment
/task-review TASK-XXX --depth=quick

# 2. Based on findings, go deeper
/task-review TASK-XXX --depth=comprehensive --focus="authentication layer"
```

## Implementation Notes

### Clarification Integration Code (TASK-CLQ-008)

The clarification module integrates at two points in the `/task-review` workflow.

**Phase 1: Review Scope Clarification (Context A)**

```python
from lib.clarification import (
    generate_review_questions,
    display_questions_full,
)
from lib.clarification.core import ClarificationContext

def execute_phase_1(task_id: str, mode: str, depth: str, flags: dict):
    """Phase 1: Load context with optional clarification."""
    # Load task
    task = load_task(task_id)
    complexity = task.get("complexity", 5)

    # Determine if clarification needed
    review_clarification = None
    should_clarify = (
        not flags.get("no_questions") and (
            flags.get("with_questions") or
            (mode in ["decision", "architectural"] and complexity >= 4) or
            complexity >= 7
        )
    )

    if should_clarify:
        # Generate questions based on mode and complexity
        questions = generate_review_questions(
            task_context=task,
            review_mode=mode,
            complexity=complexity
        )

        if flags.get("defaults"):
            # Auto-apply defaults without prompting
            review_clarification = apply_defaults(questions)
        else:
            # Display questions and collect answers
            review_clarification = display_questions_full(
                questions,
                context_name="REVIEW SCOPE CLARIFICATION"
            )

    # Continue with context loading using clarification (if provided)
    return load_review_context(task, mode, depth, review_clarification)
```

**Phase 5: Implementation Preferences (Context B)**

```python
from lib.clarification.generators.implement_generator import (
    generate_implement_questions,
)

def handle_decision_checkpoint(findings: dict, task: dict, flags: dict):
    """Phase 5: Decision checkpoint with optional implementation preferences."""
    # Display review results
    decision = present_decision_checkpoint(findings)

    if decision == "implement":
        # Determine if clarification needed
        num_subtasks = len(findings.get("recommendations", []))
        complexity = task.get("complexity", 5)

        impl_clarification = None
        should_clarify = (
            not flags.get("no_questions") and
            num_subtasks >= 2
        )

        if should_clarify:
            # Generate implementation preference questions
            questions = generate_implement_questions(
                review_findings=findings,
                num_subtasks=num_subtasks,
                complexity=complexity
            )

            if flags.get("defaults"):
                # Auto-apply defaults
                impl_clarification = apply_defaults(questions)
            else:
                # Display questions and collect answers
                impl_clarification = display_questions_full(
                    questions,
                    context_name="IMPLEMENTATION PREFERENCES"
                )

        # Create implementation subtasks with preferences
        from lib.implement_orchestrator import handle_implement_option
        await handle_implement_option(
            review_task=task,
            review_report_path=findings["report_path"],
            preferences=impl_clarification
        )

    elif decision == "accept":
        complete_review_task(task)

    elif decision == "revise":
        request_deeper_analysis(task, findings)

    elif decision == "cancel":
        cancel_review(task)
```

**Complete Integration Example**

```python
def execute_task_review(task_id: str, mode: str, depth: str, flags: dict):
    """Complete task-review workflow with clarification integration."""

    # Phase 1: Load Context (with Context A clarification)
    context = execute_phase_1(task_id, mode, depth, flags)

    # Phase 2: Execute Review Analysis
    analysis = execute_review_analysis(context, mode, depth)

    # Phase 3: Synthesize Recommendations
    recommendations = synthesize_recommendations(analysis)

    # Phase 4: Generate Review Report
    report_path = generate_review_report(
        task_id=task_id,
        analysis=analysis,
        recommendations=recommendations
    )

    # Phase 5: Decision Checkpoint (with Context B clarification)
    findings = {
        "analysis": analysis,
        "recommendations": recommendations,
        "report_path": report_path,
    }

    handle_decision_checkpoint(
        findings=findings,
        task=context["task"],
        flags=flags
    )
```

**See**:
- `lib/clarification/core.py` - Core Question/Answer data structures
- `lib/clarification/display.py` - Display and input handling
- `lib/clarification/generators/review_generator.py` - Context A generation
- `lib/clarification/generators/implement_generator.py` - Context B generation
- `lib/clarification/templates/review_scope.py` - Context A question templates
- `lib/clarification/templates/implementation_prefs.py` - Context B question templates

### Enhanced [I]mplement Flow (TASK-FW-008)

The enhanced [I]mplement option requires integration with `lib.implement_orchestrator`:

```python
from lib.implement_orchestrator import handle_implement_option

# When user chooses [I]mplement at decision checkpoint
await handle_implement_option(
    review_task=review_task_dict,
    review_report_path=".claude/reviews/TASK-XXX-review-report.md"
)
```

**Dependencies** (from Wave 2 tasks):
- FW-002: Feature slug extraction (`lib.id_generator`)
- FW-003: Subtask extraction (`lib.review_parser`)
- FW-004: Implementation mode assignment (`lib.implementation_mode_analyzer`)
- FW-005: Parallel group detection (`lib.parallel_analyzer`)
- FW-006: Guide generation (`lib.guide_generator`)
- FW-007: README generation (`lib.readme_generator`)

**See**: `installer/core/lib/implement_orchestrator.py` for orchestration logic

### Development Phases

**Phase 1 Implementation** (Current):
- Core orchestrator structure (Phases 1-5 skeleton)
- Command specification (this file)
- State management (`REVIEW_COMPLETE` state)
- Metadata schema (task_type, review_mode, review_depth)

**Phase 2 Implementation** (TASK-FW-008 - Complete):
- Enhanced [I]mplement flow with auto-detection pipeline
- Feature slug extraction
- Subtask parsing from recommendations
- Implementation mode assignment
- Parallel group detection
- Workspace name generation
- Subfolder structure creation
- Task file generation
- IMPLEMENTATION-GUIDE.md generation
- README.md generation

**Future Phases** (Upcoming):
- Phase 3: Review mode implementations
- Phase 4: Report generation templates
- Phase 5: Integration with task-create
- Phase 6: Comprehensive testing


ARGUMENTS: TASK-REV-8A3F --mode=decision --depth=standard
I'll execute the decision review for the infrastructure planning task.
Read TASK-REV-8A3F-plan-build-application-infrastructure.md
Read CLAUDE.md
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options
Globpattern: ".claude/templates/**/*"
Found 10 files
Globpattern: ".claude/rules/**/*"
Found 11 files
Read config.py.template
Read session.py.template
Read database.md
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options
Now I have enough context to perform the decision review. Let me analyze the technical options and generate recommendations.
TECHNICAL OPTIONS ANALYSIS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 DECISION REVIEW: Build Application Infrastructure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Review Mode: decision
Analysis Depth: standard
Focus: All aspects (comprehensive)
Trade-off Priority: Balanced
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current State Assessment
Component	Status	Available Template
src/ directory	Not created	-
pyproject.toml	Not created	-
requirements/	Not created	-
.env.example	Not created	-
core/config.py	Not created	✅ config.py.template
db/session.py	Not created	✅ session.py.template
alembic/	Not created	-
tests/conftest.py	Not created	✅ conftest.py.template
Option 1: Template-First Approach (Recommended)
Complexity: Medium (6/10) Effort: 2-3 hours Pros:
✅ Leverages existing production-ready templates
✅ Consistent with project documentation (CLAUDE.md)
✅ Minimal custom code required
✅ Type-safe configuration with Pydantic Settings
Cons:
⚠️ Templates may need minor adjustments
⚠️ Some templates reference each other (dependency order matters)
Implementation Order:
Project Configuration (pyproject.toml, requirements/)
Core Settings (src/core/config.py)
Database Layer (src/db/)
Main Application (src/main.py)
API Infrastructure (exception handlers, middleware)
Testing Infrastructure (tests/conftest.py)
Option 2: Minimal Bootstrap
Complexity: Low (3/10) Effort: 1 hour Pros:
✅ Fastest path to running application
✅ Simple setup, add features as needed
Cons:
❌ No database layer initially
❌ No testing infrastructure
❌ Technical debt from start
❌ Doesn't follow template patterns
Option 3: Full Production Setup
Complexity: High (8/10) Effort: 4-5 hours Pros:
✅ Complete infrastructure from day one
✅ Includes Docker, CI/CD, monitoring
Cons:
⚠️ Significant upfront investment
⚠️ May include unnecessary components
⚠️ Higher initial complexity
RECOMMENDED APPROACH

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Option 1: Template-First Approach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RATIONALE:
Aligns with project's documented architecture (CLAUDE.md)
Templates are production-tested patterns
Balanced approach: complete but not over-engineered
Enables parallel development of features after infrastructure
IMPLEMENTATION BREAKDOWN
#	Task	Complexity	Parallel?	Dependencies
1	Create pyproject.toml with ruff, mypy, pytest config	3/10	Wave 1	None
2	Create requirements/ (base.txt, dev.txt, prod.txt)	2/10	Wave 1	None
3	Create .env.example with required variables	2/10	Wave 1	None
4	Create src/ directory structure	2/10	Wave 1	None
5	Create src/core/config.py from template	4/10	Wave 2	Task 4
6	Create src/db/base.py (SQLAlchemy Base)	3/10	Wave 2	Task 4
7	Create src/db/session.py from template	4/10	Wave 2	Task 5, 6
8	Configure Alembic for migrations	5/10	Wave 3	Task 7
9	Create src/main.py FastAPI app	5/10	Wave 3	Task 5, 7
10	Create src/exceptions.py global handlers	3/10	Wave 3	Task 9
11	Create tests/conftest.py from template	4/10	Wave 4	Task 7, 9
12	Add health check endpoint	2/10	Wave 4	Task 9
PARALLEL EXECUTION GROUPS:
Wave 1 (4 tasks): Independent project setup
Wave 2 (3 tasks): Core infrastructure (depends on Wave 1)
Wave 3 (3 tasks): Application layer (depends on Wave 2)
Wave 4 (2 tasks): Testing & validation (depends on Wave 3)
ESTIMATED TOTAL EFFORT: 2-3 hours COMPLEXITY: 6/10 (Medium) RISK LEVEL: Low
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete for: Plan - Build application infrastructure

Key Recommendations:
  1. Template-First Approach (Recommended)
     - 12 subtasks across 4 parallel waves
     - 2-3 hours estimated effort
     - Low risk, high alignment with project patterns

  2. Minimal Bootstrap
     - Faster but creates technical debt
     
  3. Full Production Setup
     - Complete but over-engineered for current needs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What would you like to do?
AskUserQuestion
OUT
User has answered your questions: "What would you like to do with the infrastructure planning review?"="[I]mplement (Recommended)". You can now continue with the user's answers in mind.
Step 5: Context B - Implementation Preferences
AskUserQuestion
OUT
User has answered your questions: "Which implementation approach should subtasks follow?"="Template-First (Recommended)", "How should the 12 subtasks be executed?"="Detect automatically (Recommended)", "What testing depth for subtasks?"="Standard (Recommended)". You can now continue with the user's answers in mind.
Context B recorded:
Approach: Template-First
Execution: Auto-detect (parallel where safe)
Testing: Standard quality gates
Step 6: Generate Feature Structure
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options

Create feature subfolder and implementation tasks

Generate structured YAML feature file
Bash Create feature subfolder for infrastructure tasks
IN
mkdir -p /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/tasks/backlog/application-infrastructure

OUT
0
Write README.md
76 lines
# Feature: Application Infrastructure

## Overview

Build the foundational FastAPI application infrastructure from scratch, following the template-first approach documented in CLAUDE.md.

## Problem Statement

This is a greenfield FastAPI project with production-ready templates available but no actual implementation. The infrastructure needs to be created following established patterns to enable feature development.

## Solution Approach

**Template-First**: Leverage existing `.claude/templates/` with minimal customization to ensure consistency with documented patterns.

## Technology Stack

- **FastAPI** (>=0.104.0) - Web framework
- **SQLAlchemy** (>=2.0.0) - Async ORM
- **Pydantic** (>=2.0.0) - Data validation
- **Alembic** (>=1.12.0) - Database migrations
- **pytest** (>=7.4.0) - Testing framework
- **ruff** - Linting and formatting
- **mypy** - Static type checking

## Subtasks Summary

| Wave | Tasks | Can Parallel | Description |
|------|-------|--------------|-------------|
| 1 | 4 | Yes | Project configuration (pyproject.toml, requirements, .env, src/) |
| 2 | 3 | Yes | Core infrastructure (config, db/base, db/session) |
| 3 | 3 | Partial | Application layer (alembic, main.py, exceptions) |
| 4 | 2 | Yes | Testing & validation (conftest, health check) |

**Total**: 12 subtasks
**Estimated Effort**: 2-3 hours
**Complexity**: 6/10 (Medium)

## Execution Strategy

Tasks are organized into 4 waves based on dependencies:

```
Wave 1: Independent Setup
├── TASK-INFRA-001: Create pyproject.toml
├── TASK-INFRA-002: Create requirements/
├── TASK-INFRA-003: Create .env.example
└── TASK-INFRA-004: Create src/ structure

Wave 2: Core Infrastructure (depends on Wave 1)
├── TASK-INFRA-005: Create core/config.py
├── TASK-INFRA-006: Create db/base.py
└── TASK-INFRA-007: Create db/session.py

Wave 3: Application Layer (depends on Wave 2)
├── TASK-INFRA-008: Configure Alembic
├── TASK-INFRA-009: Create main.py
└── TASK-INFRA-010: Create exceptions.py

Wave 4: Testing & Validation (depends on Wave 3)
├── TASK-INFRA-011: Create tests/conftest.py
└── TASK-INFRA-012: Add health check endpoint
```

## Quality Gates

- All files pass `ruff check` and `ruff format`
- All files pass `mypy --strict`
- Tests pass with `pytest`
- Application starts successfully with `uvicorn`

## Related

- **Review Task**: TASK-REV-8A3F
- **Templates**: `.claude/templates/`
- **Documentation**: `.claude/CLAUDE.md`
Write IMPLEMENTATION-GUIDE.md
157 lines
# Implementation Guide: Application Infrastructure

## Execution Overview

This guide provides step-by-step execution instructions for building the FastAPI application infrastructure.

## Wave 1: Independent Setup (Parallel)

Execute all 4 tasks in parallel - no dependencies between them.

### TASK-INFRA-001: Create pyproject.toml
- Create `pyproject.toml` with project metadata
- Configure ruff, mypy, pytest settings
- Method: **direct** (straightforward configuration)

### TASK-INFRA-002: Create requirements/
- Create `requirements/base.txt` with production dependencies
- Create `requirements/dev.txt` with development dependencies
- Create `requirements/prod.txt` with production-only dependencies
- Method: **direct** (dependency listing)

### TASK-INFRA-003: Create .env.example
- Create `.env.example` with all required environment variables
- Include example values and documentation
- Method: **direct** (configuration template)

### TASK-INFRA-004: Create src/ structure
- Create `src/` directory
- Create `src/__init__.py`
- Create `src/core/`, `src/db/` subdirectories
- Method: **direct** (directory creation)

---

## Wave 2: Core Infrastructure (Parallel)

Execute after Wave 1 completes. All 3 tasks can run in parallel.

### TASK-INFRA-005: Create core/config.py
- Use `.claude/templates/core/config.py.template`
- Replace `{{ProjectName}}` placeholder
- Ensure Pydantic Settings configuration is correct
- Method: **task-work** (template customization)

### TASK-INFRA-006: Create db/base.py
- Create SQLAlchemy declarative base
- Add common mixins (TimestampMixin, etc.)
- Method: **direct** (standard boilerplate)

### TASK-INFRA-007: Create db/session.py
- Use `.claude/templates/db/session.py.template`
- Configure async engine with connection pooling
- Create get_db dependency
- Method: **task-work** (template customization + testing)

---

## Wave 3: Application Layer (Sequential where noted)

### TASK-INFRA-008: Configure Alembic
- Initialize Alembic with `alembic init alembic`
- Configure `alembic.ini` for async SQLAlchemy
- Update `alembic/env.py` for async migrations
- Create initial migration
- **Depends on**: TASK-INFRA-007
- Method: **task-work** (complex configuration)

### TASK-INFRA-009: Create main.py
- Create FastAPI application instance
- Add CORS middleware
- Register exception handlers
- Include lifespan events (startup/shutdown)
- **Depends on**: TASK-INFRA-005, TASK-INFRA-007
- Method: **task-work** (core application logic)

### TASK-INFRA-010: Create exceptions.py
- Create base exception classes
- Add HTTP exception handlers
- Add validation error handlers
- **Depends on**: TASK-INFRA-009
- Method: **direct** (straightforward exception handling)

---

## Wave 4: Testing & Validation (Parallel)

Execute after Wave 3 completes.

### TASK-INFRA-011: Create tests/conftest.py
- Use `.claude/templates/testing/conftest.py.template`
- Configure test database fixtures
- Add async client fixture
- Method: **task-work** (template customization + verification)

### TASK-INFRA-012: Add health check endpoint
- Create `/health` endpoint
- Include database connectivity check
- Return status with version info
- Method: **direct** (simple endpoint)

---

## Implementation Modes Reference

| Mode | When to Use |
|------|-------------|
| **direct** | Simple, well-defined tasks (complexity ≤3) |
| **task-work** | Complex tasks requiring quality gates (complexity ≥4) |

## Verification Checklist

After completing all tasks:

```bash
# 1. Install dependencies
pip install -r requirements/dev.txt

# 2. Run linting
ruff check src/
ruff format --check src/

# 3. Run type checking
mypy src/ --strict

# 4. Run tests
pytest tests/ -v

# 5. Start application
uvicorn src.main:app --reload

# 6. Verify health check
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

1. **Import errors in db/session.py**
   - Ensure `src/core/config.py` is created first
   - Check `PYTHONPATH` includes `src/`

2. **Alembic async errors**
   - Use `run_migrations_online()` with `asyncio.run()`
   - Configure `sqlalchemy.url` dynamically from settings

3. **Test fixtures not found**
   - Ensure `conftest.py` is in `tests/` root
   - Use `pytest-asyncio` for async fixtures

## Next Steps

After infrastructure is complete:
1. Create first feature module (e.g., `src/users/`)
2. Add initial database migration
3. Implement authentication if needed
Now I'll create the 12 subtask files:
Write TASK-INFRA-001-create-pyproject-toml.md
92 lines
---
id: TASK-INFRA-001
title: Create pyproject.toml with tool configurations
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, configuration, wave-1]
complexity: 3
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: infra-wave1-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create pyproject.toml with tool configurations

## Description

Create the project's `pyproject.toml` file with complete metadata and tool configurations for ruff, mypy, pytest, and other development tools.

## Acceptance Criteria

- [ ] `pyproject.toml` exists at project root
- [ ] Project metadata (name, version, description) configured
- [ ] Ruff configuration with FastAPI best practices
- [ ] Mypy strict mode configuration
- [ ] Pytest configuration with asyncio support
- [ ] File passes TOML validation

## Implementation Notes

### Required Sections

```toml
[project]
name = "fastapi-app"
version = "0.1.0"
description = "FastAPI Backend Application"
requires-python = ">=3.11"

[tool.ruff]
# Linting configuration

[tool.ruff.lint]
# Rule selection

[tool.mypy]
# Type checking configuration

[tool.pytest.ini_options]
# Test configuration
```

### Key Configurations

**Ruff**:
- Line length: 88
- Target Python: 3.11
- Select: E, F, W, I, UP, B, SIM
- Ignore: E501 (line too long, handled by formatter)

**Mypy**:
- strict = true
- plugins = ["pydantic.mypy"]

**Pytest**:
- asyncio_mode = "auto"
- testpaths = ["tests"]

## Dependencies

None (Wave 1 - independent task)

## Verification

```bash
# Validate TOML syntax
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"

# Test ruff config
ruff check --config pyproject.toml .

# Test mypy config
mypy --config-file pyproject.toml .
```
Write TASK-INFRA-002-create-requirements.md
101 lines
---
id: TASK-INFRA-002
title: Create requirements/ directory with dependency files
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, dependencies, wave-1]
complexity: 2
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: infra-wave1-2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create requirements/ directory with dependency files

## Description

Create the `requirements/` directory with split dependency files for base, development, and production environments.

## Acceptance Criteria

- [ ] `requirements/` directory exists
- [ ] `requirements/base.txt` with production dependencies
- [ ] `requirements/dev.txt` with development dependencies (includes base)
- [ ] `requirements/prod.txt` with production-only dependencies (includes base)
- [ ] All packages have pinned versions

## Implementation Notes

### requirements/base.txt

```txt
# Core Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.12.0

# HTTP Client (for external APIs)
httpx>=0.25.0

# Utilities
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

### requirements/dev.txt

```txt
-r base.txt

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Code Quality
ruff>=0.1.0
mypy>=1.7.0

# Development
pre-commit>=3.5.0
```

### requirements/prod.txt

```txt
-r base.txt

# Production server
gunicorn>=21.2.0

# Monitoring (optional)
sentry-sdk[fastapi]>=1.35.0
```

## Dependencies

None (Wave 1 - independent task)

## Verification

```bash
# Validate requirements files
pip-compile requirements/base.txt --dry-run
pip install -r requirements/dev.txt --dry-run
```
Write TASK-INFRA-003-create-env-example.md
109 lines
---
id: TASK-INFRA-003
title: Create .env.example with required environment variables
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, configuration, wave-1]
complexity: 2
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: infra-wave1-3
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create .env.example with required environment variables

## Description

Create `.env.example` file documenting all required and optional environment variables with example values and descriptions.

## Acceptance Criteria

- [ ] `.env.example` exists at project root
- [ ] All required variables documented
- [ ] Example values provided (safe for version control)
- [ ] Comments explain each variable's purpose
- [ ] Variables match config.py.template expectations

## Implementation Notes

### .env.example Content

```bash
# =============================================================================
# Application Settings
# =============================================================================
PROJECT_NAME=FastAPI App
VERSION=1.0.0
DEBUG=false
ENVIRONMENT=development  # development, staging, production

# =============================================================================
# Database Settings (REQUIRED)
# =============================================================================
# PostgreSQL connection string with asyncpg driver
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# =============================================================================
# Security Settings (REQUIRED)
# =============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# =============================================================================
# CORS Settings
# =============================================================================
# Comma-separated list of allowed origins
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# =============================================================================
# Optional: Redis (for caching/sessions)
# =============================================================================
# REDIS_URL=redis://localhost:6379/0

# =============================================================================
# Optional: External Services
# =============================================================================
# SENTRY_DSN=https://your-sentry-dsn
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=
# SMTP_PASSWORD=
# EMAILS_FROM_EMAIL=noreply@example.com

# =============================================================================
# Pagination
# =============================================================================
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=1000

# =============================================================================
# Rate Limiting
# =============================================================================
RATE_LIMIT_PER_MINUTE=60
```

## Dependencies

None (Wave 1 - independent task)

## Verification

```bash
# Check file exists and is readable
cat .env.example

# Validate no actual secrets in file
grep -E "(password|secret)" .env.example | grep -v "your-"
```
Write TASK-INFRA-004-create-src-structure.md
89 lines
---
id: TASK-INFRA-004
title: Create src/ directory structure
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, structure, wave-1]
complexity: 2
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-1
conductor_workspace: infra-wave1-4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/ directory structure

## Description

Create the `src/` directory structure following the feature-based organization pattern documented in CLAUDE.md.

## Acceptance Criteria

- [ ] `src/` directory exists
- [ ] `src/__init__.py` exists (empty or with version)
- [ ] `src/core/` directory with `__init__.py`
- [ ] `src/db/` directory with `__init__.py`
- [ ] Directory structure matches CLAUDE.md specification

## Implementation Notes

### Directory Structure

```
src/
├── __init__.py           # Package marker, optional version
├── core/
│   └── __init__.py       # Core package marker
└── db/
    └── __init__.py       # Database package marker
```

### src/__init__.py

```python
"""FastAPI Application Package."""

__version__ = "0.1.0"
```

### src/core/__init__.py

```python
"""Core configuration and utilities."""
```

### src/db/__init__.py

```python
"""Database infrastructure."""
```

## Dependencies

None (Wave 1 - independent task)

## Verification

```bash
# Check structure
tree src/

# Expected output:
# src/
# ├── __init__.py
# ├── core/
# │   └── __init__.py
# └── db/
#     └── __init__.py

# Verify Python can import
python -c "import src; print(src.__version__)"
```
Write TASK-INFRA-005-create-core-config.md
88 lines
---
id: TASK-INFRA-005
title: Create src/core/config.py from template
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, configuration, wave-2]
complexity: 4
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: task-work
parallel_group: wave-2
conductor_workspace: infra-wave2-1
dependencies: [TASK-INFRA-004]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/core/config.py from template

## Description

Create the application configuration module using the Pydantic Settings pattern from `.claude/templates/core/config.py.template`.

## Acceptance Criteria

- [ ] `src/core/config.py` exists
- [ ] Uses Pydantic BaseSettings for configuration
- [ ] All environment variables from `.env.example` are defined
- [ ] Field validators work correctly
- [ ] Singleton `settings` instance exported
- [ ] File passes mypy strict type checking

## Implementation Notes

### Template Reference

Use `.claude/templates/core/config.py.template` as the base.

### Required Modifications

1. Replace `{{ProjectName}}` with actual project name
2. Ensure all fields match `.env.example` variables
3. Add type hints for all fields
4. Configure Pydantic model_config properly

### Key Sections

```python
from pydantic import PostgresDsn, field_validator, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application Settings
    PROJECT_NAME: str = "FastAPI App"
    # ... etc

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

settings = Settings()
```

## Dependencies

- TASK-INFRA-004 (src/ structure must exist)

## Verification

```bash
# Type check
mypy src/core/config.py --strict

# Test loading (requires .env or environment variables)
python -c "from src.core.config import settings; print(settings.PROJECT_NAME)"
```

## Testing Requirements

- Unit test for CORS validator
- Unit test for settings loading with mock environment
Write TASK-INFRA-006-create-db-base.md
92 lines
---
id: TASK-INFRA-006
title: Create src/db/base.py with SQLAlchemy Base
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, database, wave-2]
complexity: 3
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-2
conductor_workspace: infra-wave2-2
dependencies: [TASK-INFRA-004]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/db/base.py with SQLAlchemy Base

## Description

Create the SQLAlchemy declarative base with common mixins for timestamps and other shared functionality.

## Acceptance Criteria

- [ ] `src/db/base.py` exists
- [ ] Declarative base configured for async SQLAlchemy 2.0
- [ ] TimestampMixin with created_at/updated_at
- [ ] Base class properly typed for mypy
- [ ] Mixins can be composed with models

## Implementation Notes

### Base Structure

```python
"""SQLAlchemy Base Configuration."""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### Usage Pattern

```python
from src.db.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    # ... model fields
```

## Dependencies

- TASK-INFRA-004 (src/ structure must exist)

## Verification

```bash
# Type check
mypy src/db/base.py --strict

# Test import
python -c "from src.db.base import Base, TimestampMixin; print('OK')"
```
Write TASK-INFRA-007-create-db-session.md
99 lines
---
id: TASK-INFRA-007
title: Create src/db/session.py from template
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, database, wave-2]
complexity: 4
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: task-work
parallel_group: wave-2
conductor_workspace: infra-wave2-3
dependencies: [TASK-INFRA-005, TASK-INFRA-006]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/db/session.py from template

## Description

Create the database session management module using the async SQLAlchemy pattern from `.claude/templates/db/session.py.template`.

## Acceptance Criteria

- [ ] `src/db/session.py` exists
- [ ] Async engine configured with connection pooling
- [ ] AsyncSession factory created
- [ ] `get_db` dependency function for FastAPI
- [ ] Proper session cleanup on errors
- [ ] File passes mypy strict type checking

## Implementation Notes

### Template Reference

Use `.claude/templates/db/session.py.template` as the base.

### Key Components

```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import AsyncGenerator

from src.core.config import settings

# Engine with connection pooling
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

## Dependencies

- TASK-INFRA-005 (config.py for DATABASE_URL)
- TASK-INFRA-006 (base.py for Base class)

## Verification

```bash
# Type check
mypy src/db/session.py --strict

# Test import (config loading may fail without .env)
python -c "from src.db.session import get_db; print('OK')"
```

## Testing Requirements

- Integration test with test database
- Test session cleanup on exception
Write TASK-INFRA-008-configure-alembic.md
139 lines
---
id: TASK-INFRA-008
title: Configure Alembic for database migrations
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, database, migrations, wave-3]
complexity: 5
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: task-work
parallel_group: wave-3
conductor_workspace: infra-wave3-1
dependencies: [TASK-INFRA-007]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Configure Alembic for database migrations

## Description

Initialize and configure Alembic for async SQLAlchemy database migrations.

## Acceptance Criteria

- [ ] `alembic/` directory exists with proper structure
- [ ] `alembic.ini` configured for async operations
- [ ] `alembic/env.py` updated for async migrations
- [ ] Database URL loaded from settings (not hardcoded)
- [ ] Autogenerate works with Base metadata
- [ ] Initial migration can be created

## Implementation Notes

### Initialization

```bash
alembic init alembic
```

### alembic.ini Modifications

```ini
# Remove default sqlalchemy.url line
# It will be set dynamically in env.py
```

### alembic/env.py Key Changes

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import your models' Base
from src.db.base import Base
from src.core.config import settings

config = context.config

# Set the database URL dynamically
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Dependencies

- TASK-INFRA-007 (db/session.py for engine configuration pattern)

## Verification

```bash
# Check alembic is configured
alembic current

# Test autogenerate (should show no changes if no models)
alembic revision --autogenerate -m "Initial" --dry-run
```

## Testing Requirements

- Test migration creation works
- Test upgrade/downgrade cycle
Write TASK-INFRA-009-create-main-py.md
126 lines
---
id: TASK-INFRA-009
title: Create src/main.py FastAPI application
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, fastapi, wave-3]
complexity: 5
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: task-work
parallel_group: wave-3
conductor_workspace: infra-wave3-2
dependencies: [TASK-INFRA-005, TASK-INFRA-007]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/main.py FastAPI application

## Description

Create the main FastAPI application entry point with middleware, CORS configuration, and lifespan events.

## Acceptance Criteria

- [ ] `src/main.py` exists
- [ ] FastAPI app instance configured with metadata
- [ ] CORS middleware enabled with settings from config
- [ ] Lifespan context manager for startup/shutdown
- [ ] API version prefix applied
- [ ] Application starts without errors
- [ ] File passes mypy strict type checking

## Implementation Notes

### Main Application Structure

```python
"""FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan events.

    Startup: Initialize connections, warm caches
    Shutdown: Close connections, cleanup resources
    """
    # Startup
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    yield
    # Shutdown
    print(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint - redirects to API documentation."""
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
```

### Optional Enhancements

- Request ID middleware for tracing
- Request timing middleware
- GZip compression middleware

## Dependencies

- TASK-INFRA-005 (config.py for settings)
- TASK-INFRA-007 (db/session.py for database connection)

## Verification

```bash
# Type check
mypy src/main.py --strict

# Start application
uvicorn src.main:app --reload

# Test root endpoint
curl http://localhost:8000/

# Check API docs
open http://localhost:8000/api/v1/docs
```

## Testing Requirements

- Test app creation
- Test CORS headers
- Test lifespan events
Write TASK-INFRA-010-create-exceptions.md
146 lines
---
id: TASK-INFRA-010
title: Create src/exceptions.py global exception handlers
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, error-handling, wave-3]
complexity: 3
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-3
conductor_workspace: infra-wave3-3
dependencies: [TASK-INFRA-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create src/exceptions.py global exception handlers

## Description

Create global exception classes and handlers for consistent API error responses.

## Acceptance Criteria

- [ ] `src/exceptions.py` exists
- [ ] Base exception class for application errors
- [ ] Common HTTP exception subclasses (NotFound, BadRequest, etc.)
- [ ] Exception handlers registered with FastAPI app
- [ ] Consistent error response format
- [ ] File passes mypy strict type checking

## Implementation Notes

### Exception Classes

```python
"""Global Exception Definitions."""

from typing import Any

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{identifier}' not found",
        )


class BadRequestException(AppException):
    """Invalid request."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class UnauthorizedException(AppException):
    """Authentication required."""

    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """Permission denied."""

    def __init__(self, detail: str = "Not enough permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ConflictException(AppException):
    """Resource conflict."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )
```

### Exception Handlers (add to main.py)

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )
```

## Dependencies

- TASK-INFRA-009 (main.py to register handlers)

## Verification

```bash
# Type check
mypy src/exceptions.py --strict

# Test import
python -c "from src.exceptions import NotFoundException; print('OK')"
```
Write TASK-INFRA-011-create-conftest.md
143 lines
---
id: TASK-INFRA-011
title: Create tests/conftest.py from template
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, testing, wave-4]
complexity: 4
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: task-work
parallel_group: wave-4
conductor_workspace: infra-wave4-1
dependencies: [TASK-INFRA-007, TASK-INFRA-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create tests/conftest.py from template

## Description

Create the pytest configuration and shared fixtures using the pattern from `.claude/templates/testing/conftest.py.template`.

## Acceptance Criteria

- [ ] `tests/conftest.py` exists
- [ ] Async test fixtures configured
- [ ] Test database session fixture
- [ ] Test HTTP client fixture (httpx AsyncClient)
- [ ] Database cleanup between tests
- [ ] File passes mypy strict type checking

## Implementation Notes

### Template Reference

Use `.claude/templates/testing/conftest.py.template` as the base.

### Key Fixtures

```python
"""Pytest Configuration and Fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.db.base import Base
from src.db.session import get_db
from src.main import app


# Test database URL (use separate test database)
TEST_DATABASE_URL = str(settings.DATABASE_URL).replace(
    "/dbname", "/test_dbname"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
```

## Dependencies

- TASK-INFRA-007 (db/session.py for get_db dependency)
- TASK-INFRA-009 (main.py for app instance)

## Verification

```bash
# Type check
mypy tests/conftest.py --strict

# Run tests (should pass with no tests yet)
pytest tests/ -v

# Test fixtures work
pytest tests/ -v --fixtures
```

## Testing Requirements

- Verify fixtures work correctly
- Verify database isolation between tests
Write TASK-INFRA-012-add-health-check.md
172 lines
---
id: TASK-INFRA-012
title: Add health check endpoint
status: backlog
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
tags: [infrastructure, api, wave-4]
complexity: 2
parent_feature: application-infrastructure
review_task: TASK-REV-8A3F
implementation_mode: direct
parallel_group: wave-4
conductor_workspace: infra-wave4-2
dependencies: [TASK-INFRA-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add health check endpoint

## Description

Create a `/health` endpoint that verifies application and database connectivity status.

## Acceptance Criteria

- [ ] `/health` endpoint exists
- [ ] Returns application version and status
- [ ] Checks database connectivity
- [ ] Returns appropriate status codes (200 OK, 503 Service Unavailable)
- [ ] Response includes timestamp
- [ ] File passes mypy strict type checking

## Implementation Notes

### Health Check Endpoint

```python
"""Health Check Endpoint - add to main.py or separate router."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Health check endpoint.

    Verifies:
    - Application is running
    - Database is accessible

    Returns:
        Health status with version and database connectivity
    """
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "healthy",
        },
    }

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status,
        )

    return health_status


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes liveness probe.

    Simple check that the application is running.
    Does not check dependencies.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Kubernetes readiness probe.

    Checks that the application can handle requests.
    Verifies database connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready"},
        )
```

### Integration with main.py

```python
from src.health import router as health_router

app.include_router(health_router)
```

## Dependencies

- TASK-INFRA-009 (main.py to register router)

## Verification

```bash
# Start application
uvicorn src.main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "development",
#   "timestamp": "2025-12-31T00:00:00+00:00",
#   "checks": {
#     "database": "healthy"
#   }
# }

# Test liveness
curl http://localhost:8000/health/live

# Test readiness
curl http://localhost:8000/health/ready
```

## Testing Requirements

- Test healthy response
- Test unhealthy response (mock database failure)
- Test liveness always returns 200
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options

Create feature subfolder and implementation tasks

Generate structured YAML feature file

Update review task status
Step 7: Generate Structured YAML Feature File
Bash Create .guardkit/features directory
IN
mkdir -p /Users/richardwoollcott/Projects/guardkit_testing/feature_build_test/.guardkit/features

OUT
0
Write FEAT-INFRA.yaml
185 lines
# Feature: Application Infrastructure
# Generated: 2025-12-31
# Review Task: TASK-REV-8A3F

id: FEAT-INFRA
name: "Build application infrastructure"
description: |
  Build the foundational FastAPI application infrastructure from scratch,
  following the template-first approach documented in CLAUDE.md.

  Components include:
  - Project configuration (pyproject.toml, requirements/)
  - Core settings (Pydantic Settings)
  - Database layer (SQLAlchemy async, Alembic)
  - FastAPI application with middleware
  - Testing infrastructure

status: planned
priority: high
created: 2025-12-31T00:00:00Z

# Aggregate metrics
complexity: 6  # Medium (weighted average of task complexities)
estimated_duration: "2-3 hours"
total_tasks: 12

# Technology stack
technology:
  - fastapi>=0.104.0
  - sqlalchemy>=2.0.0
  - pydantic>=2.0.0
  - alembic>=1.12.0
  - pytest>=7.4.0

# Task definitions with dependencies
tasks:
  - id: TASK-INFRA-001
    name: "Create pyproject.toml with tool configurations"
    complexity: 3
    mode: direct
    dependencies: []

  - id: TASK-INFRA-002
    name: "Create requirements/ directory with dependency files"
    complexity: 2
    mode: direct
    dependencies: []

  - id: TASK-INFRA-003
    name: "Create .env.example with required environment variables"
    complexity: 2
    mode: direct
    dependencies: []

  - id: TASK-INFRA-004
    name: "Create src/ directory structure"
    complexity: 2
    mode: direct
    dependencies: []

  - id: TASK-INFRA-005
    name: "Create src/core/config.py from template"
    complexity: 4
    mode: task-work
    dependencies:
      - TASK-INFRA-004

  - id: TASK-INFRA-006
    name: "Create src/db/base.py with SQLAlchemy Base"
    complexity: 3
    mode: direct
    dependencies:
      - TASK-INFRA-004

  - id: TASK-INFRA-007
    name: "Create src/db/session.py from template"
    complexity: 4
    mode: task-work
    dependencies:
      - TASK-INFRA-005
      - TASK-INFRA-006

  - id: TASK-INFRA-008
    name: "Configure Alembic for database migrations"
    complexity: 5
    mode: task-work
    dependencies:
      - TASK-INFRA-007

  - id: TASK-INFRA-009
    name: "Create src/main.py FastAPI application"
    complexity: 5
    mode: task-work
    dependencies:
      - TASK-INFRA-005
      - TASK-INFRA-007

  - id: TASK-INFRA-010
    name: "Create src/exceptions.py global exception handlers"
    complexity: 3
    mode: direct
    dependencies:
      - TASK-INFRA-009

  - id: TASK-INFRA-011
    name: "Create tests/conftest.py from template"
    complexity: 4
    mode: task-work
    dependencies:
      - TASK-INFRA-007
      - TASK-INFRA-009

  - id: TASK-INFRA-012
    name: "Add health check endpoint"
    complexity: 2
    mode: direct
    dependencies:
      - TASK-INFRA-009

# Parallel execution groups (waves)
parallel_groups:
  - wave: 1
    name: "Independent Setup"
    tasks:
      - TASK-INFRA-001
      - TASK-INFRA-002
      - TASK-INFRA-003
      - TASK-INFRA-004
    can_parallel: true

  - wave: 2
    name: "Core Infrastructure"
    tasks:
      - TASK-INFRA-005
      - TASK-INFRA-006
      - TASK-INFRA-007
    can_parallel: true
    depends_on_wave: 1

  - wave: 3
    name: "Application Layer"
    tasks:
      - TASK-INFRA-008
      - TASK-INFRA-009
      - TASK-INFRA-010
    can_parallel: partial  # TASK-INFRA-010 depends on TASK-INFRA-009
    depends_on_wave: 2

  - wave: 4
    name: "Testing & Validation"
    tasks:
      - TASK-INFRA-011
      - TASK-INFRA-012
    can_parallel: true
    depends_on_wave: 3

# Implementation modes summary
implementation_modes:
  task-work: 5  # Complex tasks requiring quality gates
  direct: 7     # Simple, well-defined tasks
  manual: 0     # No manual tasks

# Quality gates
quality_gates:
  linting: ruff
  type_checking: mypy --strict
  testing: pytest
  coverage_minimum: 80

# Related artifacts
artifacts:
  review_task: TASK-REV-8A3F
  task_directory: tasks/backlog/application-infrastructure/
  templates_used:
    - .claude/templates/core/config.py.template
    - .claude/templates/db/session.py.template
    - .claude/templates/testing/conftest.py.template

# AutoBuild integration
autobuild:
  enabled: true
  command: "/feature-build FEAT-INFRA"
  parallel_execution: true
  max_parallel_tasks: 4
Step 8: Update review task to completed
Read TASK-REV-8A3F-plan-build-application-infrastructure.md
Write TASK-REV-8A3F-plan-build-application-infrastructure.md
93 lines
---
id: TASK-REV-8A3F
title: "Plan: Build application infrastructure"
status: review_complete
created: 2025-12-31T00:00:00Z
updated: 2025-12-31T00:00:00Z
priority: high
task_type: review
tags: [infrastructure, planning, architecture]
complexity: 6
clarification:
  context_a:
    timestamp: 2025-12-31T00:00:00Z
    decisions:
      focus: all
      tradeoff: balanced
  context_b:
    timestamp: 2025-12-31T00:00:00Z
    decisions:
      approach: template-first
      execution: auto-detect
      testing: standard
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 3
  recommendations_count: 1
  decision: implement
  feature_id: FEAT-INFRA
  subtasks_created: 12
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan - Build application infrastructure

## Description

Create a comprehensive plan for building the FastAPI application infrastructure from scratch. This is a greenfield project with templates available but no actual implementation yet.

## Current State

- **Templates Available**: 10 production-ready templates in `.claude/templates/`
- **No Source Code**: `src/` directory does not exist
- **No Dependencies**: `requirements/` directory does not exist
- **No Configuration**: `pyproject.toml`, `.env`, `alembic.ini` not created
- **Technology Stack**: FastAPI, SQLAlchemy 2.0, Pydantic 2.0, Alembic, pytest

## Review Results

### Options Analyzed

1. **Template-First Approach** (Selected)
   - Complexity: 6/10 (Medium)
   - Effort: 2-3 hours
   - 12 subtasks across 4 parallel waves

2. **Minimal Bootstrap**
   - Complexity: 3/10 (Low)
   - Creates technical debt

3. **Full Production Setup**
   - Complexity: 8/10 (High)
   - Over-engineered for current needs

### Decision: Implement with Template-First Approach

Created feature structure with 12 implementation subtasks:
- **Wave 1**: 4 tasks (independent setup)
- **Wave 2**: 3 tasks (core infrastructure)
- **Wave 3**: 3 tasks (application layer)
- **Wave 4**: 2 tasks (testing & validation)

## Acceptance Criteria

- [x] Complete infrastructure plan with implementation order
- [x] Clear subtask breakdown for each component
- [x] Dependency graph for parallel execution opportunities
- [x] Effort estimation per component
- [x] Risk assessment for complex areas

## Generated Artifacts

- **Feature ID**: FEAT-INFRA
- **Feature File**: `.guardkit/features/FEAT-INFRA.yaml`
- **Task Directory**: `tasks/backlog/application-infrastructure/`
- **Documentation**:
  - `README.md` - Feature overview
  - `IMPLEMENTATION-GUIDE.md` - Execution instructions
Update Todos

Execute decision review for infrastructure planning

Analyze technical options and generate recommendations

Present decision checkpoint with options

Create feature subfolder and implementation tasks

Generate structured YAML feature file

Update review task status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Feature: FEAT-INFRA (Application Infrastructure)
📋 Tasks: 12 subtasks across 4 waves
⏱️  Estimated Effort: 2-3 hours
🎯 Complexity: 6/10 (Medium)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Created Files:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tasks/backlog/application-infrastructure/
├── README.md
├── IMPLEMENTATION-GUIDE.md
├── TASK-INFRA-001-create-pyproject-toml.md
├── TASK-INFRA-002-create-requirements.md
├── TASK-INFRA-003-create-env-example.md
├── TASK-INFRA-004-create-src-structure.md
├── TASK-INFRA-005-create-core-config.md
├── TASK-INFRA-006-create-db-base.md
├── TASK-INFRA-007-create-db-session.md
├── TASK-INFRA-008-configure-alembic.md
├── TASK-INFRA-009-create-main-py.md
├── TASK-INFRA-010-create-exceptions.md
├── TASK-INFRA-011-create-conftest.md
└── TASK-INFRA-012-add-health-check.md

.guardkit/features/
└── FEAT-INFRA.yaml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Execution Strategy:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Wave 1: Independent Setup (4 tasks - parallel)
  • TASK-INFRA-001: Create pyproject.toml (direct)
  • TASK-INFRA-002: Create requirements/ (direct)
  • TASK-INFRA-003: Create .env.example (direct)
  • TASK-INFRA-004: Create src/ structure (direct)

Wave 2: Core Infrastructure (3 tasks - parallel)
  • TASK-INFRA-005: Create core/config.py (task-work)
  • TASK-INFRA-006: Create db/base.py (direct)
  • TASK-INFRA-007: Create db/session.py (task-work)

Wave 3: Application Layer (3 tasks)
  • TASK-INFRA-008: Configure Alembic (task-work)
  • TASK-INFRA-009: Create main.py (task-work)
  • TASK-INFRA-010: Create exceptions.py (direct)

Wave 4: Testing & Validation (2 tasks - parallel)
  • TASK-INFRA-011: Create conftest.py (task-work)
  • TASK-INFRA-012: Add health check (direct)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Next Steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review: tasks/backlog/application-infrastructure/IMPLEMENTATION-GUIDE.md
2. Start Wave 1: /task-work TASK-INFRA-001
3. Or use AutoBuild: /feature-build FEAT-INFRA

Original review: TASK-REV-8A3F (marked review_complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━