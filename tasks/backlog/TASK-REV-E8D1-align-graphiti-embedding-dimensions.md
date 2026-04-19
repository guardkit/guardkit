---
id: TASK-REV-E8D1
title: Align graphiti embedding dimensions across guardkit repos
status: review_complete
task_type: review
decision_required: true
created: 2026-04-19T00:00:00Z
updated: 2026-04-19T14:00:00Z
priority: medium
tags: [graphiti, falkordb, embeddings, architecture-review, cross-repo, infrastructure]
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  score: 76
  findings_count: 5
  recommendations_count: 9
  decision: implement
  selected_option: A
  recommended_option: A
  report_path: .claude/reviews/TASK-REV-E8D1-review-report.md
  implementation_feature_id: FEAT-ED1A
  implementation_feature_path: tasks/backlog/graphiti-dim-alignment/
  subtasks:
    - TASK-GED-F1A1  # wave 1: inventory + config cleanup (R8+R1+R6)
    - TASK-GED-F2B2  # wave 2: resolver + warning + test (R2+R3+R4)
    - TASK-GED-F3C3  # wave 2: runtime dim check + docs (R5+R7)
  deferred_recommendations:
    - R9  # Stream 3: ensure-indexes command (defer per review)
---

# Task: Align graphiti embedding dimensions across guardkit repos

## Status update — 19 April 2026

**Original priority: high (suspected dimension mismatch / live corruption).**
**Revised priority: medium (configuration hygiene, not a live incident).**

A Claude Desktop investigation on 19 April established the pipeline is
healthy end-to-end despite the inconsistent config. See
[Investigation Findings](#investigation-findings-19-april-2026) below.
The task is retained to remove the misleading config and add guardrails
against future drift.

## Background

The `.guardkit/graphiti.yaml` files across guardkit-org repos declare
`embedding_dimensions: 1024`, but:
- The vLLM embedding server runs `nomic-ai/nomic-embed-text-v1.5` via
  [scripts/vllm-embed.sh](scripts/vllm-embed.sh), which emits **768-dim**
  native vectors (Matryoshka truncations of [768, 512, 256, 128, 64]; 1024
  is *not* a supported output dimension for this model).
- GuardKit's own source of truth
  [guardkit/knowledge/graphiti_client.py:KNOWN_EMBEDDING_DIMS](guardkit/knowledge/graphiti_client.py)
  lists `"nomic-embed-text-v1.5": 768`.

The config value therefore contradicts both the runtime reality and
GuardKit's internal dim table. The comment in `graphiti.yaml:85` further
claims "This FalkorDB was seeded with 1024-dim vectors (Matryoshka
enabled via task-transform param)" — but the live FalkorDB stores
whatever dimension the vLLM server actually returned (768), and the
`scripts/vllm-embed.sh` startup does not pass any dimension override.

## Investigation Findings (19 April 2026)

Live investigation against `whitestocks:6379` FalkorDB during Claude
Desktop review of study-tutor's `/system-arch` output:

### What's actually happening

1. **Embedder output (live test via curl):** 768 dims.
   ```bash
   curl -s http://promaxgb10-41b1:8001/v1/embeddings \
     -H "Content-Type: application/json" \
     -d '{"model":"nomic-embed-text-v1.5","input":"test"}' \
     | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r['data'][0]['embedding']))"
   # Output: 768
   ```

2. **Stored vectors in FalkorDB:** `Entity.name_embedding` and
   `RELATES_TO.fact_embedding` are stored as FalkorDB `Vectorf32` typed
   values. The dimension is fixed per-type at insert time; the system is
   internally consistent because ~732 episodes seeded successfully
   without a single dimension-mismatch error. The stored dimension is
   therefore 768 (matching the embedder output).

3. **FalkorDB vector indexes:** `CALL db.indexes()` on the
   `architecture_decisions` graph returns only RANGE and FULLTEXT
   indexes. **No VECTOR indexes exist.** This is why the `_check_embedding_dimensions`
   pre-flight never fires a dimension-mismatch error — there's no index
   dimension to compare against. Similarity search apparently runs as
   full-scan cosine comparison over the stored `Vectorf32` values, which
   is acceptable at current graph sizes (hundreds of entities per graph).

4. **End-to-end retrieval works.** `guardkit graphiti search "async
   Graphiti write-back session end"` from study-tutor's repo root
   returned 110 ranked results with sensible relevance scores and correct
   project scoping (study-tutor content, not Forge/LPA content, despite
   all projects sharing the same fleet-level `architecture_decisions`
   graph name).

5. **The `embedding_dimensions: 1024` value is effectively inert** for
   current operations because:
   - No VECTOR index exists that enforces it.
   - vLLM's `/v1/embeddings` endpoint appears to ignore the `dimensions`
     parameter for models whose native output is smaller than requested
     (returns 768 regardless of request).
   - `_build_embedder()` passes `embedding_dim=1024` to `OpenAIEmbedder`,
     but the server-side response shape determines the stored dimension.

### Why the value is still wrong and must be fixed

- **Config lies.** The comment claim that FalkorDB was seeded with
  1024-dim vectors is false. Stored vectors are 768-dim.
- **Internally inconsistent with `KNOWN_EMBEDDING_DIMS`.** GuardKit's own
  dimension table has `nomic-embed-text-v1.5: 768`. The YAML and the
  dim-table disagree. Either one or the other is wrong; the YAML is.
- **Masks a real failure mode.** If a future operator (a) upgrades
  graphiti-core to a version that does create vector indexes, or (b)
  switches embedding models to `bge-large-en-v1.5` / `mxbai-embed-large`
  (both 1024-dim), the `1024` value in YAML will silently become
  load-bearing and the system's past-inertness will stop protecting us.
- **Blast-radius on model switch is ambiguous.** If someone swaps in a
  genuinely-1024-dim model, current 768-dim stored vectors become
  unsearchable and there's no clear signal that a re-seed is required.
- **MCP server config propagates the wrong default.** `init.py:273` and
  `init.py:1605` both use `embedding_dimensions or 1024` as fallback,
  which writes `EMBEDDING_DIM=1024` into per-project `.mcp.json` files.
  Operators adding new projects will inherit the wrong value.

## Scope (revised)

Three streams, in priority order:

### Stream 1 — Correct the config (HIGH, fast)

Bring `.guardkit/graphiti.yaml` files into alignment with the running
embedding model. Options:

**Option A (preferred): Remove `embedding_dimensions` entirely.**
`_check_embedding_dimensions` already falls back to `KNOWN_EMBEDDING_DIMS`
when `embedding_dimensions is None`, and nomic-embed-text-v1.5 is in
that table at 768. This eliminates a redundant source of truth and makes
the dim-table the single source of truth.

**Option B: Set `embedding_dimensions: 768` and update the comment.**
Keeps the field as an explicit override for operators who switch models.

Choose one. Apply across every repo with a `graphiti.yaml` (see Repo
inventory below).

### Stream 2 — Fix the hardcoded `or 1024` defaults (MEDIUM)

Replace `embedding_dimensions or 1024` in
[guardkit/cli/init.py:273](guardkit/cli/init.py#L273) and
[guardkit/cli/init.py:1605](guardkit/cli/init.py#L1605) with a
model-aware lookup:

```python
# Pseudocode
from guardkit.knowledge.graphiti_client import KNOWN_EMBEDDING_DIMS
embedding_dimensions = (
    getattr(settings, "embedding_dimensions", None)
    or KNOWN_EMBEDDING_DIMS.get(embedding_model)
    or 1536  # OpenAI default (safer than 1024 which matches no default model)
)
```

This means:
- If the operator set `embedding_dimensions` explicitly, use it.
- Otherwise look up the known dim for the configured model.
- Otherwise fall back to OpenAI's default (the original design target).

Update the `with_mcp` warning at init.py:1598-1609 to match the new
default-resolution logic.

### Stream 3 — Add a vector index migration (LOW, defer)

FalkorDB's `CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding)
OPTIONS {dimension: 768, similarityFunction: 'cosine'}` would turn the
current full-scan similarity into an indexed lookup. Graphiti-core may
handle this upstream in a future release; until then, GuardKit could add
an optional `guardkit graphiti ensure-indexes` command that creates the
vector indexes if missing.

Defer this until:
- Graph sizes grow to where full-scan is slow (watch search latency in
  `docs/guides/graphiti-gemini-rollout-setup.md` telemetry), or
- A second operator hits a case where the missing index causes silent
  degradation.

Not urgent for the hackathon-horizon.

## Repositories in Scope

Confirmed list from the user (guardkit GitHub org —
https://github.com/orgs/guardkit/repositories):

- [ ] jarvis
- [ ] guardkit (this repo)
- [ ] study-tutor
- [ ] specialist-agent
- [ ] nats-core
- [ ] nats-infrastructure
- [ ] youtube-transcript-mcp
- [ ] require-kit
- [ ] lpa-platform
- [ ] agentic-dataset-factory
- [ ] forge (confirmed present — surfaced by redis `KEYS *` showing
      `forge__*` graphs on the shared FalkorDB)

For each repo, verify: (a) does `.guardkit/graphiti.yaml` exist, (b) what
value of `embedding_dimensions` does it declare, (c) does the comment
correctly describe the embedding model. Apply Stream 1 fix uniformly.

## Acceptance Criteria (revised)

### Stream 1 (must)

- [ ] Chosen option (A or B) documented with one-line rationale.
- [ ] Every guardkit-org repo's `.guardkit/graphiti.yaml` updated to
      match the chosen option.
- [ ] The misleading comment at `.guardkit/graphiti.yaml:85` removed or
      corrected on every repo.
- [ ] ADR-007 in study-tutor updated — the `graphiti.yaml` snippet inside
      the ADR currently shows `embedding_dimensions: 1024`; align with
      the chosen option.

### Stream 2 (must)

- [ ] `init.py:273` fallback logic replaced with the model-aware lookup.
- [ ] `init.py:1605` fallback logic replaced with the model-aware lookup.
- [ ] `init.py:1598-1609` warning updated — the existing warning logic
      already references `KNOWN_EMBEDDING_DIMS`, so may just need the
      default-resolution path aligned.
- [ ] Unit test added for the new resolution: given
      `embedding_model="nomic-embed-text-v1.5"` and no explicit
      `embedding_dimensions`, the resolver returns `768` (not `1024`).

### Stream 3 (nice-to-have, defer)

- [ ] Decision documented: add `guardkit graphiti ensure-indexes` command
      or rely on graphiti-core upstream. Default: defer unless a concrete
      symptom surfaces.

### Cross-cutting

- [ ] `scripts/vllm-embed.sh` updated to add a dimension-check one-liner
      in the documented test section:
      ```bash
      # Verify output dimension matches KNOWN_EMBEDDING_DIMS
      curl -s http://localhost:${PORT}/v1/embeddings \
        -H 'Content-Type: application/json' \
        -d '{"model":"'$(basename "$MODEL")'","input":"dim-check"}' \
        | python3 -c "import sys,json; d=json.load(sys.stdin); \
          print('Dim:', len(d['data'][0]['embedding']))"
      ```

## Non-goals

- **Not re-seeding Graphiti.** Live investigation confirmed stored
  vectors are consistent and retrieval works. A reseed would be wasted
  work and would briefly interrupt search during the reseed window.
- **Not creating FalkorDB vector indexes.** Out of scope here (Stream 3,
  deferred). Current full-scan similarity is fast enough at current scale.
- **Not switching embedding models.** nomic-embed-text-v1.5 is fit for
  purpose. If a switch to a 1024-dim model (e.g. `bge-large-en-v1.5`) is
  ever desired, it should be a separate tracked change with its own
  reseed plan.

## Review Methodology

`task_type: review` — execute via `/task-review TASK-REV-E8D1`, not
`/task-work`. Streamlined from the original five-step plan because the
live investigation already answered the runtime/FalkorDB questions.

1. **Config inventory** — grep each guardkit-org repo for
   `.guardkit/graphiti.yaml` and `embedding_dimensions`.
2. **Apply Stream 1 fix** — one PR per repo, or a batch scripted edit if
   repos are all at the same revision.
3. **Apply Stream 2 fix** — single PR against guardkit.
4. **Verify** — re-run `guardkit graphiti search` against a known-seeded
   query from at least two repos to confirm nothing regressed.

## Known Local References

- [.guardkit/graphiti.yaml:85](.guardkit/graphiti.yaml#L85) — declares 1024
  with misleading comment
- [scripts/vllm-embed.sh](scripts/vllm-embed.sh) — nomic-v1.5 runtime
- [guardkit/cli/init.py:273](guardkit/cli/init.py#L273) — `or 1024` default
  in `generate_mcp_server_config`
- [guardkit/cli/init.py:1598-1609](guardkit/cli/init.py#L1598-L1609) —
  with_mcp warning about dimension mismatch
- [guardkit/knowledge/graphiti_client.py:KNOWN_EMBEDDING_DIMS](guardkit/knowledge/graphiti_client.py)
  — authoritative dim table, already correct
- [guardkit/knowledge/graphiti_client.py:_check_embedding_dimensions](guardkit/knowledge/graphiti_client.py)
  — pre-flight check; relies on the dim table when config is unset
- [guardkit/knowledge/graphiti_client.py:_build_embedder](guardkit/knowledge/graphiti_client.py)
  — passes `embedding_dim` to OpenAIEmbedder when config is set
- [docs/guides/graphiti-gemini-rollout-setup.md:67](docs/guides/graphiti-gemini-rollout-setup.md#L67)
  — operator guide currently references 1024
- ADR-007 (study-tutor repo) — `embedding_dimensions: 1024` in embedded
  config snippet

## Risk if Not Addressed

- **Low (current):** System works as-is despite the config lie. Users
  and existing seeded data are unaffected.
- **Medium (future):** A model switch to any genuinely-1024-dim model
  (`bge-large-en-v1.5`, `mxbai-embed-large`, `snowflake-arctic-embed`,
  `BAAI/bge-m3`) would silently activate the wrong dim and produce
  broken search with no clear error. The config must be honest before
  any such switch is considered.
- **Medium (future):** If graphiti-core upstream starts creating VECTOR
  indexes from the config dimension, the 1024 value would cause the
  first such upgrade to break seeding. Fixing now removes this landmine.
- **Low:** New operator onboarding via `guardkit init --with-mcp` in a
  fresh repo writes `EMBEDDING_DIM=1024` to `.mcp.json` — which is
  wrong for nomic but accidentally-correct for any genuinely-1024-dim
  model they happen to be running. Fixing Stream 2 makes this robust.

## Next Steps

1. Review task details above, confirm Option A vs Option B for Stream 1.
2. When ready: `/task-review TASK-REV-E8D1 --mode=fix-and-validate`
3. Sequence:
   - Stream 1 across all repos (30 min if batched)
   - Stream 2 in guardkit (1 hour with test)
   - Cross-cutting `vllm-embed.sh` dim check (10 min)
   - Stream 3 deferred, no action
4. Complete: `/task-complete TASK-REV-E8D1`

## Related

- ADR-007 in study-tutor (the investigation trigger)
- study-tutor `docs/history/system-arch-history.md` — seeding log
  showing successful 768-dim writes despite 1024 config
- Investigation trace: Claude Desktop conversation "architecture review
  for study-tutor /system-arch output" 19 April 2026
