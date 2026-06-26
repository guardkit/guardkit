---
id: TASK-HARV-002
title: Harvest taxonomy config and deterministic episode_id
task_type: declarative
status: in_review
created: 2026-06-25 00:00:00+00:00
updated: 2026-06-25 00:00:00+00:00
complexity: 3
parent_review: TASK-REV-HARV
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
wave: 1
implementation_mode: direct
depends_on: []
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-HARV
  base_branch: main
  started_at: '2026-06-26T11:49:53.398687'
  last_updated: '2026-06-26T11:56:31.590175'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-06-26T11:49:53.398687'
    player_summary: Implemented pure-Python harvest taxonomy configuration with no
      NATS or file I/O dependencies. Created HARVEST_MAP with curated allow-list mapping
      episode types to directories and content formats. Implemented deterministic
      episode_id derivation using SHA-256 hash (byte-identical to fleet-memory algorithm).
      Added comprehensive tests covering all acceptance criteria including determinism,
      NATS subject validation, and edge cases. All functions are well-documented with
      docstrings and examples.
    player_success: true
    coach_success: true
---

# TASK-HARV-002: Harvest taxonomy config and deterministic episode_id

## Objective

Pure-Python config + helpers — **no NATS, no file I/O** — that define (a) the curated
dir → `episode_type` → `content_format` map and (b) the deterministic `episode_id`
derivation. Keeping these pure makes the determinism test trivial and lets this task
run in wave 1 with no dependencies (the `nats-core` dependency is already wired into
`pyproject.toml` + the feature's `bootstrap_extras`, so no setup task is needed).

## Context

The downstream relay routes on `episode_type` and dedupes on
`Nats-Msg-Id = episode_id`. The idempotency guarantee in the brief holds **only** if
`episode_id` is a deterministic function of the artifact's natural key — the same algo
fleet-memory's re-index publisher uses, so the two publishers never disagree on a
shared key.

## Acceptance Criteria

- [ ] A module `guardkit/memory/harvest_taxonomy.py` defines `HARVEST_MAP`, the
      curated allow-list (config-driven, easy to extend):
      - `adr` ← `docs/adr`, `docs/adrs`, `docs/decisions` (`markdown`)
      - `review_report` ← `docs/reviews`, `docs/code-review` (`markdown`)
      - `feature_outcome` ← `docs/completion-reports`, `docs/retro` (`markdown`)
      - `document` ← `docs/design`, `docs/guides`, `docs/reference` (`markdown`)
      - transient dirs (`archive`, `checkpoints`, `state`, `history`) are **excluded**.
- [ ] `derive_episode_id(natural_key: str) -> str` returns
      `f"ep-{hashlib.sha256(natural_key.encode('utf-8')).hexdigest()[:16]}"` — the
      **byte-identical** algorithm to `fleet-memory`'s `_derive_episode_id`
      (`../fleet-memory/src/fleet_memory/reindex/publisher.py`).
- [ ] `natural_key_for(repo_relative_path, episode_type) -> str` returns the
      three-segment key `f"guardkit:{repo_relative_path}:{episode_type}"`.
- [ ] `episode_type_for(repo_relative_path) -> str | None` resolves a doc path to its
      `episode_type` via `HARVEST_MAP` (longest-prefix match), returning `None` for
      paths outside the allow-list.
- [ ] Every `episode_type` value is a valid NATS subject segment, i.e. matches
      `^[a-zA-Z0-9][a-zA-Z0-9\-_]*$` (assert in a unit test).
- [ ] Determinism unit test: the same `(path, episode_type)` yields the same
      `episode_id` across two separate calls (and is reproducible — no randomness, no
      wall-clock input).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- No imports from `nats_core` here — this task is intentionally dependency-free so it
  parallelises with the publisher (TASK-HARV-004). Building the `MemoryEpisodeV1`
  envelope is the walker's job (TASK-HARV-003).
- `HARVEST_MAP` shape: `dict[str, tuple[list[str], str]]` (episode_type →
  (dirs, content_format)) or an equivalent dataclass — keep it declarative.

## Coach Validation

```bash
pytest tests/ -v -k harvest_taxonomy
```
