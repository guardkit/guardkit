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
| `bootstrap_extras` | list[str] | no | PEP 621 optional-dependency group names (e.g. `[dev]`) installed by the worktree bootstrap. See "Bootstrap extras" below (TASK-GK-BS-001). |
| `preflight_strict` | bool | no | Default `false`. When `true`, the feature orchestrator aborts before wave 1 dispatch if any task declares a `## Files to Modify` path that does not exist under `repo_root` or `worktree_path`. When `false`, missing modify paths are logged as `WARNING` and orchestration proceeds (the existing plan-audit gate at Player turn 1 catches them, just slower). See "Path-existence preflight" below (TASK-GK-PR-001). |

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

## Bootstrap extras (TASK-GK-BS-001)

Optional list of PEP 621 [optional-dependencies] group names that the
worktree environment bootstrap should install alongside the project's
base dependencies. Required when a smoke gate (or any other in-worktree
command) depends on packages that the project intentionally keeps out
of its base `dependencies` (e.g. `pytest`, `pytest-bdd`).

```yaml
bootstrap_extras: [dev]            # uv pip install -e ".[dev]"
# or
bootstrap_extras: [test, integration]  # uv pip install -e ".[test,integration]"
```

| Validation | Rule |
|------------|------|
| Type | `list[str]` |
| Default | `[]` (no extras — preserves pre-TASK-GK-BS-001 behaviour) |
| Name regex | `^[A-Za-z0-9._-]+$` (matches PyPA / PEP 621 extras spec) |
| Persistence | Empty lists are dropped from YAML on save. |

### Auto-detection from a pytest smoke gate

When `bootstrap_extras` is **unset or empty** AND `smoke_gates.command`
contains the literal `pytest` (case-insensitive, word-boundary match),
the orchestrator probes the worktree's `pyproject.toml` for a canonical
test-extras group:

1. `[project.optional-dependencies].dev` — preferred (PyPA convention
   for "everything a contributor needs").
2. `[project.optional-dependencies].test` — narrower fallback.
3. Neither declared → log a warning and proceed with no extras (the
   smoke gate will fail with `No module named pytest`, which is the
   actionable signal the operator needs).

This makes the common "pytest smoke gate against a project that already
declares `[dev]`" case work without per-feature configuration. To opt
out of auto-detection, declare `bootstrap_extras` explicitly — operator
declaration always wins.

### `uv sync --frozen` caveat

When the project has a `uv.lock`, the bootstrap uses `uv sync --frozen`
(per the install-matrix in `environment_bootstrap.py`). `uv.lock` bakes
extras at lock time, not install time, so applying `bootstrap_extras`
to this row would diverge from the frozen lock. Instead the
orchestrator emits a warning naming the lock-time fix:

```
uv lock --extra <ext1>,<ext2>
```

If you need extras to be present in the worktree's venv when `uv.lock`
exists, regenerate the lock with the extras included rather than
relying on `bootstrap_extras` at install time.

## Path-existence preflight (TASK-GK-PR-001)

Before wave 1 dispatch, the feature orchestrator probes every queued
task's `## Files to Modify` declarations against the filesystem. If
any declared path does not exist at either `repo_root / path` or
`worktree_path / path`, the operator sees a structured warning naming
the task, the line in the task body, and up to three close on-disk
matches via `difflib.get_close_matches`:

```
WARNING: TYPO in TASK-XXX line 157 (## Files to Modify):
  declared: src/example/typo/path.py
  not on disk under repo_root or worktree_path
  closest matches (top 3):
    - src/example/real/path.py (similarity 0.74)
    - src/example/other.py     (similarity 0.42)
```

The check fires in <1s for ≤50 tasks. It catches a class of
task-author typo that the existing plan-audit gate would otherwise
take 25-35 minutes to surface (4 turns of identical missing-files
feedback before `max_turns_exceeded` or `timeout_budget_exhausted`).

```yaml
preflight_strict: true   # opt-in: abort before wave dispatch on any
                         # modify-axis typo. Default `false` is
                         # warning-only — orchestration proceeds and
                         # plan-audit catches the typo at Player turn 1.
```

`## Files to Create` declarations are checked symmetrically: a path
that already exists on disk emits a warning ("is this a re-run?") but
never aborts orchestration, since legitimate re-runs in a preserved
worktree are common.

The check skips paths whose extension is not in the indexed source
list (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.cs`, `.go`, `.java`,
`.rb`, `.rs`); documentation and config bullets pass through silently.

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
