---
id: TASK-PD-010
title: Run split-agent.py --all-global (14 agents)
status: completed
created: 2025-12-03 16:00:00+00:00
updated: '2025-12-05T16:48:09.331730Z'
completed: '2025-12-05T16:48:09.330460Z'
priority: high
tags:
- progressive-disclosure
- phase-3
- execution
- global-agents
complexity: 4
estimated_hours: 8
actual_hours: 0.25
blocked_by:
- TASK-PD-009
blocks:
- TASK-PD-011
review_task: TASK-REV-426C
completed_location: tasks/completed/TASK-PD-010/
organized_files:
- TASK-PD-010.md
- completion-summary.md
test_results:
  status: passed
  coverage: 100
  last_run: 2025-12-05 16:00:00+00:00
  agents_processed: 14
  agents_failed: 0
  verification_passed: true
---


# Task: Run split-agent.py --all-global (19 agents)

## Phase

**Phase 3: Automated Global Agent Migration**

## Description

Execute the automated splitter on all 19 global agents to convert them to progressive disclosure format.

## Pre-Execution Checklist

Before running batch split:

- [ ] TASK-PD-008 complete (script created)
- [ ] TASK-PD-009 complete (rules defined)
- [ ] Dry run executed successfully
- [ ] First 3 agents split manually and validated
- [ ] Git commit of current state (for rollback)

## Execution Steps

### Step 1: Dry Run (Preview)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Preview all splits
python3 scripts/split-agent.py --dry-run --all-global

# Review output for each agent:
# - Original size
# - Projected core size
# - Projected extended size
# - Reduction percentage
# - Sections to be moved
```

### Step 2: Manual Validation (First 3 Agents)

Split and manually validate the 3 largest agents:

```bash
# Split task-manager (72KB - largest)
python3 scripts/split-agent.py --agent installer/core/agents/task-manager.md

# Manually review:
cat installer/core/agents/task-manager.md | head -100
cat installer/core/agents/task-manager-ext.md | head -50

# Verify:
# - Frontmatter intact
# - Boundaries in core
# - Examples in extended
# - Loading instruction present

# Repeat for devops-specialist (57KB)
python3 scripts/split-agent.py --agent installer/core/agents/devops-specialist.md

# Repeat for git-workflow-manager (50KB)
python3 scripts/split-agent.py --agent installer/core/agents/git-workflow-manager.md
```

### Step 3: Execute Full Batch

```bash
# Commit current state for rollback
git add -A
git commit -m "Pre-split backup: 19 global agents"

# Execute split on all remaining agents
python3 scripts/split-agent.py --all-global

# Review summary output
```

### Step 4: Post-Execution Verification

```bash
# Count files
ls installer/core/agents/*.md | wc -l
# Should be 38 (19 core + 19 extended)

# Verify no -ext in discovery
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/core/lib')
from agent_scanner import AgentScanner
scanner = AgentScanner()
agents = scanner.scan_agents(Path('installer/core/agents'))
print(f'Discovered agents: {len(agents)}')
for a in agents:
    if '-ext' in a.name:
        print(f'ERROR: Extended file in discovery: {a.name}')
"
# Should show 19 agents, no -ext files

# Check total sizes
du -sh installer/core/agents/
# Note total size (should be similar to before)

# Check core sizes average
python3 -c "
from pathlib import Path
sizes = []
for f in Path('installer/core/agents').glob('*.md'):
    if not f.stem.endswith('-ext'):
        sizes.append(f.stat().st_size)
avg = sum(sizes) / len(sizes)
print(f'Average core size: {avg/1024:.1f}KB')
print(f'Max core size: {max(sizes)/1024:.1f}KB')
"
# Average should be ~15KB, max should be ≤20KB
```

## Agents to Split (19 total)

| Agent | Original Size | Target Core | Notes |
|-------|--------------|-------------|-------|
| task-manager.md | 72KB | ~25KB | Largest, complex |
| zeplin-maui-orchestrator.md | 65KB | ~20KB | Design integration |
| devops-specialist.md | 57KB | ~18KB | Infrastructure |
| git-workflow-manager.md | 50KB | ~16KB | Git operations |
| security-specialist.md | 48KB | ~15KB | Security |
| database-specialist.md | 46KB | ~15KB | Database |
| architectural-reviewer.md | 44KB | ~14KB | SOLID/DRY |
| agent-content-enhancer.md | 33KB | ~12KB | Enhancement |
| debugging-specialist.md | 29KB | ~10KB | Debug |
| code-reviewer.md | 29KB | ~10KB | Review |
| test-verifier.md | 28KB | ~10KB | Testing |
| test-orchestrator.md | 26KB | ~9KB | Testing |
| pattern-advisor.md | 25KB | ~9KB | Patterns |
| figma-react-orchestrator.md | 25KB | ~9KB | Design |
| complexity-evaluator.md | 18KB | ~8KB | Complexity |
| build-validator.md | 17KB | ~7KB | Build |
| react-state-specialist.md | 14KB | ~6KB | React |
| dotnet-domain-specialist.md | 12KB | ~5KB | .NET |
| python-api-specialist.md | 12KB | ~5KB | Python |

## Acceptance Criteria

- [ ] Dry run shows all 19 agents can be split
- [ ] First 3 largest agents manually validated
- [ ] All 19 agents split successfully
- [ ] 38 files exist (19 core + 19 extended)
- [ ] Discovery shows only 19 agents (no -ext)
- [ ] Average core size ≤15KB
- [ ] All core files have loading instruction
- [ ] All extended files have header
- [ ] No content loss (core + ext ≈ original)

## Rollback Plan

If issues discovered:

```bash
# Restore from backup files
for f in installer/core/agents/*.md.bak; do
    mv "$f" "${f%.bak}"
done

# Remove extended files
rm installer/core/agents/*-ext.md

# Or restore from git
git checkout HEAD -- installer/core/agents/
```

## Estimated Effort

**1 day** (including validation)

## Dependencies

- TASK-PD-009 (categorization rules)

## Output

After completion:
- 19 core agent files (reduced size)
- 19 extended agent files (detailed content)
- Backup files (.md.bak)
- Split summary report
