# FEAT-BOOT: Environment Bootstrap for AutoBuild

## Problem

AutoBuild's `_setup_phase()` creates a worktree but never installs the target project's dependencies. The Player masks this gap by incidentally installing packages during its 50-turn implementation session. The Coach's 1-turn verification session fails immediately when dependencies aren't available.

For greenfield projects (like FEAT-BA28), Wave 1 creates the dependency manifest but no inter-wave hook installs from it before Wave 2 launches.

**Evidence**: TASK-DB-003 stalls with `ModuleNotFoundError: No module named 'sqlalchemy'` across 3 identical Coach turns → `UNRECOVERABLE_STALL`.

## Solution

Add a `ProjectEnvironmentDetector` that scans the worktree for dependency manifests and runs appropriate install commands, integrated at two bootstrap points:
1. **Phase 1.5**: After worktree creation (for existing projects with dependencies)
2. **Inter-wave hook**: After each wave completes (for greenfield projects where Wave 1 creates the manifest)

Secondary fixes address conditional approval wiring, classification accuracy, and defence-in-depth for Coach test execution.

## Source Review

All tasks derive from: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3)

Parent review: TASK-REV-4D57

## Subtasks

| ID | Title | Priority | Wave | Complexity | Mode | Dependencies |
|----|-------|----------|------|------------|------|--------------|
| TASK-BOOT-E3C0 | ProjectEnvironmentDetector + bootstrap phase | P0 | 1 | 6 | task-work | — |
| TASK-BOOT-3CAF | Inter-wave bootstrap hook | P0 | 1 | 3 | task-work | E3C0 |
| TASK-BOOT-43DE | Coach subprocess with sys.executable | P1 | 2 | 3 | task-work | — |
| TASK-BOOT-214B | requires_infrastructure in FEAT-BA28 | P1 | 2 | 2 | direct | — |
| TASK-BOOT-6D85 | Wire _docker_available in task dict | P1 | 2 | 2 | task-work | — |
| TASK-BOOT-F9C4 | Service-client lib classification | P2 | 3 | 2 | task-work | — |
| TASK-BOOT-7369 | Diagnostic logging | P2 | 3 | 1 | direct | — |

## Open Design Decisions

- **Virtual environment policy**: v1 installs into current Python. See TASK-BOOT-E3C0 for risks and alternatives.
- **Monorepo depth**: v1 scans depth 1. Deeper structures are a documented limitation.
