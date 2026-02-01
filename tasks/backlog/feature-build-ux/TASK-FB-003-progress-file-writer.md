---
id: TASK-FB-003
title: Add Progress File Writer for External Monitoring
status: backlog
created: 2025-01-31T16:00:00Z
priority: high
tags: [feature-build, ux, progress, phase-1]
complexity: 4
implementation_mode: task-work
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 1
dependencies: [TASK-FB-001]
---

# Task: Add Progress File Writer for External Monitoring

## Context

Claude Code Bash tool buffers output until command completion. To provide progress visibility, AutoBuild should write progress to a JSON file that can be polled externally.

This is a **stepping stone** toward Phase 2's NATS event streaming. The file-based approach provides immediate value while the event infrastructure is built.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Add progress file writing to `AutoBuildOrchestrator`:

1. Write progress JSON after each turn phase change
2. Use `.guardkit/autobuild/{task_id}/progress.json` location
3. Include: wave, task, turn, phase, elapsed, metrics
4. Atomic write (write to temp, rename) to avoid partial reads

## Acceptance Criteria

- [ ] Progress file created at `.guardkit/autobuild/{task_id}/progress.json`
- [ ] File updated at: turn start, turn complete, build complete
- [ ] JSON schema matches specification below
- [ ] Atomic write via temp file + rename
- [ ] File includes `updated_at` timestamp for polling freshness
- [ ] Existing tests pass
- [ ] Unit tests for progress file writer added

## JSON Schema

```json
{
  "build_id": "TASK-FB-002",
  "build_type": "task",
  "status": "running",
  "wave": 1,
  "wave_total": 1,
  "task_id": "TASK-FB-002",
  "task_name": "Implement text output fallback",
  "turn": 2,
  "turn_max": 5,
  "phase": "Coach Validation",
  "phase_status": "in_progress",
  "metrics": {
    "elapsed_seconds": 245,
    "files_created": 2,
    "files_modified": 1,
    "tests_passed": 5,
    "tests_total": 5
  },
  "started_at": "2025-01-31T12:34:56Z",
  "updated_at": "2025-01-31T12:38:41Z"
}
```

## Implementation Notes

```python
# In AutoBuildOrchestrator
from pathlib import Path
import json
import tempfile
import shutil

def _write_progress(self, task_id: str, data: dict) -> None:
    """Write progress to JSON file atomically."""
    progress_dir = self.repo_root / ".guardkit" / "autobuild" / task_id
    progress_dir.mkdir(parents=True, exist_ok=True)
    progress_file = progress_dir / "progress.json"

    # Add timestamp
    data["updated_at"] = datetime.now().isoformat() + "Z"

    # Atomic write: temp file + rename
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=progress_dir,
        suffix='.tmp',
        delete=False
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name

    shutil.move(tmp_path, progress_file)
    logger.debug(f"Progress written to {progress_file}")
```

## Files to Modify

- `guardkit/orchestrator/autobuild.py` - Add progress file writer
- `tests/unit/test_autobuild_orchestrator.py` - Add progress file tests

## Dependencies

- TASK-FB-001 (uses same progress data structure concepts)

## Future: Phase 2 Evolution

In Phase 2, this progress data will be **published to NATS** instead of/in addition to file:

```python
# Phase 2 (future)
await nats_client.publish(
    f"guardkit.builds.{task_id}.status",
    json.dumps(progress_data)
)
```

The JSON schema is designed for forward compatibility with NATS message envelope.
