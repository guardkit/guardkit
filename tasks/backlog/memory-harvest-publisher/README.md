# FEAT-HARV — Guardkit memory harvest publisher (P4)

Walk guardkit's curated knowledge artifacts and publish each as a canonical
`MemoryEpisodeV1` onto the NATS `MEMORY` stream via
`nats_core.NATSClient.publish_episode()`. First real publisher on the post-Graphiti
memory write path; idempotent and resumable.

- **Feature ID:** FEAT-HARV
- **Slug:** memory-harvest-publisher
- **Brief:** [`docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md`](../../../docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md)
- **Guide:** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md)
- **Planning record:** [`TASK-REV-HARV`](./TASK-REV-HARV-plan-memory-harvest-publisher.md)

## Tasks

| Wave | Task | Type | Cx | Summary |
|---|---|---|---|---|
| 1 | [TASK-HARV-002](./TASK-HARV-002-harvest-taxonomy-and-episode-id.md) | declarative | 3 | Curated taxonomy map + deterministic `episode_id` |
| 1 | [TASK-HARV-004](./TASK-HARV-004-nats-publisher-integration.md) | feature | 5 | Publisher: connect as `guardkit`, publish, 900 KB handling |
| 2 | [TASK-HARV-003](./TASK-HARV-003-harvest-walker.md) | feature | 5 | Walker: docs → `MemoryEpisodeV1` list + skip report |
| 3 | [TASK-HARV-005](./TASK-HARV-005-memory-harvest-cli.md) | feature | 4 | `guardkit memory harvest [--dry-run]` CLI |
| 4 | [TASK-HARV-006](./TASK-HARV-006-acceptance-tests.md) | testing | 3 | Acceptance suite (the brief's 4 contract tests) |
| 5 | [TASK-HARV-007](./TASK-HARV-007-live-gb10-harvest-run.md) | operator_handoff | 3 | Live GB10 run + G1 Postgres verification |

**Operator follow-up tasks: 1** (TASK-HARV-007 — run `/feature-complete` for the full
checklist post-merge).

> **Dependency pre-wired (no setup task).** The original TASK-HARV-001 ("wire `nats-core`")
> was folded into planning: `nats-core` is already declared in `pyproject.toml`
> (`[tool.uv.sources]` editable `../nats-core` + a `memory` extra), and the feature YAML
> sets `bootstrap_extras: [dev, memory]` so every wave's isolated worktree venv installs
> it. Verified: `import nats_core` resolves. See the planning record for why.

## Build

```bash
/feature-build FEAT-HARV
```

Waves 1–4 are AutoBuild-suitable, with a feature-level **smoke gate after wave 3**
(`python -m guardkit.cli.main memory harvest --dry-run`, NATS-free) verifying the assembled
walker→CLI runs before the acceptance wave. TASK-HARV-007 is `operator_handoff` — AutoBuild
skips it; run it manually on the GB10 after merge.

## Why this is next

The P3 relay is live and waiting on `memory.episode.>` but nothing publishes real
episodes yet. P4 unblocks **FEAT-MEM-07** (re-index) → **FEAT-MEM-05** (parity eval vs
the Graphiti baseline) → cutover → Graphiti decommission.
