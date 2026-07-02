# HANDOFF — FEAT-MEM-09 WS-2c (decommission guardkit graphiti code + drop graphiti-core dep) — 2026-07-02

Pick-up doc for a **fresh conversation**. Assumes no prior context. Continue with the
**staged "Option 2"** plan below (W1b → W2 → W3 → dep-drop → verify → W4), landing a
**suite-green commit at each stage** — do NOT attempt a single bulk delete (it breaks
`main` badly: the graphiti test surface is ~164 files).

> **What WS-2c is:** remove guardkit's now-dormant **graphiti CODE** and the `graphiti-core`
> dependency. It does NOT touch FalkorDB **data** (that's WS-6, one-way, gated on the fleet).
> Guardkit's graphiti reads have been **dark since FEAT-MEM-08** (`.guardkit/graphiti.yaml`
> `enabled: false`, `backend: fleet_memory`), so every `get_graphiti()` read already returns
> None and consumers already degrade to no-context — **dropping dead reads is functionally free.**

---

## 0. TL;DR — where we are, what to do next

**Done & committed this session:** WS-2c/**W1** — the "keep" write/read consumers repointed off
graphiti to fleet-memory (commit `64fd4c17`), suite green.

**Locked operator decision — Hybrid disposition** (do not re-litigate):
- **A = Hybrid**: keep+repoint high-value writes/reads; **drop** low-value planning reads.
- **B = R**: keep writing `turn_states` to fleet-memory (done in W1).
- **C = X**: remove interactive capture (`interactive_capture.py` + `guardkit graphiti capture -i`).
- **D = X**: drop planning-knowledge features (`graphiti_arch.py`, `graphiti_design.py` = the
  graphiti reads behind `/system-design` & `/arch-refine`).
- **KEEP `falkordb`** (see §5 dep-drop): `graph_export`/`guardkit memory migrate-graph` still needs
  it for the WS-3 fleet-wide migration.

**Next action (staged; §4 has detail):**
1. **W1b** — strip graphiti from the ~16 SURVIVING files (registration/warmup/planning/residual) so
   only the delete-set imports `graphiti_client`.
2. **W2** — simplify the factory (`fleet_memory_client`): fleet-memory unconditional; drop
   `graphiti`/`dual`/`DualWriteClient`/`_resolve_backend_from_config` + its `config.get_config_path`
   read. Update its tests (`test_dual_write_client`, `test_memory_backend_selection`, graphiti-backend
   cases in `test_fleet_memory_client`).
3. **W3** — delete the graphiti impl (~40 modules, §5) + delete/update their ~164 test files.
4. **dep-drop** — remove `graphiti-core` + `gemini` extra; replace `falkordb` extra
   (currently `graphiti-core[falkordb]`) with a **direct `falkordb`** dep; drop the `[tool.uv]`
   git-URL allowance.
5. **verify** — `python -c "import guardkit.cli.main"` clean; `pytest --co` collects; suite green;
   `rg graphiti guardkit/` empty bar intentional history.
6. **W4** — docs: CLAUDE.md "Knowledge Capture", the 2 `.claude/rules/graphiti-*.md`, retire/slim
   `.guardkit/graphiti.yaml`.

---

## 1. Exact current state (2026-07-02)

**guardkit `main` (newest first) — FEAT-MEM-09 WS-2 + WS-2c/W1:**
```
64fd4c17 refactor(FEAT-MEM-09): WS-2c/W1 repoint keep-consumers off graphiti to fleet-memory
bc2303b2 docs(FEAT-MEM-09): promote 7 guardkit-core decisions to docs/decisions (WS-2b)   [pre-rebase 8b300b2d]
d533e290 docs(FEAT-MEM-09): promote 13 guardkit-core decisions to .claude/rules + 2 folds  [pre-rebase 792cb9c7]
11ddeac6 docs(FEAT-MEM-09): WS-2b classification of 147 project_decisions nodes            [pre-rebase 0b4d9fd8]
2c50909d test(FEAT-MEM-09): modernize 16 stale FEAT-MEM-08 write-path tests (WS-2)          [pre-rebase e10f4f02]
9072c7f6 feat(FEAT-MEM-09): repoint autobuild job-context chain to fleet-memory (WS-2)      [pre-rebase 5eb86fdd]
```
> The last 5 were pushed to origin (rebased → the bracketed SHAs are the pushed ones). **`64fd4c17`
> (W1) is committed but NOT pushed as of this handoff** — check `git status -sb` and push if desired.

**WS-2b distillation is LIVE in the store (no git commit — it was a fleet-memory write):**
44 guardkit decisions → `adr` (store `adr` 1→45), 127 task_outcomes → `build_outcome` (5→132),
DLQ 0, `source="distilled"`, idempotent by natural_key. Retrieval verified.

**Quarantine mechanism (important):** the test conftest auto-skips known-red tests
(`[quarantine] skipped N pre-existing red test(s)`; override with `GUARDKIT_NO_QUARANTINE=1`).
So "suite green" already accounts for the pre-existing reds (memory note `main-has-preexisting-red-tests`).

---

## 2. What is DONE — WS-2c/W1 (commit `64fd4c17`)

The 3 "keep" consumers repointed `get_graphiti()` → `get_memory_client()` (so they no longer import
`graphiti_client`), + test fallout fixed:
- `knowledge/failed_approach_manager.py` — `failed_approaches` → **warning** payload (mapped/migrate).
- `knowledge/turn_state_operations.py` — `turn_states` → **document** payload (mapped/migrate; Fork B=R keeps the write).
- `knowledge/adr_service.py` — dropped `GraphitiClient` import; `client: Any` (injected factory client). Writes `adrs` → **adr**.
- Tests: swapped patch targets `<module>.get_graphiti` → `get_memory_client` in
  `test_failed_approaches.py` (25), `test_turn_state.py` (20), `test_graphiti_write_path_logging.py` (2).
- `review_knowledge_capture.py` = NOT a `graphiti_client` importer (docstring-only) — left as-is (cosmetic).

Verified: those 3 modules import cleanly; the 3 test files = 132 passed / 2 quarantined; `guardkit.cli.main` imports.

**The mapping already supports every kept write** (`fleet_memory_mapping.py`): `task_outcomes`→build_outcome,
`project_decisions`/`adrs`→adr, `failed_approaches`→warning, `turn_states`→document. No mapping work needed.

---

## 3. The verified graphiti surface (from the 2026-07-01/-02 audit — don't re-audit)

- **~64 files** mention graphiti; **~30** import the `guardkit.knowledge.graphiti_client` MODULE.
- **Only TWO files import the real `graphiti_core` PyPI package**: `knowledge/graphiti_client.py` and
  `knowledge/falkordb_workaround.py`. Everything else imports guardkit's `graphiti_client` module.
- **`memory/graph_export.py` imports the raw `falkordb` package** (lazy, line ~247), standalone — NOT
  graphiti-core. It powers `guardkit memory migrate-graph` (WS-1b), still needed for **WS-3**. → KEEP falkordb.
- **All entities/facts are graphiti-clean** (they only mention `GraphitiClient` in docstrings; none import it).
  So no entity deletion is required for the dep-drop. Orphaned entities (used only by deleted seeds/planning)
  MAY be deleted as cleanup, but that's optional and must be verified no survivor imports them.
- **~164 test files** mention graphiti (many import deleted modules → break collection). This is the bulk of the effort.

---

## 4. Staged plan (Option 2) — a suite-green commit at each stage

**Execution strategy: delete/edit, then FIX-FORWARD via the interpreter.** After each stage run:
```bash
.venv/bin/python -c "import guardkit.cli.main"      # module-level import breakage
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --co -q 2>&1 | tail   # collection breakage (test imports)
```
Each error names the exact surviving file still referencing a deleted/renamed symbol → fix that file.
This is far faster than pre-auditing every reference. Then run the affected test subset, commit, next stage.

### W1b — strip graphiti from SURVIVING files (edit, keep) — one commit
These files survive but must stop importing `graphiti_client` (so W3 can delete it). Remove the graphiti
import + the (already-dead) graphiti read/warmup branch; keep the fleet-memory path:
- `orchestrator/autobuild.py` — remove `get_graphiti`/`get_factory`/`GraphitiClientFactory`/
  `_suppress_httpx_cleanup_errors`/`_install_graphiti_unraisable_hook` import (lines ~148-154) + the graphiti
  **fallback** branch in the factory-acquisition block (§5.1 added `get_memory_factory()` first, then falls
  back to `get_factory()`/`get_graphiti()`); **KEEP `get_memory_factory()`**. Remove any use of the two
  `_suppress_/_install_` helpers. The per-thread block (`_get_or_create_thread_loader`, ~5247-5327) is already
  substrate-agnostic (holds a FleetMemoryClientFactory now) — leave it.
- `orchestrator/feature_orchestrator.py` — remove the `get_graphiti()` warmup lazy-init (~2033, 2093, 2171-2182).
- `orchestrator/quality_gates/coach_validator.py` — drop the `get_graphiti` import (~line 99; availability flag only); keep `build_coach_context`/`coach_context_builder` delegation.
- `planning/coach_context_builder.py` — drop the `get_graphiti()` try-branch (~line 25); keep the `get_memory_client()` fallback (already there).
- `knowledge/__init__.py` — drop the graphiti re-exports (`get_graphiti`, `get_factory`, `GraphitiClientFactory`, etc. ~line 149) + `ADRService` doc mention is fine.
- `cli/main.py` — drop the `guardkit graphiti` CLI group import + registration (~lines 21, 116).
- `cli/init.py` — remove the `load_graphiti_config` + `upsert_episode` seed-on-init path (~line 142); `guardkit init` stays.
- `cli/system_context.py` — remove the graphiti read branch (planning; Fork A-drop).
- `planning/system_plan.py`, `planning/impact_analysis.py`, `planning/mode_detector.py`,
  `planning/context_switch.py` — remove the graphiti read branches (files/commands STAY, just no graphiti context; already dark).
- `knowledge/feature_plan_context.py` — already resolves `get_memory_client()`; strip any residual graphiti import + the RETIRE-group reads (keep feature_specs/outcomes).
- `knowledge/autobuild_context_loader.py`, `knowledge/job_context_retriever.py`, `knowledge/task_analyzer.py`
  — residual `graphiti_client` import cleanup (functionally already on the injected fleet factory client from §5.1).
- **Test fallout**: any test patching `<these_modules>.get_graphiti` → swap to `get_memory_client`, or if the
  test targets a dropped read feature, delete it. Use `rg -l "<module>.get_graphiti" tests/`.

### W2 — simplify the factory (`knowledge/fleet_memory_client.py`) — one commit
- `get_memory_client()`: make it return the FleetMemoryClient unconditionally (drop the `graphiti`/`dual` branches that lazily import `graphiti_client`/`DualWriteClient`).
- `init_memory_client()`: drop the `graphiti`/`dual` branches; keep `fleet_memory`. (Decide: keep the
  `backend=` param as a no-op/deprecation, or remove it — callers/tests pass `backend="graphiti"`.)
- Delete `_resolve_backend_from_config()` (the LAST reader of `.guardkit/graphiti.yaml` `backend:` via
  `config.get_config_path`) and `_ensure_backend_initialized()`'s config read → always fleet_memory.
- Delete the `DualWriteClient` class (top of the module).
- **KEEP** `FleetMemoryClientFactory` + `get_memory_factory()` (added in §5.1 — the autobuild per-thread seam).
- **Tests**: `tests/unit/knowledge/test_dual_write_client.py` (delete), `test_memory_backend_selection.py`
  (drop graphiti/dual cases), `test_fleet_memory_client.py` (drop `backend="graphiti"` cases). fleet-memory
  cases stay.

### W3 — delete the graphiti impl + dead consumers — one (or few) commit(s)
`git rm` the whole delete-set (§5), then fix-forward. **Delete their test files too** (that's most of the 164):
`tests/**/*graphiti*`, seed tests, `test_dual_write*`, integration graphiti tests, `test_seeding*`, etc.
Use `pytest --co` to find every test module that fails to import a deleted module and delete/rewrite it.

### dep-drop (`pyproject.toml`) — folds into the W3 commit or its own
- Remove the base `graphiti-core @ git+...` dep (line ~41).
- Remove the **`gemini`** extra (`graphiti-core[google-genai]`, ~67-68).
- Replace the **`falkordb`** extra — currently `graphiti-core[falkordb]` (~62-63) — with a **direct
  `falkordb`** PyPI dep (just the client `graph_export` uses), so migrate-graph/WS-3 still works WITHOUT graphiti-core.
- Update the `autobuild` extra (drops graphiti-core lines ~107-108; keep direct falkordb if needed there).
- Drop the `[tool.uv]` "allow direct git+ URL … graphiti-core fork pin" allowance (~152-153).
- Re-`uv pip install -e .` (or the project's install) and confirm `python -c "import falkordb"` still works,
  `python -c "import graphiti_core"` now fails (expected).

### verify + W4 — one commit
- `rg -n graphiti guardkit/` → only intentional history/comments.
- `guardkit memory status/search` still REACHABLE; `guardkit memory migrate-graph --dry-run` still works (falkordb kept).
- Suite green on 3.12 (bar quarantined).
- **W4 docs**: rewrite CLAUDE.md "Knowledge Capture (fleet-memory; Graphiti deprecated)" to fleet-memory-only;
  retire/rewrite `.claude/rules/graphiti-knowledge-graph.md` + `graphiti-knowledge.md`; retire or slim
  `.guardkit/graphiti.yaml` (fleet-memory config is env-driven `FLEET_MEMORY_*`, independent of that file);
  leave historical task records intact.

---

## 5. Precise DELETE-wholesale set (§2a of the disposition map + Hybrid C/D drops)

`git rm` these (verify no SURVIVING importer first via `pytest --co` / `import guardkit.cli.main`):
```
guardkit/knowledge/graphiti_client.py            # 2617 LOC, the get_graphiti() client (graphiti_core importer)
guardkit/knowledge/falkordb_workaround.py        # 667 LOC (graphiti_core importer)
guardkit/knowledge/query_logger.py               # graphiti query logging
guardkit/knowledge/episode_splitting.py          # graphiti episode helper
guardkit/knowledge/config.py                     # GraphitiSettings/load_graphiti_config/get_config_path (delete AFTER W2)
guardkit/_group_defs.py                           # graphiti group_id defs
guardkit/integrations/graphiti/**                 # 20 files: parsers/episodes/project.py/metadata
guardkit/cli/graphiti.py                          # deprecated `guardkit graphiti` CLI group
guardkit/cli/graphiti_query_commands.py
guardkit/knowledge/seed_*.py + seeding.py + system_seeding.py + project_seeding.py   # 24 seed files (RETIRE groups)
guardkit/knowledge/interactive_capture.py         # Fork C=X (guardkit graphiti capture -i)
guardkit/knowledge/template_sync.py               # Fork A drop (templates RETIRE)
guardkit/planning/graphiti_arch.py                # Fork D=X (/system-design, /arch-refine knowledge)
guardkit/planning/graphiti_design.py              # Fork D=X
```
Optional cleanup (verify no survivor import first): orphaned `knowledge/entities/*` and `knowledge/facts/*`
used only by the deleted seeds/planning (e.g. `api_contract`, `architecture_context`, `component`,
`crosscutting`, `data_model`, `design_decision`, `feature_overview`, `system_context`,
`facts/quality_gate_config`, `facts/role_constraint`). KEEP `entities/{outcome,failed_approach,turn_state,adr*}`
(used by the surviving keep-consumers) — they're graphiti-clean already.

---

## 6. Gotchas

- **Never a single bulk delete.** ~164 test files reference graphiti; a bulk `git rm` breaks pytest collection
  wholesale. Stage it, `pytest --co` after each stage, suite green before each commit.
- **`falkordb` must stay** — but it currently arrives via `graphiti-core[falkordb]`. After dropping graphiti-core,
  add a DIRECT `falkordb` dep or `graph_export`/migrate-graph (WS-3) breaks. Confirm `import falkordb` post-change.
- **`config.py` + `graphiti_client.py` delete AFTER W2** — the factory's `_resolve_backend_from_config` is the last
  reader of `.guardkit/graphiti.yaml` via `config.get_config_path`. W2 must land first.
- **Quarantine**: `[quarantine] skipped N pre-existing red` is normal; don't chase those. `GUARDKIT_NO_QUARANTINE=1` to see them.
- **Grep rendering**: `rg` output in this environment sometimes mangles matched terms (replaces them with `n`/`ln`).
  Prefer `rg -l` (file lists), plain `grep -n`, or `Read` when a match looks garbled — the files are fine.
- **CI**: the main `tests.yml` runs WITHOUT guardkitfactory/langchain (memory `ci-tests-yml-no-guardkitfactory`);
  harness-touching tests skip-guard. Local `.venv` has everything.
- **Autobuild can't do W2/W3** (per the disposition map): cross-cutting deletes + `.mcp.json` edits + false-green
  risk → these are **manual** (this is why we're doing it by hand). Per-consumer W1-style repoints could be
  autobuild candidates *with a live-store assertion test* each, but the deletes are manual.
- **`.mcp.json`** still has a `graphiti` server entry (W4/W5-ish): removing it is a manual edit (Claude Code
  hard-gates `.mcp.json` under the SDK harness — memory `autobuild-cannot-edit-mcp-json`). Out of scope for the code W3.

---

## 7. Environment & run facts

- **Repo**: `~/Projects/appmilla_github/guardkit`; py3.12 `.venv` has everything. Siblings: `../fleet-memory`,
  `../nats-core`, `../nats-infrastructure` (NATS pw), `../dgx-spark`.
- **Test runner**: `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider <paths>`
  (pytest.ini adds `--cov` needing pytest-cov; `-o addopts=""` skips them).
- **Import gate**: `.venv/bin/python -c "import guardkit.cli.main"` and `... -m pytest --co -q` after each stage.
- **Memory reads still work** (fleet-memory): `set -a; . ./.env; set +a; export FLEET_MEMORY_ENABLED=true
  GUARDKIT_MEMORY_BACKEND=fleet_memory; .venv/bin/python -m guardkit.cli.main memory status` → REACHABLE.
- **migrate-graph (needs falkordb kept)**: `guardkit memory migrate-graph --dry-run --project guardkit`.

---

## 8. Acceptance for WS-2c

- [x] W1 — keep-consumers (failed_approach/turn_state/adr_service) off graphiti to fleet-memory (`64fd4c17`).
- [ ] W1b — surviving registration/warmup/planning/residual files no longer import `graphiti_client`.
- [ ] W2 — factory fleet-memory-unconditional; `_resolve_backend_from_config`/`DualWriteClient` gone; its tests updated.
- [ ] W3 — graphiti impl (~40 modules) + their ~164 test files deleted/updated; `import guardkit.cli.main` + `pytest --co` clean.
- [ ] dep — `graphiti-core` + `gemini` removed; `falkordb` kept as a DIRECT dep; `[tool.uv]` git-URL allowance dropped; `import graphiti_core` now fails, `import falkordb` works.
- [ ] verify — `rg graphiti guardkit/` only intentional history; suite green (bar quarantined); `guardkit memory` + `migrate-graph --dry-run` work.
- [ ] W4 — CLAUDE.md "Knowledge Capture" + `.claude/rules/graphiti-*.md` rewritten fleet-memory-only; `.guardkit/graphiti.yaml` retired/slimmed.
- [ ] (out of scope here → WS-5/6) drop `qwen-graphiti` LLM + decommission FalkorDB — fleet-wide, one-way.

---

## 9. Key artifacts & pointers

- **Disposition map (the authority)**: `docs/design/specs/memory-cutover/FEAT-MEM-09-consumer-disposition-map.md`
  (§2a delete / §2b leave / §2c consumers / §3 forks A-D / §4 safe deletion order W1-W6).
- **This session's WS-2 handoff** (prior): `docs/design/specs/memory-cutover/HANDOFF-FEAT-MEM-09-WS2-2026-07-01.md`.
- **WS-2b classification** (for context on which decisions are guardkit-core): `...FEAT-MEM-09-WS2b-project-decisions-classification.md`.
- **Agent memory (load these)**: `falkordb-fleet-wide-not-guardkit-local` (the FEAT-MEM-09 tracker — full WS-0→WS-2b
  progress + the distillation + this WS-2c/W1),  `graphiti-cutover-qwen25-removal`, `feat-mem-08-reads-stubbed`,
  `autobuild-cannot-edit-mcp-json`, `main-has-preexisting-red-tests`, `ci-tests-yml-no-guardkitfactory`.
- **W1 commit**: `64fd4c17` (`git show 64fd4c17`).
