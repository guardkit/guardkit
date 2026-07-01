# FEAT-MEM-09 — Graphiti consumer disposition map (verified)

> Replaces the **incomplete** §5 table in `HANDOFF-FEAT-MEM-09-2026-07-01.md`.
> Built 2026-07-01 by direct grep/read of `main` (not agent inference — the
> disposition-analysis workflow was blocked by a server-side subagent rate limit,
> so this was produced in-loop from call-site evidence). Every row cites verifiable
> call sites. **Fill in the "Decision" column with the operator before any deletion.**

## 0. Verified starting state (2026-07-01)

- FEAT-MEM-08 **stable & live**: `guardkit memory status` → REACHABLE (fleet-memory);
  `guardkit memory search` returns hits; `public.store` = 685 rows (679 harvest chunks
  + 5 `build_outcome` + 1 `adr` from the soak). `main == origin/main`.
- FalkorDB (`whitestocks:6379`, the Graphiti rollback) is **reachable again** since the
  handoff was written (operator restart took) — rollback path currently intact.
- Graphiti footprint: **64** py files mention graphiti; **~40** meaningfully touch it;
  graphiti-core is a git+ pinned base dep + `falkordb`/`gemini` extras.

## 1. Executive summary

**Big correction vs the handoff §5 table** (which listed ~11 consumers): the real surface
is ~40 modules. Key surprises found by call-site audit:

1. **The 3 orchestrators are NOT knowledge consumers.** `autobuild.py`, `feature_orchestrator.py`
   call `get_graphiti()` **only to warm the client factory** (lazy-init / thread-safety
   pre-init — `feature_orchestrator.py:2033,2093,2171-2182`, `autobuild.py:1361-1363`).
   `coach_validator.py:99` only imports `get_graphiti` for an availability flag and delegates
   to `coach_context_builder`. → all **INTERNAL_DELETE (remove warmup)**, not R/X/A decisions.
2. **7+ live read consumers not in §5**: `context_loader` (8 reads), `job_context_retriever`
   (10 groups), `autobuild_context_loader`, `gap_analyzer`, `task_analyzer`, `template_sync`,
   `review_knowledge_capture`.
3. **Most read-enrichment reads target RETIRE groups** (`product_knowledge`, `command_workflows`,
   `patterns`, `role_constraints`, `quality_gate_configs`, `implementation_modes`,
   `quality_gate_phases`, `feature_build_architecture`, `templates`) — the 17 groups the mapping
   marks "covered by the harvest corpus." So repointing them means **semantic-searching the
   harvest corpus** (chunked prose), not reading typed group records. This is the central
   product decision (Fork A).
4. **`feature_plan_context` + `coach_context_builder` are ALREADY on fleet-memory** (verified:
   `feature_plan_context.graphiti_client` property returns `get_memory_client()`;
   `coach_context_builder` falls back to `get_memory_client()`). They need group-id cleanup, not
   repointing.
5. **Deletion-order coupling**: `fleet_memory_client._resolve_backend_from_config` still imports
   `knowledge/config.py::get_config_path` to read `.guardkit/graphiti.yaml`'s `backend:` flag.
   So `config.py` + `graphiti_client.py` can only be deleted **after** the factory is made
   fleet-memory-unconditional (W2 before W3). fleet-memory's own config is **env-driven**
   (`FLEET_MEMORY_*`), independent of graphiti.yaml.
6. **`guardkit graphiti capture --interactive`** (`interactive_capture`) is the only reachable
   trigger for interactive Q&A capture, and it dies with the `guardkit graphiti` CLI group
   unless a `guardkit memory capture` replacement is added (Fork C).

## 2. Complete disposition table

**Legend** — Dir: W=write R=read S=seed; Rec: `DEL`=INTERNAL_DELETE (mechanical, no product
decision), `R`=repoint to fleet-memory, `X`=remove feature, `A`=accept loss (keep command,
drop knowledge), `LEAVE`=already cut over (drop residual branch only); Conf=confidence.

### 2a. Graphiti implementation — delete wholesale (Rec = DEL, no product decision)

| Module | LOC | Notes | Conf |
|---|---:|---|---|
| `knowledge/graphiti_client.py` | 2617 | the `get_graphiti()` client. Delete **after** W2. | high |
| `integrations/graphiti/**` (20 files) | ~3100 | parsers/episodes/project.py/metadata. Only imported by other graphiti-internals + the consumers below. | high |
| `cli/graphiti.py` + `cli/graphiti_query_commands.py` | 2806 | deprecated `guardkit graphiti` CLI group (`main.py:21,116`). Superseded by `guardkit memory`. Drop registration. | high |
| `knowledge/falkordb_workaround.py` | 667 | FalkorDB RediSearch workarounds. | high |
| `knowledge/query_logger.py` | 175 | graphiti query logging. | med |
| `knowledge/episode_splitting.py` | 138 | graphiti episode helper. | med |
| `knowledge/config.py` (`GraphitiSettings`, `load_graphiti_config`) | 533 | reads `.guardkit/graphiti.yaml`. `get_config_path` still used by factory → delete after W2. | high |
| `_group_defs.py` | 54 | graphiti group_id definitions. | high |
| `knowledge/seeding.py`, `system_seeding.py`, `project_seeding.py`, `seed_command_workflows.py`, `seed_feature_build_adrs.py`, `seed_feature_overviews.py`, `seed_pattern_examples.py`, `seed_role_constraints.py`, `seed_agents.py`, `seed_rules.py`, `seed_failed_approaches.py` | ~3k | seed the **RETIRE** groups (harvest corpus covers them). `upsert_episode` writers. | high |
| `orchestrator/autobuild.py`, `feature_orchestrator.py` (warmup only) | — | remove the `get_graphiti()` lazy-init blocks. NOT consumers. | high |
| `orchestrator/quality_gates/coach_validator.py` (import only) | — | drop `get_graphiti` import (line 99); keep `build_coach_context`. | high |
| `cli/init.py` (graphiti seeding path) | — | remove `load_graphiti_config` + `upsert_episode` seed-on-init (line 142); `guardkit init` stays. | high |

### 2b. Already cut over — LEAVE (+ small cleanup)

| Module | Dir | groups | Trigger | Cleanup | Conf |
|---|---|---|---|---|---|
| `knowledge/outcome_manager.py` | W | task_outcomes→build_outcome | `/task-complete`, autobuild | none (via factory) | high |
| `knowledge/adr_service.py` | W/R | adrs→adr | ADR capture | client injected=factory; drop graphiti fallbacks | high |
| `knowledge/feature_plan_context.py` | R/W | many (RETIRE + MIGRATE) | `/feature-plan` | already `get_memory_client()`; **strip RETIRE-group reads**, keep feature_specs/outcomes | high |
| `planning/coach_context_builder.py` | R | coach_context | autobuild Coach | drop `get_graphiti()` try-branch (line 25); keep FM fallback | high |
| `knowledge/fleet_memory_client.py` (factory) | — | — | — | **W2**: drop `graphiti`/`dual`/`DualWriteClient` + `_resolve_backend_from_config` | high |

### 2c. True consumers — **need R/X/A decision**

| Module | Dir | groups (disposition) | Trigger | FM path? | Rec | Conf | Effort |
|---|---|---|---|---|---|---|---|
| `knowledge/failed_approach_manager.py` | W+R | failed_approaches (**MIGRATE**→warning) | autobuild failure capture/lookup | trivial-add (warning payload exists) | **R** | high | S |
| `knowledge/outcome_queries.py` | R | task_outcomes (**MIGRATE**) | outcome lookups | yes (build_outcome on FM) — raw `get_graphiti` needs repoint | **R** | high | S |
| `knowledge/review_knowledge_capture.py` | W | project_decisions→adr, task_outcomes→build_outcome (**MIGRATE**) | `/task-review` capture | trivial-add | **R** | med | S |
| `knowledge/turn_state_operations.py` | W+R | turn_states (**MIGRATE**→document) | feature-build turn history | trivial-add | **R or A** | high | M |
| `knowledge/interactive_capture.py` | W | various | `guardkit graphiti capture -i` (**dies with CLI**) | needs `guardkit memory capture` | **X or R** | high | M |
| `knowledge/context_loader.py` | R | product_knowledge, command_workflows, quality_gate_phases, feature_build_architecture, feature_overviews, role_constraints (**RETIRE**) + architecture_decisions, failure_patterns (**MIGRATE**) | task-work / autobuild context priming | R = harvest-corpus search; A = drop | **R or A** | high | M |
| `knowledge/job_context_retriever.py` | R | turn_states, task_outcomes, feature_specs, project_architecture, failure_patterns, domain_knowledge (**MIGRATE**) + role_constraints, quality_gate_configs, implementation_modes, patterns (**RETIRE**) | autobuild job context | R = mixed FM search; A = drop | **R or A** | high | L |
| `knowledge/autobuild_context_loader.py` | R | (autobuild context) | autobuild | R or A | **R or A** | med | M |
| `knowledge/gap_analyzer.py` | R | (analysis) | gap analysis | R or A | **R or A** | med | M |
| `knowledge/task_analyzer.py` | R | (task analysis) | task analysis | R or A | **R or A** | med | M |
| `knowledge/template_sync.py` | S/R | templates (**RETIRE**) | template sync/init | corpus covers it | **X** | med | S |
| `planning/mode_detector.py` | R | implementation_modes (**RETIRE**) | `/task-work` mode detect | R = corpus; A = heuristic-only | **R or A** | high | S |
| `planning/system_plan.py` | R | (system knowledge) | `/system-plan` | R or A | **R or A** | med | M |
| `planning/system_overview.py` | R | (system knowledge) | `/system-overview` | R or A | **R or A** | med | M |
| `planning/impact_analysis.py` | R | (system knowledge) | `/impact-analysis` | R or A | **R or A** | med | M |
| `cli/system_context.py` | R | (system knowledge) | `/system-overview`, `/impact-analysis` | couples with above | **R or A** | med | M |
| `planning/graphiti_arch.py` | R/W | architecture knowledge | `/system-design`, `/arch-refine` | R or X | **R or X** | med | M |
| `planning/graphiti_design.py` | R/W | design knowledge | `/system-design`, `/arch-refine` | R or X | **R or X** | med | M |

## 3. Human-decision forks (decide these first)

**Fork A — read-enrichment strategy (dominant).** ~11 read consumers auto-inject knowledge
context by reading Graphiti groups, most now RETIRED into the harvest corpus.
- **R-all**: repoint every read to fleet-memory semantic search over the harvest corpus.
  Preserves behaviour; highest effort; must verify the chunked prose corpus returns useful hits
  where typed group records used to.
- **A-all**: drop read-enrichment; keep WRITE paths + explicit `guardkit memory search`.
  Big code reduction, "zero ceremony"; loses auto context-priming.
- **Hybrid (recommended)**: repoint the high-value few (feature-plan context [already FM],
  outcomes, failed-approaches, autobuild coach/job context); drop the low-value planning reads
  (system-plan / impact-analysis / system-overview / mode-detector / arch / design).

**Fork B — turn_states** (`turn_state_operations`): keep writing feature-build turn history to
fleet-memory (**R**) or drop it (**A**)? Its main reader is `job_context_retriever`; if Fork A
drops autobuild read-enrichment, turn_states loses its consumer → A.

**Fork C — interactive capture** (`interactive_capture`): add a `guardkit memory capture`
replacement (**R**) or remove interactive Q&A capture (**X**)? `guardkit memory` already has
`capture-outcome`; this is the distinct interactive-questions capture.

**Fork D — planning knowledge features** (`graphiti_arch`/`graphiti_design`, i.e. `/system-design`
& `/arch-refine`): keep and repoint to fleet-memory (**R**) or drop these architecture-knowledge
features (**X**)?

## 4. Dependency / safe deletion order

1. **W1 — repoint/settle the "keep" consumers** (Fork decisions). Each lands + verifies against
   the live store (assert real `nats_core.publish_episode`, not a mock — per
   `per-task-green-is-not-feature-green.md`).
2. **W2 — simplify the factory** (`fleet_memory_client`): fleet-memory unconditional; drop
   `graphiti`/`dual`/`DualWriteClient` + `_resolve_backend_from_config` (which is the last reader
   of `.guardkit/graphiti.yaml` `backend:` via `config.get_config_path`).
3. **W3 — delete graphiti code** (§2a) + `graphiti-core` dep + `falkordb`/`gemini` extras +
   `[tool.uv]` git-URL allowance. Safe only after W1 (no consumer imports) and W2 (no config read).
   Update `knowledge/__init__.py` re-exports (`:149`), `cli/main.py` (`:21,116`), `cli/init.py`.
4. **W4 — config/docs**: retire/rename `.guardkit/graphiti.yaml` (or slim to `.guardkit/memory.yaml`);
   rewrite the 2 rules + CLAUDE.md "Knowledge Capture" section; leave historical task records.
5. **W5 — infra**: drop the `qwen-graphiti` **LLM** from the personal llama-swap config (KEEP the
   `embed` embedder — fleet-memory needs it); decommission FalkorDB on the NAS. Coordinate the
   global Qwen2.5 pull with the OTHER 4 graph consumers (forge/jarvis/specialist-agent/study-tutor).
6. **W6 — verify**: `grep -rn graphiti guardkit/` empty (bar intentional history); suite green on
   3.12; `guardkit memory` works; FalkorDB gone; rollback-loss documented.

**Autobuild-safety**: W1 per-consumer repoints are autobuild-candidates *if* each is one tightly
scoped task with a live-store assertion test. W2/W3 (cross-cutting deletes) and W4/W5 (config-flip,
`.mcp.json`, infra) are **manual/operator** — autobuild produced false-greens on the 08 cutover
and cannot edit `.mcp.json` under the SDK harness.

## 5. Wave/task breakdown — pending Fork A–D decisions

The concrete task list (one consumer/concern each) is filled in once Forks A–D are decided.
Recommended default = **Hybrid (A) + drop turn_states-read but keep write (B=R) + remove
interactive (C=X) + drop planning knowledge (D=X)** → smallest surviving surface consistent with
the "zero ceremony" principle while preserving outcomes/ADRs/failed-approaches/feature-plan context.
