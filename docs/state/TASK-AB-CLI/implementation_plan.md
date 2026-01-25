# Implementation Plan: TASK-AB-CLI

## Package guardkit as installable Python package

### Summary

Create a proper Python package for guardkit so the CLI can be invoked reliably via `pip install -e .`

### Files to Create

1. **pyproject.toml** - Package definition with hatchling backend
2. **guardkit/worktrees/__init__.py** - Consolidated worktree module (moved from installer)
3. **guardkit/worktrees/manager.py** - WorktreeManager class

### Files to Modify

1. **guardkit/__init__.py** - Version consolidation (single source of truth)
2. **guardkit/cli/__init__.py** - Import version from parent package
3. **guardkit/orchestrator/autobuild.py** - Update imports from guardkit.worktrees
4. **guardkit/cli/autobuild.py** - Update imports from guardkit.worktrees
5. **installer/scripts/install.sh** - Add pip install step

### Implementation Phases

1. Phase 1: Create pyproject.toml (30 min)
2. Phase 2: Consolidate worktree module (45 min)
3. Phase 3: Version consolidation (15 min)
4. Phase 4: Update installer script (30 min)
5. Phase 5: Update tests (30 min)

### Dependencies

Core:
- click>=8.0.0
- rich>=13.0.0
- pyyaml>=6.0.0
- python-frontmatter>=1.0.0

AutoBuild:
- claude-agent-sdk>=0.1.0

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import path conflicts | Medium | High | Consolidate worktree module |
| claude-agent-sdk not available | High | Medium | Optional dependency with fallback |
| Breaking existing tests | Medium | Medium | Update imports in tests |

### Acceptance Criteria

- [ ] pyproject.toml created with proper package definition
- [ ] pip install -e . works from guardkit repo
- [ ] guardkit-py autobuild --help works after pip install
- [ ] Installer runs pip install during setup
- [ ] guardkit autobuild task TASK-XXX works end-to-end
- [ ] Works on fresh machine

### Architectural Review Score

- SOLID: 64/100
- DRY: 72/100
- YAGNI: 72/100
- Overall: 68/100 (Approved with recommendations)

### Key Recommendations Applied

1. Consolidate worktree module into guardkit package
2. Single source of truth for version
3. Keep claude-agent-sdk as optional (fallback already exists)

### Estimated Duration

4.5 hours total
