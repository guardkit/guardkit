---
id: TASK-GED-F3C3
title: Add vllm-embed.sh dim check and update operator guide
status: in_review
task_type: implementation
created: 2026-04-19T14:00:00Z
updated: 2026-04-19T14:30:00Z
previous_state: in_progress
state_transition_reason: "Quality gates passed (bash -n OK; R5/R7 edits scoped)"
priority: medium
tags: [graphiti, embeddings, runtime-validation, docs, vllm]
parent_review: TASK-REV-E8D1
feature_id: FEAT-ED1A
implementation_mode: direct
wave: 2
conductor_workspace: graphiti-dim-alignment-wave2-runtime-docs
complexity: 2
depends_on:
  - TASK-GED-F1A1
---

# Task: Runtime dim-check + operator guide update

Two small, orthogonal doc/infra touches that close documentation and
runtime-validation loops opened by TASK-REV-E8D1. Kept separate from
TASK-GED-F2B2 so the runtime-validation addition (R5) is visible in
the diff rather than hidden inside a resolver PR.

Bundles **R5 + R7** from TASK-REV-E8D1 review.

## Acceptance Criteria

### R5 — vLLM dim-check one-liner

- [ ] Add a dim-check snippet to [scripts/vllm-embed.sh](../../scripts/vllm-embed.sh)
      in its documented test section. Equivalent to:
      ```bash
      # Verify the embedder actually returns the expected dimension.
      # Catches: model swaps, vLLM flag changes, Matryoshka truncation drift.
      curl -s "http://localhost:${PORT}/v1/embeddings" \
        -H 'Content-Type: application/json' \
        -d '{"model":"'"$(basename "$MODEL")"'","input":"dim-check"}' \
        | python3 -c "import sys,json; d=json.load(sys.stdin); \
          print('Embedder dim:', len(d['data'][0]['embedding']))"
      ```
- [ ] Shell-quote variables correctly (the investigation trace in
      TASK-REV-E8D1 used a version with a subtle quoting bug — fix
      it here).
- [ ] Snippet is in a comment-block or clearly labelled "Post-start
      verification" section, not executed unconditionally at startup
      (avoids adding a hard dependency on python3 at startup).
- [ ] Document the expected output for nomic-embed-text-v1.5
      (`Embedder dim: 768`) next to the snippet.

### R7 — Operator guide update

- [ ] Update [docs/guides/graphiti-gemini-rollout-setup.md](../../docs/guides/graphiti-gemini-rollout-setup.md)
      around line 67 to remove the `1024` reference.
- [ ] Replace with either:
      - A description of the resolver's model-aware behaviour
        ("dimension is resolved from `KNOWN_EMBEDDING_DIMS` based on
        `embedding_model`; set `embedding_dimensions` explicitly only
        to override"), or
      - A concrete `768` example tied to nomic-embed-text-v1.5.
- [ ] Cross-link the guide to TASK-REV-E8D1's review report
      (`.claude/reviews/TASK-REV-E8D1-review-report.md`) for the
      investigation rationale.

## Implementation Notes

- **No code logic changes.** Shell script and markdown only.
- **No test gate required** beyond `bash -n scripts/vllm-embed.sh`
  for syntax.
- **Can ship in parallel with TASK-GED-F2B2** — neither depends on
  the resolver existing. (Both wait on TASK-GED-F1A1's config cleanup
  as the clean baseline.)
- Keep this PR small and obviously-reviewable; resist the temptation
  to fold in unrelated doc cleanup.

## Quality Gates

- [ ] `bash -n scripts/vllm-embed.sh` exits 0
- [ ] Operator guide renders cleanly (no broken internal links)

## Out of Scope

- YAML config changes (TASK-GED-F1A1)
- `init.py` resolver (TASK-GED-F2B2)
- Any FalkorDB index work (deferred, Stream 3)
- Extending `KNOWN_EMBEDDING_DIMS`

## References

- [TASK-REV-E8D1 review report](../../.claude/reviews/TASK-REV-E8D1-review-report.md) — recommendations R5, R7
- [scripts/vllm-embed.sh](../../scripts/vllm-embed.sh) — runtime embedder script
- [docs/guides/graphiti-gemini-rollout-setup.md:67](../../docs/guides/graphiti-gemini-rollout-setup.md#L67) — stale 1024 reference
