---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-06-26T12:12:23.620381'
  max_turns: 5
  started_at: '2026-06-26T12:01:44.431085'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    timestamp: '2026-06-26T12:01:44.431085'
    turn: 1
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-HARV
complexity: 5
created: 2026-06-25 00:00:00+00:00
depends_on:
- TASK-HARV-002
feature_id: FEAT-HARV
id: TASK-HARV-003
implementation_mode: task-work
parent_feature: memory-harvest-publisher
parent_review: TASK-REV-HARV
status: design_approved
task_type: feature
title: Harvest walker (docs to MemoryEpisodeV1 list)
updated: 2026-06-25 00:00:00+00:00
wave: 2
---

# TASK-HARV-003: Harvest walker (docs → MemoryEpisodeV1 list)

## Objective

Walk the curated allow-list (TASK-HARV-002), build one `MemoryEpisodeV1` per non-empty
doc with full provenance, and return both the episodes and a skip report. This task is
the **producer** of the `MemoryEpisodeV1` integration contract consumed by the
publisher (TASK-HARV-004).

## Context

456 `.md` files sit under the curated dirs today (331 in `docs/reviews`). Several
already exceed the 900 KB publish limit (e.g.
`docs/reviews/reduce-static-markdown/reseed_guardkit_4.md` ≈ 2.3 MB), so the
oversized-skip path must work on day one. The relay validates the storage namespace
and DLQs anything hyphenated — `project_id` must be the literal `"guardkit"`.

## Acceptance Criteria

- [ ] `guardkit/memory/harvest_walker.py` enumerates `*.md` under the `HARVEST_MAP`
      dirs (TASK-HARV-002), mapping each file to its `episode_type` + `content_format`.
- [ ] For each doc, builds a `MemoryEpisodeV1` with:
      `episode_id=derive_episode_id(natural_key_for(rel_path, episode_type))`,
      `project_id="guardkit"`, `episode_type=<resolved>`,
      `content_format="markdown"`, `body=<file text>`,
      `name=<file stem / first H1 title>`, `source="guardkit-harvest"`,
      `source_ref=<repo-relative path>`, `occurred_at=<file/git mtime, ISO 8601>`.
- [ ] Empty / whitespace-only bodies are **filtered out** (the relay acks these with
      zero chunks — harmless noise) and counted in the result.
- [ ] A doc whose UTF-8-encoded body length ≥ `nats_core.events.MAX_EPISODE_BODY_BYTES`
      (900 KB — **imported, never hardcoded**) is **skipped** and recorded in the skip
      report as `(repo_relative_path, byte_size)`; the walk continues.
- [ ] Returns a `HarvestResult` exposing: `episodes: list[MemoryEpisodeV1]`,
      `skipped_oversized: list[tuple[str, int]]`, `skipped_empty: int`, and
      `counts_per_type: dict[str, int]`.
- [ ] `project_id` is the literal `"guardkit"` (underscores only — a hyphen would be
      DLQ poison per the relay contract); asserted in a unit test.
- [ ] Unit tests cover: taxonomy mapping, empty-body filter, oversized-skip (use a
      synthetic >900 KB fixture; optionally reference a real oversized doc), and
      `counts_per_type` correctness — with **no** NATS connection.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- Import the 900 KB ceiling from `nats_core.events` so the walker's skip threshold and
  the publisher's `ValueError` threshold can never drift apart.
- `occurred_at`: prefer git last-commit time for the file; fall back to filesystem
  mtime if git is unavailable. Keep it best-effort — it aids the parity eval but is not
  load-bearing.
- This module performs **no** NATS work and constructs **no** `NATSClient`.

## Coach Validation

```bash
pytest tests/ -v -k harvest_walker
```