# Review Report: TASK-REV-AGENT-GEN

**AI Agent Generation Heuristic Fallback Investigation**

## Executive Summary

The root cause has been identified: **The checkpoint-resume bridge pattern is implemented in Python but not wired up in the Claude command execution layer**. When Python's `AgentBridgeInvoker` exits with code 42 (signaling agent invocation needed), Claude doesn't have instructions to handle this, so it falls back to manual behavior resulting in heuristic-based agent generation instead of AI-powered generation.

### Key Findings

| Aspect | Expected (AI) | Actual (Heuristic) | Root Cause |
|--------|---------------|-------------------|------------|
| Agent count | 7-8 | 3 | No bridge handler in command |
| Analysis method | architectural-reviewer via Task | Manual file reads | Exit code 42 unhandled |
| Confidence score | 90%+ | ~68% | Falls back to heuristics |
| Exit code 42 handling | Claude reads request, invokes agent, writes response | Not handled | Missing command logic |

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Comprehensive
- **Duration**: ~45 minutes
- **Reviewer**: architectural-reviewer (manual analysis)

---

## Root Cause Analysis

### The Checkpoint-Resume Pattern

The system uses an **exit code 42 bridge pattern** for Python→Claude agent invocation:

```
Expected Flow:
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Python orchestrator runs                                         │
│ 2. Needs AI analysis → AgentBridgeInvoker.invoke()                  │
│ 3. Writes .agent-request.json                                       │
│ 4. Exit with code 42 ("NEED_AGENT")                                 │
│ 5. Claude detects exit 42 ← MISSING HANDLER                         │
│ 6. Claude reads .agent-request.json                                 │
│ 7. Claude invokes Task(architectural-reviewer)                      │
│ 8. Claude writes .agent-response.json                               │
│ 9. Claude re-runs Python with --resume                              │
│ 10. Python loads response, continues execution                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Where the Chain Breaks

**File**: [installer/global/commands/template-create.md:1119-1127](installer/global/commands/template-create.md#L1119-L1127)

The command execution simply says:
```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

There is **no bridge logic** to:
1. Detect exit code 42
2. Read `.agent-request.json`
3. Invoke the requested agent
4. Write `.agent-response.json`
5. Re-run with `--resume`

### Evidence

**Python side (CORRECTLY IMPLEMENTED)**:

1. **[template_create_orchestrator.py:174-177](installer/global/commands/lib/template_create_orchestrator.py#L174-L177)**: Bridge invoker initialized
   ```python
   self.agent_invoker = AgentBridgeInvoker(
       phase=WorkflowPhase.PHASE_6,
       phase_name="agent_generation"
   )
   ```

2. **[ai_analyzer.py:87](installer/global/lib/codebase_analyzer/ai_analyzer.py#L87)**: Bridge invoker passed to ArchitecturalReviewerInvoker
   ```python
   self.agent_invoker = agent_invoker or ArchitecturalReviewerInvoker(bridge_invoker=bridge_invoker)
   ```

3. **[invoker.py:184-195](installer/global/lib/agent_bridge/invoker.py#L184-L195)**: Exit code 42 generated correctly
   ```python
   print(f"  ⏸️  Requesting agent invocation: {agent_name}")
   print(f"  📝 Request written to: {self.request_file}")
   print(f"  🔄 Checkpoint: Orchestrator will resume after agent responds")
   sys.exit(42)  # ← This fires, but nothing catches it!
   ```

4. **[agent_invoker.py:128-131](installer/global/lib/codebase_analyzer/agent_invoker.py#L128-L131)**: Fallback triggered when no bridge response
   ```python
   # TASK-769D: No bridge invoker - raise error to trigger fallback
   raise AgentInvocationError(
       "Agent invocation not yet implemented. Using fallback heuristics."
   )
   ```

**Claude side (NOT IMPLEMENTED)**:

The `template-create.md` command file only runs Python without handling exit code 42.

---

## Decision Options

### Option A: Add Bridge Logic to Command File (RECOMMENDED)

**Description**: Modify `template-create.md` to include Claude-side bridge logic that handles exit code 42.

**Implementation**:
```markdown
## Command Execution

When executing this command, Claude should:

1. Run the Python orchestrator:
   ```bash
   python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
   ```

2. **If Python exits with code 42** (checkpoint-resume pattern):
   - Read `.agent-request.json` from current directory
   - Extract `agent_name` and `prompt` from the request
   - Invoke the agent using Task tool:
     ```
     Task(subagent_type="{agent_name}", prompt="{prompt from request}")
     ```
   - Write response to `.agent-response.json`:
     ```json
     {
       "request_id": "<from request>",
       "version": "1.0",
       "status": "success",
       "response": "<agent output>",
       "created_at": "<timestamp>",
       "duration_seconds": <duration>,
       "metadata": {}
     }
     ```
   - Re-run Python with --resume:
     ```bash
     python3 ~/.agentecflow/bin/template-create-orchestrator --resume "$@"
     ```

3. If Python exits with code 0, workflow complete.
4. If Python exits with other codes, report error.
```

**Pros**:
- Minimal code change (documentation only)
- Uses existing Python infrastructure
- Clean separation of concerns

**Cons**:
- Requires Claude to understand and follow complex instructions
- May need testing to ensure reliability

**Effort**: Low (1-2 hours)
**Risk**: Low

---

### Option B: Python-Only Solution (Inline Agent Execution)

**Description**: Modify Python to execute agents directly without Claude bridge.

**Implementation**: Call Claude API directly from Python using `anthropic` SDK.

**Pros**:
- No reliance on Claude Code understanding complex patterns
- More predictable execution

**Cons**:
- Requires API key management in Python
- Adds external dependency
- Cost implications (direct API calls)
- Architectural change - agents currently designed for Claude Code execution

**Effort**: High (1-2 days)
**Risk**: Medium-High

---

### Option C: Hybrid - Fallback Enhancement

**Description**: Enhance heuristic fallback to be "good enough" without AI analysis.

**Implementation**: Improve `HeuristicAnalyzer` to generate more agents.

**Pros**:
- Works without bridge pattern
- Simpler to implement

**Cons**:
- Never achieves AI quality (90%+ confidence)
- Defeats purpose of AI-powered template creation
- Technical debt

**Effort**: Medium (4-6 hours)
**Risk**: Low but compromises quality

---

## Recommendation

**Strongly recommend Option A** - Add bridge logic to the command file.

**Rationale**:
1. **Root cause fix**: Addresses the actual problem (missing bridge handler)
2. **Minimal change**: Only modifies documentation/instructions
3. **Uses existing infrastructure**: Python code already implements checkpoint-resume
4. **No new dependencies**: No API key management or SDK additions
5. **Maintains architecture**: Keeps agent invocation in Claude Code where it belongs

### Implementation Scope

**Files to modify**:
1. `installer/global/commands/template-create.md` - Add bridge execution logic

**Testing required**:
1. Run `/template-create` and verify:
   - Exit code 42 is detected
   - `.agent-request.json` is read
   - Agent is invoked via Task tool
   - `.agent-response.json` is written
   - Python resumes correctly
   - 7-8 agents generated (not 3)
   - Confidence score 90%+ (not 68%)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Claude misinterprets bridge instructions | Medium | High | Clear, explicit instructions with examples |
| Race condition in file I/O | Low | Medium | Use atomic writes, validate JSON |
| Infinite loop (keep exiting 42) | Low | High | Add max iteration check |
| Response format mismatch | Medium | Medium | Validate against AgentResponse schema |

---

## Recommendations Summary

1. **Immediate**: Implement Option A (bridge logic in command file)
2. **Testing**: Create integration test for checkpoint-resume flow
3. **Documentation**: Update CLAUDE.md to explain bridge pattern
4. **Monitoring**: Add logging to track bridge invocations

---

## Appendix: File References

| File | Purpose | Lines |
|------|---------|-------|
| [template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py) | Main orchestrator | 2241 |
| [ai_analyzer.py](installer/global/lib/codebase_analyzer/ai_analyzer.py) | AI analysis | 434 |
| [invoker.py](installer/global/lib/agent_bridge/invoker.py) | Bridge invoker | 298 |
| [state_manager.py](installer/global/lib/agent_bridge/state_manager.py) | State persistence | 162 |
| [agent_invoker.py](installer/global/lib/codebase_analyzer/agent_invoker.py) | Agent invocation | 631 |
| [agent_generator.py](installer/global/lib/agent_generator/agent_generator.py) | Agent generation | 801 |
| [template-create.md](installer/global/commands/template-create.md) | Command spec | 1127 |

---

## Decision Checkpoint

**Review Status**: REVIEW_COMPLETE

**Findings Count**: 1 (missing bridge handler)

**Recommendations Count**: 3 (immediate fix, testing, documentation)

**Decision Options**:
- **[A]ccept** - Archive review (no implementation needed)
- **[R]evise** - Request deeper analysis
- **[I]mplement** - Create implementation task based on Option A
- **[C]ancel** - Discard review
