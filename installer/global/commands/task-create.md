# Task Create - Start a New Development Task

Create a new task with requirements, acceptance criteria, and optional BDD scenarios.

## Feature Detection

This command supports **graceful degradation** based on installed packages:

### Taskwright Only (Core Features)
```bash
# Basic task creation
/task-create "Add user authentication"
/task-create "Add user authentication" priority:high tags:[auth,security]
```

Available fields: `title`, `priority`, `tags`, `status`, `complexity`

### Taskwright + Require-Kit (Full Features)
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

### Core Fields (Taskwright)
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

### Extended Fields (Taskwright + Require-Kit)
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
from installer.global.lib.id_generator import generate_task_id, validate_task_id, check_duplicate

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
1. TASK-001.2.01: Design Event Sourcing architecture (Complexity: 5/10)
2. TASK-001.2.02: Implement EventStore infrastructure (Complexity: 6/10)
3. TASK-001.2.03: Implement Order aggregate with events (Complexity: 5/10)
4. TASK-001.2.04: Implement CQRS handlers (Complexity: 5/10)
5. TASK-001.2.05: Testing and integration (Complexity: 6/10)

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
id: TASK-001.2.05
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
- TASK-015: Add user authentication (in_progress)

Suggestions:
- Use a more specific title
- Check if you meant to update TASK-015
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

# 2. Begin implementation with context awareness
/task-work TASK-001 --with-context

# 3. Monitor progress with hierarchy visibility
/task-status TASK-001 --hierarchy

# 4. Sync progress to PM tools and rollup to feature/epic
/task-sync TASK-001 --rollup-progress

# 5. Complete with validation and automatic rollup
/task-complete TASK-001
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

# Work on task (automatically updates epic progress)
/task-work TASK-001 --sync-progress

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

**If you implement directly, you bypass all quality gates and the entire Taskwright workflow!**

### Correct Workflow:
```bash
User: /task-create "Add temperature conversion endpoint"
Claude: ✅ Task Created: TASK-001
        Next Steps: /task-work TASK-001
        [STOPS HERE - WAITS FOR USER]

User: /task-work TASK-001
Claude: [Executes Phases 2-5.5 with all quality gates]
```

### Exception:
Only proceed with implementation if the user explicitly says:
- "Create the task and implement it"
- "Create and work on the task"
- "Create the task and start working"

Otherwise, **ALWAYS STOP** after task creation.
