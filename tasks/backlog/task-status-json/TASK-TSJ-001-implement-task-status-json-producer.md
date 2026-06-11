---
id: TASK-TSJ-001
title: Implement task-status-json producer script
task_type: feature
parent_review: TASK-REV-9DDE
feature_id: FEAT-9DDE
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
priority: high
status: in_review
created: 2026-06-11 12:08:26+00:00
updated: 2026-06-11 12:08:26+00:00
tags:
- task-status
- json-output
- cli
- producer-script
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-9DDE
  base_branch: main
  started_at: '2026-06-11T13:21:03.594118'
  last_updated: '2026-06-11T13:39:45.963433'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-06-11T13:21:03.594118'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Implement task-status-json producer script

## Description

Create a deterministic Python producer script at `installer/core/commands/lib/task_status_json.py` that scans the project's `tasks/` directories, parses task frontmatter, and emits the task dashboard as stable, machine-readable JSON to stdout.

This is the deterministic producer for the `/task-status --json` flag — same pattern as `generate_feature_yaml.py` (R1) and `feature_plan_bdd_link.py` (R2). The JSON must be byte-stable across runs against the same task state: fixed key order, tasks sorted by `(status, id)`, missing frontmatter fields emitted as `null` (never omitted).

**Reuse, don't reimplement**: frontmatter parsing already exists in `installer/core/commands/lib/task_utils.py` (`parse_task_frontmatter`, `read_task_file`).

## JSON Schema (v1)

```json
{
  "schema_version": "1.0",
  "generated_at": "<ISO 8601 UTC>",
  "base_path": ".",
  "summary": {
    "backlog": 0, "in_progress": 0, "in_review": 0,
    "blocked": 0, "completed": 0, "total": 0
  },
  "tasks": [
    {
      "id": "TASK-XXXX",
      "title": "...",
      "status": "backlog",
      "priority": "high",
      "task_type": "feature",
      "complexity": 4,
      "tags": [],
      "created": "...",
      "updated": "...",
      "epic": null,
      "feature": null,
      "parent_review": null,
      "feature_id": null,
      "file_path": "tasks/backlog/TASK-XXXX-....md"
    }
  ]
}
```

## CLI Contract

```bash
python3 task_status_json.py [TASK-ID] [--base-path PATH]
```

- No args: full dashboard JSON (summary + all tasks)
- Positional `TASK-ID`: single-task JSON object (task shape only, no `summary`); exit 1 with stderr message if not found
- `--base-path`: project root (default: cwd)
- Output: `json.dumps(..., indent=2)` to stdout; nothing else on stdout

## Acceptance Criteria

- [ ] `installer/core/commands/lib/task_status_json.py` exists with a `main()` entry point and `if __name__ == "__main__":` guard
- [ ] Scans `tasks/backlog/`, `tasks/in_progress/`, `tasks/in_review/`, `tasks/blocked/`, `tasks/completed/` recursively (including feature subfolders like `tasks/backlog/{feature-slug}/` and archive folders like `tasks/completed/YYYY-MM/`)
- [ ] Parses frontmatter via `task_utils.parse_task_frontmatter` (no duplicate YAML-parsing logic)
- [ ] Emits schema v1 JSON to stdout with fixed key order and tasks sorted by `(status, id)`
- [ ] Missing frontmatter fields are emitted as `null`, never omitted
- [ ] Malformed frontmatter degrades gracefully: task entry emitted with `id` derived from filename and `"parse_error": true` (script never crashes on one bad file)
- [ ] Positional `TASK-ID` argument emits single-task JSON; unknown ID exits 1 with a stderr message
- [ ] Unit tests in `tests/unit/commands/test_task_status_json.py` cover: empty project, multi-state scan, nested feature subfolder, malformed frontmatter, single-task lookup, missing-task exit code, byte-stable output across two invocations
- [ ] All tests pass with `pytest tests/unit/commands/test_task_status_json.py -v`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- [ ] Unit tests using `tmp_path` fixtures with synthetic task trees
- [ ] Determinism test: two invocations against the same tree produce byte-identical output (excluding `generated_at`, which the test may freeze or strip)
- [ ] Coverage ≥80% line / ≥75% branch for the new module

## Implementation Notes

- Follow the structure of `installer/core/commands/lib/generate_feature_yaml.py` for argparse and stdout/stderr discipline.
- `generated_at` is the only non-deterministic field; everything else must be stable.
- Do NOT register the bin entry or touch command specs in this task — that is TASK-TSJ-002.
