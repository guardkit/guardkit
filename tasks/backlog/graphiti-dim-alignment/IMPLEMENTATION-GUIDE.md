# Implementation Guide: Graphiti Embedding Dimension Alignment

**Feature ID:** FEAT-ED1A
**Parent Review:** [TASK-REV-E8D1](../TASK-REV-E8D1-align-graphiti-embedding-dimensions.md)
**Estimated Effort:** ~2.5 hours total

## Sequencing Rationale

Three tasks across two waves. Wave 1 is sequential and must complete
before Wave 2 starts; Wave 2 tasks parallelise.

```
Wave 1 (sequential)         Wave 2 (parallel after Wave 1)
─────────────────           ──────────────────────────────
TASK-GED-F1A1               TASK-GED-F2B2  ──┐
(config cleanup)            (resolver+test)   │  parallel
                            TASK-GED-F3C3  ──┘
                            (runtime+docs)
```

### Why Wave 1 alone

TASK-GED-F1A1 is **purely subtractive** — it deletes the misleading
`embedding_dimensions: 1024` line from YAML files. Once merged, the
codebase is in a known-consistent state with no lies. That clean
baseline is the right foundation before layering on new resolver
behaviour. If the resolver in TASK-GED-F2B2 has a bug, it can't be
hidden by stale config defaults because the stale defaults are gone.

Rollback is trivial (re-add the line), so Wave 1 carries minimal
risk.

### Why Wave 2 parallelises

- **TASK-GED-F2B2** touches `guardkit/cli/init.py` and a new test file.
- **TASK-GED-F3C3** touches `scripts/vllm-embed.sh` and a markdown doc.

Zero file overlap. Independent review surfaces. Both depend only on
TASK-GED-F1A1 having shipped (so no resolver bug can be obscured by
stale YAML, and no doc update contradicts the new resolver behaviour).

## Wave 1 — Config Cleanup

### TASK-GED-F1A1: Inventory + config cleanup (R8 + R1 + R6)

- **Conductor workspace:** `graphiti-dim-alignment-wave1-config`
- **Mode:** direct (mechanical edits, no code logic)
- **Estimated effort:** 45 min (5 min inventory + 30 min apply + 10 min ADR)
- **Files touched:**
  - `.guardkit/graphiti.yaml` in each guardkit-org repo that has one
    (inventory pass first to confirm which repos)
  - study-tutor's ADR-007 markdown
- **Quality gate:** `python3 -c "import yaml; yaml.safe_load(open('.guardkit/graphiti.yaml'))"`
  per repo + smoke-test `guardkit graphiti search` from one repo
  post-merge.

**Sequencing within the task:** R8 (inventory) → R1 (apply uniformly)
→ R6 (ADR-007 fold-in). Inventory must come first because the
"one PR per repo vs. batched" decision depends on how many repos
actually carry the line.

## Wave 2 — Behaviour + Validation

### TASK-GED-F2B2: Resolver + warning + test (R2 + R3 + R4)

- **Conductor workspace:** `graphiti-dim-alignment-wave2-resolver`
- **Mode:** task-work (Python code + unit test, full quality gates)
- **Estimated effort:** 60 min
- **Files touched:**
  - `guardkit/cli/init.py` (resolver function, two call-site
    replacements, repurposed warning)
  - `tests/cli/test_init_embedding_resolver.py` (new)
- **Quality gate:** unit tests pass, ≥95% coverage on new resolver,
  no new lint warnings.

**Internal coupling:** R2 (resolver), R3 (warning), R4 (test) are
inseparable. The test validates the resolver; the warning depends on
the resolver's tier-3 fallback existing.

### TASK-GED-F3C3: Runtime dim check + docs (R5 + R7)

- **Conductor workspace:** `graphiti-dim-alignment-wave2-runtime-docs`
- **Mode:** direct (shell + markdown, no Python logic)
- **Estimated effort:** 20 min
- **Files touched:**
  - `scripts/vllm-embed.sh` (dim-check snippet in test section)
  - `docs/guides/graphiti-gemini-rollout-setup.md` (line 67 area)
- **Quality gate:** `bash -n scripts/vllm-embed.sh` exits 0; markdown
  links resolve.

**Could fold into TASK-GED-F2B2** to reduce PR count, but kept
separate so the runtime-validation addition (R5) is visible in its own
diff rather than buried in a Python PR.

## Cross-Task Concerns

- **Do not reseed any FalkorDB graph at any point.** Investigation
  confirmed stored vectors are 768-dim and self-consistent. Reseeding
  is wasted work and briefly interrupts search.
- **Do not extend `KNOWN_EMBEDDING_DIMS` in any of these tasks.** If
  a model is missing from the table, the resolver will fall back to
  1536 and emit the new warning — that's the designed signal. Adding
  models is separate work.
- **Stream 3 (`guardkit graphiti ensure-indexes` command) is
  deferred.** Triggers for revisiting: search-latency regression at
  scale, graphiti-core upstream creating indexes from config, or a
  planned model migration that needs a clean reseed anyway.

## Verification After Wave 2 Merges

1. Fresh `guardkit init --with-mcp` in a throwaway repo with
   `embedding_model: nomic-embed-text-v1.5` and no
   `embedding_dimensions` → confirm `.mcp.json` writes
   `EMBEDDING_DIM=768`.
2. Same with `embedding_model: text-embedding-ada-002` → confirm
   `EMBEDDING_DIM=1536`, no warning.
3. Same with `embedding_model: bogus-future-model` → confirm
   `EMBEDDING_DIM=1536` and warning text appears.
4. `guardkit graphiti search "any-known-query"` from at least two
   different guardkit-org repos → confirm results return and project
   scoping is correct.

## Next Step

Start with TASK-GED-F1A1. Block Wave 2 tasks until F1A1 is merged.
