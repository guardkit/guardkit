---
task_id: TASK-REV-E8D1
title: Align graphiti embedding dimensions across guardkit repos
review_mode: decision
review_depth: standard
reviewer: claude-opus-4-7
generated: 2026-04-19
status: review_complete
---

# Review Report: TASK-REV-E8D1

## Executive Summary

The task's investigation is **technically sound** and all code-level
claims were verified against the live repository. The pipeline is
healthy despite the inconsistent config; the work is configuration
hygiene + landmine removal, not incident response.

**Recommendation: proceed with Option A** for Stream 1 (remove
`embedding_dimensions` entirely), execute Stream 2 as specified with
one minor refinement, and adopt the `vllm-embed.sh` dim check.
Defer Stream 3.

| Stream | Verdict | Notes |
|--------|---------|-------|
| Stream 1 | **Approve — Option A** | Eliminates dual-source-of-truth drift |
| Stream 2 | **Approve with refinement** | Repurpose dead warning at init.py:1598-1609 |
| Stream 3 | **Defer (as proposed)** | No VECTOR indexes exist; full-scan adequate |
| Cross-cutting | **Approve** | vllm-embed.sh dim check is high-leverage |

Architecture score: **76/100** (config hygiene with structural improvement).

---

## Verification of Investigation Claims

Every code-level assertion in the task description was verified:

| Claim | Location | Verified |
|-------|----------|----------|
| YAML declares 1024 with misleading comment | [.guardkit/graphiti.yaml:85](.guardkit/graphiti.yaml#L85) | ✅ |
| `or 1024` fallback in MCP config gen | [guardkit/cli/init.py:273](guardkit/cli/init.py#L273) | ✅ |
| `or 1024` warning gate in with-mcp path | [guardkit/cli/init.py:1598-1610](guardkit/cli/init.py#L1598-L1610) | ✅ |
| `KNOWN_EMBEDDING_DIMS` exists and is authoritative | [graphiti_client.py:116](guardkit/knowledge/graphiti_client.py#L116) | ✅ |
| `_check_embedding_dimensions` falls back to dim table | [graphiti_client.py:632-668](guardkit/knowledge/graphiti_client.py#L632-L668) | ✅ |
| `_build_embedder` uses `embedding_dim` when set | [graphiti_client.py:571](guardkit/knowledge/graphiti_client.py#L571) | ✅ |

**Key meta-finding**: the warning at `init.py:1603` already detects
exactly this drift case (`known_dim != 1024`) but only fires when
`embedding_dimensions` is *unset*. The current YAML sets it explicitly,
so the warning never triggers. The system has a built-in canary that
the config silenced.

---

## Stream 1 — Decision: Option A vs Option B

### Option A — Remove `embedding_dimensions` entirely

**Pros**
- **Single source of truth.** `KNOWN_EMBEDDING_DIMS` becomes
  authoritative, eliminating the structural cause of the drift this
  task was created to fix.
- **Smaller diff per repo** — delete 6 lines × 11 repos.
- **Operator override path remains available** — Stream 2's resolver
  still honors an explicit `embedding_dimensions` if set; Option A
  just removes the *misleading default*.
- **Consistent with existing fallback contract.** `_check_embedding_dimensions`
  already prefers config but falls back to the dim table; Option A
  makes that fallback the everyday path.

**Cons**
- Loses per-repo self-documentation of "what dim is in use."
  *Mitigation*: a one-line comment naming the embedding model is
  enough; the dim table is the documentation.
- If `KNOWN_EMBEDDING_DIMS` lacks an entry for a future model and no
  explicit override is set, Stream 2's final fallback (1536) takes
  over silently.
  *Mitigation*: the task already proposes adding a pre-flight dim
  check to `vllm-embed.sh` — covers this gap from the runtime side.

### Option B — Set `embedding_dimensions: 768` + corrected comment

**Pros**
- Self-documenting in the YAML itself.
- Operators reading the file immediately see the active dim without
  cross-referencing the dim table.

**Cons**
- **Preserves dual-source-of-truth.** The exact failure mode being
  fixed (YAML diverges from runtime) can recur the next time a model
  is swapped without a corresponding YAML edit.
- **Requires a per-repo update if the model ever changes.** The dim
  table (Stream 2) handles this once for all repos; an explicit YAML
  value forces N edits.

### Recommendation: **Option A**

Rationale: the bug class here is "two writers, one fact." Option A
eliminates the writer; Option B promises that future writers will be
disciplined. Structural fixes beat policy fixes.

The only scenario where Option B is materially better is if operators
routinely run **non-default Matryoshka truncations** (e.g., requesting
512-dim from nomic-v1.5 to save vector storage). The investigation
confirmed vLLM ignores the `dimensions` request parameter for nomic-v1.5
in the current setup, so this scenario isn't in play. If it ever
becomes relevant, Stream 2's resolver still permits an explicit override
— Option A doesn't foreclose it, it just doesn't make it the default.

---

## Stream 2 — Resolver Refinement

The proposed resolver pseudocode is correct. One refinement:

**Repurpose, don't delete, the warning at [init.py:1598-1610](guardkit/cli/init.py#L1598-L1610)**.

After Stream 2, that warning becomes near-dead because the resolver
itself produces the right answer. Replace with a *different* warning
that fires when the resolver had to fall back to the OpenAI default
(1536) because the model was unknown:

```python
# After Stream 2
if resolved_via_final_fallback:
    console.print(
        f"[yellow]Warning: embedding model '{model}' not in "
        f"KNOWN_EMBEDDING_DIMS; defaulting to 1536. "
        f"Add 'embedding_dimensions: <dim>' to .guardkit/graphiti.yaml "
        f"or extend KNOWN_EMBEDDING_DIMS.[/yellow]"
    )
```

This preserves the operator-onboarding signal without keeping the
1024-specific lie around.

**Default-fallback value (1536)** is correct: it matches
`text-embedding-ada-002` and `text-embedding-3-small`, which is the
original design target per the existing `init.py:272` model default.
Do not keep `1024` as the final fallback — it matches no default model
and would simply move the same landmine.

---

## Stream 3 — Defer (Endorsed)

Investigation finding 3 (`CALL db.indexes()` returns no VECTOR
indexes) is the load-bearing fact here. Without indexes, the dim
constraint is purely runtime-side via `Vectorf32` typing on insert,
and the system is already self-consistent at 768.

Adding `guardkit graphiti ensure-indexes` is reasonable future work
but the trigger should be one of:
- A measurable search-latency regression at scale (graph >10K entities), or
- Graphiti-core upstream creating indexes from config dim (would
  *force* the issue regardless), or
- A planned model migration that needs a clean reseed anyway.

None of these apply on the hackathon-horizon. Defer.

---

## Cross-Cutting — `vllm-embed.sh` Dim Check

**Strong endorse.** This is the single highest-leverage change in the
whole task: it makes the runtime side self-validating, which is
exactly the loop the investigation had to close manually with `curl`.
Catches both:
- Model swaps that change native output dim
- vLLM flag changes that affect Matryoshka truncation

Belongs in the documented test section of the script, run once at
service startup or by an operator after any change.

---

## Findings

1. **F1 — Config drift is structural, not behavioral.** Two writers
   (YAML, dim table) for one fact (model output dim). Severity: low
   today, medium on next model migration.

2. **F2 — Built-in canary silenced.** The warning at `init.py:1603`
   would have fired and surfaced this drift, but only when
   `embedding_dimensions` is unset; the YAML being set silenced it.

3. **F3 — Default fallback (`or 1024`) matches no real default model.**
   Neither nomic-v1.5 (768) nor ada-002/3-small (1536) nor common
   1024-dim models (bge-large) are correctly served by 1024 as a
   universal default. This is a pure landmine.

4. **F4 — Investigation correctly bounded scope.** Distinguishing
   "config lies" from "data is wrong" is the right call. Reseeding
   was correctly ruled out.

5. **F5 — Repo inventory needs verification per repo.** Not every
   repo necessarily has `.guardkit/graphiti.yaml` (e.g.,
   `nats-infrastructure` may be infra-only). A `find` pass before
   batched edits is cheaper than 11 individual PRs.

---

## Recommendations

| # | Recommendation | Priority | Effort |
|---|----------------|----------|--------|
| R1 | Apply Option A to all guardkit-org repos with `.guardkit/graphiti.yaml` | High | 30 min batched |
| R2 | Implement Stream 2 resolver in `init.py` with model-aware lookup + 1536 final fallback | High | 1 hour incl. test |
| R3 | Repurpose `init.py:1598-1610` warning to fire on unknown-model fallback | Medium | 15 min |
| R4 | Add unit test: `embedding_model="nomic-embed-text-v1.5"` + no override → resolver returns 768 | High | included in R2 |
| R5 | Add dim-check one-liner to `scripts/vllm-embed.sh` test section | High | 10 min |
| R6 | Update ADR-007 in study-tutor to match Option A | Medium | 10 min |
| R7 | Update operator guide at `docs/guides/graphiti-gemini-rollout-setup.md:67` to remove 1024 reference | Medium | 10 min |
| R8 | Run `find . -path '*/.guardkit/graphiti.yaml'` across guardkit-org clones before edits to confirm inventory | High | 5 min |
| R9 | Defer Stream 3 (vector index command) until concrete trigger surfaces | Low | n/a |

Total estimated effort: **~2.5 hours** for R1-R8.

---

## Decision Matrix (Stream 1 only)

| Criterion | Option A (Remove) | Option B (Set 768) |
|-----------|-------------------|--------------------|
| Eliminates drift root cause | ✅ Yes | ❌ No (defers to discipline) |
| Diff size per repo | Small (delete) | Medium (edit + comment) |
| Future model-swap robustness | High | Low |
| Self-documentation in YAML | ❌ Lost | ✅ Preserved |
| Operator override still possible | ✅ Yes (via Stream 2 resolver) | ✅ Yes |
| Risk if KNOWN_EMBEDDING_DIMS missing entry | Falls to 1536 (acceptable) | Already explicit, no fall |
| **Verdict** | **Recommended** | Acceptable, structurally weaker |

---

## Risks & Caveats

- **Cross-repo coordination.** Eleven repos potentially affected; a
  batched script (single sed across cloned worktrees) is preferable
  to 11 PRs. Confirm inventory via R8 first.
- **ADR-007 alignment.** The embedded YAML snippet in study-tutor's
  ADR-007 must match the chosen option, otherwise next reader
  copy-pastes the obsolete value.
- **Operator-guide alignment.** `docs/guides/graphiti-gemini-rollout-setup.md`
  currently references 1024; not updating it re-creates the same
  misinformation.
- **No test for `init.py:273` today.** Stream 2's R4 test is essential;
  without it the resolver is just another writer that can drift.

---

## Context Used

No knowledge graph context loaded for this review (Phase 1.5 was not
executed; the task already encapsulates extensive investigation with
direct code references). Codebase verification was sufficient.

---

## Next Steps

User decision required at checkpoint:
- **[A]ccept** — proceed to implementation with Option A, R1-R8
- **[R]evise** — request deeper analysis (e.g., enumerate other repos' YAML state via gh CLI)
- **[I]mplement** — auto-create implementation subtasks for R1-R8
- **[C]ancel** — discard review, leave config as-is
