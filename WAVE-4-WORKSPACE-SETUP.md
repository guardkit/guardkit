# Wave 4: Parallel Workspace Setup Complete ✅

## Overview

4 Conductor workspaces have been created for parallel execution of TASK-PD-012 through TASK-PD-015 (template agent splits).

**Created**: 2025-12-05
**Base Branch**: `progressive-disclosure` (commit 961c39f)
**Estimated Duration**: 2 days (0.5 days per task, all in parallel)

## Workspace Details

| Workspace | Location | Branch | Task | Template |
|-----------|----------|--------|------|----------|
| **A** | `.conductor/pd-react` | `pd-react-typescript` | TASK-PD-012 | react-typescript |
| **B** | `.conductor/pd-fastapi` | `pd-fastapi-python` | TASK-PD-013 | fastapi-python |
| **C** | `.conductor/pd-nextjs` | `pd-nextjs-fullstack` | TASK-PD-014 | nextjs-fullstack |
| **D** | `.conductor/pd-monorepo` | `pd-react-fastapi-monorepo` | TASK-PD-015 | react-fastapi-monorepo |

## Execution Commands

Each workspace can run independently in parallel. Open 4 terminal sessions:

### Workspace A: React TypeScript (TASK-PD-012)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/pd-react

# Check template agents
ls -la installer/global/templates/react-typescript/agents/*.md

# Dry run first
python3 scripts/split_agent.py --dry-run --template react-typescript

# Execute split
python3 scripts/split_agent.py --template react-typescript

# Verify results
ls -la installer/global/templates/react-typescript/agents/*.md | wc -l
# Should show: original + core + extended + backups

# Commit changes
git add -A
git commit -m "TASK-PD-012: Split react-typescript template agents (progressive disclosure)"
```

### Workspace B: FastAPI Python (TASK-PD-013)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/pd-fastapi

# Check template agents
ls -la installer/global/templates/fastapi-python/agents/*.md

# Dry run first
python3 scripts/split_agent.py --dry-run --template fastapi-python

# Execute split
python3 scripts/split_agent.py --template fastapi-python

# Verify results
ls -la installer/global/templates/fastapi-python/agents/*.md | wc -l

# Commit changes
git add -A
git commit -m "TASK-PD-013: Split fastapi-python template agents (progressive disclosure)"
```

### Workspace C: Next.js Fullstack (TASK-PD-014)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/pd-nextjs

# Check template agents
ls -la installer/global/templates/nextjs-fullstack/agents/*.md

# Dry run first
python3 scripts/split_agent.py --dry-run --template nextjs-fullstack

# Execute split
python3 scripts/split_agent.py --template nextjs-fullstack

# Verify results
ls -la installer/global/templates/nextjs-fullstack/agents/*.md | wc -l

# Commit changes
git add -A
git commit -m "TASK-PD-014: Split nextjs-fullstack template agents (progressive disclosure)"
```

### Workspace D: React FastAPI Monorepo (TASK-PD-015)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/pd-monorepo

# Check template agents
ls -la installer/global/templates/react-fastapi-monorepo/agents/*.md

# Dry run first
python3 scripts/split_agent.py --dry-run --template react-fastapi-monorepo

# Execute split
python3 scripts/split_agent.py --template react-fastapi-monorepo

# Verify results
ls -la installer/global/templates/react-fastapi-monorepo/agents/*.md | wc -l

# Commit changes
git add -A
git commit -m "TASK-PD-015: Split react-fastapi-monorepo template agents (progressive disclosure)"
```

## Merge Strategy

After all 4 workspaces complete their tasks:

```bash
# Return to main repo
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Ensure we're on progressive-disclosure branch
git checkout progressive-disclosure

# Merge all 4 workspace branches (no fast-forward for clean history)
git merge pd-react-typescript --no-ff -m "Merge TASK-PD-012: React TypeScript template agents split"
git merge pd-fastapi-python --no-ff -m "Merge TASK-PD-013: FastAPI Python template agents split"
git merge pd-nextjs-fullstack --no-ff -m "Merge TASK-PD-014: Next.js Fullstack template agents split"
git merge pd-react-fastapi-monorepo --no-ff -m "Merge TASK-PD-015: React FastAPI Monorepo template agents split"

# Push to remote
git push origin progressive-disclosure

# Clean up worktrees (optional - can keep for future work)
git worktree remove .conductor/pd-react
git worktree remove .conductor/pd-fastapi
git worktree remove .conductor/pd-nextjs
git worktree remove .conductor/pd-monorepo

# Delete local branches (optional)
git branch -d pd-react-typescript
git branch -d pd-fastapi-python
git branch -d pd-nextjs-fullstack
git branch -d pd-react-fastapi-monorepo
```

## Validation Checklist

After merging all 4 branches, verify:

- [ ] All template agent directories have core + extended files
- [ ] No merge conflicts (should be clean - all templates modify different directories)
- [ ] Backup files (.bak) exist for all original agent files
- [ ] Agent discovery excludes `-ext.md` files
- [ ] All commits have clear messages

## Expected Results

**Per Template**:
- Original agent files backed up (*.md.bak)
- Core agent files (reduced size, with loading instructions)
- Extended agent files (detailed content, with headers)
- Total file count increase: +2 files per agent (+1 extended, +1 backup)

**Overall**:
- All 4 template agent sets migrated to progressive disclosure
- Clean merge history (4 merge commits on progressive-disclosure branch)
- Ready for Wave 5 (validation & documentation)

## Troubleshooting

**Issue**: `--template` flag not recognized
**Solution**: The script needs to be updated to support `--template` flag. Check `scripts/split_agent.py` for CLI argument parsing.

**Issue**: Merge conflicts during final merge
**Solution**: Should not happen - each workspace modifies different template directories. If conflicts occur, review file paths.

**Issue**: Agent discovery still finds `-ext.md` files
**Solution**: Verify TASK-PD-004 completed successfully (agent_scanner.py excludes `-ext` pattern).

## Notes

- **Conservative Categorization**: Same philosophy as global agents (core = decision-making, extended = implementation details)
- **Overhead Expected**: Small file size overhead (~1-2%) due to loading instructions and headers
- **Reduction Targets**: Aspirational 40-50% reduction may not be achieved initially due to limited extended content
- **Parallel Safety**: Each workspace modifies different directories, ensuring zero merge conflicts

## Next Steps

After Wave 4 completion:

1. **Validation**: Run validation checks on all split template agents
2. **Wave 5**: Begin TASK-PD-016 (template validation update) and TASK-PD-017 (CLAUDE.md docs) in parallel
3. **Final Integration**: TASK-PD-018 (command docs) and TASK-PD-019 (full integration testing)

---

**Status**: ✅ Workspaces created and ready for parallel execution
**Dependencies**: All prior tasks (PD-000 through PD-011) completed
**Blocks**: TASK-PD-016 through TASK-PD-019 (Wave 5)
