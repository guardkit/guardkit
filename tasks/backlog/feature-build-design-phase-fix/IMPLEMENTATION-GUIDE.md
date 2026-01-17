# Implementation Guide: Feature-Build Design Phase Fix

## Wave Breakdown

### Wave 1: Core Fix (Parallel)

Execute these tasks in parallel using Conductor workspaces:

| Task | Workspace | Description |
|------|-----------|-------------|
| TASK-FB-FIX-001 | fb-fix-wave1-1 | Fix TaskWorkInterface SDK invocation |
| TASK-FB-FIX-002 | fb-fix-wave1-2 | Add plan validation in pre-loop |

**Wave 1 Completion Criteria**:
- TaskWorkInterface actually invokes SDK
- Pre-loop validates plan file exists before returning success

### Wave 2: Cleanup & Testing (Parallel)

Execute after Wave 1 completes:

| Task | Workspace | Description |
|------|-----------|-------------|
| TASK-FB-FIX-003 | fb-fix-wave2-1 | Centralize path logic |
| TASK-FB-FIX-004 | fb-fix-wave2-2 | Add integration test |

**Wave 2 Completion Criteria**:
- Path logic centralized in TaskArtifactPaths utility
- Integration test passes for pre-loop + Player flow

## Execution Strategy

### Option A: Sequential (Safe)

```bash
# Wave 1
/task-work TASK-FB-FIX-001
/task-work TASK-FB-FIX-002

# Wave 2 (after Wave 1 completes)
/task-work TASK-FB-FIX-003
/task-work TASK-FB-FIX-004
```

### Option B: Parallel with Conductor (Faster)

```bash
# Wave 1 - parallel
conductor create fb-fix-wave1-1
conductor create fb-fix-wave1-2

# In workspace fb-fix-wave1-1:
/task-work TASK-FB-FIX-001

# In workspace fb-fix-wave1-2:
/task-work TASK-FB-FIX-002

# Merge Wave 1, then Wave 2
conductor create fb-fix-wave2-1
conductor create fb-fix-wave2-2
# ...
```

## Key Implementation Notes

### TASK-FB-FIX-001: Fix TaskWorkInterface

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

**Current (Broken)**:
```python
def execute_design_phase(self, task_id: str, options: Dict) -> DesignPhaseResult:
    # Returns mock data - THIS IS THE BUG
    return DesignPhaseResult(
        implementation_plan={},
        plan_path=None,
        complexity={"score": 5},
        architectural_review={"score": 80},
        ...
    )
```

**Expected (Fixed)**:
```python
async def execute_design_phase(self, task_id: str, options: Dict) -> DesignPhaseResult:
    client = await self._get_sdk_client()
    result = await client.query(
        prompt=f"/task-work {task_id} --design-only --no-questions",
        working_directory=str(self.worktree_path),
        ...
    )
    return self._parse_design_result(result)
```

### TASK-FB-FIX-002: Add Plan Validation

**File**: `guardkit/orchestrator/quality_gates/pre_loop.py`

Add validation before returning success:
```python
def _extract_pre_loop_results(self, task_id: str, result: DesignPhaseResult) -> PreLoopResult:
    # NEW: Validate plan exists
    plan_path = self._get_plan_path(task_id, result.plan_path)
    if not plan_path or not Path(plan_path).exists():
        raise QualityGateBlocked(
            f"Design phase did not generate implementation plan for {task_id}. "
            f"Expected at: {plan_path}"
        )

    # ... rest of extraction
```

### TASK-FB-FIX-003: Centralize Path Logic

**New File**: `guardkit/orchestrator/paths.py`

```python
class TaskArtifactPaths:
    """Centralized path resolution for task artifacts."""

    PLAN_LOCATIONS = [
        ".claude/task-plans/{task_id}-implementation-plan.md",
        ".claude/task-plans/{task_id}-implementation-plan.json",
        "docs/state/{task_id}/implementation_plan.md",
        "docs/state/{task_id}/implementation_plan.json",
    ]

    @classmethod
    def implementation_plan(cls, task_id: str, worktree: Path) -> List[Path]:
        return [worktree / loc.format(task_id=task_id) for loc in cls.PLAN_LOCATIONS]

    @classmethod
    def find_plan(cls, task_id: str, worktree: Path) -> Optional[Path]:
        for path in cls.implementation_plan(task_id, worktree):
            if path.exists():
                return path
        return None
```

### TASK-FB-FIX-004: Integration Test

**New File**: `tests/integration/test_preloop_player_flow.py`

```python
@pytest.mark.asyncio
async def test_preloop_creates_plan_for_player():
    """Verify pre-loop creates plan that Player can read."""
    # Given: A task in backlog with valid requirements
    task_id = "TASK-TEST-001"

    # When: Pre-loop executes
    gates = PreLoopQualityGates(worktree_path)
    result = await gates.execute(task_id, {"no_questions": True})

    # Then: Plan file exists
    assert result.plan_path is not None
    assert Path(result.plan_path).exists()

    # And: Player can read it
    invoker = AgentInvoker(worktree_path)
    plan_content = invoker._load_implementation_plan(task_id)
    assert plan_content is not None
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SDK invocation within SDK | Use separate SDK session for design phase |
| Timeout during design phase | Pass sdk_timeout from orchestrator config |
| Plan format mismatch | Validate plan schema after creation |
| Breaking existing tests | Run full test suite before merge |

## Success Verification

After all tasks complete:

```bash
# Run integration test
pytest tests/integration/test_preloop_player_flow.py -v

# Run feature-build on test task
guardkit autobuild task TASK-TEST-001 --max-turns 3

# Verify plan was created
ls -la .guardkit/worktrees/TASK-TEST-001/.claude/task-plans/
```
