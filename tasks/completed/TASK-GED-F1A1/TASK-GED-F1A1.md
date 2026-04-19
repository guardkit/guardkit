---
id: TASK-GED-F1A1
title: Inventory guardkit-org repos and remove embedding_dimensions from graphiti.yaml
status: completed
task_type: implementation
created: 2026-04-19T14:00:00Z
updated: 2026-04-19T15:45:00Z
completed: 2026-04-19T15:45:00Z
completed_location: tasks/completed/TASK-GED-F1A1/
priority: high
tags: [graphiti, falkordb, embeddings, cross-repo, config-cleanup]
parent_review: TASK-REV-E8D1
feature_id: FEAT-ED1A
implementation_mode: direct
wave: 1
conductor_workspace: graphiti-dim-alignment-wave1-config
complexity: 3
depends_on: []
---

# Task: Inventory + config cleanup (Option A)

Purely subtractive change: delete the `embedding_dimensions: 1024`
declaration (and its misleading comment) from every guardkit-org repo's
`.guardkit/graphiti.yaml`, plus the same fix inside study-tutor's
ADR-007. Leaves the codebase in a known-consistent state with
`KNOWN_EMBEDDING_DIMS` as the single source of truth.

Bundles **R8 + R1 + R6** from TASK-REV-E8D1 review because all three
are the same class of change ("delete the lie").

## Acceptance Criteria

### Inventory (R8) — done first

- [x] Run `find` / `gh` pass across guardkit-org clones to enumerate
      which repos actually contain `.guardkit/graphiti.yaml`. Capture
      the list with `embedding_dimensions` line present/absent and
      current value. Example:
      ```bash
      for repo in jarvis guardkit study-tutor specialist-agent nats-core \
                 nats-infrastructure youtube-transcript-mcp require-kit \
                 lpa-platform agentic-dataset-factory forge; do
        path="/path/to/clones/${repo}/.guardkit/graphiti.yaml"
        [ -f "$path" ] && echo "$repo: $(grep -E '^embedding_dimensions' "$path" || echo 'ABSENT')"
      done
      ```
- [x] Record the inventory output in the task's completion notes.

### Config removal (R1) — applied uniformly

For every repo identified in the inventory that has an explicit
`embedding_dimensions:` line:

- [x] Delete the `embedding_dimensions: 1024` line.
- [x] Delete the surrounding comment block that claims "This FalkorDB
      was seeded with 1024-dim vectors (Matryoshka enabled via
      task-transform param)." (Typically `.guardkit/graphiti.yaml:80-84`.)
- [x] Leave a single short comment in its place, e.g.:
      ```yaml
      # Embedding dimension is resolved from KNOWN_EMBEDDING_DIMS
      # based on embedding_model above. Set explicitly only to override
      # (e.g., for Matryoshka truncation).
      ```
- [x] Verify each edited file still parses as valid YAML
      (`python3 -c "import yaml; yaml.safe_load(open('.guardkit/graphiti.yaml'))"`).
- [x] Ship as one PR per repo **or** one batched script commit per
      repo — whichever is less churn.

### ADR-007 fix (R6)

- [x] In study-tutor's ADR-007, update the embedded `graphiti.yaml`
      snippet to match the chosen option (remove `embedding_dimensions: 1024`).
- [x] Add a one-line rationale to the ADR: "Dim resolved from
      `KNOWN_EMBEDDING_DIMS` (nomic-embed-text-v1.5 → 768). See
      TASK-REV-E8D1 for investigation."

## Implementation Notes

- **Rollback**: trivial — re-add the line. Do not pre-emptively script
  a rollback; just commit narrowly so a `git revert` works per repo.
- **Do not touch `init.py` in this task.** Stream 2 changes land in
  TASK-GED-F2B2; keeping this task purely subtractive preserves
  reversibility.
- **Do not reseed any FalkorDB graph.** Investigation in TASK-REV-E8D1
  confirmed stored vectors are 768-dim and retrieval works.
- **Canary check after merge**: run
  `guardkit graphiti search "something"` from any affected repo to
  confirm nothing regressed. The pre-flight
  `_check_embedding_dimensions` will now resolve via `KNOWN_EMBEDDING_DIMS`
  — should succeed silently.

## Out of Scope

- Resolver changes in `init.py` (TASK-GED-F2B2)
- `vllm-embed.sh` dim check (TASK-GED-F3C3)
- Operator guide update (TASK-GED-F3C3)
- Creating FalkorDB VECTOR indexes (deferred, Stream 3)

## References

- [TASK-REV-E8D1 review report](../../.claude/reviews/TASK-REV-E8D1-review-report.md) — recommendations R1, R6, R8
- [.guardkit/graphiti.yaml:80-85](../../.guardkit/graphiti.yaml#L80-L85) — the lines being removed in this repo

## Completion Notes (2026-04-19)

### R8 — Inventory

Searched `/Users/richardwoollcott/Projects/appmilla_github/**/.guardkit/graphiti.yaml`
for `^embedding_dimensions`. Results:

| Repo | File exists? | `embedding_dimensions` |
|------|--------------|------------------------|
| jarvis | No | — |
| guardkit | Yes | line 85: `1024` |
| forge | Yes | line 85: `1024` |
| study-tutor | Yes | line 14: `1024` |
| specialist-agent | Yes | line 14: `1024` |
| nats-core | Yes | line 32: `1024` |
| nats-infrastructure | Yes | line 14: `1024` |
| youtube-transcript-mcp | Yes | line 26: `1024` |
| require-kit | Yes | line 17: `1024` |
| lpa-platform | Yes | line 14: `1024` |
| agentic-dataset-factory | Yes | line 14: `1024` |
| deepagents-player-coach-exemplar | Yes | line 14: `1024` (not in original list) |
| dotnet-functional-fastendpoints-exemplar | Yes | line 14: `1024` (not in original list) |

Two repos not in the original review inventory also had the line and
were included in the cleanup for consistency.

### R1 — Config removal

All 12 affected repos edited:
- guardkit + forge had the full 5-line comment block (lines 80-84) above
  the declaration; replaced block + line with the 3-line
  `KNOWN_EMBEDDING_DIMS` rationale.
- The remaining 10 repos had only the bare line; inserted the 3-line
  rationale in its place.

All files re-parsed with `yaml.safe_load` — no parse errors, no
residual `embedding_dimensions` key.

### R6 — ADR-007 fix

`study-tutor/docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md`
snippet updated: removed `embedding_dimensions: 1024` from the embedded
yaml block, added rationale paragraph below the snippet:

> Dim resolved from `KNOWN_EMBEDDING_DIMS` (nomic-embed-text-v1.5 → 768).
> See TASK-REV-E8D1 for investigation.

### Commit strategy

Edits left uncommitted in all 12 repos per user request — to be
committed as narrow per-repo commits for clean `git revert` if needed.
Canary check (`guardkit graphiti search`) deferred until commits land.
