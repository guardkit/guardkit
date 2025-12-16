/feature-plan Let's build a pack list. So this should have items we can add and categories. We should be able to break it down into categories. So maybe there'll be category for garage, category for welfare, and then maybe even a category for shopping. I think we should have a template sort of master list we create. And then we have the facility to create a list from that for a specific race meeting. And then we can manually remove things from that or add things to that for a particular meeting. And then that way it's persisted. We can look back in history and see which ones we might want. For example, add an item for a particular meeting and then decide that we want to add that to the master later on as well.
Task:Collect review scope clarifications
IN
Execute clarification for feature planning.

CONTEXT TYPE: review_scope

FEATURE: Pack list feature for race meetings - includes items organized by categories (garage, welfare, shopping), master template list, ability to create meeting-specific lists from template, add/remove items per meeting, persist history, and option to promote meeting items to master list.

ESTIMATED COMPLEXITY: 7/10 (data modeling, CRUD operations, list derivation logic, history tracking)

FLAGS:
  --no-questions: false
  --with-questions: false
  --defaults: false
  --answers: null

Ask about:
1. Review focus (all/technical/architecture/performance/security)
2. Trade-off priority (speed/quality/cost/maintainability/balanced)
3. Any specific concerns to address

Present questions in a clear numbered format and wait for user responses. Return their decisions for use in the review phase.
Read display.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 📋 REVIEW SCOPE CLARIFICATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Feature: Pack list for race meetings
Complexity: 7/10 Please answer the following questions to guide the review:
Q1. Review Focus Areas What aspects should the review prioritize?
[A] All aspects (comprehensive)
[T] Technical implementation
[R] Architecture
[P] Performance
[S] Security
Default: A
Q2. Trade-off Priority When making design decisions, what should be prioritized?
[F] Speed of delivery
[Q] Quality/reliability
[C] Cost optimization
[M] Maintainability
[B] Balanced
Default: B
Q3. Data Modeling Approach How should master templates and meeting-specific lists relate?
[R] Recommend (AI decides)
[C] Copy-on-create (independent copies)
[L] Linked references (items reference master)
[H] Hybrid (copy with promotion path)
Default: R
Q4. History Tracking Scope What level of history to preserve?
[R] Recommend (AI decides)
[B] Basic (current state only)
[S] Snapshots (complete state per meeting)
[C] Changes (track additions/removals)
[F] Full audit (detailed log with timestamps)
Default: R
Q5. Specific Concerns Any particular areas to address?
[N] None (standard review)
[D] Database performance
[U] User experience
[I] Integration with existing features
[T] Testing strategy
Default: N
Respond with: 1:X 2:Y 3:Z 4:A 5:B or type defaults for all defaults.
defaults
✓ Using defaults: 1:A 2:B 3:R 4:R 5:N Proceeding with review task creation...
/task-create slash command
/task-create "Plan: Pack list feature for race meetings with master templates, categories, meeting-specific lists, and history tracking" task_type:review priority:high
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


ARGUMENTS: "Plan: Pack list feature for race meetings with master templates, categories, meeting-specific lists, and history tracking" task_type:review priority:high
I'll create this review task for planning the pack list feature.
Globpattern: "tasks/**/*.md"
No files found
Bash Check tasks directory structure
IN
ls -la tasks/ 2>/dev/null || echo "tasks directory does not exist"

OUT
tasks directory does not exist
Bash Create tasks directory structure
IN
mkdir -p tasks/backlog tasks/in_progress tasks/in_review tasks/blocked tasks/completed

OUT
0
Now I'll generate a unique task ID and create the review task:
Bash Generate unique task ID
IN
echo "TASK-REV-$(openssl rand -hex 2 | tr '[:lower:]' '[:upper:]')"

OUT
TASK-REV-47E0
Write TASK-REV-47E0-plan-pack-list-feature.md
80 lines
---
id: TASK-REV-47E0
title: "Plan: Pack list feature for race meetings"
status: backlog
task_type: review
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: high
tags: [planning, feature, pack-list]
complexity: 7
decision_required: true
clarification:
  context_a:
    timestamp: 2025-12-15T00:00:00Z
    decisions:
      focus: all
      tradeoff: balanced
      data_modeling: recommend
      history_tracking: recommend
      specific_concerns: none
---

# Plan: Pack list feature for race meetings

## Description

Design and plan a pack list feature for race meetings that includes:

### Core Requirements
1. **Master Template List**: A template/master list that serves as the base for all pack lists
2. **Categories**: Items organized by categories (garage, welfare, shopping, etc.)
3. **Meeting-Specific Lists**: Ability to create lists for specific race meetings derived from the master template
4. **List Customization**: Add or remove items from meeting-specific lists
5. **History Persistence**: Historical meeting lists are preserved for reference
6. **Master List Updates**: Option to promote items from meeting lists back to the master template

### Key User Stories
- As a user, I want to maintain a master pack list template so I don't have to recreate it each time
- As a user, I want to organize items into categories for easier management
- As a user, I want to create a pack list for a specific race meeting based on my template
- As a user, I want to add/remove items for a specific meeting without affecting the master
- As a user, I want to view historical pack lists to see what I packed for previous meetings
- As a user, I want to promote useful items from a meeting list to my master template

## Review Scope

### Focus Areas (All Aspects)
- Technical implementation approach
- Data model design
- Architecture patterns
- Performance considerations
- Security/access control

### Trade-off Priority
- Balanced approach across speed, quality, cost, and maintainability

## Analysis Required

- [ ] Data model design for templates, categories, items, and meeting lists
- [ ] Relationship approach (copy-on-create vs linked references vs hybrid)
- [ ] History tracking strategy
- [ ] API design for CRUD operations
- [ ] UI/UX considerations for list management
- [ ] Integration with existing race meeting features

## Decision Points

1. **Data Model**: How to structure templates, categories, items, and meeting lists
2. **Copy Strategy**: How meeting lists relate to master template
3. **History Approach**: What level of history to maintain
4. **Tech Stack**: Specific implementation technologies

## Acceptance Criteria

- [ ] Clear data model design documented
- [ ] Implementation approach recommended with justification
- [ ] Effort estimation provided
- [ ] Risk assessment completed
- [ ] Subtask breakdown ready for implementation phase

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Review Task Created: TASK-REV-47E0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Task Details
Title: Plan: Pack list feature for race meetings
Type: review (decision required)
Priority: high
Complexity: 7/10

📁 File Location
tasks/backlog/TASK-REV-47E0-plan-pack-list-feature.md

Proceeding to review analysis...
Now I'll execute the task review with decision mode:
/task-review slash command
/task-review TASK-REV-47E0 --mode=decision --depth=standard
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


ARGUMENTS: TASK-REV-47E0 --mode=decision --depth=standard
I'll execute the review analysis for the pack list feature planning task.
Read TASK-REV-47E0-plan-pack-list-feature.md
Task:Explore kartlog codebase structure
IN
Explore the kartlog codebase to understand:

1. The existing project structure and architecture
2. What frameworks/technologies are in use (React Native, Expo, etc.)
3. Existing data models and how they're structured
4. How state management is handled
5. Any existing list/item management patterns
6. Database or storage approach (SQLite, AsyncStorage, etc.)

Focus on understanding the patterns already established so we can recommend an approach for the pack list feature that aligns with existing conventions.

Be thorough - check package.json, app structure, existing components, models, services, etc.
Bash List top-level directory contents
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/

OUT
total 32
drwxr-xr-x   11 richardwoollcott  staff   352 Dec 15 18:17 .
drwxr-xr-x  125 richardwoollcott  staff  4000 Dec 15 12:13 ..
drwx------    3 richardwoollcott  staff    96 Dec 15 18:16 .claude
drwxr-xr-x   15 richardwoollcott  staff   480 Dec 15 18:13 .git
-rw-r--r--    1 richardwoollcott  staff  4688 Dec 15 18:11 .gitignore
drwxr-xr-x@  12 richardwoollcott  staff   384 Dec 15 18:12 fastapi-auth
drwxr-xr-x@  29 richardwoollcott  staff   928 Dec 15 18:12 kartlog
-rw-r--r--    1 richardwoollcott  staff  1065 Dec 15 12:13 LICENSE
drwxr-xr-x@   2 richardwoollcott  staff    64 Dec 15 14:56 migrations
-rw-r--r--    1 richardwoollcott  staff    20 Dec 15 12:13 README.md
drwxr-xr-x    7 richardwoollcott  staff   224 Dec 15 18:17 tasks
Bash List kartlog directory contents
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/

OUT
total 712
drwxr-xr-x@ 29 richardwoollcott  staff     928 Dec 15 18:12 .
drwxr-xr-x  11 richardwoollcott  staff     352 Dec 15 18:17 ..
drwxr-xr-x@ 12 richardwoollcott  staff     384 Dec 15 18:12 .claude
-rw-r--r--   1 richardwoollcott  staff      94 Dec 15 18:12 .firebaserc
drwxr-xr-x   4 richardwoollcott  staff     128 Dec 15 18:12 .github
-rw-r--r--   1 richardwoollcott  staff     264 Dec 15 18:12 .gitignore
-rw-r--r--   1 richardwoollcott  staff       0 Dec 15 18:12 .nojekyll
drwxr-xr-x   3 richardwoollcott  staff      96 Dec 15 18:12 .vscode
-rw-r--r--   1 richardwoollcott  staff    6137 Dec 15 18:12 AI_CHAT_SETUP.md
drwxr-xr-x   4 richardwoollcott  staff     128 Dec 15 18:12 docs
-rw-r--r--   1 richardwoollcott  staff    2215 Dec 15 18:12 FIREBASE_SETUP.md
-rw-r--r--   1 richardwoollcott  staff     328 Dec 15 18:12 firebase.json
-rw-r--r--   1 richardwoollcott  staff    1449 Dec 15 18:12 firestore.indexes.json
-rw-r--r--   1 richardwoollcott  staff    2280 Dec 15 18:12 firestore.rules
-rw-r--r--   1 richardwoollcott  staff    1302 Dec 15 18:12 index.html
-rw-r--r--   1 richardwoollcott  staff    4115 Dec 15 18:12 initial-specification.md
-rw-r--r--   1 richardwoollcott  staff     938 Dec 15 18:12 jsconfig.json
drwxr-xr-x@  2 richardwoollcott  staff      64 Dec 15 15:25 migrations
-rw-r--r--   1 richardwoollcott  staff  298647 Dec 15 18:12 package-lock.json
-rw-r--r--   1 richardwoollcott  staff    1053 Dec 15 18:12 package.json
drwxr-xr-x  10 richardwoollcott  staff     320 Dec 15 18:12 public
-rw-r--r--   1 richardwoollcott  staff    3752 Dec 15 18:12 README.md
drwxr-xr-x@  9 richardwoollcott  staff     288 Dec 15 18:12 src
-rw-r--r--   1 richardwoollcott  staff     228 Dec 15 18:12 svelte.config.js
drwxr-xr-x@  7 richardwoollcott  staff     224 Dec 15 18:12 tasks
drwxr-xr-x   6 richardwoollcott  staff     192 Dec 15 18:12 test
drwxr-xr-x@  5 richardwoollcott  staff     160 Dec 15 16:31 tests
drwxr-xr-x  11 richardwoollcott  staff     352 Dec 15 18:12 upload
-rw-r--r--   1 richardwoollcott  staff    2686 Dec 15 18:12 vite.config.js
Read vite.config.js
Bash Find all source files
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src -type f -name "*.js" -o -name "*.svelte" | head -30

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/App.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/main.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/components/Navigation.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/components/FilterPills.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/components/SessionsTable.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/stores.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/weather.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/engines.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/sessions.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/tracks.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/chassis.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/tyres.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore/firebase.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/databaseListeners.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/query.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/sessionFormat.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/sessionStats.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/chat.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore-mock/testData.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore-mock/index.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firestore-mock/firebase.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/firebase.js
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditTrack.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/ViewSession.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Login.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Tyres.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditEngine.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Chassis.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewTyre.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/marketing.svelte
Read stores.js
Read firebase.js
Read engines.js
Read query.js
Read NewTyre.svelte
Bash List lib directory to see what utilities exist
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/lib/

OUT
total 104
drwxr-xr-x@ 12 richardwoollcott  staff    384 Dec 15 15:22 .
drwxr-xr-x@  9 richardwoollcott  staff    288 Dec 15 18:12 ..
-rw-r--r--@  1 richardwoollcott  staff  15506 Dec 15 15:22 chat.js
-rw-r--r--@  1 richardwoollcott  staff   3716 Dec 15 15:22 databaseListeners.js
-rw-r--r--@  1 richardwoollcott  staff   3637 Dec 15 15:22 firebase.js
drwxr-xr-x@  8 richardwoollcott  staff    256 Dec 15 15:22 firestore
drwxr-xr-x@  5 richardwoollcott  staff    160 Dec 15 15:22 firestore-mock
-rw-r--r--@  1 richardwoollcott  staff   9679 Dec 15 15:22 query.js
-rw-r--r--@  1 richardwoollcott  staff   4010 Dec 15 15:22 sessionFormat.js
-rw-r--r--@  1 richardwoollcott  staff   1207 Dec 15 15:22 sessionStats.js
-rw-r--r--@  1 richardwoollcott  staff    887 Dec 15 15:22 stores.js
-rw-r--r--@  1 richardwoollcott  staff   2962 Dec 15 15:22 weather.js
Read sessionStats.js
Read chassis.js
Bash List all route files
IN
find /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes -name "*.svelte" | head -20

OUT
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditTrack.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/ViewSession.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Login.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Tyres.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditEngine.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Chassis.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewTyre.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/marketing.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewSession.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditChassis.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditSession.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewChassis.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewTrack.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Engines.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/NewEngine.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Tracks.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Sessions.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/EditTyre.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Dashboard.svelte
/Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/kartlog/src/routes/Chat.svelte
Read README.md
Read table.css
Read app.css
Excellent! I now have comprehensive understanding of the kartlog codebase. Let me complete the technical options analysis for the pack list feature.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 TECHNICAL OPTIONS ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: Pack list for race meetings
Review Mode: decision
Analysis Depth: standard
Codebase Context
Stack: Svelte 5 + Vite + Firebase/Firestore + SMUI (Material UI) Patterns: Repository pattern, user-scoped collections, reactive stores Existing entities: Tyres, Engines, Chassis, Tracks, Sessions
OPTION 1: Hybrid Copy-on-Create with Template References (Recommended)
Complexity: 6/10 Effort: 12-16 hours
Data Model

// Collection: pack_templates (master templates)
{
  id: string,
  userId: string,
  name: string,                    // "Standard Race Weekend"
  description: string,
  categories: [
    { id: "cat-1", name: "Garage", order: 0 },
    { id: "cat-2", name: "Welfare", order: 1 },
    { id: "cat-3", name: "Shopping", order: 2 }
  ],
  items: [
    { id: "item-1", categoryId: "cat-1", name: "Toolbox", checked: false },
    { id: "item-2", categoryId: "cat-1", name: "Spare sprockets", checked: false },
    { id: "item-3", categoryId: "cat-2", name: "Camping chairs", checked: false }
  ],
  createdAt: Date,
  updatedAt: Date
}

// Collection: pack_lists (meeting-specific lists)
{
  id: string,
  userId: string,
  templateId: string,              // Reference to source template
  meetingName: string,             // "Round 3 - Whilton Mill"
  meetingDate: Date,
  categories: [...],               // COPIED from template at creation
  items: [
    { id: "item-1", categoryId: "cat-1", name: "Toolbox", checked: true },
    { id: "item-4", categoryId: "cat-1", name: "Extra fuel can", checked: false, addedToList: true }
  ],
  status: "active" | "archived",
  createdAt: Date,
  updatedAt: Date
}
Pros
✅ Meeting lists are independent after creation (no cascading changes)
✅ Easy to track meeting-specific additions (addedToList: true)
✅ Simple "promote to master" flow (copy item to template)
✅ History preserved naturally (archived lists remain intact)
✅ Aligns perfectly with existing Firestore patterns
Cons
⚠️ Template changes don't propagate to existing meeting lists
⚠️ Slight data duplication (categories/items copied per list)
Why Recommended
This matches the user's mental model: "create a list from template, customize it, keep it for history." The duplication is acceptable for this use case and simplifies the architecture significantly.
OPTION 2: Linked References with Override Layer
Complexity: 8/10 Effort: 20-24 hours
Data Model

// Collection: pack_templates
{
  id: string,
  userId: string,
  name: string,
  categories: [...],
  items: [...]
}

// Collection: pack_lists
{
  id: string,
  userId: string,
  templateId: string,              // LIVE reference
  meetingName: string,
  meetingDate: Date,
  overrides: {
    removedItems: ["item-1", "item-3"],
    addedItems: [
      { id: "local-1", categoryId: "cat-1", name: "Extra fuel", checked: false }
    ],
    checkedState: { "item-2": true, "local-1": false }
  },
  status: "active" | "archived"
}
Pros
✅ Template changes automatically reflect in all linked lists
✅ Minimal data duplication
✅ Clear separation between template items and overrides
Cons
❌ Complex merge logic required at read time
❌ Confusing UX: "Why did my list change?"
❌ Archived lists would still change if template modified
❌ More complex queries and UI state management
❌ Doesn't match user's stated requirement ("persisted history")
OPTION 3: Single Collection with Type Flag
Complexity: 5/10 Effort: 10-12 hours
Data Model

// Collection: pack_lists (both templates and meeting lists)
{
  id: string,
  userId: string,
  type: "template" | "meeting",
  name: string,
  meetingDate: Date | null,
  sourceTemplateId: string | null,
  categories: [...],
  items: [...],
  status: "active" | "archived"
}
Pros
✅ Simpler single collection
✅ Easier querying (one collection)
✅ Less code to maintain
Cons
⚠️ Mixed concerns in one collection
⚠️ Harder to enforce different business rules per type
⚠️ Less clear data model semantics
⚠️ May hit Firestore query limitations with complex filters
RECOMMENDATION: Option 1 - Hybrid Copy-on-Create
Rationale:
User Intent Match: The user explicitly wants to "look back in history" - this requires immutable snapshots
Pattern Alignment: Follows existing kartlog repository pattern exactly
Simplicity: No complex merge logic, straightforward CRUD
Balanced Trade-off: Small duplication cost for major simplicity gains
IMPLEMENTATION BREAKDOWN
Subtask 1: Data Model & Repository Layer
Effort: 3-4 hours | Mode: task-work Create Firestore repository modules:
src/lib/firestore/packTemplates.js - CRUD for master templates
src/lib/firestore/packLists.js - CRUD for meeting lists + create-from-template
Subtask 2: Master Template Management UI
Effort: 3-4 hours | Mode: task-work Components:
PackTemplates.svelte - List all templates
NewPackTemplate.svelte - Create template with categories/items
EditPackTemplate.svelte - Modify template
Subtask 3: Meeting Pack List UI
Effort: 3-4 hours | Mode: task-work Components:
PackLists.svelte - List all meeting lists (active + archived)
NewPackList.svelte - Create from template, assign to meeting
ViewPackList.svelte - Check items, add/remove items
Subtask 4: Item Promotion & History Features
Effort: 2-3 hours | Mode: task-work Features:
"Add to master template" action on meeting-specific items
Archive/view historical lists
Filter lists by meeting date
Subtask 5: Navigation & Integration
Effort: 1-2 hours | Mode: direct
Add routes to App.svelte
Add navigation menu items
Dashboard widgets (if desired)
RISK ASSESSMENT
Risk	Likelihood	Impact	Mitigation
Large item lists slow Firestore	Low	Medium	Paginate or limit items per template
Category management complexity	Medium	Low	Start with fixed categories, add custom later
Mobile UX for checkboxes	Low	Medium	Use SMUI Checkbox with large touch targets
EFFORT SUMMARY
Phase	Effort	Dependencies
Data Model & Repository	3-4 hrs	None
Template Management UI	3-4 hrs	Repository
Meeting List UI	3-4 hrs	Repository
Promotion & History	2-3 hrs	Both UIs
Navigation Integration	1-2 hrs	All UIs
Total	12-17 hrs	

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete for: Plan: Pack list feature for race meetings

Options Analyzed:
  1. Hybrid Copy-on-Create (Recommended) - 6/10 complexity
  2. Linked References with Override Layer - 8/10 complexity  
  3. Single Collection with Type Flag - 5/10 complexity

Recommendation: Option 1 - Hybrid Copy-on-Create
  - Best match for user requirements (history preservation)
  - Aligns with existing kartlog patterns
  - Balanced complexity vs. maintainability

Estimated Effort: 12-17 hours across 5 subtasks

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What would you like to do?

  [A]ccept  - Approve findings, save for reference
  [R]evise  - Request deeper analysis on specific areas
  [I]mplement - Create implementation tasks (5 subtasks)
  [C]ancel  - Discard this review

Your choice [A/R/I/C]:
I
You've chosen [I]mplement. Let me collect your implementation preferences.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Approach Selection
    Which approach should subtasks follow?

    [1] Hybrid Copy-on-Create (Recommended)
    [2] Linked References with Override Layer
    [3] Single Collection with Type Flag

    Default: [1]
    Your choice [1/2/3]: 
Q2. Execution Preference How should 5 subtasks be executed?

[P]arallel - Waves with Conductor workspaces
[S]equential - One at a time
[D]etect automatically (recommended)

Default: [D]
Q3. Testing Depth What testing depth for subtasks?

[F]ull TDD (test-first)
[S]tandard (quality gates)
[M]inimal (compilation only)
[D]efault (based on complexity)

Default: [D]
Respond with: 1:X 2:Y 3:Z or type defaults for all defaults.
1, D, F
✓ Implementation preferences recorded:
Approach: Hybrid Copy-on-Create (Option 1)
Execution: Auto-detect (parallel where safe)
Testing: Full TDD (test-first)
Creating feature implementation structure...
Bash Create pack-list feature subfolder
IN
mkdir -p tasks/backlog/pack-list-feature

OUT
0
Write README.md
104 lines
# Pack List Feature for Race Meetings

## Problem Statement

Kart racers need to manage equipment and supplies for race meetings. Currently there's no way to:
- Maintain a master checklist of items to pack
- Organize items by category (garage, welfare, shopping)
- Create meeting-specific lists derived from a template
- Track what was packed for historical meetings
- Learn from past meetings by promoting items to the master template

## Solution Approach

**Selected: Hybrid Copy-on-Create with Template References**

This approach creates independent meeting lists from master templates:
- Master templates define reusable pack lists with categories and items
- Meeting lists are created by copying from a template
- Meeting lists can be customized (add/remove items) without affecting the master
- Historical lists are preserved for reference
- Items can be promoted from meeting lists back to the master template

### Why This Approach

1. **Matches User Mental Model**: "Create from template, customize, keep history"
2. **Aligns with Existing Patterns**: Follows kartlog's repository pattern
3. **Simple Implementation**: No complex merge logic or live references
4. **History Preservation**: Archived lists remain unchanged

## Data Model

### Pack Templates Collection
```javascript
{
  id: string,
  userId: string,
  name: string,                    // "Standard Race Weekend"
  description: string,
  categories: [
    { id: "cat-1", name: "Garage", order: 0 },
    { id: "cat-2", name: "Welfare", order: 1 }
  ],
  items: [
    { id: "item-1", categoryId: "cat-1", name: "Toolbox" },
    { id: "item-2", categoryId: "cat-2", name: "Camping chairs" }
  ],
  createdAt: Date,
  updatedAt: Date
}
```

### Pack Lists Collection (Meeting-Specific)
```javascript
{
  id: string,
  userId: string,
  templateId: string,              // Reference to source template
  meetingName: string,             // "Round 3 - Whilton Mill"
  meetingDate: Date,
  categories: [...],               // Copied from template
  items: [
    { id: "item-1", categoryId: "cat-1", name: "Toolbox", checked: true },
    { id: "item-4", categoryId: "cat-1", name: "Extra fuel", checked: false, addedToList: true }
  ],
  status: "active" | "archived",
  createdAt: Date,
  updatedAt: Date
}
```

## Subtasks

| ID | Title | Complexity | Mode | Wave |
|----|-------|------------|------|------|
| TASK-PL-001 | Create data model and repository layer | 6/10 | task-work | 1 |
| TASK-PL-002 | Build master template management UI | 5/10 | task-work | 2 |
| TASK-PL-003 | Build meeting pack list UI | 5/10 | task-work | 2 |
| TASK-PL-004 | Implement item promotion and history features | 4/10 | task-work | 3 |
| TASK-PL-005 | Add navigation and integration | 3/10 | direct | 3 |

## Execution Strategy

### Wave 1 (Sequential - Foundation)
- TASK-PL-001: Repository layer must complete first

### Wave 2 (Parallel - UI Components)
- TASK-PL-002 and TASK-PL-003 can run in parallel
- Both depend on Wave 1 completion

### Wave 3 (Parallel - Features & Integration)
- TASK-PL-004 and TASK-PL-005 can run in parallel
- Both depend on Wave 2 completion

## Estimated Effort

- **Total**: 12-17 hours
- **Testing**: Full TDD approach (test-first)

## Review Source

- Review Task: TASK-REV-47E0
- Review Date: 2025-12-15
- Decision: Implement Option 1 (Hybrid Copy-on-Create)
Write IMPLEMENTATION-GUIDE.md
168 lines
# Implementation Guide: Pack List Feature

## Overview

This guide provides the execution strategy for implementing the pack list feature across 5 subtasks organized into 3 waves.

## Architecture Decisions

### Approach: Hybrid Copy-on-Create
- Templates and meeting lists are separate collections
- Meeting lists copy template data at creation time
- No live references (changes to template don't affect existing lists)
- Meeting-specific items tracked with `addedToList: true` flag

### Testing: Full TDD
- Write tests before implementation
- Each subtask includes test requirements
- Quality gates enforced at completion

## Execution Waves

### Wave 1: Foundation (Sequential)

**Must complete before Wave 2**

#### TASK-PL-001: Data Model & Repository Layer
- Create `src/lib/firestore/packTemplates.js`
- Create `src/lib/firestore/packLists.js`
- Implement CRUD operations following existing patterns
- Add `createFromTemplate()` function for list creation

**Key Files**:
```
src/lib/firestore/packTemplates.js
src/lib/firestore/packLists.js
```

---

### Wave 2: UI Components (Parallel)

**Can execute TASK-PL-002 and TASK-PL-003 simultaneously**

#### TASK-PL-002: Master Template Management UI

**Components**:
```
src/routes/PackTemplates.svelte      # List all templates
src/routes/NewPackTemplate.svelte    # Create template
src/routes/EditPackTemplate.svelte   # Edit template
```

**Features**:
- SMUI DataTable for template list
- Category management (add/remove/reorder)
- Item management within categories
- Edit/Delete actions

#### TASK-PL-003: Meeting Pack List UI

**Components**:
```
src/routes/PackLists.svelte          # List all meeting lists
src/routes/NewPackList.svelte        # Create from template
src/routes/ViewPackList.svelte       # Check items, manage list
```

**Features**:
- Template selection when creating new list
- Meeting name and date assignment
- Checkbox interface for packing items
- Add custom items to list
- Archive completed lists

---

### Wave 3: Features & Integration (Parallel)

**Can execute TASK-PL-004 and TASK-PL-005 simultaneously**

#### TASK-PL-004: Item Promotion & History

**Features**:
- "Add to master template" action on meeting-specific items
- View archived/historical lists
- Filter lists by date range
- Statistics on item usage

#### TASK-PL-005: Navigation & Integration

**Changes**:
```
src/App.svelte                       # Add routes
src/routes/Dashboard.svelte          # Optional widgets
```

**Routes to add**:
```javascript
'/pack-templates': PackTemplates,
'/pack-templates/new': NewPackTemplate,
'/pack-templates/:id': EditPackTemplate,
'/pack-lists': PackLists,
'/pack-lists/new': NewPackList,
'/pack-lists/:id': ViewPackList,
```

---

## Conductor Workspace Assignments

For parallel execution with Conductor:

| Wave | Task | Workspace Name |
|------|------|----------------|
| 2 | TASK-PL-002 | pack-list-wave2-templates |
| 2 | TASK-PL-003 | pack-list-wave2-lists |
| 3 | TASK-PL-004 | pack-list-wave3-features |
| 3 | TASK-PL-005 | pack-list-wave3-nav |

## Testing Requirements (TDD)

### Repository Layer Tests
- Test CRUD operations for templates
- Test CRUD operations for pack lists
- Test `createFromTemplate()` copies correctly
- Test user scoping (userId filter)

### UI Component Tests
- Test template list rendering
- Test category/item management
- Test checkbox state persistence
- Test item promotion flow

### Integration Tests
- Test full flow: create template -> create list -> check items -> archive
- Test promotion: add item to list -> promote to master

## Dependencies

### External
- Firebase/Firestore (existing)
- SMUI components (existing)

### Internal
- Wave 2 depends on Wave 1
- Wave 3 depends on Wave 2

## File Conflict Analysis

**No conflicts detected** - all new files:
- Wave 2 tasks create different component sets
- Wave 3 tasks modify different areas (features vs navigation)

## Quality Gates

Each subtask must pass:
1. All tests passing (TDD - tests written first)
2. No TypeScript/linting errors
3. Code review checklist
4. Manual verification of feature

## Next Steps

1. Start with TASK-PL-001 (repository layer)
2. After completion, run TASK-PL-002 and TASK-PL-003 in parallel
3. After both complete, run TASK-PL-004 and TASK-PL-005 in parallel
4. Final integration testing
Now creating the 5 subtask files:
Write TASK-PL-001-data-model-repository.md
127 lines
---
id: TASK-PL-001
title: Create data model and repository layer for pack lists
status: backlog
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: high
tags: [pack-list, data-model, firestore, repository]
complexity: 6
parent_feature: pack-list-feature
wave: 1
execution_mode: task-work
testing_mode: tdd
dependencies: []
blocks: [TASK-PL-002, TASK-PL-003]
---

# Create Data Model and Repository Layer

## Description

Implement the Firestore repository layer for pack templates and pack lists, following the existing kartlog patterns (tyres, engines, chassis).

## Acceptance Criteria

- [ ] `packTemplates.js` repository with full CRUD operations
- [ ] `packLists.js` repository with full CRUD operations
- [ ] `createFromTemplate()` function that copies template to new list
- [ ] All functions filter by `userId` (user-scoped)
- [ ] Timestamps managed correctly (`createdAt`, `updatedAt`)
- [ ] Unit tests written FIRST (TDD approach)
- [ ] All tests passing

## Technical Specification

### Pack Templates Repository (`src/lib/firestore/packTemplates.js`)

```javascript
// Functions to implement:
export const addPackTemplate = async (name, description, categories, items) => {...}
export const getUserPackTemplates = async () => {...}
export const getPackTemplate = async (templateId) => {...}
export const updatePackTemplate = async (templateId, data) => {...}
export const deletePackTemplate = async (templateId) => {...}
export const addCategoryToTemplate = async (templateId, category) => {...}
export const addItemToTemplate = async (templateId, item) => {...}
export const removeItemFromTemplate = async (templateId, itemId) => {...}
```

### Pack Lists Repository (`src/lib/firestore/packLists.js`)

```javascript
// Functions to implement:
export const createPackListFromTemplate = async (templateId, meetingName, meetingDate) => {...}
export const getUserPackLists = async (status = null) => {...}  // filter by status
export const getPackList = async (listId) => {...}
export const updatePackList = async (listId, data) => {...}
export const deletePackList = async (listId) => {...}
export const toggleItemChecked = async (listId, itemId) => {...}
export const addItemToList = async (listId, item) => {...}  // sets addedToList: true
export const removeItemFromList = async (listId, itemId) => {...}
export const archivePackList = async (listId) => {...}
export const promoteItemToTemplate = async (listId, itemId, templateId) => {...}
```

### Data Structures

**Category**:
```javascript
{
  id: string,        // UUID
  name: string,      // "Garage", "Welfare", "Shopping"
  order: number      // For sorting
}
```

**Item**:
```javascript
{
  id: string,        // UUID
  categoryId: string,
  name: string,
  checked: boolean,      // Only in pack lists
  addedToList: boolean   // Only in pack lists, true if not from template
}
```

## Test Requirements (TDD)

Write tests BEFORE implementation:

### packTemplates.test.js
- `addPackTemplate` creates template with correct structure
- `getUserPackTemplates` returns only current user's templates
- `updatePackTemplate` updates fields and sets `updatedAt`
- `deletePackTemplate` removes template
- `addItemToTemplate` adds item to correct category

### packLists.test.js
- `createPackListFromTemplate` copies all categories and items
- `createPackListFromTemplate` sets `templateId` reference
- `createPackListFromTemplate` initializes all items as unchecked
- `toggleItemChecked` updates single item's checked state
- `addItemToList` adds item with `addedToList: true`
- `archivePackList` sets status to "archived"
- `promoteItemToTemplate` copies item to template

## Implementation Notes

- Use existing Firebase abstraction from `src/lib/firebase.js`
- Follow exact pattern from `src/lib/firestore/tyres.js`
- Generate UUIDs for categories and items (use `crypto.randomUUID()`)
- User scoping: always filter by `auth.currentUser.uid`

## Files to Create

```
src/lib/firestore/packTemplates.js
src/lib/firestore/packLists.js
src/lib/firestore/__tests__/packTemplates.test.js  (if test dir exists)
src/lib/firestore/__tests__/packLists.test.js      (if test dir exists)
```

## Estimated Effort

3-4 hours (including TDD test writing)
Write TASK-PL-002-template-management-ui.md
135 lines
---
id: TASK-PL-002
title: Build master template management UI
status: backlog
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: high
tags: [pack-list, ui, svelte, templates]
complexity: 5
parent_feature: pack-list-feature
wave: 2
execution_mode: task-work
testing_mode: tdd
dependencies: [TASK-PL-001]
blocks: [TASK-PL-004]
conductor_workspace: pack-list-wave2-templates
---

# Build Master Template Management UI

## Description

Create the Svelte components for managing pack list templates (master lists). Users can create, edit, and delete templates with categories and items.

## Acceptance Criteria

- [ ] `PackTemplates.svelte` - List all user's templates
- [ ] `NewPackTemplate.svelte` - Create new template with categories/items
- [ ] `EditPackTemplate.svelte` - Edit existing template
- [ ] Category management (add, rename, reorder, delete)
- [ ] Item management within categories (add, edit, delete)
- [ ] SMUI components used consistently with existing app
- [ ] Responsive design (mobile-friendly)
- [ ] Tests written FIRST (TDD approach)

## Technical Specification

### PackTemplates.svelte (List View)

```svelte
<!-- Pattern: Follow Tyres.svelte exactly -->
<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getUserPackTemplates, deletePackTemplate } from '$lib/firestore/packTemplates';

  let templates = [];
  let loading = true;

  onMount(async () => {
    templates = await getUserPackTemplates();
    loading = false;
  });
</script>

<!-- SMUI DataTable with columns: Name, Categories, Items, Actions -->
```

**Columns**:
- Name (clickable to edit)
- Categories count
- Items count
- Last updated
- Actions (Edit, Delete)

### NewPackTemplate.svelte (Create)

**Form Fields**:
- Name (required)
- Description (optional)
- Categories section (dynamic list)
- Items section (grouped by category)

**Category Management**:
- Add category button
- Inline rename
- Drag to reorder (or up/down buttons)
- Delete with confirmation

**Item Management**:
- Add item to category
- Edit item name
- Delete item
- Move item between categories (optional)

### EditPackTemplate.svelte (Edit)

Same as NewPackTemplate but:
- Load existing data in `onMount`
- Update instead of create on submit
- Show item count statistics

## UI Components to Use

From SMUI (already in project):
- `DataTable`, `Head`, `Body`, `Row`, `Cell`
- `Button`, `IconButton`
- `Textfield`
- `Card`
- `List`, `Item`
- `Menu` (for actions)

## Design Patterns

Follow existing patterns from:
- `src/routes/Tyres.svelte` - List view pattern
- `src/routes/NewTyre.svelte` - Create form pattern
- `src/routes/EditTyre.svelte` - Edit form pattern

## Test Requirements (TDD)

### Component Tests
- Template list renders correctly with mock data
- Create form validates required fields
- Category add/remove updates state
- Item add/remove updates state
- Form submission calls repository functions

## Files to Create

```
src/routes/PackTemplates.svelte
src/routes/NewPackTemplate.svelte
src/routes/EditPackTemplate.svelte
```

## Estimated Effort

3-4 hours (including TDD test writing)

## Notes

- Can run in parallel with TASK-PL-003 (different components)
- Conductor workspace: `pack-list-wave2-templates`
Write TASK-PL-003-meeting-list-ui.md
166 lines
---
id: TASK-PL-003
title: Build meeting pack list UI
status: backlog
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: high
tags: [pack-list, ui, svelte, meetings]
complexity: 5
parent_feature: pack-list-feature
wave: 2
execution_mode: task-work
testing_mode: tdd
dependencies: [TASK-PL-001]
blocks: [TASK-PL-004]
conductor_workspace: pack-list-wave2-lists
---

# Build Meeting Pack List UI

## Description

Create the Svelte components for managing meeting-specific pack lists. Users can create lists from templates, check items as packed, and add custom items.

## Acceptance Criteria

- [ ] `PackLists.svelte` - List all meeting pack lists (active + archived)
- [ ] `NewPackList.svelte` - Create list from template with meeting details
- [ ] `ViewPackList.svelte` - Interactive checklist view
- [ ] Checkbox interface for marking items as packed
- [ ] Add custom items to a meeting list
- [ ] Remove items from meeting list
- [ ] Archive completed lists
- [ ] Filter by status (active/archived)
- [ ] Tests written FIRST (TDD approach)

## Technical Specification

### PackLists.svelte (List View)

```svelte
<script>
  import { onMount } from 'svelte';
  import { getUserPackLists } from '$lib/firestore/packLists';

  let lists = [];
  let filter = 'active'; // 'active' | 'archived' | 'all'

  $: filteredLists = filter === 'all'
    ? lists
    : lists.filter(l => l.status === filter);
</script>

<!-- SMUI DataTable -->
```

**Columns**:
- Meeting Name
- Meeting Date
- Template Name
- Progress (checked/total items)
- Status badge
- Actions (View, Archive, Delete)

### NewPackList.svelte (Create from Template)

**Form Fields**:
- Template selector (dropdown of user's templates)
- Meeting name (required)
- Meeting date (date picker)

**On Submit**:
1. Call `createPackListFromTemplate(templateId, meetingName, meetingDate)`
2. Navigate to ViewPackList

### ViewPackList.svelte (Interactive Checklist)

**Layout**:
```
┌─────────────────────────────────────┐
│ Meeting: Round 3 - Whilton Mill     │
│ Date: 15 Dec 2025                   │
│ Progress: 12/15 items checked       │
├─────────────────────────────────────┤
│ ▼ Garage (5/7)                      │
│   [x] Toolbox                       │
│   [x] Spare sprockets               │
│   [ ] Fuel can                      │
│   [ ] *Extra brake pads (added)     │
│   [+ Add item to Garage]            │
├─────────────────────────────────────┤
│ ▼ Welfare (4/5)                     │
│   [x] Camping chairs                │
│   [ ] Cool box                      │
│   [+ Add item to Welfare]           │
├─────────────────────────────────────┤
│ [Archive List]                      │
└─────────────────────────────────────┘
```

**Features**:
- Collapsible category sections
- Checkbox toggles call `toggleItemChecked()`
- "Add item" inline form per category
- Added items marked with asterisk or badge
- Progress bar/percentage
- Archive button (moves to archived status)

**Item Actions**:
- Check/uncheck
- Remove (with confirmation)
- "Add to master" (for added items) - links to TASK-PL-004

## UI Components to Use

From SMUI:
- `Checkbox`, `FormField`
- `Card`
- `Button`, `IconButton`
- `Textfield`
- `Select`, `Option` (template selector)
- `Chip` (for status badges)
- `LinearProgress` (for progress bar)

## Design Patterns

**Optimistic Updates**:
```javascript
// Toggle checkbox immediately, then persist
const handleToggle = async (itemId) => {
  // Update local state immediately
  items = items.map(i =>
    i.id === itemId ? {...i, checked: !i.checked} : i
  );
  // Persist to Firestore
  await toggleItemChecked(listId, itemId);
};
```

## Test Requirements (TDD)

### Component Tests
- List view shows active lists by default
- Filter switches between active/archived
- Create form requires template selection
- Checkbox toggle updates item state
- Add item appears with "added" indicator
- Archive moves list to archived status

## Files to Create

```
src/routes/PackLists.svelte
src/routes/NewPackList.svelte
src/routes/ViewPackList.svelte
```

## Estimated Effort

3-4 hours (including TDD test writing)

## Notes

- Can run in parallel with TASK-PL-002 (different components)
- Conductor workspace: `pack-list-wave2-lists`
Write TASK-PL-004-promotion-history.md
201 lines
---
id: TASK-PL-004
title: Implement item promotion and history features
status: backlog
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: medium
tags: [pack-list, features, history, promotion]
complexity: 4
parent_feature: pack-list-feature
wave: 3
execution_mode: task-work
testing_mode: tdd
dependencies: [TASK-PL-002, TASK-PL-003]
blocks: []
conductor_workspace: pack-list-wave3-features
---

# Implement Item Promotion and History Features

## Description

Add the ability to promote meeting-specific items back to the master template, and implement history viewing/filtering for archived pack lists.

## Acceptance Criteria

- [ ] "Add to master template" action on meeting-added items
- [ ] Confirmation dialog before promotion
- [ ] Visual indicator that item was promoted
- [ ] Historical list viewing (read-only for archived)
- [ ] Filter pack lists by date range
- [ ] Item usage statistics (optional)
- [ ] Tests written FIRST (TDD approach)

## Technical Specification

### Item Promotion Flow

**In ViewPackList.svelte**:

```svelte
{#each items as item}
  <div class="item">
    <Checkbox checked={item.checked} on:change={() => toggleItem(item.id)} />
    <span>{item.name}</span>

    {#if item.addedToList && !item.promotedToMaster}
      <IconButton
        on:click={() => handlePromote(item)}
        title="Add to master template"
      >
        <Icon>add_circle</Icon>
      </IconButton>
    {/if}

    {#if item.promotedToMaster}
      <Chip>Added to master</Chip>
    {/if}
  </div>
{/each}
```

**Promotion Handler**:

```javascript
const handlePromote = async (item) => {
  const confirmed = confirm(
    `Add "${item.name}" to your master template "${templateName}"?`
  );

  if (confirmed) {
    await promoteItemToTemplate(listId, item.id, templateId);
    // Update local state to show promotion badge
    items = items.map(i =>
      i.id === item.id ? {...i, promotedToMaster: true} : i
    );
  }
};
```

### History Viewing

**Enhanced PackLists.svelte**:

```svelte
<script>
  let dateFilter = { from: null, to: null };
  let statusFilter = 'all'; // 'active' | 'archived' | 'all'

  $: filteredLists = lists.filter(list => {
    const matchesStatus = statusFilter === 'all' || list.status === statusFilter;
    const matchesDate = !dateFilter.from ||
      (list.meetingDate >= dateFilter.from && list.meetingDate <= dateFilter.to);
    return matchesStatus && matchesDate;
  });
</script>

<!-- Filter controls -->
<div class="filters">
  <Select bind:value={statusFilter}>
    <Option value="all">All Lists</Option>
    <Option value="active">Active</Option>
    <Option value="archived">Archived</Option>
  </Select>

  <Textfield type="date" bind:value={dateFilter.from} label="From" />
  <Textfield type="date" bind:value={dateFilter.to} label="To" />
</div>
```

### Archived List View

**ViewPackList.svelte** - Read-only mode for archived:

```svelte
{#if list.status === 'archived'}
  <Banner>
    This list is archived and read-only.
    <Button on:click={() => duplicateList()}>Duplicate for new meeting</Button>
  </Banner>
{/if}

<!-- Disable checkboxes for archived lists -->
<Checkbox
  checked={item.checked}
  disabled={list.status === 'archived'}
/>
```

### Item Usage Statistics (Optional Enhancement)

Track which items are most commonly added:

```javascript
// In packLists.js
export const getItemUsageStats = async () => {
  const lists = await getUserPackLists();
  const itemCounts = {};

  lists.forEach(list => {
    list.items.filter(i => i.addedToList).forEach(item => {
      itemCounts[item.name] = (itemCounts[item.name] || 0) + 1;
    });
  });

  return Object.entries(itemCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10); // Top 10 frequently added items
};
```

Display in template edit view:
```
Frequently added items (not in template):
- Extra brake pads (added 5 times)
- Rain cover (added 3 times)
[Add to template]
```

## Data Model Updates

Add to pack list items:
```javascript
{
  // existing fields...
  promotedToMaster: boolean,  // true after promotion
  promotedAt: Date            // timestamp of promotion
}
```

## Test Requirements (TDD)

### Promotion Tests
- Promote action only shows for `addedToList` items
- Promotion calls `promoteItemToTemplate()`
- Promoted items show badge and hide promote button
- Item appears in template after promotion

### History Tests
- Archived lists show in "archived" filter
- Date range filter works correctly
- Archived lists are read-only (checkboxes disabled)
- Duplicate creates new active list

## Files to Modify

```
src/routes/ViewPackList.svelte  (add promotion UI)
src/routes/PackLists.svelte     (add filters)
src/lib/firestore/packLists.js  (add stats function if needed)
```

## Estimated Effort

2-3 hours (including TDD test writing)

## Notes

- Can run in parallel with TASK-PL-005
- Conductor workspace: `pack-list-wave3-features`
Write TASK-PL-005-navigation-integration.md
160 lines
---
id: TASK-PL-005
title: Add navigation and integration
status: backlog
created: 2025-12-15T00:00:00Z
updated: 2025-12-15T00:00:00Z
priority: medium
tags: [pack-list, navigation, integration, routing]
complexity: 3
parent_feature: pack-list-feature
wave: 3
execution_mode: direct
testing_mode: tdd
dependencies: [TASK-PL-002, TASK-PL-003]
blocks: []
conductor_workspace: pack-list-wave3-nav
---

# Add Navigation and Integration

## Description

Integrate the pack list feature into the kartlog application by adding routes, navigation menu items, and optional dashboard widgets.

## Acceptance Criteria

- [ ] All pack list routes added to `App.svelte`
- [ ] Navigation menu updated with pack list links
- [ ] Routes work correctly (no 404s)
- [ ] Navigation icons appropriate
- [ ] Optional: Dashboard widget for active pack lists
- [ ] Tests for route configuration

## Technical Specification

### Routes to Add (`src/App.svelte`)

```javascript
import PackTemplates from './routes/PackTemplates.svelte';
import NewPackTemplate from './routes/NewPackTemplate.svelte';
import EditPackTemplate from './routes/EditPackTemplate.svelte';
import PackLists from './routes/PackLists.svelte';
import NewPackList from './routes/NewPackList.svelte';
import ViewPackList from './routes/ViewPackList.svelte';

const routes = {
  // ... existing routes ...

  // Pack Templates (master lists)
  '/pack-templates': PackTemplates,
  '/pack-templates/new': NewPackTemplate,
  '/pack-templates/:id': EditPackTemplate,

  // Pack Lists (meeting-specific)
  '/pack-lists': PackLists,
  '/pack-lists/new': NewPackList,
  '/pack-lists/:id': ViewPackList,
};
```

### Navigation Menu

**Location**: Sidebar or header navigation (check existing pattern)

```svelte
<!-- Add to navigation component -->
<ListItem href="/pack-templates">
  <Icon slot="graphic">checklist</Icon>
  <Text>Pack Templates</Text>
</ListItem>

<ListItem href="/pack-lists">
  <Icon slot="graphic">inventory_2</Icon>
  <Text>Pack Lists</Text>
</ListItem>
```

**Icon Suggestions**:
- Pack Templates: `checklist`, `playlist_add_check`, `fact_check`
- Pack Lists: `inventory_2`, `luggage`, `backpack`

### Dashboard Widget (Optional)

**In Dashboard.svelte**:

```svelte
<script>
  import { getUserPackLists } from '$lib/firestore/packLists';

  let activeLists = [];

  onMount(async () => {
    const lists = await getUserPackLists('active');
    activeLists = lists.slice(0, 3); // Show top 3
  });
</script>

{#if activeLists.length > 0}
  <Card>
    <h3>Active Pack Lists</h3>
    {#each activeLists as list}
      <a href="/pack-lists/{list.id}">
        <div class="pack-list-widget">
          <span>{list.meetingName}</span>
          <span>{list.checkedCount}/{list.totalItems}</span>
          <LinearProgress progress={list.checkedCount / list.totalItems} />
        </div>
      </a>
    {/each}
    <Button href="/pack-lists">View All</Button>
  </Card>
{/if}
```

### Mobile Navigation

Ensure pack list items appear in mobile hamburger menu:

```svelte
<!-- Mobile menu items -->
<Item on:click={() => { push('/pack-templates'); closeMenu(); }}>
  <Icon>checklist</Icon>
  <span>Pack Templates</span>
</Item>
<Item on:click={() => { push('/pack-lists'); closeMenu(); }}>
  <Icon>inventory_2</Icon>
  <span>Pack Lists</span>
</Item>
```

## Files to Modify

```
src/App.svelte                    # Add routes
src/routes/Dashboard.svelte       # Optional widget
src/components/Navigation.svelte  # If exists, add menu items
```

## Test Requirements

### Route Tests
- All routes resolve to correct components
- Route parameters (`:id`) work correctly
- Authenticated routes require login

### Navigation Tests
- Menu items visible when logged in
- Links navigate to correct pages
- Mobile menu includes new items

## Estimated Effort

1-2 hours

## Notes

- Can run in parallel with TASK-PL-004
- Conductor workspace: `pack-list-wave3-nav`
- This is marked as `direct` execution mode (simpler task)
Now let me update the original review task to mark it as completed:
Edit TASK-REV-47E0-plan-pack-list-feature.md
Modified
Bash Move completed review task to completed folder
IN
mv /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/tasks/backlog/TASK-REV-47E0-plan-pack-list-feature.md /Users/richardwoollcott/Projects/appmilla_github/guardkit-examples/tasks/completed/

OUT
0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE IMPLEMENTATION STRUCTURE CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created: tasks/backlog/pack-list-feature/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-PL-001-data-model-repository.md
  ├── TASK-PL-002-template-management-ui.md
  ├── TASK-PL-003-meeting-list-ui.md
  ├── TASK-PL-004-promotion-history.md
  └── TASK-PL-005-navigation-integration.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 EXECUTION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Wave 1: Foundation (Sequential)
  └── TASK-PL-001: Data model & repository layer (3-4 hrs)
      Mode: task-work | Testing: TDD

Wave 2: UI Components (Parallel)
  ├── TASK-PL-002: Template management UI (3-4 hrs)
  │   Workspace: pack-list-wave2-templates
  │   Mode: task-work | Testing: TDD
  │
  └── TASK-PL-003: Meeting pack list UI (3-4 hrs)
      Workspace: pack-list-wave2-lists
      Mode: task-work | Testing: TDD

Wave 3: Features & Integration (Parallel)
  ├── TASK-PL-004: Item promotion & history (2-3 hrs)
  │   Workspace: pack-list-wave3-features
  │   Mode: task-work | Testing: TDD
  │
  └── TASK-PL-005: Navigation & integration (1-2 hrs)
      Workspace: pack-list-wave3-nav
      Mode: direct | Testing: TDD

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Approach: Hybrid Copy-on-Create with Template References
Total Effort: 12-17 hours
Subtasks: 5
Testing: Full TDD (test-first)

Review Task: TASK-REV-47E0 (completed)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Review the implementation guide:
   tasks/backlog/pack-list-feature/IMPLEMENTATION-GUIDE.md

2. Start Wave 1 (foundation must complete first):
   /task-work TASK-PL-001

3. After Wave 1, run Wave 2 in parallel with Conductor

4. After Wave 2, run Wave 3 in parallel with Conductor