# Review Report: TASK-REV-BAF6

## Executive Summary

This decision review analyzes the feature scope explosion observed in FEAT-GR-MVP (3,793 markdown files, 1,686 task files) and proposes workflow improvements to enforce iterative development principles. The current `/feature-plan` and `/task-review [I]mplement` commands lack scope guardrails, leading to features that are difficult to verify, debug, and complete autonomously via AutoBuild.

**Key Finding**: The observed scope explosion violates the core principle of "iterative development with verification between waves" - a feature with 1,686 tasks cannot be meaningfully verified incrementally.

**Recommended Decision**: **Option D (Combination Approach)** - Implement soft limits with phased [I]mplement and default feature YAML generation.

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Standard |
| **Duration** | ~1.5 hours |
| **Reviewer** | Decision analysis workflow |
| **Files Analyzed** | feature-plan.md, task-review.md, implement_orchestrator.py, implementation_mode_analyzer.py, autobuild.md |

---

## Current Situation Assessment

### Observed Issues

1. **FEAT-GR-MVP Scope Explosion**
   - 3,793 total markdown files in worktree
   - 1,686 task files specifically
   - 24 feature subfolders in backlog
   - Multiple nested features and archived tasks
   - Scope expanded far beyond original intent

2. **Root Causes Identified**
   - No task count limits in `/feature-plan` or `/task-review [I]mplement`
   - No wave count limits (unlimited parallel groups)
   - No complexity-based feature splitting
   - [I]mplement creates all subtasks at once (no phasing)
   - Feature YAML not always generated (requires manual script)

3. **Impact on Iterative Development**
   - Cannot verify incrementally with 1,686 tasks
   - AutoBuild turn limits (max 5-10) insufficient for such scope
   - Debugging surface area is unmanageable
   - Feedback loops broken (can't test between waves meaningfully)

### Current Implementation Analysis

**`/feature-plan` Current Behavior**:
- Creates review task automatically
- Executes decision analysis
- On [I]mplement: Creates all subtasks at once
- Generates structured YAML by default (since TASK-FW-008)
- No task count limits
- No wave count limits
- No auto-split for large features

**`/task-review [I]mplement` Current Behavior**:
- Extracts subtasks from review recommendations (unlimited)
- Assigns implementation modes (task-work/direct)
- Detects parallel groups (waves) - unlimited
- Generates workspace names for Conductor
- Creates all task files at once
- No checkpoint gates between waves

**AutoBuild Integration**:
- Feature-build has pre-loop disabled by default
- Task-build has pre-loop enabled by default
- Recommended timeout: 15-30 minutes per task
- Best practice: "Right-Sized Tasks: Aim for tasks that complete in 1-3 turns"
- No explicit guidance on max tasks per feature

---

## Decision Options Analysis

### Option A: Strict Limits (Hard Constraints)

**Configuration**:
- Max 7 tasks per feature (hard limit)
- Max 3 waves (hard limit)
- Auto-split required when exceeding thresholds
- Block [I]mplement if limits exceeded

**Pros**:
- Guarantees manageable scope
- Forces upfront decomposition
- AutoBuild compatible (5-10 turn limit works)
- Clear, predictable behavior

**Cons**:
- May frustrate users with legitimate large features
- Requires significant UX work for auto-split
- Arbitrary limits may not fit all contexts
- Forces workflow changes even when not needed

**Effort**: High (auto-split logic, validation, error handling)
**Risk**: Medium (user friction, edge cases)

### Option B: Soft Limits with Warnings

**Configuration**:
- Soft threshold: 10 tasks (warning displayed)
- Soft threshold: 4 waves (warning displayed)
- Override flag: `--allow-large-feature`
- User proceeds at own risk

**Pros**:
- Preserves flexibility
- Educates users about best practices
- Easy to implement
- Low user friction

**Cons**:
- Users may ignore warnings
- Doesn't prevent scope explosion
- Doesn't enforce iterative verification
- Feature YAML may still be huge

**Effort**: Low (add warnings, optional flag)
**Risk**: Low (minimal change, may not solve problem)

### Option C: Iterative-First Mode (Phased Implementation)

**Configuration**:
- [I]mplement creates Wave 1 only
- Verification checkpoint required before Wave 2
- Progressive disclosure of subsequent waves
- Feature YAML updated incrementally

**Pros**:
- Directly addresses iterative verification principle
- Forces feedback between waves
- AutoBuild can complete Wave 1, verify, continue
- Natural workflow for complex features

**Cons**:
- More complex UX
- Requires state management between phases
- May slow down simple features
- Needs "continue" command or mechanism

**Effort**: Medium-High (state management, UX, commands)
**Risk**: Medium (new workflow, user adoption)

### Option D: Combination Approach (RECOMMENDED)

**Configuration**:
1. **Soft limits with warnings** (from Option B)
   - Warn at >10 tasks, >4 waves
   - No hard block (flexibility preserved)

2. **Phased [I]mplement as default** (from Option C)
   - [I]mplement creates Wave 1 only by default
   - Flag `--all-waves` to create all at once (opt-in)
   - Clear next steps: "Run `/task-review TASK-XXX --continue` for Wave 2"

3. **Feature YAML always generated** (new)
   - `/task-review [I]mplement` generates YAML by default
   - Consistent with `/feature-plan` behavior
   - Immediate `/feature-build` compatibility

4. **Complexity-based guidance** (new)
   - If feature complexity >7, suggest splitting
   - If task count >15, require confirmation
   - Display AutoBuild compatibility warning for large features

**Pros**:
- Addresses all identified issues
- Preserves flexibility for power users
- Enforces iterative verification by default
- AutoBuild compatible
- Consistent YAML generation

**Cons**:
- Multiple changes to implement
- Needs new `--continue` mechanism
- Learning curve for phased workflow

**Effort**: Medium (phased implementation, warnings, YAML default)
**Risk**: Low-Medium (incremental changes, clear fallbacks)

---

## Recommended Decision: Option D

### Rationale

Option D directly addresses the core principle stated in the review task:

> "I like to work iteratively and then test/verify the work done before moving on to keep the surface area/scope of the changes workable such that when there is an issue we can sensibly diagnose it."

By making phased [I]mplement the default, users are guided toward iterative verification naturally. The soft limits provide education without frustration. The YAML generation ensures AutoBuild compatibility.

### Implementation Priority

| Change | Priority | Effort | Value |
|--------|----------|--------|-------|
| Feature YAML default in [I]mplement | 1 | Low | High |
| Phased [I]mplement (Wave 1 only) | 2 | Medium | High |
| Soft limits with warnings | 3 | Low | Medium |
| `--continue` command for waves | 4 | Medium | High |
| Complexity-based guidance | 5 | Low | Medium |

### Suggested Task Breakdown

1. **TASK-FS-001**: Add feature YAML generation to `/task-review [I]mplement` (direct, 1-2h)
   - Currently only `/feature-plan` generates YAML
   - Make [I]mplement consistent

2. **TASK-FS-002**: Implement phased [I]mplement (Wave 1 only default) (task-work, 3-4h)
   - Modify `implement_orchestrator.py`
   - Add `--all-waves` flag
   - Update display/summary

3. **TASK-FS-003**: Add soft limit warnings (direct, 1h)
   - Warn at >10 tasks
   - Warn at >4 waves
   - Display in summary

4. **TASK-FS-004**: Add `--continue` mechanism for subsequent waves (task-work, 3-4h)
   - State tracking for phased implementation
   - Command extension or new command
   - Wave 2+ creation logic

5. **TASK-FS-005**: Add complexity-based guidance (direct, 1-2h)
   - Suggest splitting if complexity >7
   - Require confirmation if tasks >15
   - AutoBuild compatibility warning

---

## Success Metrics

After implementation, the following should be true:

| Metric | Target | Current |
|--------|--------|---------|
| Typical feature task count | 5-10 | Unlimited |
| Typical wave count | 2-3 | Unlimited |
| Iterative verification possible | Yes | No |
| AutoBuild completes feature | Within 10 turns | Often fails |
| Feature YAML generation | Automatic | Manual |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| User frustration with phased mode | Provide `--all-waves` escape hatch |
| Breaking existing workflows | Changes are additive, not breaking |
| Complexity of `--continue` | Start simple (re-run with wave parameter) |
| Users ignoring warnings | Make phased default, not warnings |

---

## REVISION: Deeper Analysis on Wave-by-Wave Implementation Mechanics

### Clarification on File Count Discrepancy

**Key Insight**: The 1,686 task files are in the FEAT-GR-MVP **worktree** (accumulated over time), NOT from a single `/feature-plan` invocation.

**Actual Task Distribution in Worktree**:
```
backlog:      286 files
completed:   1,161 files (in 391 subdirectories!)
in_progress:    4 files
in_review:     77 files
```

**Example of Reasonable Feature Size**:
`tasks/backlog/graphiti-refinement-mvp/` contains **35 tasks** - still large but manageable.

The issue is not that `/feature-plan` creates 1,686 tasks at once, but rather:
1. Multiple features accumulated in one worktree over time
2. Completed tasks aren't being archived/pruned effectively
3. The worktree became a "dumping ground" for multiple development streams

### The Real Workflow Problem: `/feature-build` from Shell vs Claude Code

**Current Pain Points Identified**:

1. **Claude Code Issues with `/feature-build`**:
   - VS Code Claude extension has 10-minute bash timeout
   - Long feature builds get killed (exit code 137)
   - Less feedback during execution (no real-time streaming)
   - Workaround: Must run from terminal shell

2. **Disjointed Workflow**:
   ```
   Claude Code (interactive planning)
        │
        └── /feature-plan "feature"  ✓ Works well
               │
               └── Creates FEAT-XXX.yaml + task files

   Terminal (autonomous execution)
        │
        └── guardkit autobuild feature FEAT-XXX  ✓ Works but separate
               │
               └── Creates worktree, runs Player-Coach

   Claude Code (review/complete)
        │
        └── /feature-complete FEAT-XXX  ✓ But context lost
   ```

3. **Context Switching Cost**:
   - User plans in Claude Code
   - Must switch to terminal for execution
   - Loses interactive feedback loop
   - Hard to diagnose issues without Claude Code context

### Wave-by-Wave Implementation: Current vs Proposed

**Current Behavior** (all-at-once):
```bash
/task-review TASK-REV-XXX [I]mplement
# Creates ALL subtasks at once
# Creates FEAT-XXX.yaml with all tasks
# User must run ALL tasks before verification

guardkit autobuild feature FEAT-XXX
# Executes Wave 1, Wave 2, Wave 3... in sequence
# No pause between waves for human verification
# Must complete entire feature or fail
```

**Proposed Phased Behavior** (wave-by-wave):
```bash
/task-review TASK-REV-XXX [I]mplement
# Creates Wave 1 subtasks ONLY
# Creates FEAT-XXX.yaml with Wave 1 tasks
# Displays: "Wave 1 of 3 created. Run /feature-build FEAT-XXX"

guardkit autobuild feature FEAT-XXX
# Executes Wave 1 only
# Pauses for human review after Wave 1

# After review/merge:
/task-review TASK-REV-XXX --continue  # or /feature-continue FEAT-XXX
# Creates Wave 2 subtasks
# Updates FEAT-XXX.yaml
# Executes Wave 2
# Repeat until all waves complete
```

### Integration with `/feature-build` UX

**Current `/feature-build` Limitations**:

1. **No Real-Time Feedback in Claude Code**:
   - The command invokes `guardkit autobuild` via Bash
   - Long-running commands (>10 min) get killed
   - No streaming output in VS Code extension
   - Must switch to terminal for visibility

2. **Feature Mode Complexity**:
   - Feature mode loads YAML, parses tasks, runs waves
   - Each wave runs Player-Coach loop for each task
   - Total time: (tasks × 15-30 min) = could be hours
   - No checkpoint between waves

**Proposed UX Improvements**:

1. **Hybrid Execution Model**:
   ```bash
   # In Claude Code (planning + control)
   /feature-plan "authentication"
   # → Creates FEAT-A1B2 with Wave 1 ready

   # In Claude Code (kick off execution)
   /feature-build FEAT-A1B2 --background
   # → Starts background process
   # → Returns immediately with: "Building... check status with /feature-status"

   # In Claude Code (check progress)
   /feature-status FEAT-A1B2
   # → Shows: Wave 1: 2/3 tasks complete, TASK-003 in progress (Turn 2/5)

   # After wave completes (notification or polling)
   /feature-continue FEAT-A1B2  # or automatic prompt
   # → Reviews Wave 1 results
   # → Creates Wave 2 tasks
   # → Continues execution
   ```

2. **Background Execution with Progress**:
   - `/feature-build --background` runs via Bash with `run_in_background`
   - Progress written to `.guardkit/autobuild/FEAT-XXX/progress.json`
   - `/feature-status` reads progress file and displays
   - Claude Code can poll or user can check periodically

3. **Wave Completion Hooks**:
   ```yaml
   # .guardkit/features/FEAT-A1B2.yaml
   orchestration:
     wave_completion_action: pause  # pause | continue | notify
     notify_on_completion: true
   ```

### Revised Recommendation: Option E (Enhanced Combination)

Building on Option D, add:

1. **Background execution mode** for `/feature-build`
   - `--background` flag to run asynchronously
   - Progress file for status checking
   - `/feature-status` command to check progress

2. **Wave-aware execution** in feature-build
   - Default: Pause after each wave for review
   - `--auto-continue` to skip pauses (opt-in)
   - Progress saved between waves for resume

3. **Improved Claude Code integration**
   - `/feature-status FEAT-XXX` - Check build progress
   - `/feature-continue FEAT-XXX` - Continue after wave
   - `/feature-pause FEAT-XXX` - Pause running build
   - `/feature-logs FEAT-XXX` - View execution logs

### Updated Task Breakdown

| ID | Title | Mode | Priority |
|----|-------|------|----------|
| TASK-FS-001 | Add feature YAML generation to /task-review [I]mplement | direct | 1 |
| TASK-FS-002 | Implement phased [I]mplement (Wave 1 only default) | task-work | 2 |
| TASK-FS-003 | Add background execution mode to /feature-build | task-work | 3 |
| TASK-FS-004 | Add /feature-status command for progress checking | direct | 4 |
| TASK-FS-005 | Add wave completion pause/continue in feature-build | task-work | 5 |
| TASK-FS-006 | Add soft limit warnings (>10 tasks, >4 waves) | direct | 6 |
| TASK-FS-007 | Add /feature-continue command | task-work | 7 |
| TASK-FS-008 | Add complexity-based guidance and AutoBuild warnings | direct | 8 |

### Why This Addresses the Workflow Friction

1. **Stay in Claude Code**: Background execution + status polling = no terminal switching needed
2. **Iterative Verification**: Wave completion pause = natural verification checkpoint
3. **Manageable Scope**: Phased [I]mplement = smaller batches by default
4. **Resume Support**: Progress persistence = can resume after interruption
5. **Flexibility**: `--auto-continue` for power users who want full autonomous execution

---

## Appendix: Evidence

### Worktree Task Distribution (Clarified)

**FEAT-GR-MVP Worktree** (accumulated over time):
```
Total markdown files: 3,793
├── backlog:      286 tasks
├── completed:  1,161 tasks (in 391 feature subdirectories)
├── in_progress:   4 tasks
├── in_review:    77 tasks
└── other:       2,265 (reviews, reports, docs, etc.)
```

**Main Repo Backlog** (current):
```
tasks/backlog: 267 task files
```

**Example Reasonable Feature** (graphiti-refinement-mvp):
```
tasks/backlog/graphiti-refinement-mvp/: 35 tasks
```

### AutoBuild Turn Limit Context

From autobuild.md:
- "Right-Sized Tasks: Aim for tasks that complete in 1-3 turns"
- Max turns typically 5-10
- Recommended timeout: 15-30 minutes per task
- Feature with 35 tasks × 15 min = ~8.75 hours (too long for single session)

### Claude Code Bash Timeout Issue

From feature-build.md:
> "**Important**: Claude Code's VS Code extension has a 10-minute bash command timeout. For long-running feature builds, run from terminal instead"

This is the root cause of the "disjointed workflow" - users are forced out of Claude Code for execution.

### Iterative Development Principle

From task description:
> "I like to work iteratively and then test/verify the work done before moving on to keep the surface area/scope of the changes workable such that when there is an issue we can sensibly diagnose it."

This principle requires:
- Wave-by-wave execution with verification checkpoints
- Ability to pause, review, and continue
- Visibility into progress without switching contexts

---

## Next Steps

1. Review this revised report
2. Choose decision at checkpoint ([A]ccept/[R]evise/[I]mplement/[C]ancel)
3. If [I]mplement: Create 8 implementation tasks from recommendations
4. Execute in manageable waves with verification between each
