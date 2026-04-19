# Feature: Graphiti Embedding Dimension Alignment

**Feature ID:** FEAT-ED1A
**Parent Review:** [TASK-REV-E8D1](../TASK-REV-E8D1-align-graphiti-embedding-dimensions.md)
**Review Report:** [.claude/reviews/TASK-REV-E8D1-review-report.md](../../../.claude/reviews/TASK-REV-E8D1-review-report.md)

## Problem

The `.guardkit/graphiti.yaml` files across guardkit-org repos declare
`embedding_dimensions: 1024`, but the actual vLLM embedder
(`nomic-embed-text-v1.5`) returns 768-dim vectors, and GuardKit's own
`KNOWN_EMBEDDING_DIMS` table also says 768. The 1024 value is inert
today because FalkorDB has no VECTOR indexes that enforce it and
stored `Vectorf32` values are self-consistent — but it's a landmine
that will activate the next time someone swaps in a genuinely-1024-dim
model, and it silenced an existing built-in drift-detection warning.

Investigation (19 April 2026, against `whitestocks:6379` FalkorDB)
confirmed the pipeline is healthy end-to-end. This feature is
configuration hygiene + landmine removal, not incident response.

## Solution

**Option A** (selected per review): eliminate the dual-source-of-truth
by removing `embedding_dimensions` from YAML where it's currently
mis-set, and make `KNOWN_EMBEDDING_DIMS` authoritative via a
model-aware resolver in `init.py`. Explicit override is still
supported for operators who need Matryoshka truncation or
model-specific overrides.

## Subtasks

| ID | Title | Mode | Wave | Complexity |
|----|-------|------|------|------------|
| [TASK-GED-F1A1](TASK-GED-F1A1-inventory-and-config-cleanup.md) | Inventory + config cleanup (R8+R1+R6) | direct | 1 | 3 |
| [TASK-GED-F2B2](TASK-GED-F2B2-resolver-warning-and-test.md) | Resolver + warning + test (R2+R3+R4) | task-work | 2 | 5 |
| [TASK-GED-F3C3](TASK-GED-F3C3-runtime-validation-and-docs.md) | Runtime dim check + docs (R5+R7) | direct | 2 | 2 |

## Execution Strategy

- **Wave 1 (sequential, must complete first):** TASK-GED-F1A1 only.
  Purely subtractive (deletes YAML lies). Leaves codebase in a
  known-consistent state before new behaviour is layered on.
- **Wave 2 (parallel, after Wave 1 merges):** TASK-GED-F2B2 and
  TASK-GED-F3C3 run in parallel. Neither depends on the other; both
  depend on the clean config baseline from Wave 1.

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for sequencing
rationale and Conductor workspace assignments.

## Non-Goals

- **Not reseeding any FalkorDB graph** — stored vectors are consistent.
- **Not creating VECTOR indexes** — Stream 3, deferred until a
  concrete symptom surfaces.
- **Not switching embedding models** — nomic-embed-text-v1.5 is fit
  for purpose.
- **Not extending `KNOWN_EMBEDDING_DIMS`** — separate future work.
