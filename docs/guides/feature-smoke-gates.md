# Feature-Level Smoke Gates Between AutoBuild Waves

**Task**: TASK-SMK-F703A — follow-on from TASK-REV-4D012 §6 R3
**Status**: shipped

## What this is

A smoke gate is a single subprocess invocation run inside the feature's
shared worktree **after a specified wave of tasks completes**. Its only
job is to catch **composition failures** that the per-task Player-Coach
loop cannot see — the kind where every individual task is Coach-approved
but the assembled whole is broken.

The review that created this task found a real case: FEAT-POR-EXT
reported 13/13 tasks Coach-approved and then failed on the first
`--phase roadmap` smoke test with 129 `ProductRoadmap.model_validate`
errors. Six patch tasks were filed over ~36 hours. Each bug would have
been caught by a `pytest --phase roadmap` smoke run between waves, well
before `/feature-build` completed.

## The placement rule (important)

> **Smoke gates run between WAVES, not between TASKS.**

- Per-task smoke = per-task Coach with extra steps. Noisy. Wrong scope.
- Per-wave smoke = composition starts to matter (one wave's outputs feed
  the next). Right scope.

If you find yourself reaching for a per-task smoke variant, the design
has slipped. The per-task Coach already validates per-task quality; a
second validator at the same boundary adds latency without signal.

## Configuration

Add an optional `smoke_gates` section to your `.guardkit/features/FEAT-*.yaml`:

```yaml
id: FEAT-POR-EXT
name: Product Roadmap Extractor
tasks:
  - id: TASK-POR-001
    file_path: tasks/backlog/por-ext/TASK-POR-001.md
  - id: TASK-POR-002
    file_path: tasks/backlog/por-ext/TASK-POR-002.md
orchestration:
  parallel_groups:
    - [TASK-POR-001]
    - [TASK-POR-002]
  estimated_duration_minutes: 60
  recommended_parallel: 1
smoke_gates:
  after_wave: 1
  command: "python -m specialist_agent extract --phase A --smoke-fixture docs/smoke/fixture.md"
  expected_exit: 0
  timeout: 120
```

### Field reference

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `after_wave` | int, list of ints, or `"all"` | required | Which wave(s) to fire after. Waves are 1-indexed and correspond to `orchestration.parallel_groups`. |
| `command` | str | required | Shell command to execute in the worktree. Non-empty. |
| `expected_exit` | int | `0` | Exit code that signals success. |
| `timeout` | int | `120` | Seconds before the subprocess is killed. Bounded `[1, 600]`. |

Unknown keys under `smoke_gates` are **rejected** (`extra="forbid"`).

### Choosing `after_wave`

- `after_wave: 1` — after topological level 1 completes (typical for
  "does the wave-1 slice compile and import cleanly?" smokes).
- `after_wave: [1, 3]` — after waves 1 and 3. Use when each checkpoint
  is independently meaningful.
- `after_wave: "all"` — after every wave. Use for cheap smokes where
  you want the earliest possible signal.

The wave numbers come from `orchestration.parallel_groups` — the feature
plan is the source of truth. The smoke gate never invents waves.

## What happens on failure

When the smoke gate's exit code differs from `expected_exit` (or it
times out):

1. Subsequent waves are **not started**.
2. The worktree is **preserved** for human triage
   (`.guardkit/worktrees/FEAT-X/`).
3. The feature status is set to `failed`.
4. The final `/feature-build` summary reports the smoke failure with
   exit code, command, and timeout state.

## Running a whole-feature BDD spec as a smoke gate

If your feature has a whole-feature `.feature` file (no `@task:<TASK-ID>`
tags — those belong to task-level BDD, TASK-BDD-E8954's territory), you
can point a smoke gate at it:

```yaml
smoke_gates:
  after_wave: "all"
  command: "pytest features/FEAT-POR-EXT.feature -q"
  timeout: 180
```

This is how feature-level BDD composition is validated — completing the
scoping boundary with R2.

## Zero-regression guarantee

Features without a `smoke_gates` key run identically to before — the
key is opt-in, has no default, and the code path is a pure no-op when
absent. The regression test
`tests/integration/autobuild/test_smoke_gate_noop.py` pins this.

## Non-goals

- **No per-task variant.** See the placement rule above.
- **No auto-detection of smoke commands.** You write the command.
- **No new integration-runner subsystem.** It's a subprocess with a
  timeout. That's deliberately boring.
- **No second wave concept.** Waves come from the feature-plan
  dependency graph already encoded in `FEAT-*.yaml`.

## Schema reference

See [`docs/schemas/feature-yaml.md`](../schemas/feature-yaml.md) for the
full `FEAT-*.yaml` schema including `smoke_gates`.

## Related

- Review that produced this: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` §6 R3
- Sibling task-level BDD: TASK-BDD-E8954 (`@task:<TASK-ID>`-scoped BDD)
- Graphiti pattern: `"Review-gate hole: AutoBuild 13/13 green + e2e broken"`
