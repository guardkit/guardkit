# Task Status - View Task Progress with Epic/Feature Context

Display comprehensive task status with epic/feature hierarchy context, progress tracking, PM tool sync status, and Agentecflow Stage 3 integration.

## Feature Detection

This command supports **graceful degradation** based on installed packages:

### GuardKit Only (Core Filters)
```bash
/task-status --status in_progress    # Filter by status
/task-status --assignee "John"       # Filter by assignee
/task-status --priority high         # Filter by priority
```

Available filters: `--status`, `--assignee`, `--priority`, `--tags`

### GuardKit + Require-Kit (Extended Filters)
```bash
/task-status --epic EPIC-001         # Filter by epic (requires require-kit)
/task-status --feature FEAT-003      # Filter by feature (requires require-kit)
/task-status TASK-001 --hierarchy    # Show epic/feature context (requires require-kit)
```

Additional filters: `--epic`, `--feature`, `--hierarchy`, `--sync-status`

**Note**: Epic and feature filtering requires [require-kit](https://github.com/requirekit/require-kit) to be installed. These filters will show a helpful message if require-kit is not available.

## Usage
```bash
/task-status [task-id] [options]
```

## Options
- `--json` - Output task status in machine-readable JSON format
- `--base-path PATH` - Specify project root path (default: current directory)

## Examples
```bash
# View all active tasks with hierarchy
/task-status

# View specific task details
/task-status TASK-001

# Show tasks by feature
/task-status --feature FEAT-001

# Show tasks by epic
/task-status --epic EPIC-001

# Show only blocked tasks
/task-status --blocked

# View tasks with hierarchy context
/task-status TASK-001 --hierarchy

# Show PM tool sync status
/task-status --sync-status

# View developer dashboard
/task-status --dev-dashboard

# Legacy kanban board view
/task-status --format kanban

# Output in JSON format
/task-status --json

# Output specific task in JSON format
/task-status TASK-001 --json

# Output with custom base path
/task-status --json --base-path /path/to/project
```

## Output Formats

### All Tasks Overview (Default)
```
📊 Task Portfolio Status

🏃 Active Tasks (12)
┌─────────────┬─────────────────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Task ID     │ Title                   │ Epic        │ Feature     │ Assignee    │ Progress    │ Status      │
├─────────────┼─────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ TASK-043    │ Design auth UI          │ EPIC-001    │ FEAT-003    │ Lisa        │ 100%        │ ✅ Complete │
│ TASK-044    │ Implement login API     │ EPIC-001    │ FEAT-003    │ Mike        │ 90%         │ 🔄 Review   │
│ TASK-045    │ Add session mgmt        │ EPIC-001    │ FEAT-003    │ Sarah       │ 60%         │ 🔄 Progress │
│ TASK-046    │ Password reset flow     │ EPIC-001    │ FEAT-003    │ Alex        │ 0%          │ ❌ Blocked  │
│ TASK-047    │ Auth tests              │ EPIC-001    │ FEAT-003    │ Mike        │ 0%          │ ⏳ Pending  │
└─────────────┴─────────────────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

📈 Progress by Hierarchy
EPIC-001 (User Management): 55% complete
├── FEAT-003 (Authentication): 62% complete (4/5 tasks)
└── FEAT-004 (User Profile): 15% complete (1/2 tasks)

🚨 Attention Needed
❌ TASK-046: Blocked by email service dependency
⚠️ TASK-045: Behind schedule (60% at day 3 of 2)

🔗 External Tool Health
✅ Jira: 10/12 tasks synced
⚠️ Linear: 3 tasks pending sync
✅ GitHub: All tasks linked
```

### Single Task Detailed View
```
📋 Task Details: TASK-045

🎯 Add Session Management System
Epic: EPIC-001 (User Management System)
Feature: FEAT-003 (User Authentication)
Priority: High | Complexity: Medium | Timeline: 2 days

📊 Progress Overview
┌─────────────────────────────────────────────────────────────┐
│ ████████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ 60% Complete (6/10 acceptance criteria, 3/5 implementation steps) │
└─────────────────────────────────────────────────────────────┘

🔗 Hierarchy Context
Epic Progress Impact: +12% when completed
Feature Progress Impact: +20% when completed
Blocking Tasks: TASK-047 (Authentication tests)

🔗 External Integration
Jira Sub-task: PROJ-129 (In Progress) ✅
Linear Issue: PROJECT-461 (In Progress) ✅
GitHub Issue: #253 (@sarah-chen) ✅

📊 Technical Details
Repository: backend/auth-service
Branch: feature/session-management
Test Coverage: 85% (target: 80%) ✅

🔄 Agentecflow Integration
Stage 3: Engineering (In Progress)
Quality Gates: 3/4 passed
Ready for Stage 4: No (tests incomplete)
```

### Legacy Kanban Board View
```bash
/task-status --format kanban

### 1. Kanban Board View
```
╔════════════════════════════════════════════════════════════════╗
║                    TASK BOARD - 2024-01-15                     ║
╚════════════════════════════════════════════════════════════════╝

┌─────────────────┬─────────────────┬─────────────────┐
│   BACKLOG (5)   │ IN_PROGRESS (2) │ IN_TESTING (1)  │
├─────────────────┼─────────────────┼─────────────────┤
│ TASK-043 [HIGH] │ TASK-041 [MED]  │ TASK-040 [HIGH] │
│ Add search      │ Refactor auth   │ Payment API     │
│ Tags: ui, api   │ @alice          │ ⏳ Running...   │
│                 │ 🕐 2 days       │                 │
├─────────────────┼─────────────────┼─────────────────┤
│ TASK-044 [LOW]  │ TASK-042 [HIGH] │                 │
│ Export feature  │ User profile    │                 │
│ Tags: backend   │ @bob            │                 │
│                 │ 🕐 4 hours      │                 │
├─────────────────┼─────────────────┼─────────────────┤
│ TASK-045 [MED]  │                 │                 │
│ Admin dashboard │                 │                 │
│ Tags: ui, admin │                 │                 │
└─────────────────┴─────────────────┴─────────────────┘

┌─────────────────┬─────────────────┬─────────────────┐
│  IN_REVIEW (1)  │   BLOCKED (1)   │ COMPLETED (3)   │
├─────────────────┼─────────────────┼─────────────────┤
│ TASK-039 [HIGH] │ TASK-038 [HIGH] │ ✅ TASK-037     │
│ Email service   │ Social login    │ ✅ TASK-036     │
│ ✅ 25/25 tests  │ ❌ 3 failures   │ ✅ TASK-035     │
│ 📊 92% coverage │ OAuth callback  │ Today: 3        │
└─────────────────┴─────────────────┴─────────────────┘

📊 METRICS: Velocity: 3/day | Coverage Avg: 86% | Blocked: 1
```

### 2. List View
```
TASK LIST - 2024-01-15
=======================

BACKLOG (5 tasks)
-----------------
• TASK-043 [HIGH] - Add search functionality
  Created: 2024-01-10 | Tags: ui, api
  
• TASK-044 [LOW] - Export feature
  Created: 2024-01-11 | Tags: backend
  
• TASK-045 [MED] - Admin dashboard
  Created: 2024-01-12 | Tags: ui, admin

IN_PROGRESS (2 tasks) 
---------------------
• TASK-041 [MED] - Refactor auth service
  Assignee: alice | Started: 2024-01-13 (2 days ago)
  Progress: 60% | Tests: 0/15 written
  
• TASK-042 [HIGH] - Add user profile page
  Assignee: bob | Started: 2024-01-15 (4 hours ago)
  Progress: 30% | Tests: 5/20 written
```

### 3. Metrics Dashboard
Shows velocity metrics, quality metrics, cycle time analysis, bottlenecks, risk indicators, sprint goals, priority distribution, and team performance.

## Status Indicators

### Task State Icons
- 📋 BACKLOG - Not started
- 🔄 IN_PROGRESS - Active work
- 🧪 IN_TESTING - Tests running
- 👀 IN_REVIEW - Awaiting approval
- ❌ BLOCKED - Cannot proceed
- ✅ COMPLETED - Done

### Priority Indicators
- 🔴 CRITICAL - Drop everything
- 🟠 HIGH - Important
- 🟡 MEDIUM - Normal
- 🟢 LOW - Nice to have

### Test Status
- ✅ All passing
- ⚠️ Some failures
- ❌ All failing
- ⏳ Running
- ⭕ Not started

## Options

### Filtering Options

#### Core Filters (Always Available)
```bash
# View by status
/task-status --status in_progress
/task-status --status blocked
/task-status --status completed

# View by assignment
/task-status --assignee "Sarah Chen"
/task-status --unassigned

# View by timeline
/task-status --overdue
/task-status --due-today
/task-status --current-sprint

# View by priority
/task-status --priority high
/task-status --priority critical
```

#### Extended Filters (Requires require-kit)
```bash
# View by hierarchy (requires require-kit)
/task-status --epic EPIC-001
/task-status --feature FEAT-003

# If require-kit not installed, these will show:
# "⚠️ Epic filtering requires require-kit package"
# "Install: cd require-kit && ./installer/scripts/install.sh"
```

### Display Options
```bash
# Detailed view
/task-status TASK-001 --detailed

# Hierarchy context
/task-status TASK-001 --hierarchy

# Technical details
/task-status TASK-001 --technical

# Progress focus
/task-status --progress-only

# Compact view
/task-status --compact

# Legacy kanban board
/task-status --format kanban
```

## Integration Features

### Agentecflow Stage 3 Integration
Tasks provide detailed metrics for Stage 3: Engineering progress:
- **Implementation Progress**: Code completion percentage
- **Quality Gates**: Test coverage, code quality, security scans
- **Human/AI Collaboration**: Mixed implementation mode tracking
- **Stage 3 → Stage 4 Readiness**: Deployment and QA preparation

### Real-time Progress Tracking
- **Task Progress**: Implementation steps and acceptance criteria
- **Feature Rollup**: Automatic feature progress calculation
- **Epic Rollup**: Automatic epic progress updates
- **External Sync**: Bidirectional PM tool synchronization

### Dependency Management
- **Upstream Dependencies**: Tasks this task depends on
- **Downstream Dependencies**: Tasks waiting for this task
- **Critical Path**: Impact on overall timeline
- **Blocker Resolution**: Tracking and escalation support

## Integration with Other Commands

### Cross-Command Navigation
```bash
# From task status to implementation
/task-status TASK-001 → shows "Run: /task-work TASK-001"

# From task to feature context
/task-status TASK-001 → shows "Run: /feature-status FEAT-003"

# From task to epic overview
/task-status TASK-001 → shows "Run: /epic-status EPIC-001"
```

### Workflow Integration
```bash
# Status check before starting work
/task-status TASK-001 --brief
/task-work TASK-001

# Progress check during implementation
/task-status TASK-001 --technical
# Continue with /task-work TASK-001

# Completion check
/task-status TASK-001 --completion-check
/task-complete TASK-001
```

## Best Practices

1. **Regular Monitoring**: Check task status daily during active development
2. **Blocker Management**: Address blocked tasks immediately to prevent cascade delays
3. **Progress Accuracy**: Update progress regularly for accurate feature/epic rollup
4. **Context Awareness**: Use hierarchy view to understand task impact
5. **Team Coordination**: Use team dashboard for workload distribution
6. **External Sync**: Monitor PM tool sync status for data consistency
