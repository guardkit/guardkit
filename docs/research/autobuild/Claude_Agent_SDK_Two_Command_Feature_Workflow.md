# Claude Agent SDK: Two-Command Feature Workflow

## Executive Summary

This document specifies a **two-command workflow** for feature implementation using the Claude Agent SDK. The workflow provides clear human decision points while automating the heavy lifting, and critically allows humans to **take manual control** of any subtask when needed.

### What This Is (and Isn't)

> **GuardKit is workflow automation, not AI orchestration.**

| GuardKit | Swarm Systems (e.g., Claude-Flow) |
|------------|-----------------------------------|
| Automates a developer's manual workflow | Coordinates autonomous AI agents |
| Single Claude instance (or parallel instances for independent tasks) | Multiple agents with hive-mind coordination |
| Human decides what runs and when | Agents self-organize and spawn sub-agents |
| Tasks are predetermined by investigation | Emergent behavior from agent interaction |
| No persistent learning across features | Neural patterns, vector memory, RL algorithms |
| **Workflow automation with human checkpoints** | **Swarm intelligence with autonomous coordination** |

Both approaches are valid for different use cases. GuardKit is designed for **production feature development** where human oversight, quality gates, and predictable behavior matter more than emergent AI coordination.

**Key Insight**: By separating "planning" from "execution" into two commands, we create natural points where humans can:
1. Review and approve the implementation plan before committing
2. Choose to implement specific subtasks manually for complex/risky work
3. Run automated implementation when confident in the plan

**The Two Commands**:
```bash
# Command 1: Investigate, plan, and create tasks (human decides to proceed)
/feature-task-create "implement dark mode"

# Command 2: Execute implementation (fully automated, or partial)
/feature-task-work FEATURE-DARK-MODE
```

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TWO-COMMAND WORKFLOW WITH HUMAN CONTROL                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   COMMAND 1: /feature-task-create "implement dark mode"                     │
│   ══════════════════════════════════════════════════════                    │
│   │                                                                         │
│   ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ AUTOMATED: Investigation Phase                                       │   │
│   │ • Analyze codebase for implementation approach                       │   │
│   │ • Use ultrathink + subagents for deep analysis                      │   │
│   │ • Identify files, dependencies, risks                               │   │
│   │ • Generate findings and recommendations                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 🛑 HUMAN CHECKPOINT: Review Investigation                            │   │
│   │                                                                      │   │
│   │ "Here's what I found about implementing dark mode..."               │   │
│   │                                                                      │   │
│   │ Options:                                                            │   │
│   │ • [I]mplement - Create feature task + subtasks + plan               │   │
│   │ • [R]evise - Refine the investigation with feedback                 │   │
│   │ • [C]ancel - Stop here                                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼ (if [I]mplement chosen)                          │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ AUTOMATED: Task Creation Phase                                       │   │
│   │ • Create FEATURE-DARK-MODE (parent feature task)                    │   │
│   │ • Decompose into subtasks (TASK-001, TASK-002, etc.)                │   │
│   │ • Identify parallel groups (no file conflicts)                      │   │
│   │ • Mark complexity/risk for each subtask                             │   │
│   │ • Generate implementation-plan.md                                    │   │
│   │ • Organize in .claude/tasks/features/dark-mode/                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   OUTPUT: Feature task ready, human decides next step                       │
│                                                                              │
│   "Feature FEATURE-DARK-MODE created with 5 subtasks:                      │
│    • TASK-001: Add CSS variables (parallel, low risk)                      │
│    • TASK-002: Theme toggle component (parallel, low risk)                 │
│    • TASK-003: Persist preference (parallel, low risk)                     │
│    • TASK-004: Update auth flow (sequential, HIGH RISK ⚠️)                 │
│    • TASK-005: Integration tests (sequential, low risk)                    │
│                                                                              │
│    Run /feature-task-work FEATURE-DARK-MODE to implement all, or          │
│    implement specific tasks manually for more control."                    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   HUMAN DECISION POINT: How to Implement?                                   │
│   ═══════════════════════════════════════                                   │
│                                                                              │
│   Option A: Fully Automated                                                 │
│   /feature-task-work FEATURE-DARK-MODE                                     │
│                                                                              │
│   Option B: Manual Control for Risky Tasks                                  │
│   /task-work TASK-004  ← Human implements the risky auth task manually     │
│   /feature-task-work FEATURE-DARK-MODE --skip TASK-004                     │
│                                                                              │
│   Option C: Fully Manual                                                    │
│   /task-work TASK-001                                                       │
│   /task-work TASK-002                                                       │
│   ... (human controls each task individually)                              │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   COMMAND 2: /feature-task-work FEATURE-DARK-MODE                          │
│   ═══════════════════════════════════════════════                           │
│   │                                                                         │
│   ▼                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ AUTOMATED: Implementation Execution                                  │   │
│   │ • Create feature branch                                              │   │
│   │ • Check which subtasks are already complete (manual or previous)    │   │
│   │ • Set up git worktrees for parallel tasks                           │   │
│   │ • Execute remaining tasks via Claude Agent SDK                      │   │
│   │ • Run integration tests                                              │   │
│   │ • Merge worktrees to feature branch                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 🛑 HUMAN CHECKPOINT: Review Before Merge                             │   │
│   │                                                                      │   │
│   │ "Feature implementation complete. 5/5 subtasks done."               │   │
│   │                                                                      │   │
│   │ Options:                                                            │   │
│   │ • [M]erge to main                                                   │   │
│   │ • [I]nspect changes first                                           │   │
│   │ • [R]eject                                                          │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## GuardKit vs Swarm Systems

### Understanding the Difference

There's an important distinction between what GuardKit does and what swarm/multi-agent systems like [Claude-Flow](https://github.com/ruvnet/claude-flow) do:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SWARM SYSTEMS (e.g., Claude-Flow)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          👑 Queen Agent                                      │
│                              │                                               │
│              ┌───────────────┼───────────────┐                              │
│              │               │               │                              │
│              ▼               ▼               ▼                              │
│         🐝 Worker       🐝 Worker       🐝 Worker                           │
│         (Researcher)   (Coder)        (Tester)                             │
│              │               │               │                              │
│              ├───────────────┼───────────────┤                              │
│              │               │               │                              │
│              ▼               ▼               ▼                              │
│         ┌─────────────────────────────────────┐                            │
│         │     Shared Memory / Vector DB       │                            │
│         │     Neural Patterns / Learning      │                            │
│         └─────────────────────────────────────┘                            │
│                                                                              │
│   Characteristics:                                                          │
│   • Agents communicate with each other                                     │
│   • Share discoveries via persistent memory                                │
│   • Self-organize based on task complexity                                 │
│   • Learn from past executions                                             │
│   • Spawn sub-agents dynamically                                           │
│   • Emergent behavior from agent interaction                               │
│                                                                              │
│   Best for: Exploratory work, research, complex discovery                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    GUARDKIT: WORKFLOW AUTOMATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                     👤 Human Developer                                       │
│                          │                                                   │
│                          ▼                                                   │
│                    ┌──────────┐                                             │
│                    │  Claude  │  ◄── Single instance                        │
│                    │  Code    │      (or parallel instances                 │
│                    └──────────┘       for independent tasks)                │
│                          │                                                   │
│              ┌───────────┼───────────┐                                      │
│              ▼           ▼           ▼                                      │
│         TASK-001    TASK-002    TASK-003                                   │
│         (files)     (files)     (files)                                    │
│                                                                              │
│   Characteristics:                                                          │
│   • Follows predetermined task specifications                              │
│   • No inter-task communication                                            │
│   • No persistent learning across features                                 │
│   • Human decides what runs and when                                       │
│   • Tasks are static, not self-organizing                                  │
│   • Predictable, repeatable behavior                                       │
│                                                                              │
│   Best for: Production features, quality gates, human oversight            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### When to Use What

| Use Case | Best Approach |
|----------|---------------|
| Complex, exploratory work where AI needs to discover approach | Swarm systems |
| Well-defined features following established patterns | GuardKit |
| Research and prototyping | Swarm systems |
| Production feature development with quality gates | GuardKit |
| Solo developer wanting to multiply output predictably | GuardKit |
| Team wanting AI to coordinate autonomously | Swarm systems |

GuardKit deliberately chooses **predictability over emergence** because production code needs:
- Human oversight at critical points
- Ability to take manual control
- Reproducible, auditable workflows
- Clear responsibility for what gets merged

---

## The Power of Manual Override

### Why This Matters

Not all code is equal. Some parts of a system are:
- **High risk** - Authentication, payments, data migrations
- **Complex** - Intricate business logic, performance-critical paths
- **Sensitive** - Security-related, compliance-critical
- **Novel** - Using new technologies the AI might not handle well

For these situations, developers need the ability to **take manual control** while still benefiting from automation for the routine parts.

### Manual Override Scenarios

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MANUAL OVERRIDE SCENARIOS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SCENARIO 1: One Risky Task                                                │
│   ──────────────────────────────                                            │
│   Feature has 5 tasks, but TASK-004 touches authentication.                │
│                                                                              │
│   # Human implements the risky task with full control                       │
│   /task-work TASK-004                                                       │
│   # ... human reviews each change, runs extra tests ...                    │
│   /task-complete TASK-004                                                   │
│                                                                              │
│   # Then automate the rest                                                  │
│   /feature-task-work FEATURE-XXX                                           │
│   # Runner sees TASK-004 complete, skips it, runs others                   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SCENARIO 2: Partial Automation with Explicit Skip                         │
│   ──────────────────────────────────────────────────                        │
│   Human wants to implement two specific tasks manually later.               │
│                                                                              │
│   /feature-task-work FEATURE-XXX --skip TASK-003,TASK-004                  │
│   # Runner executes TASK-001, TASK-002, TASK-005 automatically             │
│   # Leaves TASK-003, TASK-004 for human to do manually                     │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SCENARIO 3: Fully Manual (Complex Feature)                                │
│   ──────────────────────────────────────────                                │
│   Database migration - too risky for any automation.                        │
│                                                                              │
│   /feature-task-create "migrate user table to new schema"                  │
│   # Creates feature task + subtasks + plan                                 │
│   # Human reviews the plan                                                  │
│                                                                              │
│   # Human implements each task manually with full control                  │
│   /task-work TASK-001   # Backup strategy                                  │
│   /task-work TASK-002   # Migration script                                 │
│   /task-work TASK-003   # Rollback procedure                               │
│   /task-work TASK-004   # Validation queries                               │
│   /task-complete TASK-001                                                   │
│   /task-complete TASK-002                                                   │
│   # etc.                                                                    │
│                                                                              │
│   # Finally, just use feature-task-work for integration/merge              │
│   /feature-task-work FEATURE-XXX --finalize-only                           │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SCENARIO 4: Iterative/Exploratory                                         │
│   ─────────────────────────────────                                         │
│   New technology - want to learn as we go.                                  │
│                                                                              │
│   /feature-task-create "add WebSocket support"                             │
│   # Creates plan with 4 tasks                                               │
│                                                                              │
│   # Human does first task manually to understand the approach              │
│   /task-work TASK-001                                                       │
│   /task-complete TASK-001                                                   │
│                                                                              │
│   # Feels confident now, automate the rest                                 │
│   /feature-task-work FEATURE-XXX                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Risk Indicators in Task Output

The `/feature-task-create` command should flag risky tasks:

```
Feature FEATURE-AUTH-REFACTOR created with 6 subtasks:

  TASK-001: Update user model types          [parallel]  [LOW RISK]
  TASK-002: Add session token handling       [parallel]  [MEDIUM RISK ⚠️]
  TASK-003: Update login flow                [sequential] [HIGH RISK 🔴]
  TASK-004: Update password reset            [sequential] [HIGH RISK 🔴]
  TASK-005: Add rate limiting                [parallel]  [MEDIUM RISK ⚠️]
  TASK-006: Update tests                     [sequential] [LOW RISK]

⚠️  HIGH RISK tasks detected: TASK-003, TASK-004
   These touch authentication/security code.
   Consider implementing manually with /task-work for more control.

Options:
  • /feature-task-work FEATURE-AUTH-REFACTOR           (automate all)
  • /feature-task-work FEATURE-AUTH-REFACTOR --skip TASK-003,TASK-004
  • /task-work TASK-003  (implement manually first)
```

---

## Command Specifications

### Command 1: `/feature-task-create`

**Purpose**: Investigate a feature request and create an implementation plan with subtasks.

**Syntax**:
```bash
/feature-task-create <feature-description>
/feature-task-create --from-spec <spec-file.md>  # From RequireKit output
```

**Workflow**:
1. **Investigation** (automated)
   - Analyze codebase
   - Identify affected files
   - Assess complexity and risks
   - Generate implementation approach

2. **Human Review** (checkpoint)
   - Present findings
   - Options: [I]mplement, [R]evise, [C]ancel

3. **Task Creation** (automated, if [I] chosen)
   - Create parent feature task
   - Decompose into subtasks
   - Identify parallel groups
   - Flag risk levels
   - Generate implementation plan

**Output**:
- `FEATURE-{slug}.md` - Parent feature task
- `TASK-001.md`, `TASK-002.md`, etc. - Subtasks
- `implementation-plan.md` - Execution guide
- All organized in `.claude/tasks/features/{slug}/`

### Command 2: `/feature-task-work`

**Purpose**: Execute the implementation of a feature task.

**Syntax**:
```bash
/feature-task-work <feature-task-id>
/feature-task-work <feature-task-id> --skip <task-ids>
/feature-task-work <feature-task-id> --only <task-ids>
/feature-task-work <feature-task-id> --finalize-only
```

**Options**:
| Option | Description |
|--------|-------------|
| `--skip TASK-001,TASK-002` | Skip specific tasks (implement manually) |
| `--only TASK-003,TASK-004` | Only run specific tasks |
| `--finalize-only` | Skip implementation, just run integration tests and prepare merge |
| `--dry-run` | Show what would be done without executing |
| `--max-parallel N` | Limit concurrent tasks (default: 3) |

**Workflow**:
1. **Check Existing Progress**
   - Load feature task and subtasks
   - Identify already-completed tasks
   - Respect `--skip` and `--only` flags

2. **Implementation** (automated)
   - Create feature branch
   - Set up git worktrees for parallel tasks
   - Execute tasks via Claude Agent SDK
   - Run tests after each task

3. **Integration** (automated)
   - Merge worktrees to feature branch
   - Run integration tests
   - Prepare summary

4. **Human Review** (checkpoint)
   - Present completion summary
   - Options: [M]erge, [I]nspect, [R]eject

---

## Task State Management

### Task Status Tracking

Each subtask tracks its status:

```yaml
# TASK-003.md frontmatter
---
id: TASK-003
feature: FEATURE-DARK-MODE
status: completed  # pending | in_progress | completed | failed | skipped
completed_by: manual  # manual | automated
completed_at: 2025-12-02T14:30:00Z
---
```

### How `/feature-task-work` Uses Status

```python
async def run_feature_implementation(self, feature_id: str, skip: list[str] = None):
    """Execute feature implementation, respecting existing progress."""
    
    feature = self.load_feature_task(feature_id)
    subtasks = self.load_subtasks(feature_id)
    
    for task in subtasks:
        # Skip already completed tasks
        if task.status == "completed":
            print(f"  ✓ {task.id} already complete ({task.completed_by})")
            continue
        
        # Skip explicitly skipped tasks
        if skip and task.id in skip:
            print(f"  ⏭ {task.id} skipped by user")
            task.status = "skipped"
            continue
        
        # Execute this task
        await self.execute_task(task)
```

This means:
- Tasks completed manually before running `/feature-task-work` are recognized
- Tasks can be completed in any order
- Partial automation is seamless

---

## Integration with RequireKit

### The Product → Developer Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REQUIREKIT → GUARDKIT PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   REQUIREKIT (Product Perspective)                                          │
│   ════════════════════════════════                                          │
│                                                                              │
│   Product Owner / Business Analyst                                          │
│   │                                                                         │
│   ▼                                                                         │
│   requirekit gather "user authentication improvements"                      │
│   │ • Interactive Q&A with stakeholders                                    │
│   │ • Captures requirements, constraints, acceptance criteria              │
│   │                                                                         │
│   ▼                                                                         │
│   requirekit formalize                                                      │
│   │ • Generates EARS notation requirements                                 │
│   │ • Creates BDD/Gherkin scenarios                                        │
│   │ • Outputs: auth-improvements-spec.md                                   │
│   │                                                                         │
│   ▼                                                                         │
│   OUTPUT: Formal specification document                                     │
│   "Here's WHAT needs to be built and WHY"                                  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                              │                                               │
│                              ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     HANDOFF POINT                                    │   │
│   │                                                                      │   │
│   │   Spec document links the two perspectives:                         │   │
│   │   • Product: What the user needs                                    │   │
│   │   • Developer: How to implement it                                  │   │
│   │                                                                      │   │
│   │   The spec becomes input to GuardKit                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   GUARDKIT (Developer Perspective)                                        │
│   ══════════════════════════════════                                        │
│                                                                              │
│   Developer                                                                 │
│   │                                                                         │
│   ▼                                                                         │
│   /feature-task-create --from-spec auth-improvements-spec.md               │
│   │ • Investigates HOW to implement the requirements                       │
│   │ • Creates technical implementation plan                                │
│   │ • Decomposes into developer tasks                                      │
│   │                                                                         │
│   ▼                                                                         │
│   🛑 Human reviews investigation, chooses [I]mplement                       │
│   │                                                                         │
│   ▼                                                                         │
│   OUTPUT: Feature task + subtasks + implementation plan                    │
│   "Here's HOW we'll build it"                                              │
│   │                                                                         │
│   ▼                                                                         │
│   Human decides: automate all, automate some, or manual                    │
│   │                                                                         │
│   ▼                                                                         │
│   /feature-task-work FEATURE-AUTH-IMPROVEMENTS                             │
│   │ • Automated implementation                                             │
│   │ • Respects manual overrides                                            │
│   │                                                                         │
│   ▼                                                                         │
│   🛑 Human reviews, merges to main                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Traceability

When using `--from-spec`, GuardKit maintains traceability:

```yaml
# FEATURE-AUTH-IMPROVEMENTS.md
---
id: FEATURE-AUTH-IMPROVEMENTS
source_spec: auth-improvements-spec.md
requirements_covered:
  - REQ-AUTH-001: Session timeout
  - REQ-AUTH-002: Password complexity
  - REQ-AUTH-003: MFA support
bdd_scenarios:
  - auth-login.feature
  - auth-password-reset.feature
---
```

This creates an audit trail from requirement → feature → tasks → implementation.

---

## Implementation Architecture

### Core Components

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CompletionMethod(Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"

@dataclass
class SubTask:
    """An atomic implementation task."""
    id: str
    description: str
    files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    parallel_group: Optional[int] = None
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reason: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    completed_by: Optional[CompletionMethod] = None
    completed_at: Optional[str] = None

@dataclass
class FeatureTask:
    """A parent feature task containing subtasks."""
    id: str
    description: str
    slug: str
    source_spec: Optional[str] = None  # RequireKit spec file
    investigation_result: Optional[str] = None
    subtasks: list[SubTask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class FeatureWorkflow:
    """
    Two-command workflow for feature implementation.
    
    This is workflow automation, not multi-agent orchestration.
    It automates a developer's manual process while maintaining
    human control at critical checkpoints.
    
    Command 1: feature_task_create() - Investigate and plan
    Command 2: feature_task_work() - Execute implementation
    """
    
    def __init__(self, project_path: str, max_parallel: int = 3):
        self.project_path = Path(project_path)
        self.max_parallel = max_parallel
        self.features_dir = self.project_path / ".claude/tasks/features"
    
    # ═══════════════════════════════════════════════════════════════════════
    # Command 1: /feature-task-create
    # ═══════════════════════════════════════════════════════════════════════
    
    async def feature_task_create(
        self, 
        description: str,
        from_spec: Optional[str] = None
    ) -> Optional[FeatureTask]:
        """
        Create a feature task through investigation and planning.
        
        This is an interactive command with a human checkpoint.
        
        Args:
            description: Natural language feature description
            from_spec: Optional path to RequireKit spec file
            
        Returns:
            FeatureTask if user chooses to implement, None if cancelled
        """
        
        print(f"🔍 Investigating: {description}")
        
        # Phase 1: Investigation (automated)
        investigation = await self._run_investigation(description, from_spec)
        
        # Phase 2: Human checkpoint
        print("\n" + "═"*60)
        print("📋 INVESTIGATION COMPLETE")
        print("═"*60)
        print(investigation[:2000])
        if len(investigation) > 2000:
            print(f"\n... ({len(investigation) - 2000} more characters)")
        
        while True:
            choice = input("\n[I]mplement / [R]evise / [C]ancel: ").strip().lower()
            
            if choice == 'c':
                print("❌ Cancelled")
                return None
                
            elif choice == 'r':
                feedback = input("Revision feedback: ")
                investigation = await self._revise_investigation(investigation, feedback)
                print("\n" + "─"*60)
                print("📋 REVISED INVESTIGATION")
                print("─"*60)
                print(investigation[:2000])
                continue
                
            elif choice == 'i':
                break
        
        # Phase 3: Task creation (automated)
        print("\n🔨 Creating feature task and subtasks...")
        feature_task = await self._create_feature_task(description, investigation, from_spec)
        
        # Save to filesystem
        self._save_feature_task(feature_task)
        
        # Display result with risk indicators
        self._display_feature_task(feature_task)
        
        return feature_task
    
    # ═══════════════════════════════════════════════════════════════════════
    # Command 2: /feature-task-work
    # ═══════════════════════════════════════════════════════════════════════
    
    async def feature_task_work(
        self,
        feature_id: str,
        skip: Optional[list[str]] = None,
        only: Optional[list[str]] = None,
        finalize_only: bool = False,
        dry_run: bool = False
    ) -> bool:
        """
        Execute feature implementation.
        
        Respects:
        - Already completed tasks (manual or previous runs)
        - Explicitly skipped tasks
        - Task dependencies and parallel groups
        
        Args:
            feature_id: The feature task ID (e.g., FEATURE-DARK-MODE)
            skip: Task IDs to skip (for manual implementation)
            only: Only run these task IDs
            finalize_only: Skip implementation, just run integration/merge
            dry_run: Show plan without executing
            
        Returns:
            True if feature was successfully implemented and merged
        """
        
        # Load feature task
        feature = self._load_feature_task(feature_id)
        if not feature:
            print(f"❌ Feature task not found: {feature_id}")
            return False
        
        print(f"🚀 Implementing: {feature.description}")
        print(f"   Feature: {feature_id}")
        print(f"   Subtasks: {len(feature.subtasks)}")
        
        # Determine which tasks to run
        tasks_to_run = self._determine_tasks_to_run(feature, skip, only, finalize_only)
        
        if dry_run:
            self._display_dry_run(feature, tasks_to_run, skip)
            return True
        
        if not finalize_only and tasks_to_run:
            # Create feature branch
            self._create_feature_branch(feature)
            
            # Execute tasks (parallel and sequential)
            await self._execute_tasks(feature, tasks_to_run)
        
        # Integration and testing
        print("\n🔗 Running integration tests...")
        integration_passed = await self._run_integration_tests(feature)
        
        if not integration_passed:
            print("❌ Integration tests failed")
            fix = input("Attempt to fix? [Y/n]: ").strip().lower()
            if fix != 'n':
                await self._attempt_fixes(feature)
                integration_passed = await self._run_integration_tests(feature)
        
        # Human checkpoint: merge decision
        print("\n" + "═"*60)
        print("🛑 FEATURE IMPLEMENTATION COMPLETE")
        print("═"*60)
        self._display_completion_summary(feature)
        
        while True:
            choice = input("\n[M]erge to main / [I]nspect / [R]eject: ").strip().lower()
            
            if choice == 'm':
                self._merge_to_main(feature)
                print(f"\n✅ Feature {feature_id} merged to main!")
                return True
                
            elif choice == 'i':
                print(f"\nInspect changes:")
                print(f"  cd {self.project_path}")
                print(f"  git diff main..feature/{feature.slug}")
                input("\nPress Enter when ready...")
                continue
                
            elif choice == 'r':
                print("❌ Feature rejected")
                return False
    
    def _determine_tasks_to_run(
        self,
        feature: FeatureTask,
        skip: Optional[list[str]],
        only: Optional[list[str]],
        finalize_only: bool
    ) -> list[SubTask]:
        """Determine which tasks need to be executed."""
        
        if finalize_only:
            return []
        
        tasks_to_run = []
        
        for task in feature.subtasks:
            # Skip already completed tasks
            if task.status == TaskStatus.COMPLETED:
                print(f"  ✓ {task.id} already complete ({task.completed_by.value})")
                continue
            
            # Skip explicitly skipped tasks
            if skip and task.id in skip:
                print(f"  ⏭ {task.id} skipped (will implement manually)")
                task.status = TaskStatus.SKIPPED
                continue
            
            # If --only specified, skip tasks not in list
            if only and task.id not in only:
                continue
            
            tasks_to_run.append(task)
        
        return tasks_to_run
    
    def _display_feature_task(self, feature: FeatureTask):
        """Display feature task with risk indicators."""
        
        print(f"\n{'═'*60}")
        print(f"Feature {feature.id} created with {len(feature.subtasks)} subtasks:")
        print("═"*60)
        
        high_risk_tasks = []
        
        for task in feature.subtasks:
            parallel_indicator = "[parallel]" if task.parallel_group else "[sequential]"
            
            if task.risk_level == RiskLevel.HIGH:
                risk_indicator = "[HIGH RISK 🔴]"
                high_risk_tasks.append(task)
            elif task.risk_level == RiskLevel.MEDIUM:
                risk_indicator = "[MEDIUM RISK ⚠️]"
            else:
                risk_indicator = "[LOW RISK]"
            
            print(f"  {task.id}: {task.description[:40]}")
            print(f"           {parallel_indicator} {risk_indicator}")
            if task.risk_reason:
                print(f"           Reason: {task.risk_reason}")
        
        if high_risk_tasks:
            print(f"\n⚠️  HIGH RISK tasks detected: {', '.join(t.id for t in high_risk_tasks)}")
            print("   Consider implementing these manually with /task-work for more control.")
        
        print(f"\nNext steps:")
        print(f"  • /feature-task-work {feature.id}           (automate all)")
        if high_risk_tasks:
            skip_list = ','.join(t.id for t in high_risk_tasks)
            print(f"  • /feature-task-work {feature.id} --skip {skip_list}")
            print(f"  • /task-work {high_risk_tasks[0].id}  (implement risky task manually first)")
    
    def _display_dry_run(
        self, 
        feature: FeatureTask, 
        tasks_to_run: list[SubTask],
        skip: Optional[list[str]]
    ):
        """Display what would be done in a dry run."""
        
        print(f"\n{'─'*60}")
        print("DRY RUN - Would execute:")
        print("─"*60)
        
        # Group by parallel group
        parallel_groups: dict[int, list[SubTask]] = {}
        sequential: list[SubTask] = []
        
        for task in tasks_to_run:
            if task.parallel_group is not None:
                if task.parallel_group not in parallel_groups:
                    parallel_groups[task.parallel_group] = []
                parallel_groups[task.parallel_group].append(task)
            else:
                sequential.append(task)
        
        if parallel_groups:
            print("\nParallel execution:")
            for group_num in sorted(parallel_groups.keys()):
                tasks = parallel_groups[group_num]
                print(f"  Group {group_num}: {', '.join(t.id for t in tasks)}")
        
        if sequential:
            print("\nSequential execution:")
            for task in sequential:
                deps = f" (after {', '.join(task.dependencies)})" if task.dependencies else ""
                print(f"  {task.id}{deps}")
        
        if skip:
            print(f"\nSkipped (manual): {', '.join(skip)}")
        
        completed = [t for t in feature.subtasks if t.status == TaskStatus.COMPLETED]
        if completed:
            print(f"\nAlready complete: {', '.join(t.id for t in completed)}")
```

---

## CLI Interface

```python
import click
import anyio

@click.group()
def cli():
    """GuardKit - Feature workflow automation for developers."""
    pass

@cli.command('create')
@click.argument('description')
@click.option('--from-spec', '-s', help='Path to RequireKit spec file')
@click.option('--project', '-p', default='.', help='Project path')
def feature_create(description: str, from_spec: str, project: str):
    """
    Create a feature task through investigation and planning.
    
    Example:
        guardkit create "add dark mode support"
        guardkit create --from-spec auth-spec.md "implement auth improvements"
    """
    workflow = FeatureWorkflow(project)
    anyio.run(workflow.feature_task_create, description, from_spec)

@cli.command('work')
@click.argument('feature_id')
@click.option('--skip', '-s', help='Task IDs to skip (comma-separated)')
@click.option('--only', '-o', help='Only run these task IDs (comma-separated)')
@click.option('--finalize-only', is_flag=True, help='Skip implementation, just merge')
@click.option('--dry-run', is_flag=True, help='Show plan without executing')
@click.option('--max-parallel', '-j', default=3, help='Max parallel tasks')
@click.option('--project', '-p', default='.', help='Project path')
def feature_work(
    feature_id: str, 
    skip: str, 
    only: str, 
    finalize_only: bool,
    dry_run: bool,
    max_parallel: int,
    project: str
):
    """
    Execute feature implementation.
    
    Examples:
        guardkit work FEATURE-DARK-MODE
        guardkit work FEATURE-AUTH --skip TASK-003,TASK-004
        guardkit work FEATURE-DB --dry-run
    """
    skip_list = skip.split(',') if skip else None
    only_list = only.split(',') if only else None
    
    workflow = FeatureWorkflow(project, max_parallel)
    success = anyio.run(
        workflow.feature_task_work,
        feature_id, skip_list, only_list, finalize_only, dry_run
    )
    
    if not success:
        raise SystemExit(1)

@cli.command('status')
@click.argument('feature_id')
@click.option('--project', '-p', default='.', help='Project path')
def feature_status(feature_id: str, project: str):
    """
    Show status of a feature task and its subtasks.
    
    Example:
        guardkit status FEATURE-DARK-MODE
    """
    workflow = FeatureWorkflow(project)
    workflow.display_status(feature_id)

if __name__ == '__main__':
    cli()
```

---

## Summary: The Two-Command Workflow

### What GuardKit Is

> **GuardKit automates your feature development workflow** - from investigation through implementation to merge - **while keeping you in control**.

It is:
- ✅ **Workflow automation** - Automating repetitive manual steps
- ✅ **A feature pipeline** - Like CI/CD but for feature development
- ✅ **A task runner** - Executing tasks with dependencies and parallelism
- ✅ **Human-in-the-loop** - Critical checkpoints where you decide

It is NOT:
- ❌ **Not a swarm** - No hive-mind, no queen/worker hierarchy
- ❌ **Not multi-agent** - Single Claude instance (parallel for independent tasks)
- ❌ **Not self-organizing** - Tasks predetermined by investigation
- ❌ **Not emergent** - Predictable, reproducible behavior

### Command Flow

```
                    ┌─────────────────────────────────┐
                    │    /feature-task-create         │
                    │    "implement feature X"        │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │    AUTOMATED: Investigation     │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │ 🛑 HUMAN: Review & Decide       │
                    │    [I]mplement / [R]evise       │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │    AUTOMATED: Create Tasks      │
                    │    + Risk Assessment            │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │    OUTPUT: Feature + Subtasks   │
                    │    (with risk indicators)       │
                    └───────────────┬─────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
    ┌──────────────┐    ┌────────────────────┐    ┌──────────────┐
    │ FULL AUTO    │    │ PARTIAL MANUAL     │    │ FULL MANUAL  │
    │              │    │                    │    │              │
    │ /feature-    │    │ /task-work TASK-X  │    │ /task-work   │
    │ task-work    │    │ (risky ones)       │    │ (each task)  │
    │ FEATURE-X    │    │ then               │    │              │
    │              │    │ /feature-task-work │    │ then         │
    │              │    │ FEATURE-X          │    │ /feature-    │
    │              │    │ --skip TASK-X      │    │ task-work    │
    │              │    │                    │    │ --finalize   │
    └──────┬───────┘    └─────────┬──────────┘    └──────┬───────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────────┐
                    │ 🛑 HUMAN: Review Before Merge   │
                    │    [M]erge / [I]nspect          │
                    └─────────────────────────────────┘
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Human Control Points** | Two clear decision points: after investigation, before merge |
| **Manual Override** | Implement any task manually when needed for complex/risky work |
| **Automation When Confident** | Full automation for straightforward features |
| **Risk Visibility** | Clear risk indicators help humans decide what to automate |
| **Incremental Adoption** | Start with more manual control, increase automation over time |
| **RequireKit Integration** | Seamless handoff from product specs to implementation |
| **Predictable Behavior** | No emergent surprises - you know what will happen |
| **Audit Trail** | Clear record of what was automated vs manual |

### The Escape Hatches

1. **After Investigation**: Cancel or revise before committing to implementation
2. **Task-Level Control**: Implement specific tasks manually with `/task-work`
3. **Skip Flag**: `--skip TASK-X` to automate most, manual for some
4. **Finalize Only**: `--finalize-only` when all tasks done manually
5. **Before Merge**: Inspect changes before final merge to main

This gives developers **confidence to automate** because they know they can always take manual control when needed.

---

## Related Documents

- [Claude Agent SDK: Fast Path Analysis](./Claude_Agent_SDK_Fast_Path_to_GuardKit_Orchestration.md) - Initial SDK research
- [Claude Agent SDK: Full Automation Spec](./Claude_Agent_SDK_True_End_to_End_Orchestrator.md) - Earlier single-command approach
- [LangGraph Alternative](./GuardKit_LangGraph_Orchestration_Build_Strategy.md) - Multi-LLM option for future

---

## References

- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Python GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [Git Worktrees Documentation](https://git-scm.com/docs/git-worktree)
- [Claude-Flow](https://github.com/ruvnet/claude-flow) - Example of swarm-based orchestration (different paradigm)

---

*Generated: December 2025*
*Updated: December 2025 - Clarified as workflow automation (not swarm orchestration), added manual override capability*
*Context: Specifying feature workflow automation with human control points*
