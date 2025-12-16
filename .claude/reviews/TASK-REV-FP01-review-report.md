# Review Report: TASK-REV-FP01 (Final)

## Executive Summary

**FINDING: Monorepo Task Directory Detection Issue**

The `/feature-plan` command created files at the **wrong level** in a monorepo structure. Files were created in `guardkit-examples/tasks/` (root level) instead of `guardkit-examples/kartlog/tasks/` (project level).

## Final Decision: ABANDONED

**Decision Date:** 2025-12-15

After implementing partial fixes (TASK-FP-MONO-002, TASK-FP-MONO-004), the implementation was **abandoned** because:

1. **Scope creep**: The fix would need to apply to ALL task commands (`/task-create`, `/task-work`, `/task-review`, `/task-refine`, `/task-complete`), not just `/feature-plan`
2. **Effort vs value**: Estimated 15-20+ hours to fix properly across all commands
3. **Simpler alternatives exist**:
   - **Option A**: Document CLI limitation ("for monorepos, use `cd project && claude`")
   - **Option C**: Restructure `guardkit-examples` to not have root-level `.claude/` and `tasks/`

**Chosen approach**: Option A + Option C - document the limitation and restructure the example repo.

**The Real Problem:**
```
guardkit-examples/              (monorepo root)
├── .claude/                    (GuardKit config - at root)
├── tasks/                      ← FILES CREATED HERE (WRONG)
│   └── backlog/
│       └── pack-list-feature/  (7 files)
├── kartlog/                    (Svelte project)
│   ├── .claude/                (also has GuardKit config)
│   └── tasks/                  ← FILES SHOULD BE HERE
│       └── backlog/
└── fastapi-auth/               (FastAPI project - legacy)
    └── tasks/                  (has its own tasks from earlier test)
```

**Root Cause:** GuardKit doesn't properly detect which project's `tasks/` folder to use in a monorepo with nested `.claude/` configurations.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard (Revised)
- **Duration**: ~45 minutes
- **Task**: TASK-REV-FP01 - Analyze /feature-plan regression

## Findings

### Finding 1: Monorepo Structure Creates Ambiguity

**Current State:**
```
guardkit-examples/
├── .claude/                    ← GuardKit initialized at root
├── tasks/backlog/              ← Root-level tasks (where files went)
├── kartlog/
│   ├── .claude/                ← GuardKit ALSO initialized here
│   └── tasks/backlog/          ← kartlog-specific tasks (7 existing)
└── fastapi-auth/
    └── tasks/in_review/        ← Legacy tasks from earlier test
```

The monorepo has **two valid GuardKit configurations**, creating ambiguity about which `tasks/` folder should receive new files.

### Finding 2: The Explore Agent Used kartlog Context, But Files Went to Root

**Evidence from output capture:**
1. Explore agent correctly analyzed `kartlog/src/` directory
2. Review analyzed kartlog's Svelte/Firebase patterns
3. Recommendations were kartlog-specific (SMUI components, Firestore patterns)
4. **BUT:** `mkdir -p tasks/backlog/pack-list-feature` created at **root** level

The analysis was project-aware, but file creation was not.

### Finding 3: Inconsistent Task Location Strategy

**Current State:**
| Project | Has .claude/ | Has tasks/ | Example Task |
|---------|--------------|------------|--------------|
| guardkit-examples (root) | Yes | Yes | pack-list-feature (NEW - wrong location) |
| kartlog | Yes | Yes | TASK-SVELTE-COMPONEN-5521FA34.md |
| fastapi-auth | No | Yes | Tasks in in_review/ (legacy) |

There's no consistent strategy for where tasks should live in a monorepo.

### Finding 4: Clarification Integration Is NOT the Cause

The output capture confirms:
- Context A (Review Scope) completed successfully
- Context B (Implementation Preferences) completed successfully
- All file Write operations succeeded
- The issue is **where** files were created, not **whether** they were created

## Root Cause Summary

| Suspected Cause | Status | Evidence |
|----------------|--------|----------|
| Clarification integration regression | **RULED OUT** | Clarification completed, files created |
| File creation pipeline interrupted | **RULED OUT** | All files exist with correct content |
| Monorepo task directory detection | **CONFIRMED** | Files at root instead of kartlog/ |
| Missing project-level context awareness | **CONFIRMED** | Explore used kartlog, Write used root |

## Recommendations

### Option 1: Project-Relative Task Creation ~~(Recommended)~~ (NOT VIABLE)

When running `/feature-plan` from within a subdirectory (like kartlog/), detect and use that project's `tasks/` folder.

**Implementation:**
```bash
# Detect nearest tasks/ directory relative to cwd
if [ -d "./tasks" ]; then
  TASKS_DIR="./tasks"
elif [ -d "../tasks" ]; then
  TASKS_DIR="../tasks"
# ... etc
fi
```

**Why This Doesn't Work:**

| Context | cwd | Result |
|---------|-----|--------|
| CLI: `cd kartlog && claude` | `kartlog/` | Works - finds `kartlog/tasks/` |
| VS Code Extension | `guardkit-examples/` (root) | **FAILS** - finds root `tasks/` |

The VS Code Claude Code Extension opens at the **workspace root**, not the subdirectory. There's no facility to change the working directory within the extension.

**Evidence:**
- `/template-create` and `/agent-enhance` worked correctly when run from CLI after `cd kartlog`
- `/feature-plan` in VS Code Extension defaulted to root because cwd = workspace root

**Complexity:** 5/10
**Effort:** 2-4 hours
**Viability:** ❌ NOT VIABLE for VS Code Extension users

### Option 2: Explicit `--project` Flag (VIABLE)

Add a flag to specify which project in a monorepo:

```bash
/feature-plan "pack list feature" --project=kartlog
# Creates in: kartlog/tasks/backlog/pack-list-feature/
```

**Works in VS Code Extension:** ✅ Yes - user explicitly specifies target

**Pros:**
- Works regardless of cwd
- No ambiguity
- User knows exactly where files will go
- Simple implementation

**Cons:**
- Requires user to remember the flag
- Extra typing for every command

**Complexity:** 4/10
**Effort:** 2-3 hours
**Viability:** ✅ VIABLE for all contexts

### Option 3: Monorepo Configuration in Root CLAUDE.md

Add monorepo awareness to root `.claude/CLAUDE.md`:

```yaml
# In guardkit-examples/.claude/CLAUDE.md
monorepo:
  projects:
    - path: kartlog
      tasks_dir: kartlog/tasks
    - path: fastapi-auth
      tasks_dir: fastapi-auth/tasks
```

**Complexity:** 6/10
**Effort:** 4-6 hours

### Option 4: Interactive Project Selection (RECOMMENDED)

When multiple `tasks/` directories exist, prompt:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Multiple Task Directories Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found 3 possible task locations:
  [1] tasks/backlog/ (root)
  [2] kartlog/tasks/backlog/
  [3] fastapi-auth/tasks/backlog/

Which should receive the new tasks? [1/2/3]:
```

**Works in VS Code Extension:** ✅ Yes - prompts user interactively

**Pros:**
- Works regardless of cwd
- No extra flags to remember
- User sees all options and chooses explicitly
- Defensive - prevents accidental wrong location
- Aligns with existing clarification question patterns

**Cons:**
- Extra interaction step (but only in monorepos)
- Need to detect monorepo structure first

**Enhancement:** Could remember choice per session or save preference:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Multiple Task Directories Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found 3 possible task locations:
  [1] tasks/backlog/ (root)
  [2] kartlog/tasks/backlog/
  [3] fastapi-auth/tasks/backlog/

Which should receive the new tasks? [1/2/3]
(Tip: Use --project=kartlog to skip this prompt)
```

**Complexity:** 5/10
**Effort:** 2-3 hours
**Viability:** ✅ VIABLE and RECOMMENDED for all contexts

## Recommended Solution: Option 4 + Option 2 Combined

Given the VS Code Extension constraint (cwd = workspace root, not changeable):

1. **Primary:** Interactive project selection when multiple `tasks/` directories detected
2. **Override:** Support `--project=X` to skip prompt for power users
3. ~~**Default:** Use nearest `tasks/`~~ (NOT VIABLE in VS Code Extension)

## Decision Matrix (Revised)

| Option | Effort | Impact | VS Code Extension | Recommendation |
|--------|--------|--------|-------------------|----------------|
| 1. Project-relative | 2-4 hrs | High | ❌ NOT VIABLE | Skip |
| 2. --project flag | 2-3 hrs | Medium | ✅ Works | **Implement** |
| 3. Monorepo config | 4-6 hrs | High | ✅ Works | Defer |
| 4. Interactive selection | 2-3 hrs | High | ✅ Works | **Implement (Primary)** |

## Implementation Tasks

If choosing to implement the fix:

### TASK-FP-MONO-001: ~~Detect Nearest tasks/ Directory~~ (REMOVED)
~~- Implement project-relative task directory detection~~
~~- Use cwd as starting point, walk up to find tasks/~~
**Removed:** Not viable for VS Code Extension users where cwd = workspace root.

### Implementation Tasks: ABANDONED

The following tasks were partially implemented but then **discarded**:

- ~~TASK-FP-MONO-002: Interactive Selection~~ - Implemented but discarded
- ~~TASK-FP-MONO-003: --project Flag~~ - Not implemented
- ~~TASK-FP-MONO-004: Detection Utility~~ - Implemented but discarded

**Reason for abandonment**: Fixing only `/feature-plan` while leaving other task commands broken would create user confusion. A proper fix requires updating all task commands (15-20+ hours).

**Recommended alternatives**:
1. Document CLI workaround in CLAUDE.md
2. Restructure `guardkit-examples` to remove root-level ambiguity

## Appendix

### Directory Structure Evidence
```bash
# Root level (where files went)
guardkit-examples/tasks/backlog/pack-list-feature/
├── IMPLEMENTATION-GUIDE.md
├── README.md
└── TASK-PL-*.md (5 files)

# kartlog level (where files should have gone)
guardkit-examples/kartlog/tasks/backlog/
├── TASK-AI-LLM-FUNCTION-8F798186.md
├── TASK-FIRESTORE-REPOS-7B0501B8.md
└── ... (5 more existing tasks)
```

### Key Insight: VS Code Extension Constraint

The VS Code Claude Code Extension **always opens at the workspace root**. There is no facility to change the working directory within the extension. This means:

| Command Context | cwd | Implication |
|-----------------|-----|-------------|
| CLI: `cd kartlog && claude` | `kartlog/` | Can use cwd-relative detection |
| VS Code Extension | `guardkit-examples/` | **Must use interactive or explicit flag** |

This is why `/template-create` and `/agent-enhance` worked (run from CLI after `cd kartlog`) but `/feature-plan` failed (run from VS Code Extension).

### Conclusion

**This is a real issue** - not a false alarm. GuardKit's task commands lack proper monorepo awareness and create files at the wrong directory level when multiple `tasks/` directories exist.

**Final Resolution**: Rather than implementing a complex fix across all task commands:

1. **Document the CLI workaround**: "For monorepos, navigate to the project directory first: `cd project && claude`"
2. **Restructure guardkit-examples**: Remove root-level `.claude/` and `tasks/` to eliminate ambiguity

This is a **known limitation** of VS Code Extension usage in monorepos, not a bug requiring code changes.
