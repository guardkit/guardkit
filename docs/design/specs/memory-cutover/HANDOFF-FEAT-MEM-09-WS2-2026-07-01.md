# HANDOFF — FEAT-MEM-09 (decommission Graphiti / drop Qwen2.5), WS-0→WS-2 done — 2026-07-01

Pick-up doc for a **fresh conversation**. Assumes no prior context. Supersedes the initial
`HANDOFF-FEAT-MEM-09-2026-07-01.md` (which framed the work before it started). **This handoff
reflects real, committed, live-verified progress: WS-0, WS-1, and most of WS-2 are DONE.**

> **The big reframe from this session (READ THIS FIRST):** FalkorDB is **NOT** a guardkit-local
> rollback store — it is a **FLEET-WIDE knowledge store: ~11,847 nodes / 92 graphs / ~18 projects**
> (guardkit + jarvis + forge + study-tutor + lpa-platform + agentic_dataset_factory + architect_agent
> + nats-core + guardkitfactory + fleet-gateway + …). So the original handoff's §8 "decommission
> FalkorDB" is a **fleet-wide data-destruction event**, not a cleanup — it is the LAST, one-way step,
> gated on migrating every consumer + a verified backup. Everything done so far is **purely additive**
> to fleet-memory; **FalkorDB is 100% intact and untouched.**

---

## 0. TL;DR — where we are, what to do next

**Done & live-verified this session (all pushed):**
- **WS-0** per-project scoping (fleet-memory already scopes by project at the SQL level; guardkit just
  un-hardcoded `"guardkit"`).
- **WS-1** the `graph_export` migration pipeline (`guardkit memory migrate-graph`) + fleet-memory
  `DocumentPayload.content` (so migrated prose is embedded AND group-scoped). Relay rebuilt.
- **WS-2 (partial):** guardkit's **499 documents migrated live** (store now 1,184 rows, DLQ=0);
  scoped reads return real project knowledge (**letterbox closed**); the `.search()`-only read
  consumers repointed to fleet-memory.

**Next action (in priority order — see §5 for detail):**
1. **Extend `FleetMemoryClient`** with the graphiti-specific methods the autobuild job-context chain
   uses (`reset_circuit_breaker`, …), then repoint that chain
   (`autobuild.py → autobuild_context_loader → job_context_retriever`). **NOT a drop-in.**
2. **Modernize the 16 pre-existing stale FEAT-MEM-08 test failures** (they test the removed graphiti
   *write* path — red on `main` before this session; see §6).
3. **WS-2b** (optional, decided): one-time offline cloud-LLM **distillation** of the ~274 high-value
   nodes; **promote** the ~10–15 unique-at-risk decisions to git-versioned disk.
4. **WS-2c:** remove residual guardkit graphiti code + `graphiti-core` dep (per the disposition map).
5. **Fleet-wide (WS-3+):** `migrate-graph --all-projects` for the other 17 projects' DATA, then
   migrate each consumer repo, inventory remote graphs, back up, and only then ⛔ tear down FalkorDB.

---

## 1. Exact current state (2026-07-01, all pushed, `sync 0/0`)

**guardkit `main` (newest first):**
```
46dde641 feat(FEAT-MEM-09): repoint read consumers to fleet-memory (WS-2)
b8337da2 chore(FEAT-MEM-09): WS-2 guardkit live migration done (499 docs, letterbox closed)
68507414 feat(FEAT-MEM-09): scoped reads include migrated documents (WS-2 read-side)
0673ed11 chore(FEAT-MEM-09): mark WS-1 code-complete (graph_export + DocumentPayload.content)
a027fec0 feat(FEAT-MEM-09): graph_export pipeline — FalkorDB Episodic → fleet-memory (WS-1b)
ec1abe10 chore(FEAT-MEM-09): mark WS-0 code-complete (fleet-memory guard landed)
0de43a86 feat(FEAT-MEM-09): file fleet-wide decommission program + WS-0 per-project scoping
```

**fleet-memory `main` (newest first):**
```
68218dd feat(payloads): DocumentPayload carries optional prose content (FEAT-MEM-09 WS-1a)
7945d9d feat(retrieval): exact-project scope guard against namespace-prefix bleed (WS-0)
ca3f817 fix(retrieval): domain_tags filter reads tags nested in content JSON (TASK-MEM08-012)
```

**Live store** (`public.store`, Postgres on `whitestocks.tailebf801.ts.net:5433/fleet_memory`):
`(chunk) 679 | document 499 | build_outcome 5 | adr 1` → **total 1184**, DLQ=0.

**Relay:** container `fleet-memory-relay` running on **image `sha256:3d55f780…`** (rebuilt this
session with `DocumentPayload.content`; rollback image `4fe44bfb`).

**Program tracking:** `.guardkit/features/FEAT-MEM-09.yaml` — MEM09-001 (WS-0) + MEM09-002 (WS-1)
`in_review`; MEM09-003 (WS-2) `in_progress`; MEM09-004..008 `backlog`.

---

## 2. Locked operator decisions (do not re-litigate)

1. **Scope:** FULL fleet migration + FalkorDB teardown (not guardkit-local).
2. **Fact fidelity = hybrid:** migrate prose as chunk/document (LLM-free) everywhere, PLUS a **one-time,
   offline cloud-LLM distillation** of the ~274 high-value nodes (`project_decisions` 147 +
   `task_outcomes` 127). The distillation runs ONCE at migration and is discarded → **no runtime LLM**,
   so it does not violate "drop Qwen2.5".
3. **Per-project retrieval = option 2:** preserve group-scoped retrieval; migrated prose carries
   `domain_tags` (this is why `DocumentPayload.content` was added).
4. **Unique nodes:** promote the ~10–15 genuinely-unique, doc-less guardkit decisions to git-versioned
   `.claude/rules/` / `docs/decisions/` + distill; re-capture the ~27 cross-project ones under their
   true project.
5. **Teardown safety:** raw FalkorDB dump (Episodic AND the 5,735 extracted facts) to durable storage
   + **keep FalkorDB dormant N months** before the physical, one-way teardown.

---

## 3. What is DONE (with the "why", so you don't undo it)

### WS-0 — per-project + per-group scoping (guardkit `0de43a86`/`ec1abe10`, fleet-memory `7945d9d`)
- **Finding:** fleet-memory ALREADY scopes by project end-to-end at the SQL level (store prefix
  `fleet_memory.{project}.{payload_type}`, project baked into `natural_key`/`uuid5`, retrieval filters
  `store.prefix LIKE 'fleet_memory.{project}%'`). The only gap was guardkit hardcoding `"guardkit"`.
- **guardkit:** `FleetMemoryConfig.project` (default `"guardkit"`, sourced from `GUARDKIT_MEMORY_PROJECT`),
  threaded through `fleet_memory_payloads.build_memory_episode` (+ `_build_prose_episode`), and
  un-hardcoded in `FleetMemoryClient.search` / `health_check` / `add_episode`. Non-breaking.
- **fleet-memory:** exact-project post-filter (`retrieval/core.py::_matches_project`) so `project="guardkit"`
  can't `LIKE`-prefix-match a sibling like `guardkit_factory`. Tests: `test_fleet_memory_project_scoping.py`
  (guardkit), `test_search_core.py` (fleet-memory).

### WS-1 — graph_export + DocumentPayload.content (fleet-memory `68218dd`, guardkit `a027fec0`/`0673ed11`)
- **Critical finding:** fleet-memory retrieval EXCLUDES plain prose chunks from **group-scoped** reads
  (a record needs `payload_type` in its natural_key AND `domain_tags`). The typed `document` payload had
  **no prose field**, so it embedded metadata only. So "migrate as documents" (the original plan) was
  impossible as-is.
- **WS-1a (fleet-memory):** added optional `content: str | None = None` to `DocumentPayload`
  (`payloads/models.py`), mirroring `BuildOutcomePayload.lessons`. Now a document record embeds its prose
  AND carries `domain_tags` → both semantically searchable and group-scoped. **Round-trip verified**:
  the deterministic writer's embedded `content_json` contains prose + tags. **RELAY REBUILD REQUIRED**
  (`BasePayload` is `extra="ignore"`, so an old relay SILENTLY DROPS `content` — no DLQ). ← relay was
  rebuilt this session.
- **WS-1b (guardkit):** `guardkit/memory/graph_export.py` + `guardkit memory migrate-graph` CLI. Reads
  each project graph's raw `Episodic` nodes from FalkorDB → typed `DocumentPayload` episodes (prose in
  `content` + the source group's `domain_tags`). Uniform `payload_type="document"`; group identity in
  `domain_tags` (mapped groups → `fleet_memory_mapping` tags; **unmapped** groups like
  `project_knowledge`/`successful_fixes`/`rules_*` → `[sanitised_group_name]` fail-open, never dropped;
  **retire** groups → skipped). Reuses `harvest_publisher.publish_episodes` + `sanitize_identifier`;
  idempotent (`episode_id = natural_key`). The Qwen2.5-extracted Entity/edge layer is **NOT** migrated
  (pure-embeddings). Self-contained — does NOT touch `build_memory_episode`. Tests: `test_graph_export.py`.

### WS-2 (partial) — read-side + live migration + consumer repoint
- **Read-side (guardkit `68507414`):** `FleetMemoryClient.search` now adds `"document"` to the resolved
  `payload_types` for every migrate `group_id`, so a group-scoped read matches BOTH the live typed records
  (build_outcome/adr/warning) AND the migrated documents; `domain_tags` do the precise scoping.
- **Live migration (guardkit `b8337da2`):** `migrate-graph --project guardkit` published **499 documents**;
  relay drained 301→499, DLQ=0. **Scoped reads verified live** returning real project knowledge
  (`project_decisions`→"TASK-FIX-COACHSF01 coach soft-fail decision"; `project_architecture` 0.85;
  `project_overview`→"GuardKit Mission…"; `patterns` 0.98). **Letterbox closed.**
- **Consumer repoint (guardkit `46dde641`):** the `.search()`-only read consumers repointed
  `get_graphiti()` → `get_memory_client()`: `outcome_queries`, `gap_analyzer`, `context_loader`
  (functional); `task_analyzer`, `job_context_retriever` (docstring-only — they take an INJECTED client).
  `feature_plan_context` + `coach_context_builder` were ALREADY on fleet-memory (so `/feature-plan` and
  the autobuild Coach already benefit). Return-shape parity confirmed: both give `[{fact,uuid,score}]`.
  316 affected tests pass; **zero net new failures** (proven by stash-diff against clean HEAD).

---

## 4. Verified facts you can rely on

- **fleet-memory is pure-embeddings — NO LLM at read or write time.** Qwen2.5 was only Graphiti's
  write-time entity extractor. So migrating knowledge to fleet-memory RESTORES retrieval **without**
  Qwen2.5. (The letterbox regression actually happened at FEAT-MEM-08 when `.guardkit/graphiti.yaml`
  set `enabled: false` — guardkit's graphiti reads have been dark since; the migration un-darks them.)
- **Consumers never traverse the graph.** They call `client.search(query, group_ids)`; parity holds.
- **Only 5 fleet consumer repos have real code coupling** (forge/study-tutor/specialist-agent/jarvis/
  fleet-gateway). `nats-core` (the fleet-memory PRODUCER), `guardkitfactory`, `lpa-platform-poc` have
  ZERO code coupling — their graph nodes were written by guardkit's own autobuild. Full inventory:
  `docs/design/specs/memory-cutover/FEAT-MEM-09-fleet-migration-investigation.md` §3 / Appendix C.
- **Data-at-risk is tiny.** guardkit's "4,154 nodes" are ~90% Qwen2.5-extracted or already-covered;
  the raw source is ~499 Episodic (all now migrated); the genuinely-unique doc-less decisions are ~10–15.

---

## 5. NEXT WORK — detailed

### 5.1 (priority) Repoint the autobuild job-context chain — **NOT a drop-in**
`job_context_retriever` calls graphiti-specific methods (`self.graphiti.reset_circuit_breaker()`, and
likely circuit-breaker state). The chain is `orchestrator/autobuild.py` (acquires + injects) →
`knowledge/autobuild_context_loader.py` (`JobContextRetriever(self.graphiti)`) →
`knowledge/job_context_retriever.py`. To repoint:
- **Option A (recommended):** add the graphiti-compat methods to `FleetMemoryClient` as safe no-ops /
  shims (`reset_circuit_breaker`, any `circuit_breaker` accessor `job_context` touches — grep it).
- **Option B:** guard the graphiti-specific calls in `job_context_retriever` (`hasattr`/try).
- Then change `autobuild.py`'s `get_graphiti()` injection → `get_memory_client()`, and update the
  autobuild-context tests (they patch `guardkit.orchestrator.autobuild.get_graphiti` and
  `guardkit.knowledge.get_graphiti` — see `tests/unit/test_autobuild_context_integration.py`).
- Grep the exact surface first: `rg -n "self\.graphiti\.[a-z_]+\(" guardkit/knowledge/job_context_retriever.py`.

### 5.2 Modernize the 16 pre-existing stale FEAT-MEM-08 test failures (see §6)
These are red on clean `main` (NOT from this session). They test the removed graphiti WRITE path.
Update them to the fleet-memory write path or remove them:
- `tests/knowledge/test_outcome_manager.py::TestCaptureTaskOutcome` + `::TestEdgeCases` (13) — patch
  `guardkit.knowledge.outcome_manager.get_graphiti`, which no longer exists (cut over in FEAT-MEM-08).
- `tests/knowledge/test_call_site_migration.py` — 3 assertions that `outcome_manager` /
  `feature_plan_context` import `get_graphiti` (both migrated). (I already fixed the `context_loader`
  one in `46dde641`.)

### 5.3 WS-2b — distillation + unique-node promotion (decision #2, #4)
- One-time offline cloud-LLM pass over `project_decisions` (147) + `task_outcomes` (127) → concise
  summaries stored as content-bearing typed payloads (ADR/build_outcome have real content fields, so
  they're scoped-retrievable). Runs ONCE; no runtime LLM.
- Build-time **exact diff** of the ~10–15 unique-at-risk nodes (cheap; firms the estimate) and
  **promote** the valuable guardkit ones into `.claude/rules/` / `docs/decisions/` (git-versioned →
  permanently re-harvestable). Re-capture the ~27 cross-project ones under their true project scope.

### 5.4 WS-2c — remove residual guardkit graphiti code + deps
Per the disposition map (`FEAT-MEM-09-consumer-disposition-map.md` §2a + §4 safe deletion order):
simplify the factory (drop `graphiti`/`dual`/`DualWriteClient` + `_resolve_backend_from_config`), then
delete `graphiti_client.py`, `integrations/graphiti/**`, the `guardkit graphiti` CLI, seeders,
`config.py`, `_group_defs.py`, `falkordb_workaround.py`; drop `graphiti-core` + `falkordb`/`gemini`
extras + the `[tool.uv]` git-URL allowance. **Order:** consumers first (5.1) → factory simplify →
delete. `config.py::get_config_path` is the LAST reader of `.guardkit/graphiti.yaml`'s `backend:` flag.

### 5.5 Fleet-wide (WS-3 → WS-6)
- **WS-3:** `migrate-graph --all-projects` migrates the other 17 projects' DATA into fleet-memory (the
  pipeline already supports it — `--all-projects` sets `project_filter=None`; per-project scoping lands
  each under its own namespace). THEN migrate each consumer repo (forge/study-tutor/specialist-agent/
  jarvis/fleet-gateway) — cross-repo, `.mcp.json` edits are MANUAL (autobuild can't edit `.mcp.json`).
- **WS-4:** manual inventory of remote graphs with no local code (`agentic_dataset_factory` 340,
  `architect_agent` 246, `study_tutor` underscore-variant, `nats_infrastructure`, `vllm_profiling`).
- **WS-5 (⛔ precursor):** verified fleet-memory Postgres backup + raw FalkorDB dump + per-project
  read-parity sign-off.
- **WS-6 (⛔ ONE-WAY, LAST):** drop `qwen-graphiti` LLM from the personal llama-swap config (KEEP the
  `embed` embedder — fleet-memory needs it), decommission FalkorDB on the NAS. Only after WS-3/4/5 +
  dormant-N-months.

---

## 6. Hazards & gotchas

- **FalkorDB teardown is a fleet-wide one-way door.** Everything so far is additive; FalkorDB is intact.
  Do NOT run any FalkorDB delete/teardown until WS-3/4/5 are complete + a verified dump exists.
- **Relay rebuild is functionally required and SILENT if skipped.** `BasePayload` is `extra="ignore"`,
  so a document-with-content published to an un-rebuilt relay is stored WITHOUT content (no DLQ, no
  error — a false-green). The relay is currently on the correct image (`3d55f780`). If you touch
  fleet-memory payload models again, **rebuild the relay** (see §7) before publishing.
- **16 pre-existing stale FEAT-MEM-08 test failures** exist on clean `main` (see §5.2). When you run the
  knowledge suite, expect 16 reds that are NOT yours — stash-diff before blaming a change. (Separate
  from the memory-note'd `coach_sdk_stream_resilience` + dead-task-id reds.)
- **The autobuild job-context chain is not `.search()`-only** — see §5.1. Don't repoint it blindly.
- **`migrate-graph` is idempotent** (`episode_id = natural_key` → JetStream dedup). Re-running is safe;
  it will not duplicate. But it does NOT delete superseded records — content edits create new versions.
- **Only guardkit is migrated.** The other 17 projects' data is still Graphiti-only until WS-3.
- **Autobuild produced false-greens on the 08 cutover** (`per-task-green-is-not-feature-green.md`). For
  any repoint, assert the REAL client call and verify against the LIVE store, not mocks.

---

## 7. Environment & run facts (a fresh session needs these)

**Repos (siblings under `~/Projects/appmilla_github/`):** `guardkit` (this), `fleet-memory` (payloads/
retrieval/relay; py3.12 venv `../fleet-memory/.venv`), `nats-core` (write contract), `nats-infrastructure`
(NATS broker + the `guardkit` NATS user password in `../nats-infrastructure/.env`). **You are on the
GB10**, where the relay container + NATS broker run.

**guardkit's own `.venv`** (py3.12) has everything (frontmatter + fleet_memory + nats_core). Use
`.venv/bin/python` for guardkit CLI.

**Env for reads:**
```bash
cd ~/Projects/appmilla_github/guardkit
set -a; . ./.env; set +a          # FLEET_MEMORY_PG_DSN, FALKORDB_HOST=whitestocks, FLEET_MEMORY_*
export FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory
.venv/bin/python -m guardkit.cli.main memory status     # -> REACHABLE
.venv/bin/python -m guardkit.cli.main memory search "<q>"
```
**Env for writes/migration** (also):
```bash
export GUARDKIT_NATS_PASSWORD=$(grep ^GUARDKIT_NATS_PASSWORD= ../nats-infrastructure/.env | cut -d= -f2-)
```

**Graph migration (WS-1b CLI):**
```bash
guardkit memory migrate-graph --dry-run --project guardkit          # read+build, no publish
guardkit memory migrate-graph --dry-run --project guardkit --limit 3
guardkit memory migrate-graph --project guardkit                    # LIVE publish (idempotent)
guardkit memory migrate-graph --all-projects                        # fleet-wide (WS-3)
```

**Live store audit / DLQ / scoped-read verification:**
```bash
psql "$FLEET_MEMORY_PG_DSN" -tAc \
 "select coalesce(value->>'payload_type','(chunk)'),count(*) from public.store group by 1 order by 2 desc;"
# DLQ:
docker exec -i fleet-memory-relay python - <<'PY'
import asyncio,os,nats
async def m():
    nc=await nats.connect(os.environ["FLEET_MEMORY_NATS_URL"]); js=nc.jetstream()
    si=await js.stream_info("MEMORY",subjects_filter="memory.dlq.>")
    print("DLQ:", sum((si.state.subjects or {}).values())); await nc.close()
asyncio.run(m())
PY
```

**Relay rebuild** (do this if you change any fleet-memory payload model; the relay is a BAKED image,
retrieval is in-process/editable so needs no rebuild):
```bash
cd ../fleet-memory && docker compose -f deploy/relay/docker-compose.yml up -d --build
# verify: docker exec fleet-memory-relay python -c \
#   "from fleet_memory.payloads.models import DocumentPayload; print('content' in DocumentPayload.model_fields)"
# rollback image if needed: 4fe44bfb (prior baked image)
```

**Query FalkorDB directly** (read-only; the `.venv` has `falkordb`):
```python
from falkordb import FalkorDB
db = FalkorDB(host="whitestocks", port=6379)
db.list_graphs()                                   # ~186 graphs
db.select_graph("guardkit__project_decisions").query("MATCH (n:Episodic) RETURN count(n)")
```

**Test runner:** `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider <paths>`
(pytest.ini adds `--cov` flags that need pytest-cov; `-o addopts=""` skips them). Memory-extra tests
skip-guard on `nats_core`/`fleet_memory`.

---

## 8. Key artifacts & pointers

- **Design + evidence (READ):** `docs/design/specs/memory-cutover/FEAT-MEM-09-fleet-migration-investigation.md`
  (§1 per-project model, §2 migration mechanism + fact-vs-chunk, §3 consumer inventory, §4 corpus overlap,
  §5 program structure, §6 open questions + Appendices A–D with full detail).
- **Consumer disposition map:** `docs/design/specs/memory-cutover/FEAT-MEM-09-consumer-disposition-map.md`
  (verified per-module R/X/A/LEAVE/DELETE + safe deletion order).
- **Program tracking:** `.guardkit/features/FEAT-MEM-09.yaml` + `tasks/backlog/feat-mem-09/TASK-MEM09-00{1,2}-*.md`.
- **The migration code:** `guardkit/memory/graph_export.py` (+ `harvest_publisher.py`,
  `harvest_taxonomy.py`), `guardkit/cli/memory.py` (`migrate-graph` command),
  `guardkit/knowledge/{fleet_memory_client,fleet_memory_payloads,fleet_memory_mapping}.py`.
- **fleet-memory:** `src/fleet_memory/payloads/models.py` (`DocumentPayload.content`),
  `src/fleet_memory/retrieval/core.py` (`_matches_project`, `search`), `deploy/relay/`.
- **Rules to read first:** `.claude/rules/per-task-green-is-not-feature-green.md`,
  `absence-of-failure-is-not-success.md`, `stack-plugin-architecture.md`,
  `namespace-hygiene.md`.
- **Agent memory notes:** `falkordb-fleet-wide-not-guardkit-local` (the FEAT-MEM-09 tracker — has the
  full WS-0→WS-2 progress + commits + the NEXT list), `graphiti-cutover-qwen25-removal`,
  `feat-mem-08-reads-stubbed`, `qwen-embed-switch-1024`, `autobuild-cannot-edit-mcp-json`,
  `dgx-spark-repo-and-config-split`, `nas-backup-whitestocks-access`, `main-has-preexisting-red-tests`.

---

## 9. Acceptance for FEAT-MEM-09 (updated)

- [x] Per-project scoping (WS-0); relay rebuilt; `DocumentPayload.content` (WS-1a); `migrate-graph`
      pipeline (WS-1b).
- [x] guardkit data migrated (499 docs, DLQ=0); scoped reads return migrated content (letterbox closed).
- [x] `.search()`-only read consumers on fleet-memory; `/feature-plan` + Coach already benefit.
- [ ] Autobuild job-context chain repointed (FleetMemoryClient extended).
- [ ] 16 stale FEAT-MEM-08 tests modernized; full suite green on 3.12 (aside from any intentional).
- [ ] WS-2b distillation of ~274 high-value nodes + unique-node promotion to disk.
- [ ] Residual guardkit graphiti code + `graphiti-core` dep removed; `guardkit graphiti` CLI gone;
      `grep -rn graphiti guardkit/` only intentional history.
- [ ] Fleet: other 17 projects' data migrated (`--all-projects`) + all 5 consumer repos migrated +
      remote graphs inventoried.
- [ ] Verified fleet-memory backup + raw FalkorDB dump; FalkorDB kept dormant N months.
- [ ] ⛔ Qwen2.5 LLM dropped from the personal llama-swap config (embedder KEPT); FalkorDB decommissioned.
- [ ] Docs/rules/CLAUDE.md "Knowledge Capture" updated to fleet-memory-only; history left intact.
