# TASK-UX-3A8D: Make --create-agent-tasks the default behavior

**Task ID**: TASK-UX-3A8D
**Priority**: HIGH
**Status**: COMPLETED
**Created**: 2025-11-21T14:30:00Z
**Started**: 2025-11-21T14:45:00Z
**Completed**: 2025-11-21T15:20:00Z
**Tags**: ux, template-create, agent-enhancement, breaking-change
**Complexity**: 3/10 (Simple)
**Duration**: 35 minutes (estimated: 30 minutes)
**Completion Location**: tasks/completed/TASK-UX-3A8D/
**Organized Files**: TASK-UX-3A8D.md, completion-report.md

---

## Description

Make `--create-agent-tasks` the default behavior for `/template-create` command, with an opt-out flag `--no-create-agent-tasks` for edge cases (CI/CD, rapid prototyping).

**Rationale**: Based on systematic analysis (via Ultrathink agent), 90% of users need agent enhancement tasks, while only 10% are edge cases. The current optional flag hurts discoverability and leads to incomplete templates being shipped.

**Impact**: This is a **positive breaking change** that improves UX and prevents incomplete templates from reaching production.

---

## Context

### Current Behavior (Problematic)

```bash
# Default (without flag)
/template-create
# Output: "10 agents created" ← No guidance on what to do next
# Problem: Users don't know agents need enhancement

# With flag (requires users to know about it)
/template-create --create-agent-tasks
# Output: Shows Option A/B enhancement instructions ✅
# Problem: Users must discover this flag
```

### Desired Behavior (Improved)

```bash
# Default (creates tasks automatically)
/template-create
# Output: Shows Option A/B enhancement instructions ✅
# Benefit: Immediate guidance, clear next steps

# Opt-out for edge cases
/template-create --no-create-agent-tasks
# Output: "10 agents created" (no tasks)
# Use case: CI/CD automation, rapid prototyping
```

---

## Analysis Summary

**Systematic evaluation found**:
- ✅ Valid scenarios for NOT creating tasks: 5-10% (edge cases)
- ✅ Discoverability problem: Users don't know `/agent-enhance` exists
- ✅ File system impact: Trivial (~30KB for 10 tasks)
- ✅ Industry standard: All scaffolding tools show next steps by default
- ✅ Cost/Benefit: +7/10 net benefit (strong positive)

**See**: TASK-UX-2F95 completion-summary.md for full Ultrathink analysis

---

## Implementation Instructions

### Step 1: Change Default Value

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Location**: Line 85 in `OrchestrationConfig` dataclass

**Change**:
```python
# BEFORE (Line 85)
create_agent_tasks: bool = False  # TASK-PHASE-8-INCREMENTAL: Create individual enhancement tasks for each agent

# AFTER
create_agent_tasks: bool = True   # TASK-UX-3A8D: Default ON (opt-out via --no-create-agent-tasks)
```

**Complete code block for reference**:
```python
@dataclass
class OrchestrationConfig:
    """Configuration for template creation orchestration"""
    codebase_path: Optional[Path] = None
    output_path: Optional[Path] = None  # DEPRECATED: Use output_location instead
    output_location: str = 'global'  # TASK-068: 'global' or 'repo'
    max_templates: Optional[int] = None
    dry_run: bool = False
    save_analysis: bool = False
    no_agents: bool = False
    verbose: bool = False
    skip_validation: bool = False  # TASK-040: Skip Phase 5.5 validation
    auto_fix_templates: bool = True  # TASK-040: Auto-fix completeness issues
    interactive_validation: bool = True  # TASK-040: Prompt user for validation decisions
    validate: bool = False  # TASK-043: Run extended validation and generate quality report
    resume: bool = False  # TASK-BRIDGE-002: Resume from checkpoint after agent invocation
    custom_name: Optional[str] = None  # TASK-FDB2: User-provided template name override
    create_agent_tasks: bool = True  # TASK-UX-3A8D: Default ON (opt-out via --no-create-agent-tasks)
```

### Step 2: Add Opt-Out Flag

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

**Location**: Lines 2073-2074 in argument parser (inside `if __name__ == "__main__"` block)

**Add new argument** (after `--create-agent-tasks` argument):
```python
# BEFORE (Lines 2073-2074)
parser.add_argument("--create-agent-tasks", action="store_true",
                    help="Create individual enhancement tasks for each agent (TASK-PHASE-8-INCREMENTAL)")

# AFTER (add both flags for flexibility)
parser.add_argument("--create-agent-tasks", action="store_true", default=True,
                    help="Create individual enhancement tasks for each agent (default: True)")
parser.add_argument("--no-create-agent-tasks", dest="create_agent_tasks",
                    action="store_false",
                    help="Skip creating enhancement tasks (for CI/CD, rapid prototyping)")
```

**Complete code block for reference** (lines 2050-2079):
```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Template creation orchestrator")
    parser.add_argument("--path", type=str, help="Codebase path")
    parser.add_argument("--name", type=str,
                        help="Custom template name (overrides AI-generated name)")
    parser.add_argument("--output-location", choices=['global', 'repo'], default='global',
                        help="Output location: 'global' (~/.agentecflow/templates/) or 'repo' (installer/core/templates/)")
    parser.add_argument("--skip-qa", action="store_true",
                        help="DEPRECATED: Now always uses smart defaults")
    parser.add_argument("--config", type=str,
                        help="Path to config file (TASK-9039)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze and show plan without saving")
    parser.add_argument("--validate", action="store_true",
                        help="Run extended validation and generate quality report")
    parser.add_argument("--max-templates", type=int,
                        help="Maximum template files to generate")
    parser.add_argument("--no-agents", action="store_true",
                        help="Skip agent generation")
    parser.add_argument("--create-agent-tasks", action="store_true", default=True,
                        help="Create individual enhancement tasks for each agent (default: True)")
    parser.add_argument("--no-create-agent-tasks", dest="create_agent_tasks",
                        action="store_false",
                        help="Skip creating enhancement tasks (for CI/CD, rapid prototyping)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint after agent invocation")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed progress")

    args = parser.parse_args()
```

### Step 3: Update Documentation

**File**: `installer/core/commands/template-create.md`

**Location 1**: Lines 126-133 (Phase 8 description)

**Change**:
```markdown
# BEFORE
Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95) [OPTIONAL - only with --create-agent-tasks]

# AFTER
Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95, TASK-UX-3A8D) [DEFAULT - skip with --no-create-agent-tasks]
```

**Complete section** (lines 126-133):
```markdown
Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95, TASK-UX-3A8D) [DEFAULT - skip with --no-create-agent-tasks]
├─ Creates one task per agent file
├─ Task metadata includes agent_file, template_dir, template_name, agent_name
├─ Tasks created in backlog with priority: medium
├─ Displays two enhancement options:
│  ├─ Option A (Recommended): /agent-enhance template-name/agent-name --strategy=hybrid (2-5 minutes per agent)
│  └─ Option B (Optional): /task-work TASK-AGENT-XXX (30-60 minutes per agent - full workflow)
└─ Both approaches use the same AI enhancement logic
```

**Location 2**: Lines 210-228 (flag documentation)

**Replace entire section**:
```markdown
# BEFORE
--create-agent-tasks     Create individual enhancement tasks for each agent (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95)
                         Default: false (no tasks created)

                         When enabled:
                         - Runs Phase 8: Task Creation
                         - Creates one task per agent file
                         - Displays two enhancement options:
                           - Option A (Recommended): /agent-enhance for fast enhancement (2-5 minutes per agent)
                           - Option B (Optional): /task-work for full workflow with quality gates (30-60 minutes)
                         - Both approaches use the same AI enhancement logic
                         - Provides control over which agents to enhance and when

                         Use when:
                         - You want granular control over agent enhancement
                         - You want to prioritize specific agents
                         - You want to enhance agents at your own pace
                         - You need clear guidance on enhancement options

# AFTER
--no-create-agent-tasks  Skip creating agent enhancement tasks (TASK-UX-3A8D)
                         Default: Tasks are created automatically

                         By default, Phase 8 creates one enhancement task per agent with:
                         - Clear Option A/B instructions for enhancement workflow
                         - Copy-paste ready commands (/agent-enhance, /task-work)
                         - Duration estimates (2-5 min vs 30-60 min)
                         - Persistent TODO list in tasks/backlog/

                         Use --no-create-agent-tasks when:
                         - Running in CI/CD automation (no interactive workflow needed)
                         - Re-running template-create on existing template (avoid duplicates)
                         - Rapid prototyping (don't need enhancement tracking)
                         - Custom workflow (handling enhancement differently)

                         Benefits of default task creation:
                         - ✅ Immediate guidance on agent enhancement workflow
                         - ✅ Discovers /agent-enhance command automatically
                         - ✅ Prevents shipping incomplete templates
                         - ✅ Provides progress tracking with /task-status
                         - ✅ Enables batch processing with /task-work
```

**Location 3**: Add migration note in Usage section (after line 50)

**Add new section**:
```markdown
## Breaking Change: Default Task Creation (TASK-UX-3A8D)

**What Changed (v1.x.x)**:
- Agent enhancement tasks are now created by default
- Previous behavior required `--create-agent-tasks` flag
- New behavior: tasks created unless `--no-create-agent-tasks` specified

**Why This Change**:
- 90% of users needed this functionality
- Improves discoverability of agent enhancement workflow
- Prevents shipping incomplete templates with empty agent stubs
- Aligns with industry standards (showing next steps after generation)

**Migration**:
- **Normal usage**: No change needed (better experience automatically) ✅
- **CI/CD scripts**: Add `--no-create-agent-tasks` flag to automation
- **Rapid prototyping**: Add `--no-create-agent-tasks` flag when testing

**Example**:
```bash
# Before (required flag for tasks)
/template-create --create-agent-tasks

# After (default behavior, no flag needed)
/template-create

# Opt-out for CI/CD
/template-create --no-create-agent-tasks
```
```

### Step 4: Update CLAUDE.md (Project Instructions)

**File**: `CLAUDE.md` (root level)

**Location**: Search for `--create-agent-tasks` references

**Change** (around line mentioning the flag):
```markdown
# BEFORE
--create-agent-tasks     Create individual enhancement tasks (optional)

# AFTER
--no-create-agent-tasks  Skip creating enhancement tasks (opt-out, for CI/CD)
```

**Add note** about default behavior in relevant sections.

---

## Testing Instructions

### Test 1: Default Behavior (Tasks Created)

```bash
# Run without any flags
/template-create --name test-default

# Expected output:
# ✅ Template created
# ✅ "Phase 8: Agent Task Creation" runs
# ✅ Shows "AGENT ENHANCEMENT OPTIONS" with Option A/B
# ✅ 10 task files created in tasks/backlog/TASK-AGENT-*
```

### Test 2: Opt-Out Behavior (No Tasks)

```bash
# Run with --no-create-agent-tasks flag
/template-create --name test-no-tasks --no-create-agent-tasks

# Expected output:
# ✅ Template created
# ✅ Phase 8 skipped
# ✅ No "AGENT ENHANCEMENT OPTIONS" section
# ✅ No task files created in tasks/backlog/
```

### Test 3: Backward Compatibility

```bash
# Old flag should still work (redundant but harmless)
/template-create --name test-compat --create-agent-tasks

# Expected output:
# ✅ Same behavior as test 1 (tasks created)
# ℹ️  No warning needed (flag is now default)
```

### Test 4: CI/CD Simulation

```bash
# Simulate CI/CD environment
export CI=true
/template-create --name test-ci --no-create-agent-tasks

# Expected output:
# ✅ Template created without tasks
# ✅ Suitable for packaging/distribution
```

---

## Acceptance Criteria

### AC1: Default Value Changed
- [x] `OrchestrationConfig.create_agent_tasks` default changed from `False` to `True`
- [x] Code change in line 85 of `template_create_orchestrator.py`

### AC2: Opt-Out Flag Added
- [x] `--no-create-agent-tasks` argument added to parser
- [x] Flag sets `create_agent_tasks` to `False`
- [x] Help text explains use cases (CI/CD, rapid prototyping)

### AC3: Documentation Updated
- [x] `template-create.md` Phase 8 description updated (line 126)
- [x] Flag documentation replaced with `--no-create-agent-tasks` (lines 210-228)
- [x] Breaking change migration guide added
- [x] `CLAUDE.md` references updated

### AC4: Testing Validated
- [x] Default behavior creates tasks (Test 1)
- [x] Opt-out flag skips tasks (Test 2)
- [x] Old flag still works (Test 3)
- [x] CI/CD simulation works (Test 4)

### AC5: User Experience
- [x] Default behavior shows enhancement instructions immediately
- [x] Opt-out is clear and discoverable
- [x] Migration path is documented
- [x] No breaking changes for normal users (improvement only)

---

## Implementation Notes

### Code Changes Summary

**3 files modified**:
1. `template_create_orchestrator.py` - 2 changes (default value + parser flag)
2. `template-create.md` - 3 changes (Phase 8 description + flag docs + migration note)
3. `CLAUDE.md` - 1 change (flag reference update)

**Total lines changed**: ~50 lines (mostly documentation)

### Risk Assessment

**Risk Level**: LOW

**Mitigation**:
- ✅ Positive breaking change (improves UX)
- ✅ Opt-out flag preserves old behavior for edge cases
- ✅ Clear migration documentation
- ✅ Backward compatible (old flag still works)

**Impact**:
- ✅ 90% of users: Better experience (no action needed)
- ⚠️ 10% edge cases: Must add `--no-create-agent-tasks` flag

---

## Migration Guide for Users

### For Normal Users (No Action Needed) ✅

```bash
# Before: Had to remember flag
/template-create --create-agent-tasks

# After: Works by default
/template-create

# Benefit: Immediate guidance, clear next steps
```

### For CI/CD Pipelines (Add One Flag) 🔧

```bash
# Before: No flag needed
/template-create --output-location repo

# After: Add opt-out flag
/template-create --output-location repo --no-create-agent-tasks

# Why: Prevents task files in automated builds
```

### For Rapid Prototyping (Add One Flag) 🔧

```bash
# Before: Quick iteration
/template-create --name proto-1
/template-create --name proto-2

# After: Add opt-out flag
/template-create --name proto-1 --no-create-agent-tasks
/template-create --name proto-2 --no-create-agent-tasks

# Why: Avoids task accumulation during experimentation
```

---

## Related Tasks

- **TASK-UX-2F95**: Update template-create output to recommend agent-enhance (completed)
  - This task builds on 2F95's Option A/B instruction format
  - Makes those instructions visible by default
- **TASK-PHASE-8-INCREMENTAL**: Incremental agent enhancement workflow (completed)
  - Provides the task creation infrastructure
  - This task changes the default behavior
- **TASK-AI-2B37**: AI integration for agent enhancement (completed)
  - Provides the underlying `/agent-enhance` command
  - This task improves discoverability of that command

---

## Benefits

1. **Improved Discoverability**: Users immediately see enhancement workflow (+90% awareness)
2. **Quality Assurance**: Prevents incomplete templates from reaching production
3. **Better Onboarding**: New users learn `/agent-enhance` command automatically
4. **Industry Alignment**: Matches convention of showing next steps after generation
5. **Reduced Support**: Fewer questions about "how do I enhance agents?"

---

## Rollback Plan

If issues arise, revert is simple:

```bash
# Revert to old default
git revert <commit-hash>

# Or manual fix (1 line change)
create_agent_tasks: bool = False  # Revert to old default
```

---

**Created**: 2025-11-21T14:30:00Z
**Status**: BACKLOG
**Ready for Implementation**: YES
**Estimated Duration**: 30 minutes
**Complexity**: 3/10 (Simple - mostly config change)
