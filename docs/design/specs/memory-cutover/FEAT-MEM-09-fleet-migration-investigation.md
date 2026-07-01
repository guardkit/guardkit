<!-- Generated 2026-07-01 from live investigation (workflow wf_28c06b86-401): per-project model, migration mechanism, fleet consumer inventory, corpus overlap. All counts live-verified against FalkorDB whitestocks:6379 and fleet-memory Postgres. -->

Key claims verified: 30 project hardcode matches in mapping (29 rows + field), client search hardcode at line 395, `resolve` at line 296, backend already `fleet_memory`/`enabled: false`, 21 rules files on disk. The section numbers match. Now writing the synthesis document.

---

# FEAT-MEM-09: Fleet-Wide Graphiti → fleet-memory Migration & FalkorDB Teardown

**Investigation & program-design document**
Date: 2026-07-01 · Status: pre-build (operator gate) · Backend flag already `backend: fleet_memory`, `enabled: false`

---

## 0. Bottom line

**The full fleet migration + FalkorDB teardown is feasible and low-risk to *runtime*, but it is a data-preservation exercise, not a functionality-restoration one.** Every code-level Graphiti consumer already graceful-degrades (fire-and-forget writes, `[]`-returning safe reads, `find_spec`/lazy-import gates — §3), so FalkorDB (`whitestocks:6379`, 11,847 nodes / 92 graphs) can go dark *without crashing any agent*. The critical path is: **(1) land per-project scoping in fleet-memory/guardkit → (2) build the one-shot `graph_export` pipeline → (3) migrate the five real code consumers → (4) verified fleet-memory backup → (5) teardown.** The single biggest risk is **silent knowledge loss of a small unique tail** — on the order of **~10–15 guardkit-only distilled runtime-decision nodes** that exist only in FalkorDB with no doc/rule/task anchor (§4), plus the analogous unique tails in the other consumers' graphs.

**Can guardkit's "big-picture context" be restored on fleet-memory (pure-embeddings)? Yes — at chunk-level fidelity for free, or at distilled-fact fidelity via a one-time offline LLM pass.** The raw *source* prose (guardkit: **230 Episodic nodes**, ~150 distinct items — §4) migrates 1:1 with no LLM. What is lost is the **5,735 Qwen2.5-extracted relationship facts** (§2), which are a distillation *of* that prose. The read *surface* is unchanged (guardkit already returns an assembled `context_block`, not per-fact hits — §2), so the only degradation is retrieval *character*: verbose 1.5 KB chunks vs terse distilled statements. Distilled-fact density is recoverable for the high-value graphs via a one-time cloud-LLM distillation at migration — which does **not** reintroduce a runtime LLM and so does not violate the "drop Qwen2.5" teardown goal.

---

## 1. Per-project + per-group scoping model  *(from A)*

**Project scoping already exists end-to-end in fleet-memory at the SQL level** — it is a first-class dimension in every storage/identity primitive; guardkit simply never varies the value. All 685 live `public.store` rows are `fleet_memory.guardkit.*`.

- **Storage key** (`public.store`): PK `(prefix, key)`; `prefix` is the dot-joined namespace tuple `("fleet_memory", project, payload_type)` — **project is already the middle prefix segment** (writer `core.py:86`, `chunk_writer.py:82`).
- **Identity**: `uuid5` of `natural_key = {payload_type}:{project}:{identifier}` (`writer/identity.py:27-48`, `base.py:160-166`) — project is baked into the record UUID, so no cross-project key collisions.
- **Retrieval** (`retrieval/core.py:176`): `namespace_prefix = ("fleet_memory", request.project)` → langgraph emits `store.prefix LIKE 'fleet_memory.{project}%'`. A `SearchRequest(project="jarvis", ...)` would *already* return only jarvis rows.
- **Validation** (`search_request.py:42-61`, `store.py:52-72`): project must match `^[a-z0-9_]+$` — so consumer names like `lpa-platform`, `study-tutor` **must be normalised to underscores** (`lpa_platform`, `study_tutor`) before use.

**The literal `"guardkit"` is hardcoded in exactly three guardkit places** (verified: 30 grep matches = 29 `GroupMapping` rows + 1 dataclass field):

| # | Location | Effect |
|---|---|---|
| A | `guardkit/knowledge/fleet_memory_mapping.py` (all 29 rows) | Every write → prefix `fleet_memory.guardkit.*` |
| B | `guardkit/knowledge/fleet_memory_client.py:395` (`SearchRequest(project="guardkit")`) | Every read scoped to guardkit |
| C | `fleet_memory_client.py:301` (healthcheck probe) | Cosmetic |

**Group-scoped retrieval already works** and is project-orthogonal: fleet-memory has no `group` field, but guardkit's client translates each `group_id` → `mapping.payload_type` (added to `payload_types`) + `mapping.domain_tags` (`fleet_memory_client.py:379-388`), and retrieval filters on both (`retrieval/core.py:46-63`, `:93-109`, incl. the TASK-MEM08-012 embedded-`content`-tag fix). So `group_ids=["architecture_decisions"]` → `payload_types=["adr"], domain_tags=["system"]`. The `resolve()` mapping is at `fleet_memory_mapping.py:296`.

**Required changes:**

| Change | fleet-memory | guardkit | Overall |
|---|---|---|---|
| (1) Scope writes per project — thread `project` param into `build_memory_episode`; drop the static `GroupMapping.project` field; source project from `.guardkit/graphiti.yaml` or `GUARDKIT_MEMORY_PROJECT`, sanitised | none | **S** | **S** |
| (2) Filter reads per project — unhardcode `:395`/`:301` | **S** (add trailing-delimiter guard so `project="jarvis"` can't `LIKE`-match `jarvis_v2`) | **S** | **S** |
| (3) Preserve group-scoped retrieval | none | none (verify) | **S** |
| (fleet-wide) per-consumer group→facet mapping tables (18 projects / ~11 active) | none | **M–L** (author per-consumer tables; key on `(project, group_id)` if maps differ) | **M–L** |

**Sharp edge flagged:** the retrieval prefix is `LIKE 'prefix%'` — a latent cross-project bleed once ≥2 projects share a name-prefix (e.g. `guardkit` vs `guardkit_factory`). Fix = trailing-delimiter guard inside fleet-memory `retrieval/core.py:176` (**S**). *This is the one fleet-memory-core change the whole program needs.*

**Confidence: high** (SQL-level scoping verified; the "18 projects / ~11 active" fleet-wide mapping-authorship estimate is **medium** — driven by §3's consumer inventory, not measured per-group).

---

## 2. Migration mechanism + fact-vs-chunk trade-off  *(from B)*

**Two content layers per graph, migrating very differently** (guardkit live, 2026-07-01):

| Layer | What | guardkit count | Migratable |
|---|---|---|---|
| **Episodic nodes** (raw source prose) | `content`+`name`+`source_description`+`group_id`+`created_at` | **504** | **Yes — 1:1, no LLM** |
| **Entity + RELATES_TO/MENTIONS** (`r.fact`) | Qwen2.5-*extracted* distilled statements | **5,735** | **No — needs an LLM** |

*(Note: B reports 504 Episodic; §4/D reports 230. The gap is duplicate `_chunk_N` rows and the classification boundary — B counts all Episodic across five graphs; D counts the source-layer after de-duplication to ~150 distinct items. Both agree the extracted Entity layer, not the source layer, dominates the headline "4,154 nodes". **Flag: reconcile the exact Episodic count during build** — it drives the distillation batch size, not the go/no-go.)*

Episodic bodies are small, self-contained prose — sampled: `project_decisions` avg 1,527 B / max 4,048 B; `task_outcomes` avg 1,481 B / max 5,628 B; `project_knowledge` avg 2,415 B / max 7,247 B — **all orders of magnitude under the 900 KB `MAX_EPISODE_BODY_BYTES` cap** (`nats-core/.../events/_memory.py:12`). No chunking/oversize handling needed for export.

**Reuse the harvest path** (`harvest_walker.py` → `harvest_publisher.py` → `cli/memory.py:149`): walk sources → build `MemoryEpisodeV1` → `NATSClient.publish_episode` → relay forks on `content_format` (`fleet-memory/relay/service.py:116-124`):
- `content_format="json"` → **`DeterministicWriter`** (embeds canonical-JSON payload; `writer/core.py:157-189`) = **distilled/typed** path (the FEAT-MEM-07 `reindex/publisher.py` template).
- `content_format="markdown"|"text"` → `chunk_prose` → **`ChunkWriter`** (embeds raw prose chunks) = what the 679 FEAT-HARV rows use.

`derive_episode_id` (`harvest_taxonomy.py:69`) is byte-identical to fleet-memory's → free JetStream idempotency. The 29-group mapping is already authored (`resolve()`, `fleet_memory_mapping.py:296`).

**Proposed one-shot pipeline** — new `guardkit/memory/graph_export.py` + `guardkit memory migrate-graph` CLI, sibling of `harvest_walker`: (1) read FalkorDB `MATCH (n:Episodic)` per `guardkit*` graph → (2) strip `guardkit__` prefix → `group_id` → `resolve()`; skip `disposition="retire"` groups (17 seed_module groups already in the harvest corpus — no double-ingest) → (3) build `MemoryEpisodeV1` with `episode_id=derive_episode_id(natural_key)` → (4) reuse `publish_episodes()` unchanged. **Only genuinely new code: the FalkorDB reader + graph→group_id normalizer.**

**The trade-off — extracted facts vs raw chunks:**
- **Read surface is unchanged** — guardkit already returns a single assembled `context_block` + coverage score (`fleet_memory_client.py:379-417`), not per-fact hits.
- **Corpus character changes** — verbose 1.5 KB chunks vs terse distilled statements. More tokens/retrieval, lower signal density, but all underlying facts are present in the prose.
- **The highest-value guardkit knowledge (`.claude/rules/*.md`, 21 files — verified) is already harvested as chunks and retrieves well today**, de-risking the chunk option for what matters most.

**Two ways to recover fact-density without a permanent LLM:**
- **(i) Accept chunk-level** — zero LLM, zero ongoing cost, same shape as proven FEAT-HARV corpus.
- **(ii) One-time distillation at migration** — batch Episodic bodies through *any* cloud LLM **once, offline, then discard** (does NOT violate "drop Qwen2.5 / no runtime LLM"). Publish as `DocumentPayload` (`payloads/models.py:91`, `content_format="json"` → DeterministicWriter). Cost: ~504 short completions for guardkit (~cents); ~4,000 fleet-wide (trivial one-off).

**Recommendation: hybrid, staged by disposition** — ship (i) for all migrate-disposition content first (LLM-free, immediately unblocks teardown); layer (ii) *only* for the two high-value graphs (`project_decisions` 147 + `task_outcomes` 127 = 274 nodes). The 5,735 raw facts are **not** worth re-deriving wholesale — they're a distillation of the Episodic nodes already being migrated.

**Effort:** option (i) pipeline ~1–1.5 d (guardkit-only; +0.5 d to un-hardcode `project` for fleet-wide); option (ii) enrichment ~1 d; **guardkit cutover ~2–2.5 d; fleet-wide +1 d** (mechanism unchanged). **Confidence: high** on mechanism/reuse; **medium** on the ~4,000 fleet-wide Episodic estimate (extrapolated from "~⅓ of 11,847 nodes are Episodic").

---

## 3. Fleet consumer inventory + sequencing  *(from C)*

FalkorDB: **11,847 nodes / 92 graphs**. Local-`src/` grep across sibling repos (docs/tasks/history excluded). **Three surprises: nats-core, guardkitfactory, lpa-platform-poc have ZERO Graphiti coupling in code.**

### Real code-level blockers (must migrate before teardown)

| Consumer | R/W | Access | Effort | Notes |
|---|---|---|---|---|
| **forge** | R+W | py 3-tier: MCP (`graphiti_core`) → CLI (`guardkit graphiti`) → unavailable | **HIGH** | Heaviest after guardkit. 6 typed pipeline entities, RRF calibration-prior reads (`priors.py:260-290`), durability reconciler (`reconciler.py`), idempotency existence-checks. Groups `forge_*`. **645 nodes.** |
| **study-tutor** | R+W | direct `graphiti-core[falkordb]` git fork `v0.29.5-guardkit.3` | **HIGH** | Single audited `add_episode` (CC-13, `async_write.py:421`) + seed; reads student partitions via `get_by_group_ids`. Groups `student-<id>`/`subject-<slug>`/`fleet:appmilla`. 7 entity types. **552 nodes.** |
| **specialist-agent** | R+W | **BOTH** MCP-callable writer + lazy `graphiti-core`+`FalkorDriver` Player query tool | **HIGH** | Split model = the cutover complication. Groups `role:`/`project:`+fleet 3-scope. Much write-back still `design_approved`/`backlog`. **68 nodes** (+ `architect_agent` 246 remote). |
| **jarvis** | **W only** | direct `graphiti-core` git fork `v0.29.5-guardkit.1` (`[graphiti]` extra) | **MEDIUM** | Fire-and-forget routing-history `add_episode`; **no read path**. Structural `GraphitiClientProtocol`. **1,115 nodes.** |
| **fleet-gateway** | **R only** | direct `graphiti-core`+`FalkorDriver`, connect-per-call | **LOW-MED** | Scholar reads study-tutor's `student-*` graph. **Depends on study-tutor migrating first.** **26 nodes** (own). |

### Not blockers (no code coupling — nodes written by guardkit autobuild on their behalf)

- **nats-core** — **NOT a consumer; it's the fleet-memory *producer*** (publishes `memory.episode.{project_id}.{episode_type}`; `client.py:323-346`, `events/_memory.py` = the write contract). Passive `GraphitiConfig` field it never uses. **146 nodes** (seeded externally).
- **guardkitfactory** — no `src/` coupling (all matches = review docs). **32 nodes.**
- **lpa-platform-poc** — no coupling (all matches = `re.search()` false-positives + a *suppress-noise* task). **~1,000 `lpa-platform*` nodes** written by guardkit autobuild during POC builds → drop out with guardkit's migration.

### Remote — inventory needed (graph nodes, no local code)

`agentic_dataset_factory` (340), `architect_agent` (246, no local repo), `study_tutor` underscore-variant (reconcile vs local hyphenated), `nats_infrastructure`/`vllm_profiling` (local dirs, no coupling).

**Key sequencing facts:**
- **Every code consumer already graceful-degrades** → FalkorDB can go dark without crashing any agent. Risk = silent knowledge loss, not runtime failure.
- **fleet-gateway follows study-tutor** (shared `student-*` groups).
- **Per-project scoping (§1) MUST land in fleet-memory before any consumer migrates** — each needs its own `project`, not `guardkit`.
- **Access-method split** (forge 3-tier, specialist MCP+FalkorDriver) makes those two the trickiest; dropping the `v0.29.5-guardkit.{1,3}` fork pins is part of jarvis/study-tutor/fleet-gateway migration.

**Confidence: high** on local-code coupling; **low-medium** on the remote/inventory-needed graphs (no local code to inspect — genuinely requires per-deployment inventory).

---

## 4. Corpus overlap — already covered vs unique-at-risk  *(from D)*

**Method:** enumerated every `Episodic` (source) node across guardkit's five graphs, classified by origin, cross-referenced against (a) FEAT-HARV harvest corpus in `public.store`, (b) `.claude/rules/*.md` (21 files, verified), (c) on-disk `docs/`+`tasks/`.

**The source layer is small — 230 Episodic nodes (~150 distinct after de-dup), not 4,154.** The headline count is dominated by the Qwen2.5-extracted `Entity` layer (~1,832), which fleet-memory would re-derive by embedding anyway → not "lost content."

| Graph | Episodic (source) | Entity (extracted) |
|---|---|---|
| `project_decisions` | 147 | ~1,520 |
| `project_knowledge` | 36 | 187 |
| `project_overview` | 19 | 54 |
| `project_architecture` | 14 | 52 |
| `turn_states` | 14 | 19 |
| **Total** | **230** | **~1,832** |

**Overlap by category (of ~150 distinct items):**

| Category | Share | Status |
|---|---|---|
| Doc-derived (harvested/on-disk) + synthetic seed | **~40%** | Covered — in `public.store` or re-harvestable; arch/overview are 100% regenerable `seed-system` output |
| Task-outcome (`Task Completion:`) | **~30%** | Migratable — proven by 5 live `build_outcome` rows; 34/62 also have `tasks/` files |
| Design-decision restating a `.claude/rules/` file | **~10%** (~13 of 74 Decision nodes) | Covered on disk (rule files git-versioned), though NOT in fleet-memory today |
| Cross-project decisions mis-scoped into guardkit | **~10%** (~27 of 74) | Not guardkit's loss — artifact of hardcoded `project="guardkit"` (§1) |
| **Genuinely-unique, guardkit-only, doc-less runtime lessons** | **~7–10%** (~10–15 nodes) | **UNIQUE-AT-RISK** — only in FalkorDB |

**The unique-at-risk tail** (all in `project_decisions`): e.g. `cwd is a selector-layer concern, not a harness-init concern` (TASK-FIX-002R-CONSUME, describes `selector.py` semantics, no doc anchor), `TASK-LCA-003 autobuild silent-gitignore failure mode`, `TASK-FIX-COACHSF01 Coach verdict-emission soft-fail`, `R2 BDD oracle silent-false-approval on returncode != 5`. **No doc, no rule file, no task file.**

**Bottom line:** ~**90% already covered** (fleet-memory, on-disk, or regenerable). **Genuinely unique non-recoverable content = ~10–15 distilled runtime-decision nodes (~7–10%).** A further ~27 unique *cross-project* nodes are at risk for their true owner projects (not guardkit). **The teardown's actual data-preservation task is ~10–40 `project_decisions` Decision nodes, not 4,154.** *Caveat: this measures content overlap, not the retrieval-character gap (§2) — a separate question.*

**Confidence: high** on "90% covered"; **medium** on the exact unique count (~10–15 is a themed estimate, not an exhaustive diff — a build-time exact diff is cheap and recommended).

---

## 5. Recommended program structure

Ordered workstreams. **Guardkit-local** unless noted. Effort S/M/L. **ONE-WAY doors are marked ⛔ and gated.**

```
WS-0 ──► WS-1 ──► WS-2 ──► WS-3 ──► WS-4 ──► WS-5 ──► WS-6 ⛔
scoping  export   guardkit  fleet    backup   verify   TEARDOWN
core     pipeline cutover   consumers          
                            (parallel)
```

### WS-0 — Per-project scoping foundation  *(S · cross-repo: fleet-memory + guardkit)*
**Blocks everything.** (1) fleet-memory: add trailing-delimiter guard to `retrieval/core.py:176` (**S**, the *only* fleet-memory-core change). (2) guardkit: thread `project` param into `build_memory_episode`, drop static `GroupMapping.project`, source project from config/env; unhardcode `fleet_memory_client.py:395`/`:301`. **Autobuild-safe** (localised, well-tested, single call sites). Dependency: none.

### WS-1 — `graph_export` one-shot pipeline  *(M · guardkit-local + infra: FalkorDB read)*
New `guardkit/memory/graph_export.py` + `guardkit memory migrate-graph` CLI. FalkorDB reader + graph→group_id normalizer; reuse `publish_episodes`, `resolve()`, `derive_episode_id`. Skip retire-disposition groups. **Autobuild-safe** for the code; the *live FalkorDB read* is infra-touching (needs `whitestocks:6379` reachable). Depends on WS-0 (project param).

### WS-2 — guardkit cutover  *(M · guardkit-local)*
Run WS-1 for guardkit's 5 graphs (option (i) chunk-level). **Then** optional WS-2b distillation enrichment (**M**, option (ii)) for `project_decisions`+`task_outcomes` (274 nodes) — *only if operator chooses fact-density (Q1)*. **Build-time exact diff** of the ~10–15 unique-at-risk nodes here (cheap; de-risks §4's estimate). Depends on WS-1. Autobuild-safe.

### WS-3 — Fleet consumer migration  *(L · cross-repo, parallelizable per consumer)*
Each consumer gets its own `project` (WS-0 must be generalised to a shared pattern first). Ordering within: **study-tutor before fleet-gateway** (shared `student-*`).
- forge (**HIGH/L**), study-tutor (**HIGH/L**), specialist-agent (**HIGH/L**, split MCP+py), jarvis (**MEDIUM/M**, write-only), fleet-gateway (**LOW-MED/S**, read-only, last).
- Drop `v0.29.5-guardkit.{1,3}` fork pins as part of each.
- **Mixed autobuild-safety:** the graceful-degrade wiring changes are autobuild-safe; **the `.mcp.json` / MCP-server reconfiguration is MANUAL** (Claude Code hard-gates `.mcp.json` under the SDK harness — known to stall autobuild at max_turns, per prior FEAT-MEM-08/009 experience).

### WS-4 — Remote-graph inventory  *(S–M · infra/manual)*
Per-deployment inventory of `agentic_dataset_factory` (340), `architect_agent` (246), `study_tutor` underscore-variant, `nats_infrastructure`/`vllm_profiling`. **Must-be-manual** (no local code). Reconcile the underscore/hyphen `study_tutor` namespace variants. Can run parallel to WS-2/WS-3.

### WS-5 — Verified fleet-memory backup + read-parity sign-off  ⛔-precursor *(M · infra/manual)*
Export/dump `public.store` (Postgres) to durable storage. **Read-parity check:** for each migrated project, confirm `group_ids`-scoped reads return non-empty assembled context. **Decision on fact-layer must be closed here** (Q1). This is the last checkpoint before the one-way door.

### WS-6 — FalkorDB teardown  ⛔ ONE-WAY DOOR · LAST *(S · infra/manual)*
Only after: **all code consumers migrated (WS-3)** + **remote graphs inventoried (WS-4)** + **verified fleet-memory backup (WS-5)** + **fact-layer decision made (Q1)** + **(recommended) FalkorDB kept dormant-but-alive for N months (Q4)**. **Must-be-manual.** Irreversible: the 5,735 guardkit facts (and fleet-wide equivalents) are *not* backed up unless option (ii) captured them or the FalkorDB dump is retained.

**Autobuild-safe vs manual summary:**
- **Autobuild-safe:** WS-0, WS-1 (code), WS-2, most of WS-3 (wiring).
- **Must-be-manual:** `.mcp.json` reconfig (WS-3), WS-4 remote inventory, WS-5 backup/parity, WS-6 teardown, any live FalkorDB read/dump.

---

## 6. Open questions for the operator

1. **Fact-layer fidelity — chunk-level vs one-time distillation? (gates WS-2b, WS-5, WS-6)** Accept verbose chunk-level retrieval (option (i), LLM-free, zero cost, ships fastest) as the fleet default? Or fund a **one-time offline cloud-LLM distillation** (option (ii)) for the two high-value graphs (274 nodes, ~cents) to restore today's fact-density? Recommendation: hybrid — (i) everywhere, (ii) for `project_decisions`+`task_outcomes` only. *This is the load-bearing decision; it determines whether the 5,735 facts are recovered as distilled documents or discarded.*

2. **Per-project scoping design — drop the static field, or key mappings on `(project, group_id)`?** WS-0 preferred design threads `project` as runtime context and removes it from `GroupMapping`. Do you also anticipate **different group→facet maps per project** (forge's `forge_*`, study-tutor's `student-*`, etc.)? If yes, the mapping table must key on `(project, group_id)` (**M** not **S**), and each consumer authors its own table (the **M–L** fleet-wide cost in §1).

3. **Unique-at-risk preservation policy.** For the ~10–15 guardkit-only doc-less Decision nodes (and the ~27 cross-project ones): migrate as-is via chunk export, distill, **or** promote the genuinely-valuable ones into `.claude/rules/*.md` / `docs/decisions/` on disk (making them git-versioned and re-harvestable, permanently)? The cross-project nodes specifically — re-capture under their true project scope, or accept loss?

4. **Keep FalkorDB dormant-but-alive as a fallback for N months?** ⛔ WS-6 is one-way. Strong recommendation: after migration + backup, **stop writes but keep the FalkorDB container/data alive read-only for N months** (operator picks N) as a rollback path, then physically tear down. What is N, and is the Synology/`whitestocks` capacity cost acceptable?

5. **Backup/export policy for the raw FalkorDB dump.** Independent of fleet-memory backup (WS-5): do you want a **one-time FalkorDB graph dump** (both Episodic *and* the 5,735 extracted facts) archived to durable storage (NAS/`whitestocks`) *before* teardown, as the ultimate insurance against the fact-layer being unrecoverable? Cheap; makes WS-6 psychologically safer.

6. **Remote-graph ownership (WS-4).** Who inventories `architect_agent` (246, no local repo) and `agentic_dataset_factory` (340, graph exists but no local `src/` coupling)? These are the only genuinely unknown-writer graphs — do we block teardown on inventorying them, or accept their loss if no owner claims them?

---

### Low-confidence / flagged items
- **Episodic count discrepancy (504 vs 230):** §2 and §4 disagree on the guardkit source-node count (de-dup + classification boundary). Reconcile with an exact `MATCH (n:Episodic)` count + distinct-item de-dup during WS-1. Does **not** affect go/no-go; affects distillation batch size.
- **Fleet-wide "~4,000 Episodic" / "18 projects / ~11 active consumers":** extrapolated, not measured. WS-4 inventory firms these up.
- **The ~10–15 unique-at-risk count** is a themed estimate; the exact diff is cheap and should run in WS-2.
- **Remote graphs** (WS-4) are the lowest-confidence area — no local code to inspect.

---

# Appendices — full deep-dive detail

## Appendix A — Per-project + per-group scoping model (full)

I have the full change surface mapped. Here is the deliverable.

## Per-project + per-group scoping model

### 1. Where `project` is hardcoded today

`project` is **not** hardcoded in fleet-memory itself — it is a first-class dimension in every storage/identity primitive. It is only hardcoded to the literal `"guardkit"` in **guardkit's mapping and read-client**, in exactly three places:

| # | Location | Hardcode | Effect |
|---|---|---|---|
| A | `guardkit/knowledge/fleet_memory_mapping.py:89-274` | `project="guardkit"` in **all 29** `GroupMapping` rows (grep count: 30 incl. dataclass field) | Every write's `payload.project`/`project_id` becomes `"guardkit"` → namespace prefix `fleet_memory.guardkit.*` |
| B | `guardkit/knowledge/fleet_memory_client.py:395` | `SearchRequest(project="guardkit", ...)` in `FleetMemoryClient.search` | Every read is scoped to `("fleet_memory", "guardkit")` regardless of caller |
| C | `guardkit/knowledge/fleet_memory_client.py:301` | `self._store.aget(("fleet_memory", "guardkit", "chunk"), "__healthcheck__")` in `health_check` | Cosmetic (healthcheck probe only); harmless but should track the active project |

The mapping table's project field flows to the writer via `fleet_memory_payloads.py:187` (`project = mapping.project`), then onto `BasePayload.project` (`fleet_memory_payloads.py:203`) and `MemoryEpisodeV1.project_id` (`:212`).

### 2. Does the store/retrieval already support a project filter? — **Yes, fully, at the SQL level.**

Project scoping is already implemented end-to-end in fleet-memory; guardkit just never varies the value:

- **Storage key** (`public.store`): PK is `(prefix, key)`. The `prefix` column is the dot-joined namespace tuple. Live values confirmed: `fleet_memory.guardkit.chunk` (679), `fleet_memory.guardkit.build_outcome` (5), `fleet_memory.guardkit.adr` (1) — all 685 rows are `fleet_memory.guardkit.*`. **Project is already the middle prefix segment.**
  - Writes build `("fleet_memory", payload.project, payload_type)` — writer `core.py:86`, chunk_writer `chunk_writer.py:82`.
  - Identity (`writer/identity.py:27-48`) is `uuid5` of `natural_key` = `{payload_type}:{project}:{identifier}` (`base.py:160-166`), so project is baked into the record UUID too — no cross-project key collisions.
- **Retrieval** (`retrieval/core.py:176`): `namespace_prefix = ("fleet_memory", request.project)` → `store.asearch` → langgraph emits `store.prefix LIKE 'fleet_memory.{project}%'` (verified in `langgraph.store.postgres.base:445-446`). So a `SearchRequest(project="jarvis", ...)` would already return only jarvis rows.
- **Validation** (`search_request.py:42-61`, `store.py:52-72`): project must match `^[a-z0-9_]+$` (underscores only) on both read and write — so consumer project names like `lpa-platform*` must be normalised to `lpa_platform` before use.

**One sharp edge to fix when multi-project lands:** the retrieval prefix is a `LIKE 'prefix%'` match, so `project="guardkit"` would also match a future `guardkit_factory` project (`fleet_memory.guardkit_factory.*`). Today irrelevant (single project); with 18 projects sharing distinct names it is a latent cross-project bleed. The safe fix is to pass the **3-segment prefix per payload type** or add a trailing-delimiter guard (search `("fleet_memory", project)` is a 2-tuple by design to span payload types, so the delimiter guard — matching `fleet_memory.{project}.` — is the correct remediation, done inside fleet-memory retrieval).

### 3. Group-scoped retrieval (`group_ids=["architecture_decisions"]`) — already mapped, via payload_types + domain_tags

fleet-memory has **no `group` field**; it has two orthogonal read facets that together reconstruct group semantics, and guardkit's client already translates to them:

- `fleet_memory_client.py:379-388`: for each `group_id`, `resolve(gid)` → adds `mapping.payload_type` to `payload_types` and `mapping.domain_tags` to `domain_tags`.
- `retrieval/core.py:46-63` filters by payload type (via `natural_key` prefix); `:93-109` filters by domain tags. Domain-tag matching resolves tags from the top-level field OR from inside the embedded `content` JSON (`_item_domain_tags`, `:66-90`) — the TASK-MEM08-012 fix, so typed-payload tags are honoured.

So group-scoped reads **already work** for the migrate groups. The mapping is lossy in one direction: multiple Graphiti groups collapse onto the same `(payload_type, domain_tags)` — e.g. `project_decisions→adr[project]`, `adrs→adr[decision]`, `architecture_decisions→adr[system]` — but domain_tags disambiguate them, so `group_ids=["architecture_decisions"]` → `payload_types=["adr"], domain_tags=["system"]` retrieves only system ADRs. This mechanism is **project-independent** and needs no change to preserve group-scoped retrieval across projects.

### The three required changes

**(1) Scope writes per project — S (guardkit only; fleet-memory unchanged)**

The writer already honours `payload.project`. The only change is to stop hardcoding `"guardkit"` in the 29 mappings. Two options:
- **Preferred (S):** drop `project` from `GroupMapping` entirely; thread the active project as a parameter into `build_memory_episode(mapping, ..., project=...)` (`fleet_memory_payloads.py:187,203,212,239`) and its callers (`FleetMemoryClient.add_episode`, `DualWriteClient`). Project is a runtime/context property (which repo is emitting the episode), not a per-group static — so it does not belong in the group table.
- Source the project from `.guardkit/graphiti.yaml` (the config already read at `fleet_memory_client.py:548-556`) or a `GUARDKIT_MEMORY_PROJECT` env var, sanitised via `sanitize_identifier` (`fleet_memory_payloads.py:38-53`).
- **fleet-memory: zero changes** — the write path is already project-parameterised (`core.py:86`, `chunk_writer.py:82`, `identity.py`, NATS subject `memory.episode.{project_id}.{episode_type}` per `handler.py:52`).

**(2) Filter reads per project — S in guardkit; S–M in fleet-memory (only for the LIKE-prefix guard)**

- **guardkit (S):** replace the hardcoded `project="guardkit"` at `fleet_memory_client.py:395` (and healthcheck `:301`) with the same context-derived project used for writes. `FleetMemoryClient.search`/`DualWriteClient.search` need no signature change — the `scope` param already exists and is currently ignored, or add an optional `project=` param that defaults to the client's configured project.
- **fleet-memory (S, optional but recommended):** add the trailing-delimiter guard to `retrieval/core.py:176` so `project="jarvis"` cannot prefix-match `project="jarvis_v2"`. Small, localised, well-tested (`search` has a single call site).

**(3) Preserve group-scoped retrieval — S (no change; verify only)**

- No code change required. The `group_id → (payload_type, domain_tags)` translation (`fleet_memory_client.py:379-388`) is project-orthogonal and already works. Effort is only: extend `GROUP_ID_MAP` (or make it per-project) if other consumers (jarvis, forge, study_tutor, etc.) use group_ids that guardkit's 29-row table doesn't cover — that is **per-consumer mapping authorship (M)**, not a fleet-memory change. If different projects need different group→facet mappings, the mapping table must key on `(project, group_id)` rather than `group_id` alone (**M**).

### Effort summary

| Change | fleet-memory | guardkit | Overall |
|---|---|---|---|
| (1) Scope writes per project | none | **S** (thread `project`, drop static field) | **S** |
| (2) Filter reads per project | **S** (LIKE-prefix delimiter guard) | **S** (unhardcode `:395`/`:301`) | **S** |
| (3) Preserve group-scoped retrieval | none | none (verify); **M** if per-project group maps needed | **S** (guardkit-only) / **M** (fleet-wide) |
| (fleet-wide) per-consumer group→facet mapping tables | none | **M–L** (18 projects, ~11 active consumers) | **M–L** |

**Bottom line:** the identity + storage + retrieval layers already carry a full project dimension (prefix middle-segment, natural_key, UUID, NATS subject) and a working group→(payload_type, domain_tags) translation. Multi-project + group-scoped retrieval for guardkit is an **S** change concentrated in three literals in two guardkit files (`fleet_memory_mapping.py:89-274`, `fleet_memory_client.py:395` and `:301`), plus one **S** hardening guard inside fleet-memory retrieval (`retrieval/core.py:176`). Extending it to the whole fleet is **M–L**, driven not by fleet-memory core but by authoring per-consumer group→facet mapping tables (currently guardkit-only, 29 rows).

## Appendix B — Migration mechanism + fact-vs-chunk (full)

I now have complete understanding of both the typed-payload path (JSON → DeterministicWriter, embeds a canonical-JSON `content` string) and the prose path (markdown → chunker → ChunkWriter, embeds raw chunks). The DeterministicWriter embeds `json.dumps(payload_dict)` — so a distilled document's prose must be a field within the payload (e.g. via `DocumentPayload` with the summary text carried in body/content), whereas raw Episodic prose is a natural fit for the markdown chunk path. I have everything I need to write the deliverable.

## Migration mechanism + fact-vs-chunk trade-off

### The two content layers in the graph (live counts, 2026-07-01)

Each guardkit FalkorDB graph holds two distinct layers, and they migrate very differently:

| Layer | What it is | guardkit* live count | Migratable? |
|---|---|---|---|
| **Episodic nodes** | Raw source prose (doc bodies, task-outcome notes, decision notes) — `content` + `name` + `source_description` + `group_id` + `created_at` | **504** episodes | Yes — 1:1, no LLM |
| **Entity + RELATES_TO/MENTIONS edges** (`r.fact`) | The Qwen2.5-*extracted* distilled relationship statements | **5,735** facts | Not without an LLM |

Episodic content is small and self-contained prose, not pointers — I sampled it live: `project_decisions` avg 1,527 B / max 4,048 B; `task_outcomes` avg 1,481 B / max 5,628 B; `project_knowledge` avg 2,415 B / max 7,247 B. **Every sampled node is orders of magnitude under the 900 KB `MAX_EPISODE_BODY_BYTES` cap** (`nats-core/src/nats_core/events/_memory.py:12`), so no chunking or oversized-skip handling is needed for the graph export. Example Episodic body: *"TASK-GMO-004: End-to-end test Graphiti add_episode… Found and fixed two bugs in factories.py: (1) base_url not passed… (2) OpenAIClient uses Responses API which Ollama doesn't support…"* — this is migratable knowledge, verbatim.

### How content already gets into fleet-memory (the tooling to reuse)

The harvest path (`guardkit/memory/harvest_walker.py` → `harvest_publisher.py` → `guardkit/cli/memory.py:149`) is the template: **walk sources → build `MemoryEpisodeV1` → `NATSClient.publish_episode` → relay routes on `content_format`.** The relay is the load-bearing fork (`fleet-memory/src/fleet_memory/relay/service.py:116-124`):

- `content_format="json"` → `DeterministicWriter` — embeds a canonical-JSON payload (`writer/core.py:157-189`, `content` field). This is the **distilled / typed** path (the FEAT-MEM-07 re-index publisher at `fleet-memory/src/fleet_memory/reindex/publisher.py`).
- `content_format="markdown"|"text"` → `chunk_prose` → `ChunkWriter` — embeds **raw prose chunks**. This is what the 679 FEAT-HARV rows and today's `685`-row store use.

The `(project, group_id) → (payload_type, domain_tags)` mapping is **already authored** in `guardkit/knowledge/fleet_memory_mapping.py` (29 groups, `resolve()` at line 296) — it just needs a graph→group_id feed, and `derive_episode_id` (`harvest_taxonomy.py:69`) is already byte-identical to fleet-memory's, giving free JetStream idempotency.

### Proposed pipeline: `graph_export`

A new `guardkit/memory/graph_export.py` + `guardkit memory migrate-graph` CLI command, structurally a sibling of `harvest_walker`:

1. **Read** — connect FalkorDB (`whitestocks:6379`), for each `guardkit*` graph run `MATCH (n:Episodic) RETURN n`. Pull `content`, `name`, `source_description`, `group_id`, `created_at`.
2. **Map** — strip the `guardkit__` prefix → group_id → `resolve(group_id)`. Skip `disposition="retire"` (the 17 seed_module groups already covered by the harvest corpus — no double-ingest). Derive `payload_type` + `domain_tags` from the mapping.
3. **Build episode** — `MemoryEpisodeV1(project_id="guardkit", body=content, name=name, source="graphiti-migration", source_ref=f"{group_id}:{uuid}", occurred_at=created_at, episode_type=…)`, `episode_id=derive_episode_id(natural_key)` for idempotency.
4. **Publish** — reuse `publish_episodes()` unchanged (already handles per-episode 900 KB guard + idempotent retry).

Reuse is high: publisher, ID derivation, mapping table, and NATS/relay plumbing are all existing. The **only genuinely new code** is the FalkorDB reader + the graph→group_id normalizer — an evening's work.

### Per-project volume (live)

- **guardkit**: 504 Episodic (the migratable set), dominated by `project_decisions` (147) + `task_outcomes` (127). Retire-disposition groups contribute little Episodic content (the `rules_*` graphs, ~130 episodes, map to retired `seed_module` groups → skipped).
- **Fleet-wide** (for the full teardown): FalkorDB's 11,847 nodes are ~⅓ Episodic, so ~3,500–4,000 Episodic across all 18 projects — a bounded, one-shot publish. Note `fleet_memory_mapping.py` **hardcodes `project="guardkit"`** for all 29 groups (`harvest_walker.py:147` too); fleet-wide export requires a per-project `project_id` (derived from graph prefix) — a small but required change, flagged for Deep-Dive on scoping.

### The trade-off: extracted facts vs raw chunks

Migrating Episodic content gives you the **raw source prose** back, but you lose the 5,735 Qwen2.5-distilled facts. Concretely:

- **Today's read** (`fleet_memory_client.py:379-417`): guardkit already does *not* return per-fact hits post-cutover — it calls `fm_search` → `assemble_context` and returns a single assembled `context_block` with a coverage score. So the retrieval *surface* is unchanged. What changes is **corpus character**: verbose 1.5 KB chunks ("we tested X, found bug Y, fixed Z…") instead of terse distilled statements ("The editable install of guardkit-py adds its top-level directories to sys.path"). More tokens per retrieval, lower signal density, but the underlying facts are all present in the prose.
- The `.claude/rules/*.md` design-rule corpus (the highest-value guardkit knowledge — `absence-of-failure`, `path-string-mismatch`, etc.) is **already harvested as chunks** and retrieves well today, which de-risks the chunk-level option for the most important content.

**Options to recover fact-density without a permanent LLM:**

**(i) Accept chunk-level (raw Episodic → markdown chunker).** Zero LLM, zero ongoing cost, simplest. Retrieval is more verbose but complete. This is the same shape as the proven FEAT-HARV corpus.

**(ii) One-time distillation at migration.** Batch the 504 (or ~4,000 fleet-wide) Episodic bodies through *any* LLM (cloud is fine — it runs once, offline, at migration time, then is discarded — this does **not** violate the "drop Qwen2.5 / no runtime LLM" goal), producing 1–3 sentence summary-documents. Publish those as `DocumentPayload` (`content_format="json"` → DeterministicWriter), embedded once. Result: fact-dense retrieval matching today's character, **no runtime LLM in the read path.** Cost is bounded and small: ~504 short completions for guardkit (~cents on a cloud model); ~4,000 fleet-wide (still trivial, a one-off). The `DocumentPayload` target already exists (`payloads/models.py:91`); you'd add a thin distillation step between read and build.

### Recommendation

**Do a hybrid, staged by disposition:**

1. **Ship option (i) first** for all migrate-disposition Episodic content — it's the existing pipeline with a FalkorDB reader bolted on, fully LLM-free, and immediately unblocks FalkorDB decommission. The 504-node guardkit corpus lands as markdown chunks alongside the 679 harvest chunks.
2. **Layer option (ii) as an optional enrichment pass** *only* for the two high-value graphs (`project_decisions` 147 + `task_outcomes` 127 = 274 nodes) where distillation buys the most, using a cloud LLM once at migration. This restores fact-density for the knowledge that matters, at negligible one-time cost, with **no permanent Qwen2.5/FalkorDB dependency** — which is the whole point of the teardown.

The 17 retire-disposition groups migrate nothing (already in the harvest corpus). The 5,735 raw extracted facts are **not** worth re-deriving wholesale — they're a distillation *of* the 504 Episodic nodes you're already migrating; option (ii)'s selective re-distillation recovers the density where it counts without reproducing the extraction graph.

### Effort estimate

- **Option (i) pipeline** (`graph_export.py` FalkorDB reader + `migrate-graph` CLI + graph→group_id normalizer, reusing publisher/mapping/ID-derivation; tests): **~1–1.5 days** (guardkit-only; +0.5 day to un-hardcode `project` for fleet-wide).
- **Option (ii) distillation enrichment** (batch LLM caller, `DocumentPayload` builder, prompt, dedup): **~1 day** on top, guardkit-only; runs offline once.
- **Total for guardkit cutover: ~2–2.5 days.** Fleet-wide (per-project scoping + re-run across 18 projects): **+1 day**, mostly the `project` parameterization and a batch driver — the mechanism is unchanged.

Key file references: `guardkit/memory/harvest_walker.py:145-155` (episode build), `guardkit/memory/harvest_publisher.py:89` (publish, reuse as-is), `guardkit/memory/harvest_taxonomy.py:69` (idempotent ID), `guardkit/knowledge/fleet_memory_mapping.py:296` (`resolve`, 29 groups), `fleet-memory/src/fleet_memory/relay/service.py:116-124` (content_format fork), `fleet-memory/src/fleet_memory/reindex/publisher.py` (JSON/DeterministicWriter template for option ii), `guardkit/knowledge/fleet_memory_client.py:379-417` (read path — already context-block, not per-fact).

## Appendix C — Fleet consumer inventory (full)

Complete. agentic-dataset-factory, nats-infrastructure, and vllm-profiling have no src Graphiti coupling locally (agentic-dataset-factory has a graph namespace but no local src coupling — its writes came from elsewhere or an older layout; treat as remote-inventory-needed since the graph holds 340 nodes). I have everything I need.

## Fleet consumer inventory

The other Graphiti consumers must migrate before FalkorDB (whitestocks:6379, 11,847 nodes / 92 graphs) can be torn down. I grepped each local sibling repo's `src/` for live coupling (docs/tasks/history matches excluded). Three big surprises: **nats-core, guardkitfactory, and lpa-platform-poc have ZERO Graphiti coupling in code** — all their hits are regex `.search()` false-positives or docs/task/retro references. nats-core is actually the fleet-memory *producer*, not a consumer.

| Consumer | R/W | access (MCP/py) | groups | optional? | migration effort | notes |
|---|---|---|---|---|---|---|
| **forge** | **R+W** | py client, **3-tier**: MCP-first (`graphiti_core`) → CLI (`guardkit graphiti add-context`/`query`) → unavailable | `forge_pipeline_history`, `forge_calibration_history` | **Yes** — `fire_and_forget_write` never raises (`writer.py:19-20`); reconcile query degrades gracefully (`reconciler.py:46-51`); `find_spec("graphiti_core")` gate (`reconciler.py:406`) | **HIGH** | Heaviest fleet consumer after guardkit. Writes 6 typed pipeline entities (`GateDecision`/`CapabilityResolution`/`OverrideEvent`/`CalibrationAdjustment`/`SessionOutcome`/`CalibrationEvent`), fan-out RRF reads for calibration priors (`priors.py:260-290`), plus a durability reconciler (`reconciler.py`) and idempotency existence-checks (`session_outcome.py`). Also two LangChain `@tool` wrappers over `guardkit graphiti` (`tools/graphiti.py`). Live graph: **forge 645 nodes**. Own group namespace (`forge_*`, not `guardkit__`). |
| **study-tutor** | **R+W** | py client, **direct** `graphiti-core[falkordb]` (git fork `v0.29.5-guardkit.3`, `pyproject.toml:35`) | prefix discipline: `student-<id>`, `subject-<slug>`, `fleet:appmilla` (`async_write.py:149-167`, `student_model.py:67-72`) | **Yes** — writes fire-and-forget/log-only, never raise (`async_write.py:26-27`); lazy `import graphiti_core` inside methods so absence is tolerated (`graphiti_client.py:9-11`) | **HIGH** | Writes live-tutor-session episodes via single audited `add_episode` call-site (CC-13 invariant, `async_write.py:421`) + seed script. Reads student-model partitions via `EntityNode/EntityEdge.get_by_group_ids` (`queries.py:181-264`). 7 entity types (`student_model.py`). Live graph: **study_tutor 552 nodes** (+ underscore-variant remote). |
| **specialist-agent** | **R+W** | **BOTH**: MCP-callable writer (injected `mcp__graphiti__add_memory`/`search_nodes`/`search_memory_facts`, `writer.py:140-143`) AND lazy `graphiti-core`+`FalkorDriver` py client for the Player query tool (`graphiti_client.py:162-163`) | `role:{role_id}` (writer, `writer.py:43-55`), `project:{project_id}` + `role:` + fleet 3-scope (query tool `graphiti_query.py`, `po_knowledge.py:147`) | **Yes** — writer degrades gracefully (`writer.py:4`); query client is circuit-breaker + `*_safe` methods returning `[]` (`graphiti_client.py:4-8`); `graphiti_query` tool only conditionally injected into Player (`session.py:2259-2267`) | **HIGH** | Split access model is the migration complication: role-learning-metrics writes go through MCP callables; the Player's knowledge-query tool goes direct to FalkorDB. No `graphiti-core` in root `pyproject.toml` (lazy-imported). Much of the write-back surface is still `tasks/design_approved`/`backlog` (SWB, RLM), so live wiring < full design. Live graph: **specialist_agent 68 nodes** (+ architect_agent 246 remote). |
| **jarvis** | **W only** | py client, **direct** `graphiti-core` (git fork `v0.29.5-guardkit.1`, `pyproject.toml:80-81`, `[graphiti]` extra) | `jarvis_routing_history` (episode name `jarvis_routing_history:{decision_id}`, `routing_history.py:936`) | **Yes** — `memory_store_backend` defaults to `in_memory` (`settings.py:55`); `_connect_graphiti` returns `None` on unimportable SDK / bad endpoint (`lifecycle.py:409-456`); writes fire-and-forget, WARN-on-failure per DDR-019, never touch dispatch hot path | **MEDIUM** | Write-only: fire-and-forget `add_episode` for routing-history via `RoutingHistoryWriter` (`routing_history.py:508,731,935`). No read path (grep for `.search`/`search_nodes` on graphiti = none). Structural `GraphitiClientProtocol` (only needs `add_episode`). Live graph: **jarvis 1,115 nodes**. |
| **fleet-gateway** | **R only** | py client, **direct** `graphiti-core`+`FalkorDriver`, connect-per-call (`common/graphiti_client.py:119-120`) | default `student-lilymay` / `student:` groups (`graphiti_client.py:55`) — reads study-tutor's data | **Yes** — both `search`/`search_student_progress` swallow all errors; former returns `[]`, latter `{"data_available": False, ...}` (`graphiti_client.py:14-19`); auth-vs-unreachable classified | **LOW-MEDIUM** | Read-only cross-agent: Scholar's `query_student_model` tool reads the study-tutor student graph (`reachy/.../query_student_model.py`, `common/graphiti_client.py`). No writes. Migration depends on study-tutor migrating first (shared `student-*` groups). Live graph: **fleet-gateway 26 nodes** (its own, likely test/e2e). |
| **nats-core** | **none (producer)** | n/a — never imports `graphiti_core`, no `add_episode`/`.search` | n/a — passive optional `GraphitiConfig`/`FalkorDB endpoint` config field only (`agent_config.py:64-70,110`) | n/a | **NONE** | **NOT a Graphiti consumer.** It is the **fleet-memory producer**: publishes `memory.episode.{project_id}.{episode_type}` to NATS for the fleet-memory relay (`client.py:323-346`, `topics.py:134`, `events/_memory.py` = the cross-repo write contract). The `GraphitiConfig` is a passive per-agent config field (FalkorDB URL) it never uses itself. This is migration-target infra, not teardown blocker. Live graph: **nats_core 146 nodes** (seeded from elsewhere, not by nats-core code). |
| **guardkitfactory** | **none** | n/a | n/a | n/a | **NONE** | No `src/` Graphiti coupling — all matches are autobuild-migration review docs / task files. Not a consumer. Live graph: **guardkitfactory 32 nodes** (guardkit's autobuild wrote these on its behalf). |
| **lpa-platform-poc** | **none** | n/a | n/a | n/a | **NONE** | No `src/` coupling — all matches are regex `re.search()` false-positives (`docling.py`, `voice/service.py`) and docs/retros/task files (`TASK-FIX-9A4B-D-graphiti-falkordb-asyncio-noise.md` is a *suppress-noise* task, not usage). Live graph: **lpa-platform\* ~1000 nodes** — written by guardkit autobuild during the POC builds, not by lpa code. |

### Remote — inventory needed (in graph list, no local code coupling)

These hold nodes in FalkorDB but have no live local `src/` Graphiti coupling here — the writers are either remote repos not checked out, or the nodes were seeded by guardkit's autobuild on the project's behalf:

| Graph namespace | Nodes | Status |
|---|---|---|
| `agentic_dataset_factory` | 340 | Local dir exists (`agentic-dataset-factory/`) but **no `src/` Graphiti coupling** found — remote/older-layout writer; inventory the deployed agent. |
| `architect_agent` | 246 | **Remote** — no local repo; specialist-agent's 3-scope reads reference it (`project:`/`role:`/fleet). |
| `lpa-platform` (+ variants ~1000) | ~1000 | Written by **guardkit autobuild** during POC, not by lpa-platform-poc code. Likely torn down with guardkit's own migration. |
| `study_tutor` (underscore variant) | (subset of 552) | **Remote/legacy** namespace variant vs local `study-tutor`'s hyphenated `student-`/`subject-` groups — reconcile before teardown. |
| `nats_infrastructure` | — | Local dir (`nats-infrastructure/`) but **no Graphiti coupling** in code; graph nodes (if any) seeded externally. |
| `vllm_profiling` | — | Local dir (`vllm-profiling/`) but **no Graphiti coupling** in code. |

### Migration summary

- **Real code-level blockers (must migrate):** forge (HIGH), study-tutor (HIGH), specialist-agent (HIGH, split MCP+py model), jarvis (MEDIUM, write-only), fleet-gateway (LOW-MEDIUM, read-only, follows study-tutor).
- **Not blockers (no code coupling):** nats-core (it's the fleet-memory *producer*), guardkitfactory, lpa-platform-poc — their graph nodes were written by guardkit's own autobuild, so they drop out when guardkit migrates.
- **Every code consumer already graceful-degrades** (fire-and-forget writes, `[]`-returning safe reads, `find_spec`/lazy-import gates) — so FalkorDB can go dark *without crashing any agent*; the risk is silent knowledge loss, not runtime failure.
- **Access-method split matters for cutover:** forge (3-tier MCP→CLI→core) and specialist-agent (MCP-callables for writes, direct FalkorDriver for the Player query tool) are mixed; jarvis/study-tutor/fleet-gateway are direct `graphiti-core` git-fork pins (`v0.29.5-guardkit.{1,3}`) — dropping the fork pin is part of each's migration.
- **Group-namespace fragmentation:** forge (`forge_*`), jarvis (`jarvis_routing_history`), study-tutor (`student-`/`subject-`/`fleet:appmilla`), specialist (`role:`/`project:`), fleet-gateway (reads `student-*`) — fleet-memory currently HARDCODES `project="guardkit"` for all groups (`guardkit/knowledge/fleet_memory_mapping.py`), so **per-project scoping must land in fleet-memory before any of these can migrate** (each needs its own `project` value, not `guardkit`).

## Appendix D — Corpus overlap (full)

I have all the evidence needed. Here is the deliverable markdown section.

---

## Corpus overlap (what's already covered vs unique-at-risk)

**Method.** I enumerated every `Episodic` node (the raw *source* layer, not the Qwen2.5-extracted `Entity`/`RELATES_TO` layer) across guardkit's five FalkorDB graphs, classified each by origin (doc-derived / task-outcome / synthetic-seed / turn-state / captured-decision), then cross-referenced each against (a) the FEAT-HARV harvest corpus in `public.store` (`fleet-memory`), (b) the `.claude/rules/*.md` design-rule files, and (c) on-disk `docs/` and `tasks/`.

### The source layer is small — 230 Episodic nodes, not 4,154

The verified "guardkit=4,154 nodes" figure is dominated by the extracted `Entity` layer (Qwen2.5 output). The **raw source** content is only the Episodic nodes:

| Graph | Episodic (source) | Entity (extracted) |
|---|---|---|
| `guardkit__project_decisions` | 147 | ~1,520 |
| `guardkit__project_knowledge` | 36 | 187 |
| `guardkit__project_overview` | 19 | 54 |
| `guardkit__project_architecture` | 14 | 52 |
| `guardkit__turn_states` | 14 | 19 |
| **Total** | **230** | **~1,832** |

The entire migration-at-risk surface is these **230 source nodes** (many are duplicate `_chunk_N` rows — e.g. `DECISION-DF-001` appears as 18 duplicated chunk nodes; distinct source items are ~150). Everything downstream is Qwen2.5-derived and would be *re-derived by embedding* under fleet-memory anyway, so it is not "lost content."

### Breakdown by origin, with overlap verdict

**(a) Doc-derived → already harvested or on-disk (LOW risk).**
- `project_knowledge` doc-derived nodes reference only **3 distinct docs**: `docs/decisions/DECISION-DF-001…` (harvested — 6 chunks live in `public.store`, `episode_type=adr`/`document`), `docs/architecture/guardkit-positioning-2026-q2.md`, and `docs/features/FEAT-TPL-PLAYER-…md`. The latter two dirs are **outside `HARVEST_MAP`** (`harvest_taxonomy.py:37-63` walks only `docs/adr[s]`, `docs/decisions`, `docs/code-review`, `docs/completion-reports`, `docs/retro`, `docs/design`, `docs/guides`, `docs/reference`) — but **both files still exist on disk** (verified: 6,958 B and 14,267 B, git-versioned). Recoverable by re-harvest, zero unique captured content.
- `project_architecture` (14) and `project_overview` (19) are **100% synthetic seed episodes** (`guardkit_purpose`, `guardkit_core_principles`, `guardkit_project_structure`, `guardkit_installation_setup`, …) generated by `guardkit graphiti seed-system` from `CLAUDE.md`/README prose. Fully regenerable; no unique knowledge.

**(b) Task-outcome-derived → migratable as `build_outcome` (LOW risk).**
- `project_decisions` holds **62 `Task Completion: TASK-*` nodes**. **34/62** have a live task file under `tasks/` in the guardkit repo (recoverable). **27/62** have no guardkit-repo file — and inspection shows most are **cross-project contamination** seeded into the guardkit group: `TASK-W4…W7` (dotnet exemplar), `TASK-PO02-*`/`TASK-MDF-*`/`TASK-POE-*` (study-tutor / po-orchestrator), `TASK-CDR-*`/`TASK-DRD-*`/`TASK-FMDR-*` (forge/dark-factory). These are the same `build_outcome` shape already proven migratable in the FEAT-MEM-08 soak (5 `build_outcome` rows live in `public.store`). The 4 `/tmp/guardkit-task-outcome-TASK-*` nodes in `project_knowledge` are the same class.

**(c) Captured decision / runtime knowledge → genuinely at-risk (the real question).**
- `project_decisions` holds **74 `Decision: …` nodes** — the distilled runtime/design-rule knowledge that has no doc source and is not a task file.
  - **~13 map to an existing `.claude/rules/*.md` design-rule file** by theme (the low-fidelity-oracle family: `absence-of-failure`, `path-string-mismatch`, `per-task-green-is-not-feature-green`, `smoke-gate-is-feedback`, `evidence-boundary`, `harness-cancellation`, `namespace-hygiene`, `stack-plugin`, `uv-sources`, `absence-must-survive`). These 21 rule files (`.claude/rules/`) are **NOT harvested** (outside `HARVEST_MAP`) but **are on disk and git-versioned** — the graph node is a *restatement* of a documented rule, so no loss.
  - **~27 are cross-project decisions** (study-tutor MCP `SR-01/02/03`, dotnet `NatsEventPublisher`, LPA `lpa_uuid`, forge NATS shaping) — content verified as *not guardkit runtime* (e.g. `TASK-PO02-005` body = "baked into the study-tutor MCP runtime"; `TASK-W7` = "dotnet-functional-fastendpoints-exemplar"). At-risk only for *those* projects, not guardkit, and only if never re-captured under a correct project scope.
  - **~10-15 are genuinely-unique, guardkit-only, doc-less runtime lessons** — e.g. `Decision: cwd is a selector-layer concern, not a harness-init concern` (seeded by TASK-FIX-002R-CONSUME; describes `selector.py` cwd-consumption semantics with no doc anchor), `Decision: TASK-LCA-003 - autobuild silent-gitignore failure mode`, `Decision: TASK-FIX-COACHSF01 - Coach verdict-emission failures soft-fail`, `Decision: R2 BDD oracle silent-false-approval on returncode != 5`. These are the only nodes with **no doc, no rule file, no task file** — captured knowledge that lives *only* in FalkorDB.

### Rough proportions (of the ~150 distinct guardkit source items)

| Category | Share | Overlap status |
|---|---|---|
| Doc-derived (harvested or on-disk) + synthetic seed | **~40%** (33 arch/overview seeds + doc chunks; `DECISION-DF-001` harvested) | Already covered — in `public.store` or re-harvestable from `docs/` on disk |
| Task-outcome (`Task Completion:` / task-outcome) | **~30%** (62 completion nodes; 34 have task files, rest are `build_outcome`-migratable) | Already migratable — proven by 5 live `build_outcome` rows; 34/62 also have `tasks/` files |
| Design-decision that restates a `.claude/rules/` file | **~10%** (~13 of 74 Decision nodes) | Covered on disk (rules files git-versioned), though **not** in fleet-memory today |
| Cross-project decisions mis-scoped into guardkit | **~10%** (~27 of 74) | Not guardkit's loss; noise from the hardcoded `project="guardkit"` mapping |
| **Genuinely-unique, guardkit-only, doc-less runtime lessons** | **~7-10%** (~10-15 nodes) | **UNIQUE-AT-RISK** — only in FalkorDB; no doc, rule file, or task file |

### Bottom line

Of guardkit's raw graph source, roughly **90% is already covered** — either in `fleet-memory` (harvested docs/ADRs), on disk (rule files, task files, the 2 unharvested but git-versioned docs), or trivially regenerable (synthetic seeds). The **genuinely unique, non-recoverable content is a small tail — on the order of 10-15 distilled runtime-decision nodes** (~7-10% of distinct items), all in `guardkit__project_decisions`, that were captured directly into the graph with no doc/rule/task anchor (e.g. `cwd is a selector-layer concern`, `autobuild silent-gitignore`, `Coach soft-fail`, the R2 BDD-oracle defect note). A further ~27 unique-but-*cross-project* decision nodes are at risk for their true owner projects, not guardkit — an artifact of `fleet_memory_mapping.py` hardcoding `project="guardkit"` for all 29 groups (guardkit/knowledge/fleet_memory_mapping.py). **The teardown's actual data-preservation task is to migrate ~10-40 `project_decisions` Decision nodes, not 4,154 nodes.** A note-of-caution: this measures *content* overlap; it does not equalize the retrieval-character gap (graph `search()` returns Qwen2.5-distilled relationship facts; fleet-memory returns raw chunks) — that is a separate retrieval-quality question, not a corpus-coverage one.