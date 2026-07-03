# FEAT-MEM-09 §3.3 — code-layer de-graphiti: current-state scoping (2026-07-03)

> Scopes the "remaining `guardkit/` Python code" chunk (§3.3 of
> [`HANDOFF-FEAT-MEM-09-docs-and-code-degraphiti-2026-07-03.md`](HANDOFF-FEAT-MEM-09-docs-and-code-degraphiti-2026-07-03.md)).
> Reconciles the pre-WS-2c [`FEAT-MEM-09-consumer-disposition-map.md`](FEAT-MEM-09-consumer-disposition-map.md)
> (dated 2026-07-01, **before** the WS-2c deletion) against the **current** tree at
> `HEAD == 7594c19e`. Built from a direct read + import-graph classification of every
> `guardkit/**/*.py` module that still mentions graphiti (6 parallel classifiers, verified
> against the live tree — not inference). Suite is green: **12469 passed / 7 pre-existing fails**.

---

## 0. TL;DR — §3.3 is small, low-risk, and W2/W3/W4 are already done

The handoff called §3.3 the "big, risky" chunk (~20 modules, "must not be mechanically
renamed"). The current-state audit **de-risks it substantially**:

- **Zero modules import a removed graphiti symbol.** Nothing references the deleted
  `get_graphiti` / `GraphitiClient` / `load_graphiti_config` / `integrations.graphiti`.
  Every remaining `graphiti` reference is one of: a **fleet-memory-shim legacy name**
  (a var/param named `graphiti`/`graphiti_client` that resolves to `get_memory_client()`),
  a **docstring/comment** ("formerly Graphiti"), a **telemetry enum literal**
  (`GraphitiQueryType`, `"digest+graphiti"`), or a **live read-consumer going through the
  FM shim**. That is why the suite is green — **there is no dead-import / latent-bug cleanup**.
- **W2 (factory simplification) is DONE.** `fleet_memory_client.py:509` — "fleet-memory is
  the only backend; the graphiti/dual routing and the `.guardkit/graphiti.yaml backend:`
  reader were retired." `knowledge/config.py` is gone. Only a stale docstring (line 15)
  remains.
- **W3 (delete graphiti implementation) is DONE**, except an **empty `integrations/graphiti/`
  husk** (0 `.py` files, no importers — trivially deletable).
- **W4 (docs/rules + CLAUDE.md) is DONE** this session (§3.4, commit `7594c19e`) and earlier.
- **W1 (repoint/settle the read consumers) is the only substantive code work left**, and it
  is a **product decision (Fork A + Fork B)**, not a mechanical rename.
- **Forks C and D are already resolved** by WS-2c (see §3).

**Bottom line:** §3.3 reduces to (a) one trivial dead-husk deletion + a handful of optional
cosmetic docstring/legacy-name touch-ups (zero-decision), and (b) the **Fork A/B decision**
about read-enrichment, which parameterizes a small W1 wave. It is not the large risky rename
the handoff feared.

---

## 1. What changed since the disposition map (2026-07-01 → 2026-07-03)

| Map assumption (2026-07-01) | Current reality (2026-07-03) |
|---|---|
| §2a "delete wholesale" (graphiti_client.py, config.py, cli/graphiti.py, seeding cluster, integrations/graphiti) still present | **All deleted by WS-2c (2026-07-02)** — except an **empty `integrations/graphiti/` husk** (0 `.py`, 0 importers) |
| W2 factory simplification pending | **Done** — `fleet_memory_client` is fleet-memory-unconditional; `config.py`/`graphiti.yaml` reader gone |
| Fork C (interactive_capture) open | **Resolved** — `interactive_capture.py`, `review_knowledge_capture.py`, `template_sync.py` all **gone** |
| Fork D (planning knowledge: graphiti_arch/graphiti_design) open | **Mostly resolved** — `planning/graphiti_arch.py` + `graphiti_design.py` **gone**; the 4 arch command specs (`system-design`, `arch-refine`, `system-arch`, `system-plan`) kept + **already repointed to fleet-memory this session**. Residue folds into Fork A |
| W4 rules/CLAUDE.md pending | **Done** (§3.4, `7594c19e`) |
| "~20 modules, big/risky, don't bulk-rename" | ~28 files mention graphiti, but **none is a dead import**; almost all are shim-legacy-name / docstring / telemetry / live-read-via-shim |

---

## 2. Current-state classification (every remaining module)

**Legend — Action:** `DELETE`=dead, remove now · `LEAVE`=working, no change · `COSMETIC`=optional
docstring/legacy-name tidy (no behavior) · `FORK`=gated by a product decision below.

### 2a. `DELETE` — the one genuine dead-code removal (zero decision)

| Path | State | Action |
|---|---|---|
| `guardkit/integrations/graphiti/` | empty husk: 0 `.py` files, empty `episodes/`+`parsers/`+ stale `__pycache__`, **0 importers** | `git rm -r` now |

### 2b. `LEAVE` — working fleet-memory code with legacy graphiti naming (no change needed)

| Path | Why it's fine |
|---|---|
| `knowledge/fleet_memory_client.py` | **the shim itself** — intentional `GraphitiClient`-shaped interface (compat). (stale docstring line 15 → COSMETIC) |
| `knowledge/fleet_memory_mapping.py` | authoritative `group_id → (project, payload_type, domain_tags)` map — the migration Rosetta stone |
| `knowledge/graph_export.py` | legitimate FalkorDB→FM exporter for `guardkit memory migrate-graph` (KEEP per handoff) |
| `knowledge/outcome_manager.py`, `outcome_queries.py`, `failed_approach_manager.py`, `adr_service.py` | write/read via `get_memory_client()` shim; `graphiti`-named locals only |
| `knowledge/feature_plan_context.py` | `graphiti_client` property → `get_memory_client()` (already FM); reads gated by Fork A |
| `knowledge/query_logger.py` | live JSONL memory-query logger (1 importer: feature_plan_context) |
| `knowledge/adr.py`, `feature_detector.py` | **no graphiti code at all** — only example strings/URLs in docstrings |
| `knowledge/__init__.py`, `planning/__init__.py`, `cli/memory.py`, `commands/feature_plan_integration.py` | re-exports / FM-backed; no removed symbols |
| `orchestrator/feature_orchestrator.py` | **zero graphiti** (grep-clean; the "2 refs" were false positives) |
| `orchestrator/instrumentation/schemas.py`, `prompt_profile.py` | **telemetry enum literals** (`GraphitiQueryType`, `GraphitiStatus`, `"digest+graphiti"`). Renaming breaks stored-telemetry/profile continuity → LEAVE (rename only with a schema-migration task, low value) |

### 2c. `COSMETIC` — optional docstring / dead-param tidy (no behavior, defer freely)

| Path | Note |
|---|---|
| `orchestrator/autobuild.py` | `loader.graphiti` = legacy param name for the FM client (warmup). Optional rename `graphiti`→`memory` |
| `planning/mode_detector.py` | accepts a deprecated `graphiti_client` param it **ignores**; drop the param when convenient |
| `orchestrator/quality_gates/coach_validator.py`, `environment_bootstrap.py`, `cli/system_context.py`, `cli/init.py` | docstring-only historical "…retired in FEAT-MEM-09" prose — accurate, harmless |
| `knowledge/fleet_memory_client.py:15` | stale docstring "routes graphiti vs fleet_memory vs dual" contradicts line 509 (backend is unconditional) — one-line fix |

### 2d. `FORK` — live read-consumers gated by a product decision (§3)

| Path | Reads (group_ids) | Fork |
|---|---|---|
| `knowledge/context_loader.py` | product_knowledge, command_workflows, quality_gate_phases, feature_build_architecture, feature_overviews, role_constraints (RETIRE) + architecture_decisions, failure_patterns (MIGRATE) | **A** |
| `knowledge/job_context_retriever.py` | feature_specs, task_outcomes, project_architecture, failure_patterns, domain_knowledge, turn_states, role_constraints, quality_gate_configs, implementation_modes, patterns | **A + B** |
| `knowledge/task_analyzer.py`, `gap_analyzer.py`, `autobuild_context_loader.py` | autobuild job/gap context via shim | **A** |
| `knowledge/feature_plan_context.py` (reads) | RETIRE + feature_specs/outcomes | **A** (high-value keep) |
| `knowledge/turn_state_operations.py` | turn_states write+read via shim | **B** |
| `planning/mode_detector.py`, `system_plan.py` | implementation_modes / system knowledge (markdown-only mode already) | **A** (low value) |

> All 2d modules read fleet-memory **through the shim** today — they already *work*. The Fork
> question is not "make them work" but "should these reads keep targeting legacy group_ids that
> are now the harvest corpus, be repointed to `domain_tags`/`payload_types`, or be dropped."

---

## 3. The two open decisions (Forks A & B) — C & D already resolved

**Fork A — read-enrichment strategy (dominant).** ~7 consumers auto-inject knowledge context by
reading fleet-memory (via the shim) using legacy Graphiti `group_id`s. Most of those groups are
**RETIRE** groups now covered by the harvest corpus (chunked prose), not typed records.
- **R (repoint):** rewrite each read to fleet-memory `memory_search(project, query, payload_types,
  domain_tags)` per `fleet_memory_mapping.py`; verify the harvest corpus returns useful hits where
  typed group records used to. Highest effort; preserves auto-context-priming.
- **A (accept loss):** drop read-enrichment; keep WRITE paths (outcomes/ADRs/failed-approaches) +
  explicit `guardkit memory search`. Biggest code reduction; "zero ceremony"; loses auto-priming.
- **Hybrid (map's recommendation):** repoint the high-value few (feature-plan context [already FM],
  outcomes, failed-approaches, autobuild coach/job context); drop the low-value planning reads
  (mode-detector, system-plan).

**Fork B — turn_states (`turn_state_operations`).** Keep writing feature-build turn history to
fleet-memory (**R**) or drop it (**A**)? Its only reader is `job_context_retriever`; if Fork A drops
autobuild read-enrichment, turn_states loses its consumer → A.

**Fork C — interactive capture: RESOLVED (X).** `interactive_capture.py` is gone; there is no
`guardkit graphiti capture -i` trigger left. No action.

**Fork D — planning knowledge: RESOLVED (kept + repointed).** `graphiti_arch.py`/`graphiti_design.py`
are gone; the arch command specs were repointed to fleet-memory this session. Residual `mode_detector`
/ `system_plan` reads fold into Fork A (low value).

---

## 4. Proposed waves

**W0 — zero-decision mechanical (no fork; can land immediately, own commit):**
- `git rm -r guardkit/integrations/graphiti/` (empty husk).
- Fix the stale docstring `fleet_memory_client.py:15`.
- (Optional, same or separate commit) the §2c cosmetic docstring/dead-param tidies.
- Gate: suite stays at 7 pre-existing fails; `grep -rn "integrations.graphiti" guardkit/` empty.

**W1 — consumer settle (AFTER Fork A/B decided):** one tightly-scoped task per consumer, each
with a **live-store assertion test** (assert a real `nats_core` fleet-memory call, not a mock —
per [`per-task-green-is-not-feature-green.md`](../../../.claude/rules/per-task-green-is-not-feature-green.md)).
Shape depends on the fork answers:
- **A=Hybrid, B=A (map default):** repoint feature_plan_context (already FM — just strip RETIRE-group
  reads) + outcomes/failed-approaches; **drop** read-enrichment in context_loader / job_context_retriever
  / autobuild_context_loader / task_analyzer / gap_analyzer / mode_detector; **drop** turn_states read,
  keep the write or drop both. Smallest surviving surface.
- **A=R-all:** repoint all 7 reads to `memory_search` + harvest-corpus verification (largest effort).
- **A=A-all:** delete all read-enrichment paths (largest deletion, simplest result).

**W5/W6 — infra (operator, §3.5, out of scope here):** drop `qwen-graphiti` LLM (keep the embedder),
decommission FalkorDB (fleet-wide, one-way), coordinate the global Qwen2.5 pull with the other 4
graph consumers. Autobuild cannot do these (`.mcp.json` gate; false-green history).

**Autobuild-safety:** W0 is a trivial manual commit. W1 per-consumer repoints are autobuild-candidates
*only* as single tightly-scoped tasks each with a live-store assertion. W5/W6 are manual/operator.

---

## 5. Acceptance (whole of §3.3, once W0+W1 land)

- `grep -rn graphiti guardkit/ --include='*.py'` returns only: intentional history (docstrings),
  the FM shim's compat naming, telemetry enum literals, and `graph_export.py` (FalkorDB migrator).
- No module imports a removed symbol (already true today).
- Suite green on 3.12; `guardkit memory search`/`status` work; the chosen Fork A/B behavior verified
  against the **live** store (not a mock).
- `.guardkit/graphiti.yaml` fully unreferenced (already true); W5/W6 infra tracked separately.

---

## 6. Pointers

- Pre-WS-2c map (product forks + W-order): [`FEAT-MEM-09-consumer-disposition-map.md`](FEAT-MEM-09-consumer-disposition-map.md).
- This session's completed chunks: §3.1/§3.2 `237f5d4c`, §3.4 `7594c19e`; handoff `b5fd892e`.
- Migration Rosetta stone: `guardkit/knowledge/fleet_memory_mapping.py` (`group_id → payload/domain_tags`).
- Write contract: `docs/internals/commands-lib/memory-preamble.md`.
- Live-store verification rule: `.claude/rules/per-task-green-is-not-feature-green.md`.
