# `.guardkit/features/FEAT-*.yaml` schema

The authoritative schema for feature definitions consumed by
`/feature-build` (feature mode). This reference covers the core fields
plus the optional `smoke_gates` section added by TASK-SMK-F703A.

For the Pydantic source of truth, see
`guardkit/orchestrator/feature_loader.py`.

## Top-level keys

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `id` | str | yes | `FEAT-{hash}` identifier. |
| `name` | str | yes | Human-readable feature name. |
| `description` | str | no | Free-form summary. |
| `created` | str (ISO 8601) | no | Auto-populated by `/feature-plan`. |
| `status` | enum | no | `planned`, `in_progress`, `completed`, `failed`, `paused`. |
| `complexity` | int (1-10) | no | Aggregate complexity from `/feature-plan`. |
| `estimated_tasks` | int | no | Set by `/feature-plan`. |
| `tasks` | list | yes | See "Task schema" below. |
| `orchestration` | object | yes | See "Orchestration schema" below. |
| `execution` | object | no | Runtime state; managed by the orchestrator. |
| `smoke_gates` | object | **no** | See "Smoke gates schema" below (TASK-SMK-F703A). |

## Task schema

Each entry in `tasks`:

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `id` | str | yes | `TASK-*` identifier. |
| `file_path` | str | yes | Path to the task markdown file. |
| `name` | str | no | Defaults to `id`. |
| `complexity` | int (1-10) | no | Default 5. |
| `dependencies` | list[str] | no | Task IDs this depends on. |
| `status` | enum | no | `pending`, `in_progress`, `completed`, `failed`, `skipped`. |
| `implementation_mode` | enum | no | `task-work`, `direct`, `manual`. |
| `estimated_minutes` | int | no | Default 30. |
| `requires_infrastructure` | list[str] | no | e.g. `["postgresql", "redis"]`. |

## Orchestration schema

```yaml
orchestration:
  parallel_groups:
    - [TASK-A, TASK-B]     # wave 1 (runs in parallel)
    - [TASK-C]             # wave 2 (depends on wave 1)
  estimated_duration_minutes: 90
  recommended_parallel: 2
```

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `parallel_groups` | list of list of task IDs | yes | Topological levels from the dependency graph. Each inner list is one wave. |
| `estimated_duration_minutes` | int | no | Default 0. |
| `recommended_parallel` | int | no | Default 1. |

## Smoke gates schema (TASK-SMK-F703A)

Optional section that runs a single subprocess inside the shared worktree
**between waves** — not between tasks. See
[`docs/guides/feature-smoke-gates.md`](../guides/feature-smoke-gates.md)
for motivation, placement rules, and examples.

```yaml
smoke_gates:
  after_wave: 1                         # 1 | [1, 3] | "all"
  command: "pytest features/FEAT-X.feature -q"
  expected_exit: 0                      # default 0
  timeout: 120                          # default 120, bounded [1, 600]
```

| Key | Type | Required | Default | Notes |
|-----|------|----------|---------|-------|
| `after_wave` | int, list[int], or `"all"` | yes | — | Waves are 1-indexed and must come from `parallel_groups`. Rejects `0`, negative values, empty lists, booleans, and arbitrary strings. |
| `command` | str | yes | — | Shell command. Non-empty. Run with `shell=True` in the worktree. |
| `expected_exit` | int | no | `0` | Exit code that signals success. |
| `timeout` | int | no | `120` | Seconds before the subprocess is killed. Bounded `[1, 600]` so `/feature-build` stays deterministic. |

**Unknown keys are rejected** (`extra="forbid"`). A typo like
`after_ave: 1` fails fast with `SchemaValidationError` before
`/feature-build` starts, rather than silently ignoring the intent.

### Failure behaviour

- Exit code ≠ `expected_exit` → feature build stops; subsequent waves do
  not start; worktree preserved; final summary reports the failure.
- Timeout → treated as failure; `timed_out` set on the result.

### Relationship to the wave definition

The smoke gate never computes waves. It receives the 1-indexed wave
number from the orchestrator, which iterates
`enumerate(parallel_groups, 1)`. If the orchestrator and the smoke
gate ever disagreed on what "wave 1" is, that would be a bug —
`guardkit/orchestrator/smoke_gates.py::should_fire_for_wave` takes the
wave number as input precisely to rule this out.

## Minimal valid example

```yaml
id: FEAT-EXAMPLE
name: Example feature
tasks:
  - id: TASK-EX-001
    file_path: tasks/backlog/example/TASK-EX-001.md
  - id: TASK-EX-002
    file_path: tasks/backlog/example/TASK-EX-002.md
orchestration:
  parallel_groups:
    - [TASK-EX-001]
    - [TASK-EX-002]
  estimated_duration_minutes: 30
  recommended_parallel: 1
# smoke_gates omitted — feature runs identically to before TASK-SMK-F703A.
```
