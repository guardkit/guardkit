# Implementation Guide: SDK-Based Task-Work Delegation

## Wave Breakdown

### Wave 1: Core SDK Integration (Parallel)

**TASK-SDK-001** and **TASK-SDK-002** can run in parallel.

| Task | Focus | Files |
|------|-------|-------|
| TASK-SDK-001 | Replace subprocess with SDK query | `agent_invoker.py` |
| TASK-SDK-002 | Implement stream parser | `agent_invoker.py` (new methods) |

### Wave 2: Results Writer

**TASK-SDK-003** depends on Wave 1.

| Task | Focus | Files |
|------|-------|-------|
| TASK-SDK-003 | Create task_work_results.json writer | `agent_invoker.py` |

### Wave 3: Integration Testing

**TASK-SDK-004** depends on all previous waves.

| Task | Focus | Files |
|------|-------|-------|
| TASK-SDK-004 | End-to-end testing | `tests/integration/` |

## Technical Details

### SDK Query Pattern (from existing code)

Reference: `agent_invoker.py:714-797` (`_invoke_with_role` method)

```python
async def _invoke_task_work_implement(self, task_id: str, mode: str) -> TaskWorkResult:
    options = ClaudeAgentOptions(
        cwd=str(self.worktree_path),
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
        permission_mode="acceptEdits",
        max_turns=50,
        setting_sources=["project"],
    )

    result_data = {}
    async with asyncio.timeout(self.sdk_timeout_seconds):
        async for message in query(
            prompt=f"/task-work {task_id} --implement-only --mode={mode}",
            options=options
        ):
            if message.type == "assistant":
                text = extract_text(message)
                result_data = self._parse_task_work_stream(text, result_data)
            elif message.type == "result":
                result_data["completed"] = True

    self._write_task_work_results(task_id, result_data)
    return TaskWorkResult(success=result_data.get("completed", False), output=result_data)
```

### Stream Parsing Strategy

Parse these patterns from task-work output:

1. **Phase completion markers**: `Phase N: ...` or `✓ Phase N complete`
2. **Test results**: `X tests passed`, `X tests failed`
3. **Coverage metrics**: `Coverage: XX%`
4. **Quality gate status**: `Quality gates: PASSED/FAILED`
5. **Files modified**: `Modified: file.py`, `Created: file.py`

### Results File Schema

```json
{
  "task_id": "TASK-XXX",
  "completed": true,
  "phases": {
    "phase_3": {"status": "passed", "duration": 45},
    "phase_4": {"status": "passed", "tests_passed": 12, "tests_failed": 0},
    "phase_4_5": {"status": "passed", "fix_attempts": 0},
    "phase_5": {"status": "passed", "score": 85}
  },
  "quality_gates": {
    "tests_passing": true,
    "coverage_met": true,
    "code_review_passed": true
  },
  "files_modified": ["src/auth.py"],
  "files_created": ["tests/test_auth.py"],
  "summary": "Implementation complete with all quality gates passed"
}
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Stream parsing fails | Fallback to git-based detection (files changed, tests run) |
| Timeout handling | Use existing `sdk_timeout_seconds` with `asyncio.timeout()` |
| Command not found in worktree | Verify `.claude/commands/task-work.md` exists at worktree creation |

## Verification

After implementation:

```bash
# Run unit tests
pytest tests/unit/test_agent_invoker.py -v

# Run integration test
guardkit autobuild task TASK-TEST-001 --verbose

# Verify task_work_results.json created
cat .guardkit/autobuild/TASK-TEST-001/task_work_results.json
```
