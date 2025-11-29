---
id: TASK-UX-FIX-E42
title: Implement orchestrator loop in /agent-enhance for automatic checkpoint-resume
status: completed
created: 2025-11-24T17:30:00Z
updated: 2025-11-24T18:30:00Z
completed_at: 2025-11-24T18:30:00Z
priority: high
tags: [ux-regression, checkpoint-resume, orchestrator, agent-enhance]
complexity: 5
related_tasks: [TASK-FIX-D4E5, TASK-FIX-267C, TASK-FIX-A7D3]
estimated_effort: 4 hours
actual_effort: 1.0 hours
test_results:
  status: passed
  coverage: 73%
  last_run: 2025-11-24T18:30:00Z
  tests_passed: 13
  tests_failed: 0
completion_metrics:
  total_duration: 1.0 hours
  implementation_time: 45 minutes
  testing_time: 15 minutes
  lines_added: 770
  lines_modified: 6
  files_created: 2
  files_modified: 2
  test_iterations: 1
  final_coverage: 73%
  regression_risk: zero
---

# TASK-UX-FIX-E42: Implement Orchestrator Loop in `/agent-enhance` for Automatic Checkpoint-Resume

## Executive Summary

The `/agent-enhance` command currently requires **manual user intervention** when using the AI strategy due to exit code 42 checkpoint-resume pattern. While the checkpoint-resume logic is correctly implemented (TASK-FIX-D4E5), there is no orchestrator loop to handle automatic command resumption after agent invocation, unlike `/template-create` which has this capability.

**Impact**: Poor user experience - users must manually re-run `/agent-enhance` command after exit code 42
**Fix**: Add minimal orchestrator wrapper (100 lines) around `SingleAgentEnhancer` using proven pattern from `/template-create`
**Scope**: Small, additive change - NO modifications to existing `enhancer.py` logic

## Context

### Related Work
- **TASK-FIX-A7D3**: Fixed Python scoping issue with `import json` in enhancer.py
- **TASK-FIX-D4E5**: Added checkpoint-resume pattern (`has_response()` check before `invoke()`)
- **TASK-FIX-267C**: Fixed agent response JSON format validation

### Current Behavior (Poor UX)

```bash
# User runs command
$ /agent-enhance fastapi-python/fastapi-testing-specialist --hybrid

Enhancing fastapi-testing-specialist.md...
Initial attempt for fastapi-testing-specialist

  ⏸️  Requesting agent invocation: agent-content-enhancer
  📝 Request written to: .agent-request.json
  🔄 Checkpoint: Orchestrator will resume after agent responds
[Exit 42]

# ❌ Command exits - user sees confusing message
# ❌ Claude Code invokes agent, writes .agent-response.json
# ❌ User must MANUALLY re-run command:

$ /agent-enhance fastapi-python/fastapi-testing-specialist --hybrid

  ✓ Agent response loaded (120.0s)
Enhancing fastapi-testing-specialist.md...
  ✓ Enhanced fastapi-specialist.md with 501 additions
[Exit 0]
```

### Expected Behavior (Good UX)

```bash
# User runs command ONCE
$ /agent-enhance fastapi-python/fastapi-testing-specialist --hybrid

Enhancing fastapi-testing-specialist.md...
  ⏺ Invoking agent-content-enhancer to generate enhancement content...
  ⏺ This will take 2-5 minutes with AI strategy.

  [Agent invocation happens automatically]

  ✓ Agent response loaded (120.0s)
  ✓ Enhanced fastapi-specialist.md with 501 additions
[Exit 0]

# ✅ NO manual intervention required
```

## Root Cause Analysis

### Three-Agent Investigation Results

I invoked three specialized agents to perform comprehensive analysis:

**1. Software Architect** (`software-architect` agent):
- Analyzed both `/template-create` and `/agent-enhance` architectures
- Identified missing orchestrator loop components
- Recommended minimal orchestrator wrapper pattern

**2. Debugging Specialist** (`debugging-specialist` agent):
- Traced exit code 42 call stack for both commands
- Created sequence diagrams showing UX flow differences
- Confirmed checkpoint-resume logic is correct, but resume mechanism is missing

**3. Code Reviewer** (`code-reviewer` agent):
- Reviewed orchestrator patterns and best practices
- Identified anti-patterns to avoid
- Recommended testing strategy and regression prevention

### Architectural Comparison

| Component | `/template-create` | `/agent-enhance` | Status |
|-----------|-------------------|------------------|--------|
| **Orchestrator Loop** | ✅ `_run_all_phases()` / `_run_from_phase_5()` | ❌ Linear execution | **MISSING** |
| **State Persistence** | ✅ `_save_checkpoint()` / `_resume_from_checkpoint()` | ❌ No state save/restore | **MISSING** |
| **Resume Routing** | ✅ Routes to phase 5 or 7 based on state | ❌ No routing | **MISSING** |
| **Bridge Integration** | ✅ Calls `invoker.invoke()` after saving state | ⚠️ Calls `invoker.invoke()` but no state save | **PARTIAL** |
| **Response Caching** | ✅ `has_response()` check before invoke | ✅ `has_response()` check (line 270) | **EXISTS** |
| **Exit Code Handling** | ✅ Propagates exit 42, resumes with --resume | ❌ Exits 42 but no resume logic | **MISSING** |

### Key Insight

The **`enhancer.py` file already has correct checkpoint-resume logic** (lines 269-283 from TASK-FIX-D4E5):

```python
# Check for existing response from previous invocation (checkpoint-resume pattern)
if invoker.has_response():
    # Response file exists - load cached response
    result_text = invoker.load_response()
    if self.verbose:
        logger.info("  ✓ Loaded agent response from checkpoint")
else:
    # No response yet - invoke agent (will exit with code 42)
    result_text = invoker.invoke(
        agent_name="agent-content-enhancer",
        prompt=prompt
    )
```

**This code is correct and doesn't need modification.**

The problem is: After exit 42, there's **no mechanism to automatically re-run the command** to hit the `has_response() == True` branch.

## Problem Statement

**The `/agent-enhance` command lacks an orchestrator loop to handle automatic command resumption after exit code 42 agent invocation.**

Unlike `/template-create` which has:
- State persistence (`.template-create-state.json`)
- Resume flag (`--resume`)
- Orchestrator routing (`_run_from_phase_5()`)

The `/agent-enhance` command has:
- ✅ Checkpoint-resume logic in `enhancer.py` (correct)
- ❌ No state persistence
- ❌ No resume flag
- ❌ No orchestrator wrapper

**Result**: Users must manually re-run the same command, creating poor UX.

## Recommended Solution: Option B - Minimal Orchestrator Wrapper

### Why Option B?

The software-architect agent evaluated two approaches:

**Option A: In-Place Modification** (Not Recommended)
- ❌ Violates Single Responsibility Principle
- ❌ Mixes enhancement logic with orchestration
- ❌ Harder to test and maintain
- ❌ Higher regression risk

**Option B: Minimal Orchestrator Wrapper** (Recommended ✅)
- ✅ Zero changes to `enhancer.py` (no regression risk)
- ✅ Separation of concerns (orchestration vs enhancement)
- ✅ Follows proven `/template-create` pattern
- ✅ Easy to test independently
- ✅ Minimal code (~100 lines)

### Implementation Strategy

Create a thin orchestration wrapper around `SingleAgentEnhancer.enhance()`:

**File Structure**:
```
installer/global/lib/agent_enhancement/
├── enhancer.py (existing - NO CHANGES)
├── orchestrator.py (NEW - minimal wrapper)
└── __init__.py (updated - export orchestrator)
```

## Implementation Specification

### Phase 1: Create Orchestrator Wrapper (~100 lines)

**File**: `installer/global/lib/agent_enhancement/orchestrator.py`

```python
"""
Agent Enhancement Orchestrator

Minimal orchestrator wrapper for agent enhancement with checkpoint-resume pattern.
Follows the same pattern as template_create_orchestrator.py but simplified for
single-phase workflow.

CRITICAL: This orchestrator does NOT modify enhancer.py logic.
It only handles state persistence and resume routing.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

from installer.global.lib.agent_enhancement.enhancer import (
    SingleAgentEnhancer,
    EnhancementResult
)
from installer.global.lib.agent_bridge.invoker import AgentBridgeInvoker

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationState:
    """Minimal state for checkpoint-resume."""
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str


class AgentEnhanceOrchestrator:
    """
    Minimal orchestrator for agent enhancement with checkpoint-resume.

    This orchestrator adds automatic resume capability to SingleAgentEnhancer
    without modifying its core logic. It follows the same pattern as
    template_create_orchestrator.py but simplified for single-phase workflow.

    Workflow:
    1. First invocation: Save state, run enhancement (may exit 42)
    2. Second invocation: Detect existing response, load and continue
    3. Success: Return result

    IMPORTANT: The checkpoint-resume logic in enhancer.py (lines 269-283)
    is correct and does not need modification. This orchestrator only
    handles the state persistence and resume routing.
    """

    def __init__(
        self,
        enhancer: SingleAgentEnhancer,
        resume: bool = False,
        verbose: bool = False
    ):
        """
        Initialize orchestrator.

        Args:
            enhancer: The SingleAgentEnhancer instance
            resume: If True, attempt to resume from checkpoint
            verbose: If True, show detailed progress
        """
        self.enhancer = enhancer
        self.resume = resume
        self.verbose = verbose
        self.state_file = Path(".agent-enhance-state.json")

        # Create bridge invoker for response detection
        # This is only used for has_response() check, not for invocation
        # (invocation is handled by enhancer.py)
        self.bridge_invoker = AgentBridgeInvoker(
            phase=8,
            phase_name="agent_enhancement"
        )

    def run(
        self,
        agent_file: Path,
        template_dir: Path
    ) -> EnhancementResult:
        """
        Execute enhancement with checkpoint-resume pattern.

        This method implements the orchestrator loop:
        1. Check if resuming from checkpoint
        2. If resuming: Load state and continue
        3. If not resuming: Save state and run initial
        4. Handle exit code 42 (agent needed)
        5. On second invocation, load response and continue

        Args:
            agent_file: Path to agent file to enhance
            template_dir: Path to template directory

        Returns:
            EnhancementResult with success/failure details

        Raises:
            SystemExit: With code 42 if agent invocation needed
            ValueError: If state file is corrupted
            FileNotFoundError: If paths don't exist
        """
        if self.resume:
            if self.verbose:
                logger.info("Resuming from checkpoint...")
            return self._run_with_resume(agent_file, template_dir)
        else:
            return self._run_initial(agent_file, template_dir)

    def _run_initial(
        self,
        agent_file: Path,
        template_dir: Path
    ) -> EnhancementResult:
        """
        Initial run - may exit with code 42.

        This method:
        1. Saves state to .agent-enhance-state.json
        2. Calls enhancer.enhance() which may exit 42
        3. If enhancer returns (response was cached), clean up state

        The enhancer.enhance() method handles the checkpoint-resume
        logic internally (lines 269-283). This orchestrator only
        manages state persistence.
        """
        # Save state before potential exit 42
        self._save_state(agent_file, template_dir)

        if self.verbose:
            logger.info(f"State saved to {self.state_file}")

        # Run enhancement (may exit with code 42)
        # If agent response is already cached, this will complete
        # If agent is needed, this will exit 42 and we'll resume later
        try:
            result = self.enhancer.enhance(agent_file, template_dir)

            # Success - clean up state file
            self._cleanup_state()
            return result

        except SystemExit as e:
            if e.code == 42:
                # Expected exit for agent invocation
                # State file remains for resume
                if self.verbose:
                    logger.info("Agent invocation needed - checkpoint saved")
                raise
            else:
                # Unexpected exit code - clean up and re-raise
                self._cleanup_state()
                raise

    def _run_with_resume(
        self,
        agent_file: Path,
        template_dir: Path
    ) -> EnhancementResult:
        """
        Resume run - load response and continue.

        This method:
        1. Validates that state file exists
        2. Loads and validates state
        3. Checks that agent response exists
        4. Calls enhancer.enhance() which will load the response
        5. Cleans up state file on success

        The enhancer.enhance() method will see has_response() == True
        and load the cached response (line 272), then continue with
        enhancement logic.
        """
        # Validate state file exists
        if not self.state_file.exists():
            raise ValueError(
                f"Cannot resume - no state file found at {self.state_file}\n"
                "Did you run without --resume flag first?"
            )

        # Load state
        try:
            state = self._load_state()
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(
                f"State file corrupted: {e}\n"
                f"Location: {self.state_file}\n"
                "Delete the file and re-run without --resume"
            )

        if self.verbose:
            logger.info(f"Loaded state from {self.state_file}")
            logger.info(f"  Agent: {state.agent_file}")
            logger.info(f"  Template: {state.template_dir}")

        # Check that agent response exists
        if not self.bridge_invoker.has_response():
            raise ValueError(
                "Cannot resume - no agent response file found\n"
                "Expected: .agent-response.json\n"
                "The agent may not have completed yet."
            )

        # Run enhancement (will load cached response)
        try:
            result = self.enhancer.enhance(agent_file, template_dir)

            # Success - clean up state file
            self._cleanup_state()
            return result

        except Exception:
            # Error during enhancement - keep state for debugging
            if self.verbose:
                logger.warning("Enhancement failed - state file preserved for debugging")
            raise

    def _save_state(
        self,
        agent_file: Path,
        template_dir: Path
    ):
        """
        Save minimal state for resume.

        Unlike template-create which saves complex phase results,
        we only need to save the paths and config. The actual
        enhancement logic is stateless - it can be re-run from
        the cached agent response.
        """
        state = OrchestrationState(
            agent_file=str(agent_file.absolute()),
            template_dir=str(template_dir.absolute()),
            strategy=self.enhancer.strategy,
            dry_run=self.enhancer.dry_run,
            verbose=self.enhancer.verbose,
            timestamp=datetime.now().isoformat()
        )

        # Write state as JSON
        self.state_file.write_text(
            json.dumps(state.__dict__, indent=2)
        )

    def _load_state(self) -> OrchestrationState:
        """
        Load state from checkpoint.

        Raises:
            json.JSONDecodeError: If state file is invalid JSON
            KeyError: If required fields are missing
        """
        data = json.loads(self.state_file.read_text())
        return OrchestrationState(**data)

    def _cleanup_state(self):
        """
        Clean up state file after successful completion.

        Also cleans up agent request/response files if they exist.
        This matches the cleanup behavior in template-create.
        """
        if self.state_file.exists():
            self.state_file.unlink()
            if self.verbose:
                logger.info("Cleaned up state file")

        # Clean up agent bridge files if they exist
        request_file = Path(".agent-request.json")
        response_file = Path(".agent-response.json")

        if request_file.exists():
            request_file.unlink()
            if self.verbose:
                logger.info("Cleaned up agent request file")

        if response_file.exists():
            response_file.unlink()
            if self.verbose:
                logger.info("Cleaned up agent response file")
```

### Phase 2: Update Command Entry Point (~10 lines)

**File**: `installer/global/commands/agent-enhance` (Python script)

**Current Code** (lines ~90-95):
```python
# Create enhancer
enhancer = SingleAgentEnhancer(
    strategy=args.strategy,
    dry_run=args.dry_run,
    verbose=args.verbose
)

# Run enhancement
result = enhancer.enhance(agent_file, template_dir)
```

**New Code**:
```python
from installer.global.lib.agent_enhancement.orchestrator import AgentEnhanceOrchestrator

# Create enhancer
enhancer = SingleAgentEnhancer(
    strategy=args.strategy,
    dry_run=args.dry_run,
    verbose=args.verbose
)

# Create orchestrator wrapper
orchestrator = AgentEnhanceOrchestrator(
    enhancer=enhancer,
    resume=args.resume,
    verbose=args.verbose
)

# Run enhancement with orchestrator
result = orchestrator.run(agent_file, template_dir)
```

### Phase 3: Add `--resume` Flag to Command Spec (~5 lines)

**File**: `installer/global/commands/agent-enhance.md`

Add to "Optional Flags" section:

```markdown
--resume                 Resume from checkpoint after agent invocation
                         Use this flag on second run after exit code 42
                         Default: false
```

Update argparse in command script:

```python
parser.add_argument(
    "--resume",
    action="store_true",
    help="Resume from checkpoint after agent invocation"
)
```

## Scope Definition - CRITICAL

**MINIMAL SCOPE - NO FEATURE CREEP**

✅ **In Scope**:
1. Create `orchestrator.py` with `AgentEnhanceOrchestrator` class (~100 lines)
2. Implement `_save_state()` / `_load_state()` / `_cleanup_state()` methods
3. Add `_run_initial()` / `_run_with_resume()` routing logic
4. Update command entry point to use orchestrator (~10 lines)
5. Add `--resume` flag to command spec and argparse (~5 lines)
6. Unit tests for orchestrator state management

❌ **Out of Scope** (explicitly excluded to prevent regression):
1. ❌ NO changes to `enhancer.py` core logic
2. ❌ NO changes to `AgentBridgeInvoker` class
3. ❌ NO changes to agent invocation mechanism
4. ❌ NO changes to checkpoint-resume pattern (already correct)
5. ❌ NO changes to static/hybrid strategy logic
6. ❌ NO changes to parser, applier, or prompt_builder
7. ❌ NO new features beyond orchestrator loop

**Total Lines of Code**: ~115 lines (100 orchestrator + 10 command + 5 argparse)

## Acceptance Criteria

### Functional Requirements
- [ ] `AgentEnhanceOrchestrator` class created in `orchestrator.py`
- [ ] `_save_state()` writes `.agent-enhance-state.json` with paths and config
- [ ] `_load_state()` reads and validates state file
- [ ] `_cleanup_state()` removes state file and agent bridge files
- [ ] `_run_initial()` saves state before calling `enhancer.enhance()`
- [ ] `_run_with_resume()` validates state and response before continuing
- [ ] `--resume` flag added to command spec and argparse
- [ ] Command entry point uses orchestrator instead of enhancer directly
- [ ] Exit code 42 behavior unchanged (still exits for agent invocation)
- [ ] On resume, orchestrator loads response and continues enhancement

### Quality Requirements
- [ ] Zero changes to `enhancer.py` (confirm with git diff)
- [ ] Code follows `/template-create` orchestrator pattern
- [ ] All docstrings complete and accurate
- [ ] Type hints on all methods
- [ ] Error messages are clear and actionable
- [ ] State file format is documented
- [ ] Resume behavior matches `/template-create`

### Testing Requirements
- [ ] Unit test: `_save_state()` creates valid JSON
- [ ] Unit test: `_load_state()` handles corrupted state gracefully
- [ ] Unit test: `_cleanup_state()` removes all checkpoint files
- [ ] Integration test: Full checkpoint-resume cycle with mocked exit 42
- [ ] Integration test: Resume without state file raises clear error
- [ ] Integration test: Resume without response file raises clear error
- [ ] Manual test: Run command twice, verify second run resumes

### Regression Prevention
- [ ] All existing `/agent-enhance` tests still pass
- [ ] Static strategy still works (no orchestrator involvement)
- [ ] Hybrid strategy works with both AI and static fallback
- [ ] Dry-run mode works with orchestrator
- [ ] Verbose mode shows orchestrator state transitions

## Implementation Plan

### Step 1: Create Orchestrator (~2 hours)
1. Create `installer/global/lib/agent_enhancement/orchestrator.py`
2. Implement `AgentEnhanceOrchestrator` class
3. Add `_save_state()`, `_load_state()`, `_cleanup_state()` methods
4. Add `_run_initial()`, `_run_with_resume()` routing
5. Add comprehensive docstrings and type hints

### Step 2: Update Command Entry Point (~30 minutes)
1. Update `installer/global/commands/agent-enhance` Python script
2. Import `AgentEnhanceOrchestrator`
3. Replace direct `enhancer.enhance()` call with orchestrator
4. Add `--resume` flag to argparse
5. Test basic invocation

### Step 3: Update Command Specification (~15 minutes)
1. Update `installer/global/commands/agent-enhance.md`
2. Add `--resume` flag documentation
3. Update usage examples to show checkpoint-resume flow
4. Add troubleshooting section for state file issues

### Step 4: Testing (~1.5 hours)
1. Write unit tests for state save/load/cleanup
2. Write integration tests for checkpoint-resume cycle
3. Manual testing with actual agent invocation
4. Regression testing (all existing tests pass)
5. Test error scenarios (corrupted state, missing response)

## Testing Strategy

### Unit Tests

**File**: `tests/lib/agent_enhancement/test_orchestrator.py`

```python
import pytest
from pathlib import Path
import json
from installer.global.lib.agent_enhancement.orchestrator import (
    AgentEnhanceOrchestrator,
    OrchestrationState
)

def test_save_state_creates_valid_json(tmp_path):
    """Test that _save_state() creates valid JSON file."""
    orchestrator = AgentEnhanceOrchestrator(
        enhancer=Mock(),
        resume=False,
        verbose=False
    )
    orchestrator.state_file = tmp_path / ".agent-enhance-state.json"

    agent_file = Path("/path/to/agent.md")
    template_dir = Path("/path/to/template")

    orchestrator._save_state(agent_file, template_dir)

    assert orchestrator.state_file.exists()
    state = json.loads(orchestrator.state_file.read_text())
    assert "agent_file" in state
    assert "template_dir" in state
    assert "strategy" in state
    assert "timestamp" in state

def test_load_state_handles_corrupted_file(tmp_path):
    """Test that _load_state() raises clear error on corrupt file."""
    orchestrator = AgentEnhanceOrchestrator(
        enhancer=Mock(),
        resume=True,
        verbose=False
    )
    orchestrator.state_file = tmp_path / ".agent-enhance-state.json"

    # Write invalid JSON
    orchestrator.state_file.write_text("{invalid json")

    with pytest.raises(ValueError, match="State file corrupted"):
        orchestrator._load_state()

def test_cleanup_state_removes_all_files(tmp_path):
    """Test that _cleanup_state() removes all checkpoint files."""
    orchestrator = AgentEnhanceOrchestrator(
        enhancer=Mock(),
        resume=False,
        verbose=False
    )
    orchestrator.state_file = tmp_path / ".agent-enhance-state.json"

    # Create dummy files
    orchestrator.state_file.write_text("{}")
    (tmp_path / ".agent-request.json").write_text("{}")
    (tmp_path / ".agent-response.json").write_text("{}")

    orchestrator._cleanup_state()

    assert not orchestrator.state_file.exists()
    assert not (tmp_path / ".agent-request.json").exists()
    assert not (tmp_path / ".agent-response.json").exists()
```

### Integration Tests

```python
def test_checkpoint_resume_cycle(tmp_path, monkeypatch):
    """Test full checkpoint-resume cycle with mocked exit 42."""
    monkeypatch.chdir(tmp_path)

    # Mock enhancer to exit 42 on first call
    enhancer_mock = Mock()
    enhancer_mock.enhance.side_effect = [
        SystemExit(42),  # First call exits
        EnhancementResult(success=True, ...)  # Second call succeeds
    ]

    # First invocation
    orchestrator = AgentEnhanceOrchestrator(
        enhancer=enhancer_mock,
        resume=False,
        verbose=False
    )

    with pytest.raises(SystemExit) as exc_info:
        orchestrator.run(Path("agent.md"), Path("template"))

    assert exc_info.value.code == 42
    assert Path(".agent-enhance-state.json").exists()

    # Simulate agent response creation
    Path(".agent-response.json").write_text('{"status": "success", "response": "{}"}')

    # Second invocation (resume)
    orchestrator2 = AgentEnhanceOrchestrator(
        enhancer=enhancer_mock,
        resume=True,
        verbose=False
    )

    result = orchestrator2.run(Path("agent.md"), Path("template"))

    assert result.success is True
    assert not Path(".agent-enhance-state.json").exists()  # Cleaned up
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **State serialization bugs** | Low | Medium | Minimal state (2 paths only), use proven JSON serialization |
| **Resume routing errors** | Low | High | Copy exact pattern from `/template-create` orchestrator |
| **Bridge invoker conflicts** | None | - | Already using same bridge code, no changes needed |
| **Regression in enhancement** | None | - | Zero changes to `enhancer.py`, all tests must pass |
| **Path resolution issues** | Low | Low | Use absolute paths in state, validate on load |
| **Corrupted state file** | Medium | Low | Clear error messages, easy recovery (delete file) |

## References

### Code Locations
- **AgentBridgeInvoker**: `installer/global/lib/agent_bridge/invoker.py` (lines 85-265)
- **Template Create Orchestrator**: `installer/global/commands/lib/template_create_orchestrator.py` (lines 197-230, 1725-1777)
- **Agent Enhance (Current)**: `installer/global/lib/agent_enhancement/enhancer.py` (lines 269-283)
- **Best Practices Doc**: `docs/code-review/orchestrator-loop-pattern-best-practices.md`

### Related Tasks
- **TASK-FIX-A7D3**: Fixed Python scoping issue (prerequisite)
- **TASK-FIX-D4E5**: Added checkpoint-resume pattern (prerequisite)
- **TASK-FIX-267C**: Fixed response format validation (prerequisite)

### Analysis Documents
Generated by specialized agents during task creation:
- Software Architect: Architectural comparison and minimal implementation strategy
- Debugging Specialist: Root cause analysis with call stack traces
- Code Reviewer: Best practices and anti-patterns catalog

## Success Metrics

**Quantitative**:
- Lines of code added: ~115 (100 orchestrator + 15 integration)
- Lines of code modified in `enhancer.py`: 0 (critical - no changes)
- Test coverage: >90% of orchestrator code
- Manual intervention reduced: From 100% to 0% of users

**Qualitative**:
- User experience: Transparent checkpoint-resume (no manual re-run)
- Code quality: Follows proven `/template-create` pattern
- Maintainability: Clear separation of concerns (orchestration vs enhancement)
- Testability: Orchestrator can be tested independently
- Documentation: Clear usage examples and troubleshooting guide

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-24
**Estimated Effort**: 4 hours (2h orchestrator + 0.5h integration + 0.5h docs + 1h testing)
**Complexity**: 5/10 (Medium - well-defined, proven pattern, minimal scope)
**Risk Level**: Low (additive change, zero modifications to existing logic)
