# HANDOFF — FEAT-MEM-09 (decommission Graphiti / drop Qwen2.5) — 2026-07-01

Pick-up doc for a **fresh conversation**. Assumes no prior context. FEAT-MEM-08 (the
guardkit→fleet-memory cutover) is **DONE, verified live, merged, and pushed**; FEAT-MEM-09
is the decommission that FEAT-MEM-08 unblocked.

> ⚠️ **FEAT-MEM-09 is large and NOT a simple delete.** ~9,500 LOC of Graphiti Python + 20
> files under `guardkit/integrations/graphiti/` + **~19 consumer modules** (many still call
> Graphiti directly) + **397 docs** + 2 rules + 13 CLAUDE.md mentions + a graphiti-core git
> dependency (3 extras). It needs **per-consumer scoping decisions** (repoint vs remove vs
> accept-loss) before any code is deleted. Do NOT hand this to autobuild unscoped — see
> "Why not just autobuild it" below.

---

## 0. TL;DR — what to do first

1. **Confirm FEAT-MEM-08 is stable** (§2). Removing Graphiti removes the rollback path, so
   verify the fleet-memory write+read path is solid over a real observation window first.
2. **Decide the disposition of every Graphiti consumer** (§5 table). This is the real work
   and the real risk — most consumers were NEVER cut over in FEAT-MEM-08.
3. Only then remove code/deps/config/docs (§6) and decommission the infra (Qwen2.5 §7,
   FalkorDB §8).

---

## 1. Context — what FEAT-MEM-08 delivered (so you know the starting line)

FEAT-MEM-08 cut guardkit's **knowledge capture** from Graphiti/FalkorDB to the
**fleet-memory** pure-embeddings backend (NATS → relay → Postgres+pgvector). Completed
2026-06-30/07-01, merged to `main` and pushed. Key commits (guardkit `main`):

- `cd36b708` — real fleet-memory **write path** (`fleet_memory_payloads.build_memory_episode`
  + `FleetMemoryClient.add_episode` publishes typed `MemoryEpisodeV1` via NATS), the
  **`adrs`→`adr` mapping fix**, and the **backend-selection wiring**
  (`get_memory_client()` lazily inits from `GUARDKIT_MEMORY_BACKEND` → `.guardkit/graphiti.yaml`
  `backend:` → `"graphiti"`).
- `422d8b1e` — real fleet-memory **reads** (`FleetMemoryClient.search` reuses
  `fleet_memory.retrieval`).
- `5cca36f8` — **requires-python `>=3.11`→`>=3.12`** (the `memory` extra needs fleet-memory
  which is 3.12+). CI matrix now `['3.12']`.
- `ca3f817` (**fleet-memory repo**) — retrieval `domain_tags` filter reads tags from the
  embedded `content` JSON (GROI reads of typed records were returning 0).
- `fdc55af3` — FEAT-MEM-08 status reconciliation (feature+tasks marked completed, archived).

**What actually got cut over (IMPORTANT — it is NOT everything):**

| Path | Cut over? | How |
|---|---|---|
| Task-outcome **writes** (`outcome_manager.capture_task_outcome`) | ✅ | via `get_memory_client()` factory → `FleetMemoryClient` → `build_outcome` |
| ADR **writes** (`adr_service.create_adr`, group `adrs`) | ✅ | via the factory → `adr` payload |
| GROI **reads** (`feature_plan_context`, `coach_context_builder`) | ✅ | `get_memory_client().search()` → `fleet_memory.retrieval` |
| Everything else (see §5) | ❌ **still on Graphiti** | direct `get_graphiti()` |

Proven live: soak 5/5 published==stored, `memory.dlq`=0; GROI reads return typed records;
`guardkit memory status`→REACHABLE, `guardkit memory search`→hits. Full audit:
`docs/design/specs/memory-cutover/TASK-MEM08-005-dual-write-soak-audit.md`.

---

## 2. PRECONDITION — confirm FEAT-MEM-08 stability BEFORE removing the rollback

Graphiti is currently the **rollback** for the cutover (`backend: graphiti` + re-add the
graphiti MCP server). FEAT-MEM-09 **deletes that rollback**. So first:

- [ ] Run real guardkit operations for an observation window (`guardkit task-complete` on a
      few real tasks; `guardkit feature-plan`; a real autobuild) and confirm outcomes/ADRs
      land in fleet-memory (`public.store`) and GROI reads fire.
- [ ] `memory.dlq` stays empty (`docker exec -i fleet-memory-relay python -c` JetStream
      check — see §9), relay healthy.
- [ ] `guardkit memory status` REACHABLE; `guardkit memory search "<q>"` returns hits.
- [ ] Decide: is a fleet-memory backup/export wanted before burning the Graphiti bridge?

Only proceed once you're confident you won't need to roll back to Graphiti.

---

## 3. Scope of FEAT-MEM-09

1. **Repoint or remove every remaining Graphiti consumer** (§5) — the bulk of the work.
2. **Simplify the backend factory** to fleet-memory-only: drop the `graphiti`/`dual`
   branches + `DualWriteClient` from `fleet_memory_client.py`
   (`init_memory_client`/`get_memory_client`/`_resolve_backend_from_config`).
3. **Remove Graphiti code** (§4): `graphiti_client.py`, `cli/graphiti.py`,
   `cli/graphiti_query_commands.py`, `planning/graphiti_*.py`,
   `guardkit/integrations/graphiti/**`, seed scripts, `outcome_queries`, `interactive_capture`,
   `turn_state_operations` (or repoint — decide in §5).
4. **Drop the graphiti-core dependency** + `falkordb` + `gemini` extras (pyproject §4 refs).
5. **Drop Qwen2.5** (§7) — Graphiti was its only consumer (entity extraction); fleet-memory is
   pure-embeddings (no LLM).
6. **Decommission FalkorDB** (§8) on the NAS.
7. **Clean config**: `.guardkit/graphiti.yaml` (rename/retire; the file still carries
   `llm_model: qwen-graphiti`, FalkorDB host, group_ids), the `backend:` flag (becomes moot),
   and any residual graphiti env vars. (`.mcp.json` already has ONLY the `fleet_memory`
   server — the graphiti server was removed in 009.)
8. **Clean docs/rules**: `.claude/rules/graphiti-knowledge.md` + `graphiti-knowledge-graph.md`,
   the 13 CLAUDE.md mentions, and ~397 docs referencing graphiti (most are historical/task
   records — decide which to update vs leave as history).

---

## 4. Graphiti footprint inventory (concrete, as of 2026-07-01)

**Python (~9,524 LOC):**
```
guardkit/knowledge/graphiti_client.py            2617   # the core client (get_graphiti)
guardkit/cli/graphiti.py                         2482   # `guardkit graphiti` CLI (deprecated)
guardkit/cli/graphiti_query_commands.py           324
guardkit/planning/graphiti_design.py              341
guardkit/planning/graphiti_arch.py                 (arch knowledge)
guardkit/integrations/graphiti/**                 ~3100  (20 files: parsers, episodes, project.py…)
```
Plus `knowledge/{seeding,project_seeding,seed_*,interactive_capture,outcome_queries,
turn_state_operations,failed_approach_manager}.py`, `planning/{system_plan,mode_detector,
impact_analysis}.py`, `cli/{system_context,init}.py` — all touch Graphiti.

**Dependency (pyproject.toml):**
- L41 base dep: `graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1`
- L62 `falkordb` extra, L67 `gemini` extra, L107-108 `all` extra include graphiti-core variants
- L152 `[tool.uv]` allows the git+ URL for the fork pin

**Config:**
- `.guardkit/graphiti.yaml`: `enabled: false`, `backend: fleet_memory`,
  `llm_provider: vllm`, `llm_model: qwen-graphiti`, `embedding_model: nomic-embed`,
  FalkorDB host `whitestocks:6379`, group_ids list. (This file is now mostly vestigial —
  fleet-memory reads its own `.env`; only `backend:` is still consulted, by
  `_resolve_backend_from_config`.)
- `.mcp.json`: only `fleet_memory` (graphiti server already gone).

**Docs/rules:** `.claude/rules/graphiti-knowledge.md`, `graphiti-knowledge-graph.md`;
13 mentions in `CLAUDE.md`; ~397 files under `docs/` mention graphiti (mostly history).

**Tests that will go / break:** `tests/unit/knowledge/test_upsert_episode.py`,
`test_seed_feature_spec.py` (import `guardkit.integrations.graphiti` → need `frontmatter`),
plus graphiti-client/CLI/parser tests. Expect a meaningful test-suite delta.

---

## 5. The real work — consumer disposition (DECIDE EACH before deleting)

Every module below currently calls `get_graphiti()` (Graphiti directly) and was **NOT** cut
over in FEAT-MEM-08. For each, decide: **(R)epoint** to fleet-memory via
`get_memory_client()`, **(X) remove** the feature, or **(A)ccept loss** (drop the knowledge
capability). This table is the heart of FEAT-MEM-09 — fill in the decision column.

| Consumer | What it does with Graphiti | Suggested disposition |
|---|---|---|
| `knowledge/failed_approach_manager.py` | writes `failed_approaches` (warning payloads) | **R** — mapping already exists (`failure_patterns`/`failed_approaches`→`warning`); route through `get_memory_client()` like outcome_manager. The write path already handles `warning`. |
| `knowledge/turn_state_operations.py` | writes `turn_states` | R or A — `turn_states`→`document` mapping exists; low value? decide |
| `knowledge/seeding.py`, `project_seeding.py`, `seed_*.py` | seed system/project knowledge into groups | X or R — most `seed_module` groups are marked `retire` in the mapping (covered by the FEAT-HARV harvest corpus). Likely **remove**. |
| `knowledge/interactive_capture.py` | `guardkit graphiti capture --interactive` | R (→ `guardkit memory capture`?) or X |
| `knowledge/outcome_queries.py` | reads outcomes | R — fleet-memory search |
| `planning/graphiti_arch.py`, `graphiti_design.py` | architecture/design knowledge (system-design, arch-refine) | R or X — decide if these features stay |
| `planning/impact_analysis.py`, `mode_detector.py`, `system_plan.py` | `/impact-analysis`, `/system-plan` read graphiti | R or A |
| `cli/system_context.py` (`/system-overview`, `/impact-analysis`) | reads graphiti | R or A |
| `cli/graphiti.py`, `cli/graphiti_query_commands.py` | the whole `guardkit graphiti` CLI (deprecated) | **X** — remove; `guardkit memory` supersedes it |
| `orchestrator/autobuild.py`, `feature_orchestrator.py`, `coach_validator.py` | graphiti seeding/queries in the autobuild loop | R or X — trace exactly what they use |
| `knowledge/adr_service.py`, `outcome_manager.py` | ALREADY route via factory (cut over) | leave (just drop the graphiti fallback branch) |

**Note:** `feature_plan_context.py` + `coach_context_builder.py` reads are already on
fleet-memory (via `get_memory_client()`); they only need the residual graphiti code removed.

---

## 6. Suggested wave/task breakdown

- **W0 — stability gate + backup** (§2): confirm FEAT-MEM-08 solid; optional fleet-memory export.
- **W1 — repoint the "keep" consumers** (failed_approaches→warning is the obvious one; others
  per §5 decisions) through `get_memory_client()`; verify each lands + reads via the soak
  pattern (§9). Add write-shape tests that assert `nats_core.publish_episode` is called
  (mirror the `test_fleet_memory_client.py` publish tests — DO NOT mock away the publish, or
  you recreate the FEAT-MEM-08 false-green).
- **W2 — simplify the factory**: drop `graphiti`/`dual` branches + `DualWriteClient`;
  `get_memory_client()` returns fleet-memory unconditionally; delete `_resolve_backend_from_config`
  graphiti/dual handling (keep the env override for test seams if useful).
- **W3 — delete Graphiti code + deps**: remove the modules (§4), the graphiti-core dep + extras,
  the graphiti tests; run the full suite; fix fallout.
- **W4 — config/docs**: retire `.guardkit/graphiti.yaml` (or slim to a fleet-memory config),
  rewrite the 2 rules + CLAUDE.md "Knowledge Capture" section; decide docs policy (update
  active guides, leave historical task records).
- **W5 — infra**: drop Qwen2.5 from llama-swap (§7); decommission FalkorDB (§8).
- **W6 — verify + sign off**: `guardkit memory` still works; `grep -rn "graphiti" guardkit/`
  is empty (or only intentional history); tests green; FalkorDB gone; CI green on 3.12.

---

## 7. Drop Qwen2.5 (the LLM served ONLY Graphiti extraction)

Graphiti used an LLM for entity/edge extraction; **fleet-memory is pure-embeddings (no LLM)**.
So once Graphiti is gone, the `qwen-graphiti` model (Qwen2.5-14B-Instruct on the DGX-Spark
llama-swap front door at `promaxgb10-41b1:9000`) has no guardkit consumer.

- `.guardkit/graphiti.yaml` `llm_model: qwen-graphiti` / `llm_provider: vllm` become dead.
- The **embedder** (`embed` = Qwen3-Embedding-0.6B @ 1024, also on `:9000`) is STILL NEEDED —
  fleet-memory embeds on write/read. Do NOT drop the embedder; only the Qwen2.5 **LLM**.
- The llama-swap configs live in the sibling **`../dgx-spark`** repo (see memory
  `dgx-spark-repo-and-config-split`): public (open) vs personal (coach-ft-v3). Per memory
  `graphiti-cutover-qwen25-removal`, the **public spark runbooks are already Qwen2.5-free**;
  the personal/reference `:9000` config may still serve `qwen-graphiti` — remove that model
  entry there. Coordinate with any OTHER Qwen2.5 consumers before pulling it globally.

---

## 8. Decommission FalkorDB

- FalkorDB ran on the Synology NAS (`whitestocks`) via docker-compose
  (`/volume1/guardkit/docker/docker-compose.falkordb.yml`, port 6379).
- **Reachability note (2026-07-01):** from the build host, `whitestocks:6379` is currently
  **unreachable** (the same host's Postgres on `:5433` works fine). The operator restarted
  FalkorDB after a power cut, so it may be up but not reachable from here (port/binding/
  firewall) — verify actual state on the NAS before assuming it's down.
- Decommission = stop + remove the FalkorDB container on the NAS, free the volume, remove the
  compose file / any Tailscale ACL for 6379. Do this LAST (after code no longer references it),
  and only once you're sure no rollback to Graphiti is wanted.

---

## 9. Environment & run facts (carried from FEAT-MEM-08 — a fresh session needs these)

**Repos (siblings under `~/Projects/appmilla_github/`):** `guardkit` (this),
`fleet-memory` (the relay + retrieval + payloads; py3.12 venv at `../fleet-memory/.venv` has
everything), `nats-core` (the write contract), `nats-infrastructure` (NATS broker + the
`guardkit` NATS user password in `../nats-infrastructure/.env`).

**Run guardkit with the memory extra** (after the requires-python 3.12 bump, this resolves):
```bash
cd ~/Projects/appmilla_github/guardkit
uv sync --extra all --python 3.12          # full dev env incl. fleet_memory + nats_core editable
set -a; . ./.env; set +a                    # FLEET_MEMORY_PG_DSN, EMBED_*, NATS_URL (gitignored)
export FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory
.venv/bin/python -m guardkit.cli.main memory status     # -> REACHABLE
.venv/bin/python -m guardkit.cli.main memory search "<q>"
```
For NATS **writes** (soak/repoint verification) also:
```bash
export GUARDKIT_NATS_PASSWORD=$(grep ^GUARDKIT_NATS_PASSWORD= ../nats-infrastructure/.env | cut -d= -f2-)
```
**Live store audit** (a write landed?):
```bash
psql "$FLEET_MEMORY_PG_DSN" -tAc \
 "select prefix,count(*) from public.store group by 1 order by 2 desc;"
# prefix = fleet_memory.<project>.<payload_type>; key = uuid5(NS 6ba7b810-…, '<type>:<project>:<id>')
# value->>'natural_key', value->>'payload_type', value->>'content' (embedded JSON, incl domain_tags)
```
**DLQ empty check:**
```bash
docker exec -i fleet-memory-relay python - <<'PY'
import asyncio,os,nats
async def m():
    nc=await nats.connect(os.environ["FLEET_MEMORY_NATS_URL"]); js=nc.jetstream()
    si=await js.stream_info("MEMORY",subjects_filter="memory.dlq.>")
    print("DLQ:", sum((si.state.subjects or {}).values())); await nc.close()
asyncio.run(m())
PY
```
**Relay:** container `fleet-memory-relay` (docker-compose `../fleet-memory/deploy/relay/`,
`.env.deploy` holds ack_wait=1200/max_deliver=5/embed). Rebuild (if you touch payload models):
`docker compose -f ../fleet-memory/deploy/relay/docker-compose.yml up -d --build`. The corpus
is EXTERNAL (NAS Postgres `whitestocks.tailebf801.ts.net:5433/fleet_memory`) — container
rebuilds don't touch it. Current corpus ~685 rows (679 harvest chunks + FEAT-MEM-08 soak records).

**Test runner:** the full `.venv` (after `uv sync --extra all`) has pytest + fleet_memory +
nats_core + frontmatter. Run `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider ...`
(pytest.ini adds `--cov` flags that need pytest-cov). Memory-extra tests skip-guard on
`nats_core`/`fleet_memory` for minimal CI envs.

---

## 10. Hazards & gotchas

- **Removing Graphiti removes the rollback.** Gate on §2.
- **DON'T recreate the FEAT-MEM-08 false-green.** The 08 autobuild shipped THREE stubs that
  passed the per-task Coach because their tests mocked the client
  (`per-task-green-is-not-feature-green`). When you repoint a consumer, add a test that
  asserts the REAL publish (`nats_core.publish_episode` called with the right typed episode),
  and verify against the LIVE store, not mocks.
- **The embedder stays; only the Qwen2.5 LLM goes.** fleet-memory embeds on read/write via
  `embed`/1024 on `:9000`. Dropping the embedder breaks reads.
- **graphiti-core is a git+ pinned dep** (`v0.29.5-guardkit.1`, a guardkit fork). Removing it
  also lets you drop the `[tool.uv]` git-URL allowance (L152) and the falkordb/gemini extras.
- **requires-python is now `>=3.12`** (5cca36f8); CI matrix `['3.12']`. Keep it.
- **Two graphiti tests already fail to collect** without `frontmatter`
  (test_upsert_episode, test_seed_feature_spec) — they'll be deleted with the graphiti code.
- **Docs volume:** ~397 docs mention graphiti; most are historical task/review records. Update
  the *active* guides + rules + CLAUDE.md "Knowledge Capture" section; leave history as history
  (don't rewrite completed task records).
- **`.guardkit/graphiti.yaml` is mostly vestigial now** but `_resolve_backend_from_config`
  still reads its `backend:` key. When you make fleet-memory unconditional, remove that read
  (or repoint it to a new `.guardkit/memory.yaml`).

### Why not just autobuild it
This is a decommission with cross-cutting deletions + per-consumer product decisions (§5) +
infra teardown (§7-8) + a lost rollback. Autobuild is good at additive, well-specified tasks;
it produced false-greens on the 08 cutover. Make the §5 disposition decisions with a human,
scope tasks tightly (one consumer or one concern each), and verify against the live system.
A `/feature-plan` pass is fine to STRUCTURE it, but review the plan hard before building.

---

## 11. Key artifacts & pointers

- **FEAT-MEM-08 audit / evidence:** `docs/design/specs/memory-cutover/TASK-MEM08-005-dual-write-soak-audit.md`,
  `TASK-MEM08-007-read-path-evidence.md`, `HANDOFF-FEAT-MEM-08-2026-06-29.md`.
- **The cutover code:** `guardkit/knowledge/{fleet_memory_client,fleet_memory_payloads,fleet_memory_mapping}.py`,
  `guardkit/memory/{harvest_walker,harvest_publisher}.py`, `guardkit/cli/memory.py`.
- **The mapping** (group_id → project/payload_type/domain_tags/disposition; `retire` marks the
  groups the harvest corpus already covers): `guardkit/knowledge/fleet_memory_mapping.py`.
- **fleet-memory repo:** payloads `src/fleet_memory/payloads/`, retrieval `src/fleet_memory/retrieval/`,
  relay `src/fleet_memory/{app.py,relay/}`, writer `src/fleet_memory/writer/`.
- **Rules to read first:** `.claude/rules/per-task-green-is-not-feature-green.md`,
  `absence-of-failure-is-not-success.md`, `stack-plugin-architecture.md`.
- **Memory notes (in the agent memory dir):** `feat-mem-08-reads-stubbed` (now "cutover COMPLETE"),
  `graphiti-cutover-qwen25-removal`, `dgx-spark-repo-and-config-split`, `qwen-embed-switch-1024`,
  `autobuild-cannot-edit-mcp-json`, `nas-backup-whitestocks-access`.
- **FEAT-MEM-09 is NOT yet filed** as a feature. First step after §2/§5 decisions: file it
  (`/feature-plan` or by hand) with the wave breakdown in §6.

---

## 12. Acceptance for FEAT-MEM-09 (proposed)

- [ ] `grep -rn "graphiti\|get_graphiti\|graphiti_core" guardkit/` returns only intentional
      history/comments (no live imports/consumers).
- [ ] `graphiti-core` (+ falkordb/gemini extras) removed from `pyproject.toml`; `uv.lock`
      re-resolved; `uv sync --extra all` green.
- [ ] Every "keep" consumer (§5) writes/reads via fleet-memory, verified against the live
      store (not mocks); DLQ empty.
- [ ] Full test suite green on 3.12 (graphiti tests removed, not skipped-and-forgotten).
- [ ] `guardkit memory status/search` still work; `guardkit graphiti` CLI removed.
- [ ] Qwen2.5 LLM removed from the personal llama-swap config; embedder untouched.
- [ ] FalkorDB container decommissioned on the NAS; no rollback path remains (documented).
- [ ] Docs/rules/CLAUDE.md "Knowledge Capture" updated to fleet-memory-only; historical
      records left intact.
