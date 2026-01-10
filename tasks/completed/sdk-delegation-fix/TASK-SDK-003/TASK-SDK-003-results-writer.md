---
id: TASK-SDK-003
title: Create task_work_results.json writer
status: completed
task_type: implementation
created: 2026-01-10T11:00:00Z
completed: 2026-01-10T17:30:00Z
priority: high
tags: [sdk-delegation, results-file, coach-validation, feature-build]
complexity: 4
wave: 2
parent_feature: sdk-delegation-fix
depends_on:
  - TASK-SDK-001
  - TASK-SDK-002
completed_location: tasks/completed/sdk-delegation-fix/TASK-SDK-003/
organized_files: ["TASK-SDK-003-results-writer.md"]
---

# Create task_work_results.json writer

## Description

Implement a method to write the parsed quality gate results to `task_work_results.json` in the format expected by Coach validation.

## Target Implementation

```python
def _write_task_work_results(self, task_id: str, result_data: dict) -> Path:
    """
    Write task-work results to JSON file for Coach validation.

    Location: .guardkit/autobuild/{task_id}/task_work_results.json
    """
    import json
    from datetime import datetime

    results_dir = self.worktree_path / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / "task_work_results.json"

    # Build structured results
    results = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "completed": result_data.get("completed", False),
        "phases": result_data.get("phases", {}),
        "quality_gates": {
            "tests_passing": result_data.get("tests_failed", 0) == 0,
            "tests_passed": result_data.get("tests_passed", 0),
            "tests_failed": result_data.get("tests_failed", 0),
            "coverage": result_data.get("coverage"),
            "coverage_met": (result_data.get("coverage", 0) >= 80),
            "all_passed": result_data.get("quality_gates_passed", False)
        },
        "files_modified": list(set(result_data.get("files_modified", []))),
        "files_created": list(set(result_data.get("files_created", []))),
        "summary": self._generate_summary(result_data)
    }

    results_file.write_text(json.dumps(results, indent=2))
    self.logger.info(f"Wrote task_work_results.json to {results_file}")

    return results_file

def _generate_summary(self, result_data: dict) -> str:
    """Generate human-readable summary from results."""
    parts = []

    if result_data.get("tests_passed"):
        parts.append(f"{result_data['tests_passed']} tests passed")

    if result_data.get("coverage"):
        parts.append(f"{result_data['coverage']}% coverage")

    if result_data.get("quality_gates_passed"):
        parts.append("all quality gates passed")
    elif result_data.get("quality_gates_passed") is False:
        parts.append("quality gates failed")

    return ", ".join(parts) if parts else "Implementation completed"
```

## Expected Output Schema

```json
{
  "task_id": "TASK-XXX",
  "timestamp": "2026-01-10T11:30:00Z",
  "completed": true,
  "phases": {
    "phase_3": {"detected": true, "text": "Implementation"},
    "phase_4": {"detected": true, "text": "Testing"},
    "phase_4.5": {"detected": true, "text": "Test enforcement"},
    "phase_5": {"detected": true, "text": "Code review"}
  },
  "quality_gates": {
    "tests_passing": true,
    "tests_passed": 12,
    "tests_failed": 0,
    "coverage": 85.5,
    "coverage_met": true,
    "all_passed": true
  },
  "files_modified": ["src/auth.py"],
  "files_created": ["tests/test_auth.py"],
  "summary": "12 tests passed, 85.5% coverage, all quality gates passed"
}
```

## Acceptance Criteria

- [x] Results file written to correct location
- [x] Directory created if not exists
- [x] JSON format matches Coach expectations
- [x] Handles missing/partial data gracefully
- [x] Deduplicates file lists
- [x] Generates readable summary
- [x] Logs file location on write
- [x] Unit tests for writer
- [ ] Integration test with Coach validator (deferred to TASK-SDK-004)

## Coach Validation Reference

Coach reads results from: `guardkit/orchestrator/quality_gates/coach_validator.py:395`

```python
results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"
```

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` - Add `_write_task_work_results` method
- `tests/unit/test_agent_invoker.py` - Add writer tests

## Related

- TASK-SDK-001: SDK query (dependency)
- TASK-SDK-002: Stream parser (dependency)
- TASK-SDK-004: Integration testing (dependent)
