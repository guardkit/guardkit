---
id: TASK-REV-TMPL-CMD
title: "Review: template-create Command Orchestrator Bypass Investigation"
status: review_complete
created: 2025-12-02T21:30:00Z
updated: 2025-12-02T22:45:00Z
priority: critical
task_type: review
tags: [template-create, regression, orchestrator, public-release-blocker]
related_tasks: [TASK-IMP-REVERT-V097, TASK-REV-TMPL-REGRESS, TASK-IMP-TMPL-FIX]
review_results:
  mode: decision
  depth: comprehensive
  findings_count: 5
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-TMPL-CMD-review-report.md
  implementation_task: TASK-IMP-TMPL-FIX
  completed_at: 2025-12-02T22:45:00Z
---

# Review Task: template-create Command Orchestrator Bypass Investigation

## CRITICAL CONTEXT

**This is a pre-release blocker.** The user is preparing for public release and these regressions are causing significant problems.

**IMPORTANT**: Before making ANY diagnosis or implementing fixes, the historical evolution of the template-create command and its related code MUST be reviewed thoroughly. This workflow was working reliably in previous versions (see TASK-IMP-REVERT-V097 for baseline reference).

## Problem Statement

When `/template-create` is invoked, Claude Code **completely bypasses the Python orchestrator** and manually creates template files by:
1. Reading source files directly with Read tool
2. Writing template files directly with Write tool
3. Never executing the `template_create_orchestrator.py` script

This defeats the entire checkpoint-resume architecture and AI analysis pipeline.

## Observed Symptoms

### Expected Behavior (Working in v0.97)
```
/template-create --name kartlog-test

⏺ Bash(PYTHONPATH="..." python3 .../template_create_orchestrator.py --path . --name kartlog-test)
  ⎿  INFO:installer.global.lib.codebase_analyzer.ai_analyzer:Analyzing codebase...
     INFO:lib.codebase_analyzer.stratified_sampler:Starting stratified sampling...
     ... orchestrator output ...
     Exit code: 42 (agent invocation needed)

⏺ Read(.agent-request.json)
⏺ Task(architectural-reviewer agent...)
⏺ Write(.agent-response.json)
⏺ Bash(python3 ... --resume)
  ⎿  ... continues processing ...
     Template created with 90%+ confidence
```

### Actual Behavior (Current)
```
/template-create --name kartlog-test

⏺ Bash(ls -la ~/.agentecflow)  # Just checking paths
⏺ Read(package.json)           # Manually reading files!
⏺ Read(src/App.svelte)         # More manual reading
⏺ Read(src/lib/stores.js)      # Not using orchestrator
⏺ Write(~/.agentecflow/templates/kartlog-test/manifest.json)  # Manual creation!
⏺ Write(~/.agentecflow/templates/kartlog-test/CLAUDE.md)      # Manual creation!
  ⎿  Template created with 68% confidence (heuristic fallback)
```

### Key Differences
| Aspect | Expected (v0.97) | Actual (Current) |
|--------|------------------|------------------|
| Orchestrator invoked | Yes (via Bash) | No |
| AI analysis used | Yes (architectural-reviewer) | No (manual analysis) |
| Checkpoint-resume | Yes (exit 42 pattern) | No |
| Confidence score | 90%+ | 68% (heuristic fallback) |
| Agent generation | AI-powered (7-8 agents) | Manual (2 agents) |

## Initial Analysis Findings

### Hypothesis 1: Command File Instructions Unclear

The `template-create.md` command file (1656 lines) may not have clear enough instructions telling Claude to run the Python orchestrator.

**Evidence reviewed**:
- Lines 1119-1147: "Execution" section describes args and command building
- Lines 1149-1154: Says "Execute orchestrator in a loop" but implementation is Python pseudocode
- Lines 1649-1654: Actual command is buried at the very end
- No explicit "CRITICAL: YOU MUST RUN THIS COMMAND" instruction found

**BUT**: This needs historical verification - was this section changed during recent commits?

### Hypothesis 2: Bridge Invoker Not Passed Correctly

A bug was identified where `bridge_invoker` wasn't passed to `ArchitecturalReviewerInvoker`:

```python
# Line 86 of ai_analyzer.py (before fix):
self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker()

# After fix (commit 93955e7):
self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker(bridge_invoker=bridge_invoker)
```

**Status**: This fix was applied and pushed, but it only fixes the AI analysis fallback - it doesn't explain why Claude bypasses the orchestrator entirely.

### Hypothesis 3: Installation/Symlink Issues

The symlink at `~/.agentecflow/bin/template-create-orchestrator` may not exist or may not be discoverable by Claude.

**Needs verification**:
```bash
ls -la ~/.agentecflow/bin/template-create-orchestrator
readlink ~/.agentecflow/bin/template-create-orchestrator
```

## REQUIRED INVESTIGATION (Before Any Fix)

### 1. Historical Git Analysis

Review the git history of these files to understand what changed:

```bash
# Command file history
git log --oneline -20 -- installer/global/commands/template-create.md

# Check when "Execution" section was added/modified
git log -p -- installer/global/commands/template-create.md | grep -A 50 "## Execution"

# Orchestrator history
git log --oneline -20 -- installer/global/commands/lib/template_create_orchestrator.py

# Check v0.97 baseline (commit 6c651a3)
git show 6c651a3:installer/global/commands/template-create.md | grep -A 50 "## Execution"
```

### 2. Verify v0.97 Working State

The v0.97 baseline (commit 6c651a3) was confirmed working. Need to understand:
- What did the template-create.md file look like then?
- What instructions did it give Claude?
- How did Claude know to run the orchestrator?

### 3. Compare Current vs v0.97

```bash
# Diff the command file
git diff 6c651a3..HEAD -- installer/global/commands/template-create.md

# Check if Execution section was modified
git diff 6c651a3..HEAD -- installer/global/commands/template-create.md | grep -A 20 "Execution"
```

### 4. Check Other Slash Commands That Work

Review other commands that successfully invoke Python scripts to understand the pattern:
- `/agent-enhance` - Does it invoke Python correctly?
- `/task-work` - How does it invoke the orchestrator?

What's different about template-create?

## Files to Review

| File | Purpose | Check For |
|------|---------|-----------|
| `installer/global/commands/template-create.md` | Command spec | Instructions for orchestrator invocation |
| `installer/global/commands/lib/template_create_orchestrator.py` | Main script | Entry point and arg handling |
| `installer/global/lib/codebase_analyzer/ai_analyzer.py` | AI analysis | Bridge invoker integration |
| `installer/global/lib/agent_bridge/invoker.py` | Agent bridge | Checkpoint-resume pattern |
| `installer/scripts/install.sh` | Installation | Symlink creation |

## Related Tasks

- **TASK-IMP-REVERT-V097**: Reverted to v0.97 baseline and selectively re-applied improvements
- **TASK-REV-TMPL-REGRESS**: Parent review task for template-create regressions

## Potential Fixes (DO NOT IMPLEMENT UNTIL INVESTIGATION COMPLETE)

### Option A: Add CRITICAL Section to Command File

Add explicit instructions at the start of the Execution section:

```markdown
## Execution

### CRITICAL: ORCHESTRATOR REQUIRED

**YOU MUST RUN THE PYTHON ORCHESTRATOR. DO NOT MANUALLY CREATE TEMPLATES.**

Execute this command via Bash:
\`\`\`bash
python3 ~/.agentecflow/bin/template-create-orchestrator [args]
\`\`\`
```

**Risk**: May not be the root cause. Historical analysis needed first.

### Option B: Revert Command File to v0.97

If the command file was modified since v0.97, consider reverting it:

```bash
git checkout 6c651a3 -- installer/global/commands/template-create.md
```

**Risk**: May lose valid improvements. Need to understand what changed.

### Option C: Fix Installation/Symlink Discovery

Ensure the symlink is created correctly and discoverable:

```bash
# In install.sh
ln -sf "$TASKWRIGHT_PATH/installer/global/commands/lib/template_create_orchestrator.py" \
       "$HOME/.agentecflow/bin/template-create-orchestrator"
```

**Risk**: May not be the root cause if Claude isn't looking for symlinks.

## Acceptance Criteria

1. [ ] Historical analysis of template-create.md completed (git log, diff vs v0.97)
2. [ ] Root cause identified with evidence from git history
3. [ ] Comparison with other working slash commands documented
4. [ ] Minimal fix scope defined (no speculative changes)
5. [ ] Fix tested on clean VM installation
6. [ ] Confidence score returns to 90%+ (not 68% heuristic fallback)
7. [ ] Orchestrator is invoked (not manual file creation)

## Review Mode

- **Mode**: `decision` (need to choose correct fix approach)
- **Depth**: `comprehensive` (pre-release blocker, need thorough analysis)

## Notes

**From User**: "I am trying to prepare for public release and these regressions are a big problem"

This is a critical path issue. The template-create command is a core feature of Taskwright and must work correctly before public release. Adhoc fixes have already caused regressions - thorough investigation is required before any changes.

## Next Steps

1. Assign this review task
2. Complete historical investigation (see "REQUIRED INVESTIGATION" section)
3. Document findings with evidence
4. Propose minimal-scope fix
5. Get approval before implementing
6. Test on clean VM
7. Only then merge to main
