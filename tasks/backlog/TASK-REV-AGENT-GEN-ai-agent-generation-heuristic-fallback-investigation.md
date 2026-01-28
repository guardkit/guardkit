---
id: TASK-REV-AGENT-GEN
title: "Review: AI Agent Generation Heuristic Fallback Investigation"
status: backlog
created: 2025-12-03T07:15:00Z
updated: 2025-12-03T07:15:00Z
priority: critical
task_type: review
tags: [template-create, ai-analysis, agent-generation, heuristic-fallback, pre-release-blocker]
related_tasks: [TASK-REV-TMPL-CMD, TASK-IMP-TMPL-FIX, TASK-IMP-REVERT-V097]
---

# Review Task: AI Agent Generation Heuristic Fallback Investigation

## CRITICAL CONTEXT

**This is a pre-release blocker.** The previous fix (TASK-IMP-TMPL-FIX) resolved the orchestrator bypass issue, but `/template-create` is still not using AI to generate specialized agents - it's falling back to heuristic-based generation with lower quality output.

**Related Tasks**:
- **TASK-REV-TMPL-CMD**: Identified orchestrator bypass (pseudocode in command file)
- **TASK-IMP-TMPL-FIX**: Fixed orchestrator bypass by removing pseudocode (commit 773f534)
- **TASK-IMP-REVERT-V097**: Baseline reference for working v0.97 behavior

## Problem Statement

When `/template-create` runs, the system is:
1. ✅ Invoking the Python orchestrator correctly (fix from TASK-IMP-TMPL-FIX working)
2. ❌ **NOT** using AI analysis via architectural-reviewer agent for agent generation
3. ❌ Falling back to heuristic-based agent generation with reduced quality

### Observed Symptoms

**Evidence from User's `/template-create` Run**:

The command output shows Claude:
- Manually reading files (`Read(package.json)`, `Read(src/lib/stores.js)`, etc.)
- Manually creating template files (`Write(~/.agentecflow/templates/svelte-firebase-spa/manifest.json)`)
- Generating only 3 agents (heuristic pattern) instead of 7-8 (AI analysis)

**Expected Behavior (AI Analysis)**:
```
⏺ Bash(PYTHONPATH="..." python3 .../template_create_orchestrator.py --path . --name test)
  ⎿  INFO:lib.codebase_analyzer.ai_analyzer:Analyzing codebase...
     INFO:lib.codebase_analyzer.stratified_sampler:Starting stratified sampling...
     Exit code: 42 (agent invocation needed)

⏺ Read(.agent-request.json)
⏺ Task(architectural-reviewer agent...)  # ← AI ANALYSIS HERE
⏺ Write(.agent-response.json)
⏺ Bash(python3 ... --resume)
  ⎿  Template created with 90%+ confidence
     Agents generated: 7-8 (AI-powered)
```

**Actual Behavior (Heuristic Fallback)**:
```
⏺ Bash(ls -la ...)
⏺ Read(package.json)           # Manual file reading
⏺ Read(src/lib/stores.js)      # More manual reading
⏺ Write(manifest.json)          # Manual creation
⏺ Write(agents/svelte-firebase-crud-specialist.md)  # Heuristic agent
⏺ Write(agents/svelte-smui-component-specialist.md) # Heuristic agent
⏺ Write(agents/firebase-security-specialist.md)     # Heuristic agent
  ⎿  Template created with ~68% confidence (heuristic)
     Agents generated: 3 (heuristic-based)
```

### Key Differences

| Aspect | Expected (AI) | Actual (Heuristic) |
|--------|---------------|-------------------|
| Agent count | 7-8 | 3 |
| Analysis method | architectural-reviewer via Task tool | Manual file reads |
| Confidence score | 90%+ | ~68% |
| Exit code 42 | Yes (agent bridge) | Not seen |
| Agent quality | AI-inferred capabilities | Pattern-matched keywords |

## Initial Hypotheses

### Hypothesis 1: AI Analyzer Not Being Invoked

The `CodebaseAnalyzer` in `lib/codebase_analyzer/ai_analyzer.py` may not be invoking the AI analysis path:

**Files to investigate**:
- `installer/core/lib/codebase_analyzer/ai_analyzer.py` - Lines 80-100 (agent_invoker initialization)
- `installer/core/lib/agent_bridge/invoker.py` - Bridge invoker integration

**Known previous issue** (commit 93955e7):
```python
# BEFORE (broken):
self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker()

# AFTER (fixed):
self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker(bridge_invoker=bridge_invoker)
```

This was fixed, but there may be another issue in the call chain.

### Hypothesis 2: Agent Bridge Not Writing Exit Code 42

The agent bridge pattern requires exit code 42 to signal "agent invocation needed". If this isn't happening:
- The orchestrator continues without AI analysis
- Falls back to heuristic generation

**Files to investigate**:
- `installer/core/commands/lib/template_create_orchestrator.py` - Exit code handling
- `installer/core/lib/agent_bridge/invoker.py` - Exit code 42 generation
- `installer/core/lib/agent_bridge/state_manager.py` - State persistence

### Hypothesis 3: Environment/Path Issues

The orchestrator may not be finding required modules or configurations:
- PYTHONPATH not set correctly
- Module imports failing silently
- Fallback to heuristic when AI import fails

**Files to investigate**:
- `installer/core/commands/lib/template_create_orchestrator.py` - Lines 20-60 (imports)
- `installer/scripts/install.sh` - Symlink creation

### Hypothesis 4: Agent Response Not Being Processed

If the orchestrator runs but doesn't process the agent response correctly:
- AI analysis runs
- Response written to `.agent-response.json`
- But orchestrator doesn't read/use it

**Files to investigate**:
- `installer/core/commands/lib/template_create_orchestrator.py` - `--resume` handling
- `.agent-response.json` format validation

## REQUIRED INVESTIGATION

### Phase 1: Add Diagnostic Logging

Add comprehensive logging to trace the execution path:

```python
# In template_create_orchestrator.py (entry point)
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('template_create_orchestrator')

logger.debug(f"Starting orchestrator with args: {sys.argv}")
logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
logger.debug(f"Working directory: {os.getcwd()}")
```

```python
# In ai_analyzer.py (AI analysis entry)
logger = logging.getLogger('ai_analyzer')

logger.debug(f"CodebaseAnalyzer initialized")
logger.debug(f"agent_invoker type: {type(self.agent_invoker)}")
logger.debug(f"bridge_invoker: {self.bridge_invoker}")

# Before AI invocation
logger.info(f"Invoking architectural-reviewer for codebase analysis")

# After AI invocation (or fallback)
logger.info(f"Analysis complete - method: {'AI' if used_ai else 'heuristic'}")
```

```python
# In invoker.py (agent bridge)
logger = logging.getLogger('agent_bridge.invoker')

logger.debug(f"AgentBridgeInvoker.invoke() called")
logger.debug(f"Writing .agent-request.json")
logger.info(f"Exiting with code 42 (agent invocation needed)")

# After resume
logger.debug(f"Processing .agent-response.json")
logger.debug(f"Response status: {response.get('status')}")
```

### Phase 2: Trace Execution Path

Run `/template-create` with logging and capture:

1. **Does CodebaseAnalyzer initialize correctly?**
   - Check `agent_invoker` is not None
   - Check `bridge_invoker` is passed correctly

2. **Does AI invocation path get triggered?**
   - Look for "Invoking architectural-reviewer" log
   - If not seen, identify where the path diverges

3. **Does exit code 42 get generated?**
   - Look for "Exiting with code 42" log
   - If not seen, identify why bridge invoker isn't called

4. **Does the orchestrator handle agent response?**
   - Look for "Processing .agent-response.json" log
   - If not seen, identify why `--resume` isn't working

### Phase 3: Compare with Working v0.97

Reference commit 6c651a3 (v0.97 baseline) and compare:

```bash
# Diff the key files
git diff 6c651a3..HEAD -- installer/core/lib/codebase_analyzer/ai_analyzer.py
git diff 6c651a3..HEAD -- installer/core/lib/agent_bridge/invoker.py
git diff 6c651a3..HEAD -- installer/core/commands/lib/template_create_orchestrator.py
```

### Phase 4: Test with Isolated Components

1. **Test AI analyzer directly**:
   ```python
   from installer.core.lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer
   analyzer = CodebaseAnalyzer(path="./test-project")
   result = analyzer.analyze()
   print(f"Method used: {result.method}")  # Should be 'ai', not 'heuristic'
   ```

2. **Test agent bridge directly**:
   ```python
   from installer.core.lib.agent_bridge.invoker import AgentBridgeInvoker
   invoker = AgentBridgeInvoker()
   # Should write .agent-request.json and return exit code 42
   ```

## Files to Review

| File | Purpose | Check For |
|------|---------|-----------|
| `installer/core/commands/lib/template_create_orchestrator.py` | Main orchestrator | AI vs heuristic branching |
| `installer/core/lib/codebase_analyzer/ai_analyzer.py` | AI analysis | Agent invoker initialization |
| `installer/core/lib/agent_bridge/invoker.py` | Bridge pattern | Exit code 42 generation |
| `installer/core/lib/agent_bridge/state_manager.py` | State persistence | Request/response handling |
| `installer/core/agents/architectural-reviewer.md` | Agent definition | Invocation requirements |

## Acceptance Criteria

1. [ ] Diagnostic logging added to all key code paths
2. [ ] Root cause identified with evidence from logs
3. [ ] Execution path documented (AI vs heuristic decision point)
4. [ ] Comparison with v0.97 baseline documented
5. [ ] Minimal fix scope defined (no speculative changes)
6. [ ] Fix tested - AI analysis invoked (not heuristic)
7. [ ] Agent count returns to 7-8 (not 3)
8. [ ] Confidence score returns to 90%+ (not 68%)

## Review Mode

- **Mode**: `decision` (need to choose correct fix approach)
- **Depth**: `comprehensive` (pre-release blocker, need thorough analysis)

## Notes

**From User**: This is the second issue with `/template-create` discovered during pre-release testing. The first issue (orchestrator bypass) was fixed in TASK-IMP-TMPL-FIX, but the AI agent generation is still not working correctly.

**Scope Warning**: The fix for TASK-IMP-TMPL-FIX was intentionally minimal (530 lines removed). This investigation should similarly result in a minimal, targeted fix to avoid new regressions.

## Next Steps

1. Assign this review task
2. Add diagnostic logging (see Phase 1)
3. Run `/template-create` and capture logs
4. Analyze logs to identify root cause
5. Document findings with evidence
6. Propose minimal-scope fix
7. Get approval before implementing
8. Test fix with actual template creation

---

**Review Status**: REVIEW_COMPLETE
**Root Cause**: IDENTIFIED - Missing bridge handler for exit code 42 in template-create.md
**Implementation Task**: TASK-IMP-BRIDGE-FIX (created)
**Review Report**: .claude/reviews/TASK-REV-AGENT-GEN-review-report.md
