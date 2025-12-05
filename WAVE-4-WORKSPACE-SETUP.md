# Wave 4: Parallel Workspace Setup Guide

## Overview

This guide provides instructions for creating 4 parallel Conductor workspaces for TASK-PD-012 through TASK-PD-015 (template agent splits).

**Base Branch**: `progressive-disclosure` (commit 961c39f)
**Estimated Duration**: 2 days (0.5 days per task, all in parallel)

## Creating Workspaces via Conductor UI

Use Conductor's built-in workspace creation to ensure proper UI integration:

| Workspace Name | Base Branch | Task | Template |
|----------------|-------------|------|----------|
| **pd-react** | `progressive-disclosure` | TASK-PD-012 | react-typescript |
| **pd-fastapi** | `progressive-disclosure` | TASK-PD-013 | fastapi-python |
| **pd-nextjs** | `progressive-disclosure` | TASK-PD-014 | nextjs-fullstack |
| **pd-monorepo** | `progressive-disclosure` | TASK-PD-015 | react-fastapi-monorepo |

### Steps to Create Each Workspace

1. **Open Conductor UI** - Look for the sidebar workspace panel
2. **Click "+" button** - Add new workspace
3. **Configure workspace**:
   - **Name**: Use names from table above (e.g., `pd-react`)
   - **Base Branch**: Select `progressive-disclosure`
   - **Create Branch**: Conductor will create feature branch automatically
4. **Repeat** for all 4 workspaces

## Execution Commands

Each workspace can run independently in parallel. Open 4 terminal sessions:

### Workspace A: React TypeScript (TASK-PD-012)

```bash
# Open workspace 'pd-react' in Conductor UI
# Or navigate to it via terminal (path will vary based on Conductor setup)

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
# Open workspace 'pd-fastapi' in Conductor UI

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
# Open workspace 'pd-nextjs' in Conductor UI

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
# Open workspace 'pd-monorepo' in Conductor UI

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

### Option 1: Via Conductor UI (Recommended)

1. **Navigate to main workspace** (on `progressive-disclosure` branch)
2. **Use Conductor's merge UI** to merge each workspace branch:
   - Merge workspace `pd-react` → progressive-disclosure
   - Merge workspace `pd-fastapi` → progressive-disclosure
   - Merge workspace `pd-nextjs` → progressive-disclosure
   - Merge workspace `pd-monorepo` → progressive-disclosure
3. **Push to remote** via Conductor or command line
4. **Clean up workspaces** in Conductor UI if desired

### Option 2: Via Command Line

```bash
# Navigate to main repo
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Ensure we're on progressive-disclosure branch
git checkout progressive-disclosure

# Merge all 4 workspace branches (branch names created by Conductor)
# Note: Actual branch names may vary - check with: git branch -a
git merge <pd-react-branch-name> --no-ff -m "Merge TASK-PD-012: React TypeScript template agents split"
git merge <pd-fastapi-branch-name> --no-ff -m "Merge TASK-PD-013: FastAPI Python template agents split"
git merge <pd-nextjs-branch-name> --no-ff -m "Merge TASK-PD-014: Next.js Fullstack template agents split"
git merge <pd-monorepo-branch-name> --no-ff -m "Merge TASK-PD-015: React FastAPI Monorepo template agents split"

# Push to remote
git push origin progressive-disclosure
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
