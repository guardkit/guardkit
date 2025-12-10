# Review Report: TASK-REV-D8F2

## Executive Summary

After thorough analysis of the template-create agent generation regression, I have identified the **root cause** and evaluated three solution options. The issue is a **global resume counter** that is incremented on every resume regardless of which phase triggered it, causing Phase 5 to be forced into heuristic mode after Phase 1 completes.

**Key Finding**: The architecture change in TASK-FIX-7B74 (separate phase invokers) is correct and working. The real bug is in the `StateManager.increment_resume_count()` which uses a **single global counter** instead of phase-specific counters.

**Recommended Decision**: **Option B** - Reset resume counter after successful Phase 1 completion.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard (1-2 hours)
- **Duration**: ~1.5 hours
- **Reviewer**: architectural-reviewer analysis + code inspection

## Root Cause Analysis

### The Resume Counter Problem

The `StateManager` (line 161-195 in `state_manager.py`) maintains a single `resume_count` field:

```python
@dataclass
class TemplateCreateState:
    # ...
    resume_count: int = 0  # ← SINGLE COUNTER FOR ALL PHASES

def increment_resume_count(self) -> int:
    state = self.load_state()
    new_count = state.resume_count + 1  # ← INCREMENTED ON EVERY RESUME
    # ... persists new_count back to state file
```

### What Actually Happens (The Bug Flow)

1. **First Run (Normal)**: Phase 1 saves checkpoint, exits with code 42
2. **First Resume**: `increment_resume_count()` → count becomes 1
3. **Second Resume** (may happen if user runs again or test restarts): count becomes 2
4. **Third Resume**: count becomes 3 → **_force_heuristic = True**
5. **Phase 5 Entry**: `if self._force_heuristic:` is True → heuristic fallback

### Evidence from Logs

From [template_create.md](docs/reviews/progressive-disclosure/template_create.md) (line 1076-1081):

```
🔄 Resuming from checkpoint...
  Resume attempt: 3                    ← Counter already at 3!
  ⚠️  Maximum resume attempts reached (3)
  → Will use heuristic agent generation (no AI)
  Checkpoint: pre_ai_analysis         ← But we're in Phase 1!
  Phase: 1
  ✓ Agent response loaded successfully ← Phase 1 response is fine
```

**Critical Observation**: The counter reached 3 before Phase 5 even started because:
- Phase 1 requires 1 resume cycle (exit 42 → agent response → resume)
- Any additional resumes (testing, interruptions, manual runs) accumulate
- When Phase 5 finally runs, the counter is already exhausted

### Why Phase-Specific Invokers Don't Solve This

TASK-FIX-7B74 correctly implemented separate invokers:

```python
self.phase1_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_1,
    phase_name="ai_analysis"
)
self.phase5_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_5,
    phase_name="agent_generation"
)
```

And the `_resume_from_checkpoint()` correctly selects the invoker:

```python
if state.phase == WorkflowPhase.PHASE_1:
    invoker = self.phase1_invoker
elif state.phase >= WorkflowPhase.PHASE_5:
    invoker = self.phase5_invoker
```

**But**: The `_force_heuristic` flag is set based on the global `resume_count`, not per-phase:

```python
if resume_count >= 3:
    self._force_heuristic = True  # ← Applied globally to ALL phases!
```

### Why Heuristic Returns No Agents

From `_generate_heuristic_agents()` (line 957-1010 in `template_create_orchestrator.py`):

```python
def _generate_heuristic_agents(self, analysis: Any) -> List[Any]:
    language = getattr(analysis, 'language', 'unknown')
    architecture = getattr(analysis, 'architecture_pattern', 'unknown')
    # ...
    if language and language != 'unknown':
        # Generate language-specific agent
```

The heuristic depends on `analysis.language` and `analysis.architecture_pattern`. When AI analysis worked (91.67% confidence), these fields are populated. But the heuristic agent generation has additional logic that may fail if the analysis doesn't have the expected format from its perspective.

The actual issue is that `_generate_heuristic_agents` was designed as a last-resort fallback, not as the primary agent generation path. It returns "insufficient analysis data" because it expects simpler analysis formats, not the rich AI analysis data structure.

## Decision Options

### Option A: Clear Resume Counter at Phase 5 Entry

**Implementation**:
```python
def _phase5_agent_recommendation(self, analysis: Any) -> List[Any]:
    self._print_phase_header("Phase 5: Agent Recommendation")

    # TASK-FIX-D8F2: Reset resume state for Phase 5
    self._force_heuristic = False
    self._resume_count = 0
    self.state_manager.reset_resume_count()  # New method needed
```

**Pros**:
- Minimal code change (~5 lines)
- Doesn't change StateManager architecture
- Phase 5 gets fresh attempts

**Cons**:
- Treats symptom, not root cause
- May need similar fixes for future phases
- Counter manipulation feels hacky
- `reset_resume_count()` method doesn't exist yet

**Effort**: Low (0.5-1 hour)
**Risk**: Low
**Quality**: Medium

### Option B: Reset Resume Counter After Successful Phase Completion (RECOMMENDED)

**Implementation**:
```python
# In _run_from_phase_1() after successful AI analysis:
def _run_from_phase_1(self) -> OrchestrationResult:
    # ... existing code ...

    self.analysis = self._phase1_ai_analysis(codebase_path)
    if self.analysis:
        # TASK-FIX-D8F2: Reset resume count after successful phase completion
        self.state_manager.reset_resume_count()
        self._force_heuristic = False
        self._resume_count = 0

    # Continue with Phase 2 onwards...
```

**Pros**:
- Addresses root cause (counter should reset between phases)
- Logical semantics: "successful phase = fresh start"
- Works for any multi-phase workflow
- Clean separation of concerns

**Cons**:
- Requires adding `reset_resume_count()` to StateManager
- Need to identify all phase completion points

**Effort**: Low-Medium (1-2 hours)
**Risk**: Low
**Quality**: High

### Option C: Phase-Specific Resume Counters

**Implementation**:
```python
@dataclass
class TemplateCreateState:
    # ...
    resume_counts: dict = field(default_factory=lambda: {1: 0, 5: 0})  # Per-phase

def increment_resume_count(self, phase: int) -> int:
    # Increment only for specific phase
```

**Pros**:
- Complete isolation
- Architecturally pure
- Future-proof for any number of phases

**Cons**:
- More invasive change
- Requires StateManager API change
- Breaking change for state file format
- Higher risk of introducing bugs

**Effort**: Medium-High (2-4 hours)
**Risk**: Medium
**Quality**: High

## Decision Matrix

| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Addresses Root Cause | 30% | 4/10 | 9/10 | 10/10 |
| Implementation Effort | 20% | 9/10 | 7/10 | 4/10 |
| Risk Level | 20% | 8/10 | 8/10 | 5/10 |
| Code Quality | 15% | 5/10 | 8/10 | 9/10 |
| Maintainability | 15% | 5/10 | 8/10 | 9/10 |
| **Weighted Score** | 100% | **6.05** | **8.15** | **7.45** |

## Recommendation

**Implement Option B**: Reset resume counter after successful Phase 1 completion.

### Rationale

1. **Best ROI**: High quality improvement with low effort
2. **Addresses Root Cause**: Counter semantically should reset between phases
3. **Low Risk**: Minimal code changes, no API breaking changes
4. **Future-Proof**: Works for any multi-phase workflow

### Implementation Plan

1. Add `reset_resume_count()` method to `StateManager`:
   ```python
   def reset_resume_count(self) -> None:
       """Reset resume count to 0 (called after successful phase completion)."""
       if self.state_file.exists():
           data = json.loads(self.state_file.read_text(encoding="utf-8"))
           data["resume_count"] = 0
           self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
   ```

2. Call `reset_resume_count()` after successful Phase 1 completion in `_run_from_phase_1()`

3. Also reset `self._force_heuristic = False` and `self._resume_count = 0`

4. Add regression test verifying Phase 5 uses AI when Phase 1 completed successfully

### Test Plan

1. **Unit Test**: `test_resume_count_resets_after_phase1()`
2. **Integration Test**: Full `/template-create` run producing agents
3. **Regression Test**: Verify 9+ agents generated for complex codebases

## Impact on Token Savings

Option B preserves the Progressive Disclosure token savings:
- Phase 1 AI analysis: 55-60% token reduction vs full context
- Phase 5 AI agents: Full agent generation capability restored
- No regression in quality (91.67% confidence maintained)

## Files to Modify

1. `installer/core/lib/agent_bridge/state_manager.py` - Add `reset_resume_count()`
2. `installer/core/commands/lib/template_create_orchestrator.py` - Reset counter after Phase 1 success

## Appendix

### Supporting Evidence

**Log Analysis** (from template_create.md):
- Resume attempt: 3 at Phase 1 checkpoint
- Agent response loaded successfully
- Phase 5 forced to heuristic mode
- 0 agents generated

**Code Analysis**:
- `StateManager.increment_resume_count()` uses global counter
- `_resume_from_checkpoint()` sets `_force_heuristic` based on global count
- Phase-specific invokers are correctly implemented (TASK-FIX-7B74)
- Heuristic fallback designed for simple analysis, not AI analysis data

---

*Generated by /task-review TASK-REV-D8F2 --mode=decision --depth=standard*
*Review Date: 2025-12-08*
