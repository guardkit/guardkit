# HANDOFF — FEAT-MEM-09 WS-2c **W3** (delete graphiti impl + drop graphiti-core dep) — 2026-07-02

Pick-up doc for a **fresh conversation**. Assumes no prior context. W1 + W1b + W2 are
**DONE and committed** (suite-green). This doc covers **W3** (the bulk delete) + the
**dep-drop**, then W4 (docs). Continue with the **staged fix-forward** plan below — do
NOT attempt a single bulk delete without the interpreter/collection gate after each step.

> **What W3 is:** remove guardkit's now-dormant **graphiti CODE** (the ~40 impl modules)
> and, in the dep-drop, the `graphiti-core` dependency. It does NOT touch FalkorDB **data**
> (that's WS-6, one-way, fleet-wide, gated). Guardkit's graphiti reads have been **dark since
> FEAT-MEM-08** and the orchestrators/factory are now fully de-coupled (W1b/W2), so every
> deletion here is behaviour-preserving.

---

## 0. TL;DR — where we are, what to do next

**Done & committed this session (local `main`, rebased onto origin/main, NOT pushed):**
- `60ebde5d` WS-2c/**W1b-planning** — retire graphiti planning-knowledge stack (Fork D=X + hollow-command retirement).
- `dc1b77c3` WS-2c/**W1b-rest** — de-couple `autobuild.py` + `feature_orchestrator.py` from graphiti (warmup/hook/preflight/seed removed).
- `cc7c3cf2` WS-2c/**W2** — factory (`fleet_memory_client.py`) fleet-memory-unconditional; `DualWriteClient` + `_resolve_backend_from_config` deleted. **This removed the LAST reader of `.guardkit/graphiti.yaml` `backend:`, so `config.py` + `graphiti_client.py` are now safe to delete.**

**Locked operator decisions (do NOT re-litigate — carried from WS-2c handoff + this session):**
- **Hybrid disposition**: keep+repoint high-value writes/reads; drop low-value planning reads.
- **Fork C=X** remove interactive capture (`interactive_capture.py`).
- **Fork D=X** drop planning-knowledge features (already done in W1b-planning).
- **Retire the two hollow commands** `/system-overview` + `/impact-analysis` (done in W1b-planning).
- **KEEP `falkordb`** — `guardkit/memory/graph_export.py` (`read_falkordb_episodics`, `from falkordb import FalkorDB` at line 247) needs it for `guardkit memory migrate-graph` (WS-3). It currently arrives via `graphiti-core[falkordb]`; dep-drop must replace that with a **direct `falkordb`** PyPI dep.

**Next action (staged; §4 has detail):**
1. **W3a — de-graphiti the 3 SURVIVING consumers** so nothing outside the delete-set imports it:
   `cli/init.py` (BIG refactor — see §6), `cli/main.py` (graphiti CLI group), `knowledge/__init__.py` (re-exports).
2. **W3b — `git rm` the delete-set** (~40 modules, §5) + **delete/update the ~89 test files** that import them, fix-forward with `import guardkit.cli.main` + `pytest --co` until clean.
3. **dep-drop** (`pyproject.toml`, §7) — remove `graphiti-core` base dep + `gemini` extra; replace the `falkordb` extra (`graphiti-core[falkordb]`) with a **direct `falkordb`**; drop graphiti-core from the `autobuild` extra; drop the `[tool.uv]` git-URL allowance. Reinstall; confirm `import falkordb` works, `import graphiti_core` fails.
4. **verify** — `rg graphiti guardkit/` only intentional history; suite green (bar pre-existing/quarantine); `guardkit memory status/search` + `migrate-graph --dry-run` still work.
5. **W4 docs** — CLAUDE.md "Knowledge Capture"; the 2 `.claude/rules/graphiti-*.md`; retire/slim `.guardkit/graphiti.yaml`; cosmetic docstring cleanups deferred from this session; **flag `/system-design` & `/arch-refine` skills** (they still reference deleted `SystemDesignGraphiti`/`SystemPlanGraphiti` — their spec tests only check the markdown text, so they pass, but the skills are effectively broken post-cutover).

---

## 1. Exact current state (2026-07-02)

**guardkit local `main` (newest first, post-rebase onto origin/main):**
```
<this handoff> docs(FEAT-MEM-09): WS-2c/W3 pickup handoff
cc7c3cf2 refactor(FEAT-MEM-09): WS-2c/W2 make memory factory fleet-memory-unconditional
dc1b77c3 refactor(FEAT-MEM-09): WS-2c/W1b-rest de-couple orchestrators from graphiti
60ebde5d refactor(FEAT-MEM-09): WS-2c/W1b retire graphiti planning-knowledge stack
562b3504 Merge remote-tracking branch 'origin/main'                       [origin]
9539770b Added new ADR (ADR-FLEET-003-agent-interface-boundary)           [origin]
6a4fe4f6 docs(FEAT-MEM-09): WS-2c staged pickup handoff (Option 2, W1 done)
64fd4c17 refactor(FEAT-MEM-09): WS-2c/W1 repoint keep-consumers off graphiti to fleet-memory
```

> **GIT STATE — reconciled, `main...origin/main [ahead 4]`, NOT pushed.** My 4 commits
> (`60ebde5d`/`dc1b77c3`/`cc7c3cf2` + this handoff) were **rebased onto origin/main** after it
> advanced by +2 (`9539770b "Added new ADR"` = `docs/decisions/ADR-FLEET-003-agent-interface-boundary.md`
> + `562b3504` merge — disjoint files, clean rebase). **W3 continues on local HEAD.** The branch is
> ahead of origin by 4, behind by 0 — just `git push` when ready (no further reconcile needed).

**Working tree:** clean **except one unrelated deletion** `docs/state/TASK-TEST-WORKFLOW/test_state.txt`
(some other machine/session deleted it; **NOT mine — never stage it**), plus untracked
`.claude/hooks/.state/`, `docs/history/`, `tasks/backlog/memory-cutover/`.

**Quarantine mechanism (important):** the test conftest auto-skips known-red tests
(`[quarantine] skipped N pre-existing red test(s)`; override with `GUARDKIT_NO_QUARANTINE=1`).
"Suite green" already accounts for pre-existing reds (memory `main-has-preexisting-red-tests`).

---

## 2. What is DONE (W1 + W1b + W2)

- **W1** (`64fd4c17`, prior session): repointed the 3 keep-consumers (`failed_approach_manager`,
  `turn_state_operations`, `adr_service`) off `get_graphiti()` → `get_memory_client()`.
- **W1b-planning** (`60ebde5d`): deleted 5 planning modules (`graphiti_arch`, `graphiti_design`,
  the dead `coach_context_builder`, `system_overview`, `impact_analysis`); retired
  `/system-overview` + `/impact-analysis`; kept degraded `/system-plan` (markdown-only),
  `/context-switch` (nav), `mode_detector` (setup-only). 34 files, −16,438.
- **W1b-rest** (`dc1b77c3`): `autobuild.py` — dropped graphiti import block + FALK01
  unraisable-hook call + graphiti fallback in factory-acquisition (kept `get_memory_factory`);
  `feature_orchestrator.py` — retired `_preflight_check` (→ no-op True), `_seed_stall_episodes_to_graphiti`,
  `_pre_init_graphiti` + call sites + module-level `get_graphiti` import. 8 files, −1,188.
- **W2** (`cc7c3cf2`): factory fleet-memory-unconditional; deleted `DualWriteClient` +
  `_resolve_backend_from_config`; dropped graphiti/dual branches from
  `init_memory_client`/`get_memory_client`/`get_memory_factory` (`backend`/`graphiti_config`
  params kept, ignored). 4 files, −454.

**Verification each stage:** `python -c "import guardkit.cli.main"` clean; full `pytest --co`
collects (16,208 tests); affected subsets green. Two **pre-existing** reds surfaced and were
proven pre-existing (do NOT chase — see §8): `test_autobuild_orchestrator.py::TestResolveTestsRequired::{test_testing_task_does_not_require_tests,test_alias_benchmark_maps_to_testing}`.

---

## 3. The verified W3 surface (audited this session — trust it)

- **SURVIVING guardkit consumers that STILL import the delete-set (must de-graphiti FIRST, §6):**
  - `guardkit/cli/init.py` — **BIG** (~40 graphiti refs; live imports of `graphiti_client`,
    `integrations.graphiti.episodes.project_overview`, `knowledge.config`). Seed-on-init +
    MCP-config generation + `graphiti.yaml` writing + `--skip-graphiti`/`--copy-graphiti` flags.
    Comparable in size to the W1b-planning refactor.
  - `guardkit/cli/main.py` — `from guardkit.cli.graphiti import graphiti` (line ~21) +
    `cli.add_command(graphiti)` (~111-112). Remove both. (`system_context` import was already
    fixed in W1b-planning.)
  - `guardkit/knowledge/__init__.py` — the `from guardkit.knowledge.graphiti_client import (...)`
    re-export block (~140-151) + the `__all__` entries (~339-348: `GraphitiConfig`,
    `GraphitiClient`, `GraphitiClientFactory`, `init_graphiti`, `get_graphiti`, `get_factory`,
    `GraphitiSettings`, `load_graphiti_config`). Remove them. **Blast radius:** only the seed
    files (`seed_role_constraints`, `seed_feature_build_adrs`) consume these re-exports, and
    they're all in the delete-set — so removing the re-exports + deleting the seeds is atomic
    (that's why `__init__` is W3, not W1b — see the disposition map §4).
- **Cosmetic-only (leave for W4 / opportunistic — NOT live imports):**
  `knowledge/adr_service.py:13` (a `from ...graphiti_client import GraphitiClient` inside the
  MODULE DOCSTRING example, not code); `knowledge/feature_plan_context.py` (the `graphiti_client`
  property NAME + `[Graphiti]` log prefixes + `_get_backend_type` "graphiti" string);
  `knowledge/fleet_memory_mapping.py` (a comment). None import graphiti at runtime.
- **~89 test files** import a delete-set module (they break collection when the modules go).
  This is the bulk of the effort. Fix-forward: delete tests of deleted features; update tests
  of surviving consumers.
- **KEEP `falkordb`**: `guardkit/memory/graph_export.py:247` `from falkordb import FalkorDB`
  (lazy, in `read_falkordb_episodics`). Standalone — NOT graphiti-core. Powers
  `guardkit memory migrate-graph` (WS-1b/WS-3).
- **Entities/facts are graphiti-clean** (docstrings only). KEEP
  `knowledge/entities/{outcome,failed_approach,turn_state,adr*}` (used by keep-consumers).
  Optional cleanup: orphaned `knowledge/entities/*` + `knowledge/facts/*` used only by deleted
  seeds/planning (verify no survivor imports first).

---

## 4. Staged plan (fix-forward) — a suite-green commit at each stage

**Execution strategy: de-graphiti consumers → `git rm` delete-set → FIX-FORWARD via the interpreter.**
After each step:
```bash
.venv/bin/python -c "import guardkit.cli.main"                                    # module-level import breakage
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --co -q 2>&1 | tail  # collection breakage (test imports)
```
Each error names the exact surviving file still referencing a deleted symbol → fix that file.

### W3a — de-graphiti the 3 surviving consumers (edit, keep) — one commit (§6 detail)
- Rewrite `cli/init.py` to remove ALL graphiti (seed-on-init, MCP config, graphiti.yaml
  writing, the graphiti CLI flags). `guardkit init` keeps template application + project setup.
  Fleet-memory config is env-driven (`FLEET_MEMORY_*`), so init writes no memory config.
- `cli/main.py`: drop the `graphiti` group import + `add_command`.
- `knowledge/__init__.py`: drop the graphiti re-exports + `__all__` entries.
- **Do NOT delete the delete-set modules yet** — do this step, gate green, commit (or fold into W3b).

### W3b — `git rm` the delete-set (§5) + test fallout — one (or few) commit(s)
`git rm` the whole delete-set, then fix-forward. **Delete their test files too** (most of the 89):
`tests/**/*graphiti*`, seed tests, `test_seeding*`, integration graphiti tests, `test_dual_write*`
(already gone in W2), etc. Use `pytest --co` to find every test module that fails to import a
deleted module and delete/rewrite it. Keep tests of surviving consumers (update them).

### dep-drop (`pyproject.toml`, §7) — folds into W3b or its own commit
See §7. Reinstall + confirm imports.

### verify + W4 — one commit (§0 step 4-5)

---

## 5. Precise DELETE-set (`git rm` after W3a; verify no SURVIVING importer via `pytest --co`)

```
guardkit/knowledge/graphiti_client.py            # 2617 LOC, the get_graphiti() client (graphiti_core importer). Safe now (W2 done).
guardkit/knowledge/falkordb_workaround.py        # 667 LOC (graphiti_core importer)
guardkit/knowledge/query_logger.py               # graphiti query logging
guardkit/knowledge/episode_splitting.py          # graphiti episode helper
guardkit/knowledge/config.py                     # GraphitiSettings/load_graphiti_config/get_config_path. Safe now (W2 dropped its last reader).
guardkit/_group_defs.py                           # graphiti group_id defs
guardkit/integrations/graphiti/**                 # ~20 files: parsers/episodes/project.py/metadata/constants
guardkit/cli/graphiti.py                          # deprecated `guardkit graphiti` CLI group
guardkit/cli/graphiti_query_commands.py
guardkit/knowledge/seed_*.py + seeding.py + system_seeding.py + project_seeding.py   # ~24 seed files (RETIRE groups)
guardkit/knowledge/interactive_capture.py         # Fork C=X (guardkit graphiti capture -i)
guardkit/knowledge/template_sync.py               # Fork A drop (templates RETIRE)
```
> Already deleted in W1b-planning: `planning/graphiti_arch.py`, `planning/graphiti_design.py`,
> `planning/coach_context_builder.py`, `planning/system_overview.py`, `planning/impact_analysis.py`.
> Already deleted in W2: `knowledge/fleet_memory_client.py::DualWriteClient` (class) +
> `tests/unit/knowledge/test_dual_write_client.py`.

Optional cleanup (verify no survivor import first): orphaned `knowledge/entities/*` +
`knowledge/facts/*` used only by deleted seeds (e.g. `api_contract`, `architecture_context`,
`component`, `crosscutting`, `data_model`, `design_decision`, `feature_overview`,
`system_context`, `facts/quality_gate_config`, `facts/role_constraint`). KEEP
`entities/{outcome,failed_approach,turn_state,adr*}`.

---

## 6. W3a detail — de-graphiti the surviving consumers

### `cli/init.py` (the big one — treat like a mini-refactor)
Grep its graphiti surface first (`grep -n graphiti guardkit/cli/init.py`). It has:
- module imports (~42-44): `integrations.graphiti.episodes.project_overview.ProjectOverviewEpisode`,
  `knowledge.config.{_find_project_root,load_graphiti_config}`,
  `graphiti_client.{GraphitiClient,GraphitiConfig,normalize_project_id}`, and `KNOWN_EMBEDDING_DIMS` (~267, ~639).
- **Retire:** `_check_llm_reachable`, `SeedingProgressClient` (wraps `GraphitiClient.upsert_episode`),
  the graphiti MCP-config helpers (`discover_graphiti_mcp_path`, `generate_mcp_config`,
  `write_mcp_config`, entity-type defaults), the `graphiti.yaml` writers
  (`write_graphiti_config`, `copy_graphiti_config`, `_find_source_graphiti_config`), the whole
  **Step 2 seed-on-init** block (~1447-1611), and the `--skip-graphiti`/`--copy-graphiti`/
  `--copy-graphiti-from`/MCP CLI options + their handling.
- **Keep:** the `guardkit init` command itself — template application, project directory setup,
  the non-graphiti steps. Fleet-memory needs no init-time config (env-driven).
- **Decide with the operator if unsure:** whether `guardkit init` should print a "memory is
  env-driven (FLEET_MEMORY_*)" note where the graphiti-seed step was. Default: yes, a short note.
- **Tests:** `tests/**/test_init*` / `test_guardkit_init*` will have heavy graphiti fallout —
  delete the seed/MCP/graphiti.yaml tests, keep the template-application tests. Fix-forward.

### `cli/main.py` + `knowledge/__init__.py`
Mechanical (see §3). Remove the graphiti group import+registration and the graphiti re-exports+`__all__`.

---

## 7. dep-drop (`pyproject.toml`)

Exact current lines (verify before editing — origin rebase may shift them):
- **Line 41** (base dep): `"graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1",` → **remove**.
- **Lines 61-63** (`falkordb` extra): `graphiti-core[falkordb] @ git+...` → **replace** the extra body with a **direct** `"falkordb"` (or a pinned `"falkordb>=...,<..."`) PyPI dep, so `graph_export`/`migrate-graph` still work WITHOUT graphiti-core.
- **Lines 66-68** (`gemini` extra): `graphiti-core[google-genai] @ git+...` → **remove the whole `gemini` extra**.
- **Lines 107-108** (`autobuild` extra): drop the two `graphiti-core[...] @ git+...` lines; keep direct `falkordb` if autobuild needs it.
- **Lines 152-153** (`[tool.uv]`): drop the "Allow direct git+ URL … graphiti-core fork pin" allowance.

Then reinstall (`uv pip install -e .` or the project's install) and confirm:
```bash
.venv/bin/python -c "import falkordb; print('falkordb OK')"        # must work (kept)
.venv/bin/python -c "import graphiti_core"                          # must now FAIL (expected)
```

---

## 8. Gotchas

- **Never a single bulk delete without the gate.** ~89 test files import delete-set modules; a
  bulk `git rm` breaks collection wholesale. Stage it, `pytest --co` after each step, suite-green
  before each commit.
- **`config.py` + `graphiti_client.py` are NOW safe to delete** — W2 removed the last
  `.guardkit/graphiti.yaml` `backend:` reader (`_resolve_backend_from_config`). The W2-before-W3
  ordering gate is cleared.
- **`falkordb` must stay** — currently arrives via `graphiti-core[falkordb]`. After dropping
  graphiti-core, add a DIRECT `falkordb` dep or `graph_export`/migrate-graph (WS-3) breaks.
- **PRE-EXISTING reds — do NOT chase (not yours):**
  - `test_autobuild_orchestrator.py::TestResolveTestsRequired::{test_testing_task_does_not_require_tests,test_alias_benchmark_maps_to_testing}` (2, proven pre-existing via stash-diff; unrelated to graphiti).
  - `tests/knowledge/test_graphiti_client_*` (driver_creation log-message, embedding_preflight, llm_health, retry) — pass in isolation, fail only in broad runs = test-ordering pollution. Moot after W3 (files deleted).
  - `tests/unit/cli/test_graphiti_capture_outcome.py` (8 errors, pre-existing) — delete-set (tests `guardkit graphiti capture-outcome`).
  - The memory note `main-has-preexisting-red-tests` (coach_sdk_stream_resilience + dead-task-id lint) also applies.
- **Dead-task-id lint** (`tests/rules/test_no_dead_task_id_references.py`) greps
  `guardkit/orchestrator/**` for `TASK-XXXX` refs that must resolve to a filed task. My new
  comments referenced only `TASK-SC-009` (pre-existing) + `FEAT-MEM-09` (a FEAT-id, not matched).
  If you add orchestrator comments in W3, use real/filed task IDs.
- **Quarantine**: `[quarantine] skipped N pre-existing red` is normal; `GUARDKIT_NO_QUARANTINE=1` to see them.
- **`git` hygiene (parallel-activity hazard).** A stray `git add -A && git commit "Save state for
  TASK-031"` fired mid-work once this session (swept staged deletes; recovered by soft-reset).
  Origin/main also diverged (§1). So: **commit with EXPLICIT pathspecs**, `git diff --cached
  --name-status` before every commit, and **verify HEAD before/after each commit**. **Never stage
  `docs/state/TASK-TEST-WORKFLOW/test_state.txt`** (unrelated deletion). Memory notes:
  `commit-with-explicit-pathspecs-shared-index`, `check-existing-tasks-before-filing`.
- **rg mangling**: `rg` output in this environment sometimes garbles matched terms. Prefer `rg -l`,
  plain `grep -n`, or `Read` when a match looks garbled.
- **CI**: main `tests.yml` runs WITHOUT guardkitfactory/langchain (memory
  `ci-tests-yml-no-guardkitfactory`); local `.venv` has everything.
- **`.mcp.json`** still has a `graphiti` server entry — removing it is a **manual** edit (Claude
  Code hard-gates `.mcp.json` under the SDK harness — memory `autobuild-cannot-edit-mcp-json`).
  Out of scope for the code W3; note it for W4/W5.
- **Cosmetic graphiti docstrings/comments** left this session (defer to W4): `adr_service.py`
  docstring, `feature_plan_context.py` (`graphiti_client` property name + `[Graphiti]` logs +
  `_get_backend_type`), `fleet_memory_mapping.py` comment, `task_analyzer.py`/`autobuild_context_loader.py`/
  `job_context_retriever.py` `graphiti` param/attr names, `context_switch.py` display string.
- **`/system-design` & `/arch-refine` skills** reference the now-deleted `SystemDesignGraphiti`/
  `SystemPlanGraphiti` classes; their spec tests (`tests/unit/commands/test_system_design_spec.py`,
  `test_design_refine_spec.py`) only assert the markdown text, so they pass — but the skills are
  effectively broken post-cutover. **W4 decision:** retire those skills (Fork-D-adjacent) or
  rewrite their specs. Flag to the operator.

---

## 9. Environment & run facts

- **Repo**: `~/Projects/appmilla_github/guardkit`; py3.12 `.venv` has everything. Siblings:
  `../fleet-memory`, `../nats-core`, `../nats-infrastructure`, `../dgx-spark`.
- **Test runner**: `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider <paths>`
  (pytest.ini adds `--cov` needing pytest-cov; `-o addopts=""` skips them).
- **Import gate**: `.venv/bin/python -c "import guardkit.cli.main"` + `... -m pytest --co -q` after each step.
- **Memory reads still work** (fleet-memory): `set -a; . ./.env; set +a; export FLEET_MEMORY_ENABLED=true
  GUARDKIT_MEMORY_BACKEND=fleet_memory; .venv/bin/python -m guardkit.cli.main memory status` → REACHABLE.
- **migrate-graph (needs falkordb kept)**: `guardkit memory migrate-graph --dry-run --project guardkit`.
- **Fast fallout triage tip (worked well this session):** delegate a mechanical multi-file test
  rewrite to a focused subagent with an OBJECTIVE pytest-green gate + a list of the known
  pre-existing failures to leave alone. It offloads context; verify its diff after.

---

## 10. Acceptance for W3 (+ dep-drop + verify)

- [ ] W3a — `cli/init.py` de-graphiti'd (guardkit init template application intact, no seed/MCP/graphiti.yaml); `cli/main.py` graphiti group gone; `knowledge/__init__.py` graphiti re-exports + `__all__` gone.
- [ ] W3b — delete-set (~40 modules, §5) `git rm`'d; ~89 test files deleted/updated; `import guardkit.cli.main` + `pytest --co` clean.
- [ ] dep — `graphiti-core` base + `gemini` extra removed; `falkordb` kept as a DIRECT dep; `autobuild` extra de-graphiti'd; `[tool.uv]` git-URL allowance dropped; `import graphiti_core` fails, `import falkordb` works.
- [ ] verify — `rg graphiti guardkit/` only intentional history/cosmetic; suite green (bar pre-existing/quarantine); `guardkit memory status/search` + `migrate-graph --dry-run` work.
- [ ] W4 — CLAUDE.md "Knowledge Capture" + `.claude/rules/graphiti-*.md` rewritten fleet-memory-only; `.guardkit/graphiti.yaml` retired/slimmed; cosmetic docstrings cleaned; `/system-design` & `/arch-refine` skills retired-or-flagged; `.mcp.json` graphiti server entry noted for manual removal.
- [ ] push — `git fetch && git rebase origin/main` (integrate the +2 ADR/merge commits), then push.
- [ ] (out of scope here → WS-5/6) drop `qwen-graphiti` LLM + decommission FalkorDB — fleet-wide, one-way.

---

## 11. Key artifacts & pointers

- **Disposition map (the authority)**: `docs/design/specs/memory-cutover/FEAT-MEM-09-consumer-disposition-map.md`
  (§2a delete / §2b leave / §2c consumers / §3 forks A-D / §4 safe deletion order W1-W6). NB: §4 puts
  `knowledge/__init__` re-exports + `cli/main` + `cli/init` in W3 (delete-time consumer updates) — followed here.
- **Prior WS-2c handoff** (W1 done): `docs/design/specs/memory-cutover/HANDOFF-FEAT-MEM-09-WS2c-2026-07-02.md`.
- **This session's commits**: `git show 60ebde5d`, `git show dc1b77c3`, `git show cc7c3cf2`.
- **Agent memory (load these)**: `falkordb-fleet-wide-not-guardkit-local` (FEAT-MEM-09 tracker),
  `graphiti-cutover-qwen25-removal`, `feat-mem-08-reads-stubbed`, `autobuild-cannot-edit-mcp-json`,
  `main-has-preexisting-red-tests`, `ci-tests-yml-no-guardkitfactory`, `commit-with-explicit-pathspecs-shared-index`.
- **Scope-estimate lesson from this session:** the original WS-2c handoff UNDER-scoped W1b
  ("16 trivial branch-strips" was actually a module-level-coupled planning-package refactor).
  Expect W3's `cli/init.py` to be similarly bigger than a one-liner, and the ~89 test files to
  be the bulk of the effort.
