# Implementation Guide: CLAUDE.md Size Optimization

## Execution Strategy

All 5 tasks can be executed in **parallel** - they modify different sections of CLAUDE.md with no conflicts.

## Wave 1 (All Tasks - Parallel)

| Task | Section | Method | Workspace |
|------|---------|--------|-----------|
| TASK-OPT-8085.1 | Core AI Agents | direct | claude-md-opt-wave1-1 |
| TASK-OPT-8085.2 | BDD Workflow | direct | claude-md-opt-wave1-2 |
| TASK-OPT-8085.3 | Boundaries | direct | claude-md-opt-wave1-3 |
| TASK-OPT-8085.4 | Clarifying Questions | task-work | claude-md-opt-wave1-4 |
| TASK-OPT-8085.5 | Incremental Enhancement | direct | claude-md-opt-wave1-5 |

## Task Details

### TASK-OPT-8085.1: Core AI Agents (4,696 char savings)
- **Method**: Direct edit
- **Action**: Replace 5,496 char section with ~800 char summary + link
- **Target**: `docs/guides/agent-discovery-guide.md`

### TASK-OPT-8085.2: BDD Workflow (4,240 char savings)
- **Method**: Direct edit
- **Action**: Replace 4,740 char section with ~500 char summary + link
- **Target**: `docs/guides/bdd-workflow-for-agentic-systems.md`

### TASK-OPT-8085.3: Boundaries (3,490 char savings)
- **Method**: Direct edit
- **Action**: Consolidate 2 sections (4,690 chars) into 1 (~1,200 chars)
- **Target**: Internal consolidation

### TASK-OPT-8085.4: Clarifying Questions (3,068 char savings)
- **Method**: task-work (creates new file)
- **Action**: Create `.claude/rules/clarifying-questions.md`, reduce CLAUDE.md section
- **Target**: `.claude/rules/clarifying-questions.md`

### TASK-OPT-8085.5: Incremental Enhancement (2,943 char savings)
- **Method**: Direct edit
- **Action**: Replace 3,343 char section with ~400 char summary + link
- **Target**: `docs/workflows/incremental-enhancement-workflow.md`

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| CLAUDE.md size | 57,821 chars | ~39,384 chars |
| Threshold | 40,000 chars | 40,000 chars |
| Status | ❌ Over | ✅ Under |

## Verification Checklist

After all tasks complete:

- [ ] Run `wc -c CLAUDE.md` - should be < 40,000
- [ ] Start Claude Code in guardkit directory - no size warning
- [ ] Verify all "See:" links resolve to valid files
- [ ] Verify no duplicate ## headings (especially Boundaries)

## Rollback

If issues occur, git revert the commits:

```bash
git log --oneline -10  # Find optimization commits
git revert <commit-hash>
```
