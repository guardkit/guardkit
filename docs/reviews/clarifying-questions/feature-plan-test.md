/feature-plan lets create the base application infrastructure
I'll help you create the base application infrastructure for a production-ready FastAPI backend. Let me start by creating a feature plan for this.
Update Todos

Create review task for base application infrastructure

Execute decision review analysis

Present decision checkpoint to user

Generate implementation structure based on decision
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ FEATURE PLANNING: Create base application infrastructure ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 1: Creating review task...
Bash Check current directory structure
IN
ls -la

OUT
total 0
drwxr-xr-x@  2 richwoollcott  staff   64 Dec 13 16:03 .
drwxr-xr-x@ 10 richwoollcott  staff  320 Dec 13 16:03 ..
/task-create slash command
/task-create "Plan: Create base FastAPI application infrastructure" task_type:review priority:high
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
/task-create <title> [options]
```

## Examples
```bash
# Simple task creation
/task-create "Add user authentication"

# With priority and tags
/task-create "Add user authentication" priority:high tags:[auth,security]

# Link to requirements immediately
/task-create "Add user authentication" requirements:[REQ-001,REQ-002]

# Link to epic for hierarchy and PM tool integration
/task-create "Add user authentication" epic:EPIC-001

# Full specification with epic linking
/task-create "Add user authentication" priority:high epic:EPIC-001 requirements:[REQ-001,REQ-002] bdd:[BDD-001]

# Epic linking with automatic PM tool integration
/task-create "Add user authentication" epic:EPIC-001 export:jira
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
- ✅ Title must be 5-100 characters
- ✅ No duplicate titles in active tasks
- ✅ Linked requirements must exist
- ✅ Linked BDD scenarios must exist
- ✅ Epic must be valid if specified
- ✅ Feature must belong to specified epic if both are provided
- ✅ Export tools must be configured and accessible
- ✅ Complexity score calculated (if requirements linked)

## Best Practices

1. **Clear titles**: Use action verbs ("Implement", "Add", "Fix", "Refactor")
2. **Link specifications**: Always link to requirements for traceability
3. **Set priority**: Helps with sprint planning
4. **Use tags**: Improves discoverability and filtering
5. **Add description**: Provide context beyond the title

## Output Format

### Success
```
✅ Task Created: TASK-E01-B2C4

📋 Task Details
Title: Add user authentication
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
tasks/backlog/TASK-E01-B2C4-add-user-authentication.md

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


ARGUMENTS: "Plan: Create base FastAPI application infrastructure" task_type:review priority:high
I need to execute the /task-create command to create a review task for planning the base FastAPI application infrastructure.
Bash Create task directory structure
IN
mkdir -p tasks/backlog tasks/in_progress tasks/in_review tasks/blocked tasks/completed

OUT
0
Globpattern: "**/.claude/commands/task-create.md"
No files found
Let me create the task directly based on the task-create command specifications:
Bash Generate unique task ID
IN
python3 -c "
import hashlib
import time

# Generate hash-based task ID
title = 'Plan: Create base FastAPI application infrastructure'
timestamp = str(time.time())
hash_input = f'{title}:{timestamp}'.encode('utf-8')
hash_digest = hashlib.sha256(hash_input).hexdigest()
task_hash = hash_digest[:4].upper()

# Review task prefix
task_id = f'TASK-REV-{task_hash}'
print(task_id)
"

OUT
TASK-REV-07FC
Write TASK-REV-07FC-plan-create-base-fastapi-application-infrastructure.md
106 lines
---
id: TASK-REV-07FC
title: "Plan: Create base FastAPI application infrastructure"
status: backlog
created: 2025-12-13T16:03:00Z
updated: 2025-12-13T16:03:00Z
priority: high
tags: [infrastructure, architecture, planning, review]
complexity: 0
task_type: review
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Create base FastAPI application infrastructure

## Description

This is a review/analysis task to plan the complete base infrastructure for a production-ready FastAPI backend application. The plan should follow best practices from the fastapi-best-practices repository and align with the project template structure defined in CLAUDE.md.

## Objectives

1. **Analyze infrastructure requirements** for a production-ready FastAPI application
2. **Evaluate technical options** for core components:
   - Project structure and organization
   - Database setup (SQLAlchemy + Alembic)
   - Configuration management (Pydantic settings)
   - Testing infrastructure (pytest + fixtures)
   - Code quality tools (ruff, mypy, pre-commit)
   - Development environment setup
3. **Recommend implementation approach** with breakdown into manageable subtasks
4. **Identify dependencies** and prerequisites
5. **Estimate effort** and complexity for each component

## Review Focus Areas

### 1. Project Structure
- Feature-based organization pattern
- Core infrastructure (config, database, security)
- Testing directory structure
- Requirements management (base/dev/prod split)

### 2. Database Infrastructure
- SQLAlchemy 2.0+ async setup
- Alembic migration configuration
- Database session management
- Base models and utilities

### 3. Configuration & Settings
- Pydantic settings with environment variables
- Logging configuration
- Security settings
- Database connection settings

### 4. Development Tools
- pytest configuration with async support
- Code quality tools (ruff, mypy)
- Pre-commit hooks setup
- Development dependencies

### 5. Application Initialization
- FastAPI app factory pattern
- Middleware configuration
- Error handling setup
- Health check endpoints

## Success Criteria

- [ ] Complete technical options analysis
- [ ] Recommended approach with justification
- [ ] Implementation breakdown into subtasks
- [ ] Dependency identification
- [ ] Effort estimation
- [ ] Risk assessment
- [ ] Architecture documentation

## Expected Deliverables

1. **Technical Options Analysis**: Comparison of approaches for each component
2. **Recommended Architecture**: Complete infrastructure design
3. **Implementation Plan**: Breakdown into 8-12 subtasks
4. **Risk Analysis**: Potential blockers and mitigation strategies
5. **Effort Estimation**: Time estimates for each subtask

## Implementation Notes

This task uses `/task-review` for decision-making analysis:
- Mode: `decision` (technical options analysis)
- Depth: `standard` (comprehensive but focused)
- Output: Implementation recommendations + subtask breakdown

After review completion, use the [I]mplement option to create the feature structure with subtasks.

## References

- FastAPI Best Practices: https://github.com/zhanymkanov/fastapi-best-practices
- Project Template: /Users/richwoollcott/Projects/.claude/CLAUDE.md
- FastAPI Documentation: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

## Review Execution Log

[This section will be populated by /task-review]
Update Todos

Create review task for base application infrastructure

Execute decision review analysis

Present decision checkpoint to user

Generate implementation structure based on decision
✅ Task Created: TASK-REV-07FC ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 📋 Task Details ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Title: Plan: Create base FastAPI application infrastructure
ID: TASK-REV-07FC (Review Task)
Priority: high
Status: backlog
Tags: [infrastructure, architecture, planning, review]
Task Type: review ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🔍 Review Task Detected ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ This is a review/analysis task for planning the base FastAPI application infrastructure. Suggested workflow:
✅ Task created (current step)
⏭️ Execute review: /task-review TASK-REV-07FC
🚀 (Optional) Implement findings based on review recommendations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 📁 File Location
tasks/backlog/TASK-REV-07FC-plan-create-base-fastapi-application-infrastructure.md Step 2: Executing review analysis... Now I'll execute the /task-review command with decision-making mode to analyze technical options and provide recommendations for the base infrastructure.
/task-review slash command
/task-review TASK-REV-07FC --mode=decision --depth=standard
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

The `/task-review` command integrates with the clarification module at two key points to gather user preferences before analysis and implementation.

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

The clarification module uses task complexity to determine when clarification is needed.

**Context A Gating Rules**:

| Complexity | Review Mode | Clarification Behavior |
|------------|-------------|------------------------|
| 0-3 | Any | Skip (unless --with-questions) |
| 4-6 | decision, architectural | Ask (unless --no-questions) |
| 4-6 | code-quality, technical-debt, security | Skip (unless --with-questions) |
| 7-10 | Any | Always ask (unless --no-questions) |

**Context B Gating Rules**:

| Condition | Clarification Behavior |
|-----------|------------------------|
| Single subtask | Skip (no parallelization decisions needed) |
| 2-3 subtasks | Ask approach + testing only |
| 4-6 subtasks | Ask approach + parallelization + testing |
| 7+ subtasks | Ask all 5 questions (full preferences) |
| --no-questions | Skip always |

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
- Read task description and acceptance criteria
- **[NEW]** Present review scope clarification questions (Context A)
  - Triggered for: decision mode, complexity ≥4, or --with-questions flag
  - Skipped if: --no-questions flag or quick depth
  - Questions help clarify: focus areas, analysis depth, trade-offs, concerns
- Identify review scope and objectives (using clarification if provided)
- Load relevant codebase files/modules
- Load related design documents and ADRs

### Phase 2: Execute Review Analysis
- Invoke appropriate review agents based on mode
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


ARGUMENTS: TASK-REV-07FC --mode=decision --depth=standard
I'll execute the task review for the base FastAPI application infrastructure planning task.
Update Todos

Create review task for base application infrastructure

Execute decision review analysis

Present decision checkpoint to user

Generate implementation structure based on decision
Read TASK-REV-07FC-plan-create-base-fastapi-application-infrastructure.md
Now I'll execute the decision-mode review analysis for the base FastAPI application infrastructure. Let me analyze the requirements and provide technical options. 🔍 Analyzing: Create base FastAPI application infrastructure ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 1: Loading Review Context ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Review Mode: Decision Analysis
Depth: Standard
Complexity: Medium (infrastructure setup) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 2: Technical Options Analysis ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL OPTIONS ANALYSIS
Option 1: Comprehensive Infrastructure Setup (Recommended)
Description: Full production-ready infrastructure following fastapi-best-practices template Components:
Project Structure
Feature-based organization (src/{feature}/)
Core infrastructure (src/core/)
Database layer (src/db/)
Clean separation of concerns
Database Infrastructure
SQLAlchemy 2.0+ with async support
Alembic for migrations
PostgreSQL with asyncpg driver
Session management with dependency injection
Configuration Management
Pydantic Settings v2
Environment-based configuration
Validation at startup
Secret management ready
Testing Infrastructure
pytest with pytest-asyncio
Test fixtures for DB/API
Coverage reporting (pytest-cov)
Async test client (httpx)
Code Quality Tools
ruff (linting + formatting)
mypy (type checking)
pre-commit hooks
CI/CD ready configuration
Application Setup
FastAPI app factory pattern
Middleware stack (CORS, logging, error handling)
Health check endpoints
API versioning structure
Complexity: Medium-High (7/10)
Effort: 6-8 hours
Risk Level: Low Pros:
✅ Production-ready from day one
✅ Follows industry best practices
✅ Scalable architecture
✅ Complete testing infrastructure
✅ Enforces code quality standards
✅ Easy onboarding for new developers
Cons:
⚠️ Higher initial setup time
⚠️ More files to manage initially
⚠️ Requires understanding of all components
Dependencies:
Python 3.11+
PostgreSQL (or can use SQLite for dev)
Core packages: fastapi, sqlalchemy, alembic, pydantic, pytest
Option 2: Minimal Viable Infrastructure
Description: Simplified setup with essential components only Components:
Basic FastAPI app structure
Simple SQLAlchemy setup (sync mode)
Basic configuration (no Pydantic Settings)
Minimal testing setup
No code quality tools initially
Complexity: Low (3/10)
Effort: 2-3 hours
Risk Level: Medium Pros:
✅ Quick to set up
✅ Easy to understand
✅ Less overhead initially
Cons:
❌ Technical debt accumulates quickly
❌ Missing production requirements
❌ No quality enforcement
❌ Harder to scale later
❌ Not aligned with best practices
Dependencies:
Minimal package set
Option 3: Modular Incremental Setup
Description: Start with core, add components incrementally Components (Phase 1):
Basic FastAPI structure
Configuration management
Database foundation (async SQLAlchemy)
Basic testing
Components (Phase 2 - later):
Code quality tools
Advanced middleware
Complete test infrastructure
Complexity: Medium (5/10)
Effort: 4-5 hours (initial), 2-3 hours (phase 2)
Risk Level: Medium Pros:
✅ Balanced approach
✅ Core features first
✅ Can start development sooner
Cons:
⚠️ Quality tools added later (potential debt)
⚠️ Two-phase setup more complex
⚠️ May need refactoring between phases
RECOMMENDED APPROACH
✅ Option 1: Comprehensive Infrastructure Setup
Rationale
Production-Ready: You need a production-ready backend, not a prototype
Best Practices Alignment: Follows proven patterns from 12k+ star repository
Long-term Efficiency: Initial investment saves refactoring time
Code Quality: Quality enforcement from day one prevents technical debt
Team Scalability: Well-structured codebase easier for team growth
Risk Mitigation: Testing and validation infrastructure catches issues early
Implementation Breakdown (8 Subtasks)
Wave 1: Foundation (Parallel - 3 tasks)
TASK-001: Create project structure and configuration
Set up directory structure (src/, tests/, alembic/)
Create pyproject.toml with dependencies
Set up requirements files (base/dev/prod)
Configure environment variables (.env template)
Effort: 1 hour
Complexity: 3/10
Mode: Direct implementation
TASK-002: Set up database infrastructure
Configure SQLAlchemy 2.0 async engine
Create base model and session management
Set up Alembic for migrations
Create initial migration
Effort: 1.5 hours
Complexity: 6/10
Mode: /task-work (requires testing)
TASK-003: Configure Pydantic settings
Create Settings class with validation
Database connection settings
Logging configuration
Security settings (SECRET_KEY, etc.)
Effort: 1 hour
Complexity: 4/10
Mode: Direct implementation
Wave 2: Application Core (Sequential - 2 tasks)
TASK-004: Create FastAPI application factory
App factory pattern implementation
Middleware stack (CORS, logging, error handling)
Database session dependency
Health check endpoints
Effort: 1.5 hours
Complexity: 5/10
Mode: /task-work (requires testing)
TASK-005: Set up error handling and middleware
Global exception handlers
Request/response logging middleware
CORS configuration
Security headers middleware
Effort: 1 hour
Complexity: 4/10
Mode: Direct implementation
Wave 3: Quality & Testing (Parallel - 3 tasks)
TASK-006: Configure testing infrastructure
pytest configuration (pytest.ini)
Async test setup (pytest-asyncio)
Test fixtures (DB, API client)
Coverage configuration
Effort: 1.5 hours
Complexity: 6/10
Mode: /task-work (needs verification)
TASK-007: Set up code quality tools
ruff configuration (linting + formatting)
mypy configuration (strict type checking)
pre-commit hooks setup
CI configuration template
Effort: 1 hour
Complexity: 4/10
Mode: Direct implementation
TASK-008: Create example feature module
Example feature following template structure
router.py, schemas.py, models.py, crud.py
Feature tests demonstrating patterns
Documentation of patterns
Effort: 1.5 hours
Complexity: 5/10
Mode: /task-work (demonstrates testing)
Execution Strategy
Total Effort: 6-8 hours
Parallel Execution: 3 waves
Conductor Workspaces: Recommended for Wave 1 and Wave 3 Wave 1 Tasks (1-3): Can run in parallel - no file conflicts
Wave 2 Tasks (4-5): Sequential - task 5 depends on task 4
Wave 3 Tasks (6-8): Can run in parallel - independent components
Risk Analysis
Risk	Likelihood	Impact	Mitigation
Async setup complexity	Medium	Medium	Use proven SQLAlchemy 2.0 async patterns
Alembic configuration issues	Low	Medium	Follow official documentation, test migrations
Pre-commit hook conflicts	Low	Low	Use standard configurations
Testing setup complexity	Medium	High	Start with simple fixtures, expand gradually
Success Metrics
✅ All 8 tasks completed
✅ Tests pass (100% of infrastructure tests)
✅ Type checking passes (mypy --strict)
✅ Linting passes (ruff check)
✅ Example feature demonstrates all patterns
✅ Documentation complete
EFFORT ESTIMATION
Total Estimated Time: 6-8 hours Breakdown by Category:
Project Structure & Config: 2 hours (Tasks 1, 3)
Database Infrastructure: 1.5 hours (Task 2)
Application Core: 2.5 hours (Tasks 4, 5)
Testing & Quality: 4 hours (Tasks 6, 7, 8)
Parallel Execution Savings: ~40% time reduction (6-8 hours → 4-5 hours actual time with 3 parallel workspaces)
DEPENDENCIES & PREREQUISITES
Required Knowledge
Python 3.11+ async/await patterns
SQLAlchemy 2.0 ORM concepts
FastAPI dependency injection
pytest basics
Required Tools
Python 3.11+
PostgreSQL (or SQLite for development)
Git
IDE with Python support
Package Dependencies
Core (base.txt):

fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
alembic>=1.12.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
asyncpg>=0.29.0
python-dotenv>=1.0.0
Development (dev.txt):

pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0
ruff>=0.1.0
mypy>=1.7.0
pre-commit>=3.5.0
Update Todos

Create review task for base application infrastructure

Execute decision review analysis

Present decision checkpoint to user

Generate implementation structure based on decision
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 📋 DECISION CHECKPOINT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Review Complete: Plan: Create base FastAPI application infrastructure Analysis Summary:
Options Evaluated: 3 approaches
Recommended: Option 1 (Comprehensive Infrastructure Setup)
Subtasks Identified: 8 tasks across 3 waves
Estimated Effort: 6-8 hours (4-5 hours with parallel execution)
Risk Level: Low
Key Recommendations:
Comprehensive Infrastructure Setup (Recommended)
Production-ready from day one
Complete testing and quality infrastructure
Follows fastapi-best-practices patterns
Supports team scaling
Implementation organized in 3 parallel waves:
Wave 1 (Foundation): Project structure, database, configuration
Wave 2 (Core): FastAPI factory, middleware
Wave 3 (Quality): Testing, linting, example feature
Use Conductor for parallel execution to reduce actual time by ~40%
Decision Options: [A]ccept - Approve the recommended approach and save the analysis
Review findings saved to task metadata
Ready for reference when you're ready to implement
No implementation tasks created yet
[R]evise - Request deeper analysis or explore alternatives
Focus on specific components
Evaluate different technology choices
Explore deployment considerations
[I]mplement - Create implementation tasks based on recommendations
Automatically generates 8 subtasks
Creates feature structure with IMPLEMENTATION-GUIDE.md
Sets up parallel execution waves with Conductor workspace names
Generates complete README.md
[C]ancel - Discard this review
Move task to cancelled state
Preserve review for future reference
Your choice [A/R/I/C]: