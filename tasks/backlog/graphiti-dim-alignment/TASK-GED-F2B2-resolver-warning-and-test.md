---
id: TASK-GED-F2B2
title: Replace or-1024 defaults with model-aware resolver in init.py, repurpose warning, add test
status: in_review
task_type: implementation
created: 2026-04-19T14:00:00Z
updated: 2026-04-19T14:15:00Z
priority: high
tags: [graphiti, embeddings, resolver, init, testing]
parent_review: TASK-REV-E8D1
feature_id: FEAT-ED1A
implementation_mode: task-work
wave: 2
conductor_workspace: graphiti-dim-alignment-wave2-resolver
complexity: 5
depends_on:
  - TASK-GED-F1A1
---

# Task: Resolver + repurposed warning + unit test

Replace the two `embedding_dimensions or 1024` fallbacks in
`guardkit/cli/init.py` with a model-aware resolver that consults
`KNOWN_EMBEDDING_DIMS`, and repurpose the existing with-mcp warning
to fire on the genuinely informative case (unknown model falling
through to the OpenAI default).

Bundles **R2 + R3 + R4** from TASK-REV-E8D1 review — three
coordinated changes that must ship as one unit.

## Acceptance Criteria

### R2 — Resolver (`init.py:273` and `init.py:1605`)

- [ ] Introduce a single resolver function (e.g.
      `_resolve_embedding_dimensions(settings)`) in
      [guardkit/cli/init.py](../../guardkit/cli/init.py) with this
      precedence:
      1. Explicit `settings.embedding_dimensions` if not None → use it.
      2. Else `KNOWN_EMBEDDING_DIMS.get(settings.embedding_model)` →
         use it.
      3. Else `1536` (OpenAI ada-002 / 3-small default, which matches
         `init.py:272`'s default model).
- [ ] Replace the `or 1024` fallback at
      [init.py:273](../../guardkit/cli/init.py#L273) with a call to
      the resolver.
- [ ] Replace the equivalent fallback path at
      [init.py:1605](../../guardkit/cli/init.py#L1605)-area with the
      resolver (the existing warning block already imports
      `KNOWN_EMBEDDING_DIMS`, so use the resolver output as the single
      authoritative value written to `.mcp.json`).

### R3 — Repurpose the warning (`init.py:1598-1610`)

- [ ] Remove the current warning that fires only when
      `embedding_dimensions` is unset AND `known_dim != 1024`.
- [ ] Replace with a warning that fires when the resolver fell back
      to the **tier-3 default (1536)** because the model is not in
      `KNOWN_EMBEDDING_DIMS`. Message shape:
      ```
      Warning: embedding model '{model}' not in KNOWN_EMBEDDING_DIMS;
      defaulting to 1536. Add 'embedding_dimensions: <dim>' to
      .guardkit/graphiti.yaml, or extend KNOWN_EMBEDDING_DIMS, to
      silence this warning.
      ```
- [ ] No warning should fire when the resolver returns a value via
      tier 1 or tier 2 (the common case should be silent).

### R4 — Unit test

- [ ] Add a unit test (suggested location: `tests/cli/test_init_embedding_resolver.py`)
      covering at minimum:
      - `embedding_model="nomic-embed-text-v1.5"` + no
        `embedding_dimensions` → resolver returns **768**.
      - `embedding_model="text-embedding-ada-002"` + no
        `embedding_dimensions` → resolver returns **1536**.
      - `embedding_model="unknown-future-model"` + no
        `embedding_dimensions` → resolver returns **1536** (final fallback).
      - Explicit override respected: any model + explicit
        `embedding_dimensions=256` → resolver returns **256**.
      - (Optional but recommended) Warning is emitted only when the
        final fallback fires.
- [ ] Test uses `pytest` conventions already in the repo.
- [ ] All tests pass locally with `pytest tests/cli/test_init_embedding_resolver.py -v`.

## Implementation Notes

- **Single source of truth**: import `KNOWN_EMBEDDING_DIMS` from
  `guardkit.knowledge.graphiti_client` (already used at
  [init.py:1601](../../guardkit/cli/init.py#L1601)).
- **Keep the resolver small and pure** — no I/O, no logging. The
  warning is a separate concern handled in the with-mcp path only.
- **Preserve behaviour for operators who already set
  `embedding_dimensions` explicitly.** Option A in TASK-GED-F1A1
  removed the default value but not the *field*; operators can still
  set it as an override. Tier 1 of the resolver honours that.
- **Do not change `KNOWN_EMBEDDING_DIMS` in this task.** If a model
  table extension is needed, it belongs in a separate task.
- **Interface contract**: the resolver's output is written into
  `.mcp.json` as `EMBEDDING_DIM` and also passed to `OpenAIEmbedder`
  via `_build_embedder`. Both consumers expect an integer.

## Quality Gates

- [ ] Compilation: 100% (Python import test)
- [ ] Tests pass: 100%
- [ ] Line coverage on new resolver function: ≥95% (it's small)
- [ ] No new ruff/lint warnings in touched lines

## Out of Scope

- Removing `embedding_dimensions` from YAML files (TASK-GED-F1A1)
- Runtime-side dim check in `vllm-embed.sh` (TASK-GED-F3C3)
- Adding new models to `KNOWN_EMBEDDING_DIMS`
- Creating FalkorDB VECTOR indexes (deferred)

## References

- [TASK-REV-E8D1 review report](../../.claude/reviews/TASK-REV-E8D1-review-report.md) — recommendations R2, R3, R4
- [guardkit/cli/init.py:273](../../guardkit/cli/init.py#L273) — first `or 1024` fallback
- [guardkit/cli/init.py:1598-1610](../../guardkit/cli/init.py#L1598-L1610) — current warning and second fallback path
- [guardkit/knowledge/graphiti_client.py:116](../../guardkit/knowledge/graphiti_client.py#L116) — `KNOWN_EMBEDDING_DIMS`
