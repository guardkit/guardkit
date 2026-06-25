---
id: TASK-REV-HARV
title: "Plan: Guardkit memory harvest publisher (P4)"
task_type: review
status: review_complete
created: 2026-06-25T00:00:00Z
updated: 2026-06-25T00:00:00Z
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
clarification:
  context_a:
    decisions:
      harvest_scope: curated_subset_config_driven
      cli_surface: new_guardkit_memory_group
      oversized_handling: skip_and_report
      live_gb10_run: include_as_operator_handoff
---

# Plan: Guardkit memory harvest publisher (P4)

Planning record for `FEAT-HARV`. Source of truth: the P4 feature brief at
[`docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md`](../../../docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md)
plus the contract verification performed during `/feature-plan` (2026-06-25).

## What was verified against real code (not the brief's prose)

- **CLI surface**: guardkit uses Click; subcommands live in `guardkit/cli/` and
  register in [`guardkit/cli/main.py`](../../../guardkit/cli/main.py) via
  `cli.add_command(...)`.
- **`nats_core` contract** (`../nats-core/src/nats_core/`):
  `NATSConfig(url, user, password: SecretStr, name)` →
  `connect()` / `publish_episode(episode)` / `disconnect()`.
  `publish_episode` resolves `memory.episode.{project_id}.{episode_type}`,
  sets the `Nats-Msg-Id` header, and raises `ValueError` when the encoded body
  exceeds `MAX_EPISODE_BODY_BYTES` (900 KB).
- **Idempotency pattern to mirror**: `fleet-memory`'s
  `_derive_episode_id(natural_key) = f"ep-{sha256(natural_key).hexdigest()[:16]}"`.
- **Dependency wiring**: `nats-core` is **not installed** in guardkit's env — it
  is sibling `../nats-core` (pkg `nats-core` v0.4.0). guardkit pulls siblings via
  `[tool.uv.sources]` editable paths (the `guardkitfactory` pattern at
  `pyproject.toml:110`).
- **Harvest volume (today)**: 456 `.md` under the curated allow-list (331 in
  `docs/reviews`). **8+ docs already exceed 900 KB** (e.g.
  `docs/reviews/reduce-static-markdown/reseed_guardkit_4.md` ≈ 2.3 MB) — the
  oversized-skip path fires on the first run; it is a real, testable case.

## Decisions (clarification answers, 2026-06-25)

1. **Harvest scope** — curated, config-driven allow-list (not the whole `docs/`
   tree). Excludes transient/archive dirs (`archive`, `checkpoints`, `state`,
   `history`) to keep the downstream parity eval high-signal. The map is config
   so dirs are cheap to add later.
2. **CLI surface** — new `guardkit memory` Click group (`guardkit memory harvest
   [--dry-run]`). This is the post-Graphiti memory write path; future memory
   subcommands fit under it. (Deliberately NOT under `guardkit graphiti`, which
   is being decommissioned downstream — FEAT-MEM-09.)
3. **Oversized docs (>900 KB body)** — skip + report (path + byte size) and
   continue; never abort the run. Auto-chunking deferred (the relay already
   prose-chunks each received episode).
4. **Live GB10 run** — included as a `task_type: operator_handoff` task
   (TASK-HARV-007). AutoBuild will not attempt it; the operator runs it
   post-merge and ticks the runtime ACs via `/feature-complete`.

## Pre-build de-risk (applied 2026-06-25, before `/feature-build`)

A focused investigation of the AutoBuild **worktree-venv bootstrap** changed two
things in the plan:

1. **`nats-core` dependency wired now (TASK-HARV-001 removed).** AutoBuild
   bootstraps an *isolated* worktree-local venv at
   `<repo>/.guardkit/worktrees/<feat>/.venv` via `uv pip install -e .[<extras>]`,
   and **by default installs only `[dev]`** (`env_bootstrap.derive_bootstrap_extras`).
   So a `memory` extra alone would never be installed, and a wave-1 "wire the dep"
   task could not make `import nats_core` work for itself. The robust fix is
   repo-level config, applied at planning time:
   - `pyproject.toml`: `[tool.uv.sources] nats-core = { path = "../nats-core",
     editable = true }` + a `memory = ["nats-core>=0.4,<1"]` extra (+ added to `all`).
     The relative `../nats-core` resolves from the nested worktree via the
     orchestrator's auto-created **bridging symlink** (same mechanism proven for
     `guardkitfactory`).
   - `FEAT-HARV.yaml`: top-level **`bootstrap_extras: [dev, memory]`** — the
     decisive lever that threads `memory` into the worktree install. `dev` is kept
     because operator-declared extras *suppress* the Coach-needs-pytest auto-add;
     dropping it would break the Coach independent-test gate.
   - Verified: `uv pip install -e .[memory]` builds editable `nats-core==0.4.0`
     (pulls `nats-py`), and `import nats_core` resolves
     (`MAX_EPISODE_BODY_BYTES == 921600`).
   - The original TASK-HARV-001 ("wire nats-core") is therefore redundant and was
     removed; the 6 remaining tasks renumber-free (002–007).
2. **Feature-level smoke gate added.** `FEAT-HARV.yaml` `smoke_gates:` fires
   `python -m guardkit.cli.main memory harvest --dry-run` **after wave 3** (the CLI
   wave). It exercises the assembled walker→CLI (catching composition/import
   failures the per-task Coach misses) with **no live broker** (`--dry-run`
   short-circuits before any NATS connect). `python -m …` is used (not the
   `guardkit-py` console script) so it resolves via the worktree venv interpreter +
   editable package, independent of console-script PATH. Failures feed back to the
   Player (per the smoke-gate-is-feedback rule), bounded by
   `GUARDKIT_SMOKE_GATE_MAX_RETRIES`.

## Out of scope (do NOT re-plan)

- The broker user `guardkit` — already provisioned + verified live
  (`nats-infrastructure` commit `5c3b8df`). The harvest only *reads*
  `GUARDKIT_NATS_PASSWORD` and connects.
- NATS subject building, the `Nats-Msg-Id` header, the 900 KB guard — owned by
  `nats_core.publish_episode`. Do not hand-roll.
- The `nats-core` dependency wiring — done (see Pre-build de-risk above). Do not
  re-add a "wire nats-core" task.
- Downstream chain (FEAT-MEM-07 re-index → FEAT-MEM-05 parity → cutover).
