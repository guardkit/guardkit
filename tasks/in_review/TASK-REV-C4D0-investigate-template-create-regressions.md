---
id: TASK-REV-C4D0
title: Investigate template-create orchestrator regressions after TASK-ENH-D960
status: review_complete
created: 2025-12-07T15:10:00Z
updated: 2025-12-07T16:00:00Z
priority: high
tags: [template-create, regression, debugging, review]
task_type: review
complexity: 7
related_tasks: [TASK-ENH-D960]
review_results:
  mode: architectural
  depth: standard
  score: 60
  findings_count: 6
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-C4D0-review-report.md
  implementation_task: TASK-IMP-D93B
---

# Task: Investigate Template-Create Orchestrator Regressions

## Description

After implementing TASK-ENH-D960 (AI agent invocation in Phase 1), running `/template-create --name kartlog` exhibits major issues:

1. **Phase 1 exits with code 42** (checkpoint-resume pattern triggered)
2. **Resume with `--resume` flag fails** - orchestrator re-starts Phase 1 instead of continuing
3. **Output shows re-analysis** instead of using cached agent response
4. **Potential infinite loop** - keeps requesting agent invocation

## Observed Behavior

From user-provided output:

```
python3 ~/.agentecflow/bin/template-create-orchestrator --name kartlog 2>&1
Exit code 42

Phase 1: AI Codebase Analysis
------------------------------------------------------------
  💾 State saved (checkpoint: pre_ai_analysis)
  ⏸️  Requesting agent invocation: architectural-reviewer
  📝 Request written to: .agent-request.json
  🔄 Checkpoint: Orchestrator will resume after agent responds
```

After writing `.agent-response.json` and running `--resume`:

```
python3 ~/.agentecflow/bin/template-create-orchestrator --name kartlog --resume 2>&1

INFO:lib.codebase_analyzer.ai_analyzer:Analyzing codebase: /Users/richwoollcott/Projects/Github/kartlog
```

**Problem**: The orchestrator is re-analyzing instead of loading the cached response.

## Suspected Root Causes

### 1. AgentBridgeInvoker Phase Mismatch
The invoker was initialized for PHASE_1 but checkpoint/resume may expect different phase handling.

```python
# TASK-ENH-D960 change in template_create_orchestrator.py
self.agent_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_1,  # First use in Phase 1
    phase_name="ai_analysis"
)
```

### 2. Response Not Being Loaded Before Re-invocation
The `_run_from_phase_1()` method may not be loading the cached response before calling analyzer.

### 3. State File Phase Not Being Set Correctly
The checkpoint may not be recording the phase correctly for resume routing.

### 4. Response File Path Mismatch
The response file may be in a different location than expected.

## Files to Investigate

1. **`installer/global/commands/lib/template_create_orchestrator.py`**
   - `_run_from_phase_1()` method (lines 272-332)
   - `_phase1_ai_analysis()` method (lines 700-707)
   - Phase resume routing (lines 254-260)
   - Checkpoint save logic

2. **`installer/global/lib/agent_bridge/invoker.py`**
   - `load_response()` method
   - `invoke()` method cached response handling
   - Response file path resolution

3. **`installer/global/lib/codebase_analyzer/ai_analyzer.py`**
   - How bridge_invoker is used
   - When/if `load_response()` is called

4. **`installer/global/lib/codebase_analyzer/agent_invoker.py`**
   - ArchitecturalReviewerInvoker implementation
   - Bridge invoker integration

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Reproduction steps confirmed
- [ ] Fix implemented or recommended
- [ ] Resume from Phase 1 works correctly
- [ ] Agent response is loaded and used (not re-requested)
- [ ] Backward compatibility maintained for Phase 5 and Phase 7 resume

## Test Cases to Verify

1. **Fresh run**: `template-create --name test` should exit 42 and request agent
2. **Resume after response**: `template-create --name test --resume` should load response and continue
3. **Phase 5 resume**: Existing Phase 5 resume should still work
4. **Phase 7 resume**: Existing Phase 7 resume should still work

## Evidence From User Output

The full output shows:
- Phase 1 checkpoint triggered correctly
- Agent request written to `.agent-request.json`
- User manually invoked agent and wrote `.agent-response.json`
- Resume started re-analysis instead of loading response

This confirms the bug is in the resume path, not the initial checkpoint.

## Priority Justification

**High priority** because:
- Template creation is a core workflow
- Users cannot complete `/template-create` with AI analysis enabled
- TASK-ENH-D960 was just deployed and needs immediate fix
- Blocks user workflows
