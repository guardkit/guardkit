# HANDOFF — FEAT-MEM-09 de-graphiti: command specs + docs DONE; what remains — 2026-07-03

Pick-up doc for a **fresh conversation**. Assumes no prior context. Three commits landed
this session (§2). The **command-spec tree and the published docs are now graphiti-free**,
and `/system-overview` + `/impact-analysis` are fully retired. This doc records exactly
what's done and the remaining de-graphiti surface (§3), ranked with recommendations.

---

> ## ✅ UPDATE 2026-07-03 (later session): §3.1 + §3.2 DONE — commit `237f5d4c`
>
> Agent-def tool grants (§3.1) and the dead libs (§3.2) are cleaned + pushed.
> **§3.2 was materially larger than described in §3.2/§4/§5 below** — the "0
> importers" claim came from a broken grep (`grep -rln a|b path`: the unquoted
> `|` piped grep into a bogus command, silently missing the real callers). The
> two dead libs were wired into a substantial installer surface:
> - **`install.sh`** — a `graphiti-core` pip-install flow (for a now-removed
>   dependency), `guardkit graphiti` CLI help + a `graphiti)` dispatcher case
>   (for the removed CLI group), the `graphiti-check` wrapper heredoc,
>   init-comment mentions, and a drift-warning special-case.
> - **`bin-entries.txt`** — the `graphiti_diagnose` entry + `graphiti_check`
>   wrapper comment.
> - **`init-project.sh`** (NOT mentioned anywhere below) — a `--copy-graphiti`
>   flag + three helpers (`find_source`/`copy`/`write_graphiti_config`) +
>   `normalize_project_id`, all writing the **retired** `.guardkit/graphiti.yaml`
>   (the shell-init fallback was the last holdout; `cli/init.py` already retired
>   it in FEAT-MEM-09).
>
> All removed so the installer matches the already-degraphiti'd Python init.
> **One deliberate behavior change:** `--copy-graphiti` also served as an
> explicit source-path hint for the `.mcp.json` copy; that niche hint is gone —
> `.mcp.json` now always auto-discovers from parent dirs (already the default).
> **Gates:** full suite 12469 passed / **7 pre-existing fails / zero new**;
> `bash -n` clean on both scripts; adversarial 3-lens shell review (bash-correctness
> · behavior-preservation · completeness) returned **clean**. Files: the 2 agent
> `.md`, the 2 `git-rm`'d libs, `bin-entries.txt`, `install.sh`, `init-project.sh`,
> `test_install_wrapper_feature_subcommand.py`.
>
> **Still remaining:** §3.3 (guardkit/ Python — the big workstream, unstarted),
> §3.4 (`.claude/rules/graphiti-knowledge*.md` — in progress this session),
> §3.5 (infra, operator-only).

---

## 0. TL;DR

- **Done + pushed (origin/main):** 3 commits — arch command specs + fleet-memory preamble
  (`71becc51`); non-arch command specs + `/impact-analysis` deletion (`ce914f7c`); Graphiti
  **docs** removal + finish retiring the 2 pure-graphiti-reader commands (`6f116157`). See §2.
- **State:** `HEAD == origin/main == 6f116157`. Full suite: **12469 passed, 7 pre-existing
  failures, zero new** (baseline dropped 8→7 this session — see §6). Working tree clean except
  the unrelated `D docs/state/TASK-TEST-WORKFLOW/test_state.txt` (**never stage it**).
- **The whole `installer/core/commands/*.md` tree + the published docs (guides/nav/index) are
  graphiti-free.** Historical archives (`docs/reviews|research|state|retro|adr|features`) were
  deliberately left untouched (they're records).
- **What remains (§3), ranked:**
  1. **Agent definitions** — `architectural-reviewer.md` + `code-reviewer.md` still grant the
     **deleted** `mcp__graphiti__*` tools. LIVE rot, small. *(quick win)*
  2. **Dead libs** — `installer/core/commands/lib/graphiti_check.py` + `graphiti_diagnose.py`
     have **0 importers**. Safe deletion. *(quick win)*
  3. **`guardkit/` Python code** — ~20 modules still mention graphiti; two are heavy
     (`context_loader.py` ~48 non-comment refs, `job_context_retriever.py` ~18). This is the
     **big, risky** code-layer cleanup — needs the disposition map, NOT a mechanical rename.
  4. **`.claude/rules/graphiti-knowledge*.md`** — 2 historical-marked rule files loaded into
     every session (context cost). Slim/retire + fix CLAUDE.md refs. *(small)*
  5. **Infra (separate, one-way, needs operator):** FalkorDB decommission + fleet-wide
     FalkorDB→fleet-memory migration (gates Qwen2.5 removal). NOT a code/docs session.
- **Recommended next:** knock out #1 + #2 (quick, clear, live rot) in one commit; then scope
  #3 against the disposition map as its own workstream. #4 is a cheap bonus. #5 is operator infra.

---

## 1. Background — the fleet-memory contract (what everything migrates TO)

The Graphiti/FalkorDB **implementation** was removed earlier in FEAT-MEM-09 (WS-2c, commit
`c40324d9` et al.). Knowledge capture now runs on **fleet-memory** (pure-embeddings). The
canonical, agent-facing contract this session established is:

- **Shared preamble:** [`docs/internals/commands-lib/memory-preamble.md`](../../../internals/commands-lib/memory-preamble.md)
  (replaced the deleted `graphiti-preamble.md`). Read this first — it defines availability tiers,
  the typed-payload write shape, search, and the domain_tags vocabulary.
- **Write:** MCP tool `mcp__fleet_memory__memory_write_payload(payload={...})`. There is **no**
  general `guardkit memory` write CLI — only `guardkit memory capture-outcome` (build_outcome).
- **Search:** `mcp__fleet_memory__memory_search(project="guardkit", query, payload_types,
  domain_tags, token_budget)` OR `guardkit memory search`.
- **7 payload types:** `adr`, `review_report`, `build_outcome`, `pattern`, `warning`,
  `seed_module`, `document`. BasePayload requires `project` + `identifier` (underscores only,
  `^[a-zA-Z0-9_]+$`) + `source_ref` + `domain_tags`.
- **Authoritative old-group → FM mapping:** `guardkit/knowledge/fleet_memory_mapping.py`
  (this IS the payload-shape design pass — reuse it).
- **`.mcp.json`** has one server: `fleet_memory` (stdio, `uv run --project ../fleet-memory
  python -m fleet_memory.mcp`, `EMBED_URL` = GB10 `:9000`). The `mcp__graphiti__*` tools and
  the graphiti HTTP MCP (`:8004`) are **gone**.
- **Domain_tags vocabulary this session standardised (write tag == read tag):** architecture
  ADRs/docs → `["architecture"]`; design decisions/DDRs → `["design"]`; API contracts →
  `["design","api_contract"]`; data models → `["design","data_model"]`; task outcomes →
  `build_outcome`/`["task"]`; project decisions → `adr`/`["project"]`; review verdicts →
  `review_report`/`["review"]`.

---

## 2. What was done this session (3 commits, all pushed)

### `71becc51` — arch command specs + shared preamble → fleet-memory
- New `docs/internals/commands-lib/memory-preamble.md`.
- Rewrote **5 arch specs**: `system-design.md`, `arch-refine.md`, `system-arch.md`,
  `system-plan.md`, `design-refine.md` (Graphiti seeding → typed adr/document payloads;
  prereq/search → `memory_search` + `docs/` Glob; supersession → payload `supersedes`).
- Updated their 4 spec tests to assert fleet-memory. Deleted retired `system-overview.md` spec.
- Repointed all 12 preamble citations to `memory-preamble.md`.

### `ce914f7c` — non-arch command specs + delete retired `/impact-analysis`
- Rewrote **5 live non-arch specs**: `task-work`, `task-complete` (outcomes → `guardkit memory
  capture-outcome`; decisions → adr payloads), `task-review` (project_decisions→adr,
  task_outcomes→build_outcome, verdicts→review_report), `feature-plan`, `context-switch`.
- Fixed 3 stray graphiti mentions in `feature-build`/`feature-spec`/`task-create`.
- Deleted retired `installer/core/commands/impact-analysis.md`; removed all dangling
  `/system-overview` + `/impact-analysis` refs across every live spec.

### `6f116157` — Graphiti **docs** removal + finish retiring the 2 commands
- Deleted **24 docs** (15 `docs/guides/graphiti-*.md`, `setup/graphiti-setup.md`,
  `architecture/graphiti-architecture.md`, `deep-dives/graphiti/*` ×3,
  `deep-dives/mcp-integration/graphiti-mcp-setup.md`, `relevance-tuning-testing.md`,
  `system-overview-guide.md`, `impact-analysis-guide.md`).
- Deleted **3 coupled doc-tests** (`test_graphiti_integration_guide`, `test_graphiti_setup_guide`,
  `test_graphiti_navigation`) + **dead lib** `graphiti_response_parser.py` + its test.
- CLAUDE.md: dropped both retired commands from *System Context Commands* + *Key References*;
  the *Graphiti Knowledge* row → `memory-preamble.md`.
- Updated the 2 doc validators (`test_claude_md_references.py`, `test_mkdocs_navigation.py`) to
  assert only `/context-switch` (they're **quarantined/skipped** in the suite but now correct —
  verify green with `GUARDKIT_NO_QUARANTINE=1`).
- Rewrote `context-switch-guide.md` → fleet-memory; rewrote the "MCP server" section of
  `claude-code-multi-machine-setup.md` to the **real** fleet-memory stdio `.mcp.json` (was the
  removed Graphiti HTTP MCP `:8004`); dropped a stale init-seeding note in `GETTING-STARTED.md`.
- `mkdocs.yml`: removed the Knowledge Graph nav section + 2 retired-guide entries + Graphiti MCP
  Setup. `docs/index.md`: removed the Knowledge Graph (Graphiti) section.

> **⚠️ Verify before trusting:** the `claude-code-multi-machine-setup.md` MCP-section rewrite was
> reconstructed from `.mcp.json` (HTTP→stdio is a fundamental transport change). It is a personal
> operational doc — sanity-check it against the real GB10 multi-machine setup.

---

## 3. What remains (the de-graphiti surface still present)

### 3.1 Agent definitions — LIVE rot, HIGH value, SMALL *(recommend next)*
`installer/core/agents/architectural-reviewer.md:4` and `code-reviewer.md:18` still grant the
**deleted** MCP tools in their `tools:` frontmatter:
```
mcp__graphiti__get_status, mcp__graphiti__search_nodes, mcp__graphiti__search_memory_facts
```
When these agents run, those tool grants reference tools that no longer exist. **Fix:** remove
the three `mcp__graphiti__*` entries from both `tools:` lines, and de-graphiti any prompt-body
instructions telling the agent to query graphiti (grep each file for `graphiti`). Consider
whether to add the fleet-memory equivalents (`mcp__fleet_memory__memory_search`) or just drop
knowledge lookup from these agents — check what the bodies actually do. **Note:** these agent
`.md` files may have spec tests (`tests/**/*agent*`); grep before editing.

### 3.2 Dead graphiti libs — SMALL, clean deletion *(recommend next, bundle with 3.1)*
`installer/core/commands/lib/graphiti_check.py` and `graphiti_diagnose.py` both have **0
importers** (verified: `grep -rln graphiti_check|graphiti_diagnose installer/ guardkit/` →
only their own files). Same situation as the `graphiti_response_parser.py` we deleted in
`6f116157`. **Fix:** `git rm` both + any test that references them (grep `tests/` first).

### 3.3 `guardkit/` Python code — LARGE, RISKY, needs the disposition map *(its own workstream)*
~20 live modules still mention graphiti. Two are heavy and **must not be mechanically renamed**:
- `guardkit/knowledge/context_loader.py` — **~48 non-comment** graphiti refs
- `guardkit/knowledge/job_context_retriever.py` — **~18 non-comment**
- lighter: `outcome_manager.py` (~0 non-comment, mostly docstring), `cli/system_context.py` (1),
  `cli/init.py` (~1), `mode_detector.py`, `feature_detector.py`, `gap_analyzer.py`,
  `turn_state_operations.py`, `autobuild_context_loader.py`, `feature_plan_context.py`,
  `coach_validator.py`, `environment_bootstrap.py`, `instrumentation/*`, `knowledge/__init__.py`.
- **KEEP:** `guardkit/memory/graph_export.py` — legitimately reads FalkorDB for
  `guardkit memory migrate-graph` (the legacy-export tool). Not rot.

**Why risky:** the suite is **green** (12469 passed), so these are almost certainly *legacy-named
but working* (e.g. a `graphiti_client` variable that now holds a fleet-memory client via a compat
shim, or historical docstrings), **not** dead imports. This is the code-layer cutover cleanup the
**disposition map already scoped** — drive it from
[`FEAT-MEM-09-consumer-disposition-map.md`](FEAT-MEM-09-consumer-disposition-map.md) and the memory
`[[FEAT-MEM-09 disposition map]]` (deletion order: **W1 repoint → W2 factory → W3 delete**;
`config.py`/`graphiti_client` only after W2). Do NOT bulk-rename — investigate each module against
the disposition map, keep the suite green, and land in small commits.

### 3.4 `.claude/rules/graphiti-knowledge*.md` — SMALL *(cheap bonus)*
`.claude/rules/graphiti-knowledge.md` + `graphiti-knowledge-graph.md` are banner-marked
"REMOVED/historical" but **still load into every session's context** (cost) and are still cited by
CLAUDE.md's "Knowledge Capture (fleet-memory)" section (lines ~227/229). **Options:** (a) slim each
to a short "graphiti removed → see memory-preamble.md, these conventions still apply" stub;
(b) delete + fold the still-applicable no-hyphens/group-id conventions into `memory-preamble.md`,
and repoint the CLAUDE.md citations. Keep the no-hyphens/underscore identifier convention alive
somewhere (fleet-memory still enforces `^[a-zA-Z0-9_]+$`).

### 3.5 Infra — separate, one-way, needs the operator *(not a code/docs session)*
Per memory `[[falkordb-fleet-wide-not-guardkit-local]]` + `[[FEAT-MEM-09 disposition map]]`:
FalkorDB is **fleet-wide** (11.8k nodes / 92 graphs / ~18 projects); guardkit's 4,154 nodes were
**not** migrated to fleet-memory (685 rows). The **FalkorDB decommission (WS-6)** = fleet-wide
data destruction (one-way) and is gated on a fleet-wide FalkorDB→fleet-memory migration, which in
turn gates **Qwen2.5 removal** (see `[[graphiti-cutover-qwen25-removal]]`). Split code-decommission
from infra-teardown. This needs operator decisions, not autonomous work.

---

## 4. Recommended next + execution notes

1. **One quick commit: §3.1 (agent defs) + §3.2 (dead libs).** Both are live rot, unambiguous,
   low-risk. Gate: `grep -rn mcp__graphiti__ installer/core/agents/` → empty; `grep -rln
   graphiti_check\|graphiti_diagnose installer guardkit` → empty; full suite still exactly the 7
   pre-existing fails.
2. **Then scope §3.3 as its own workstream** off the disposition map. Read
   `context_loader.py` + `job_context_retriever.py` first to learn whether "graphiti" is a live
   code path or legacy naming over a fleet-memory shim — that determines whether it's a rename, a
   repoint, or a delete. Small commits, suite green after each.
3. **§3.4 whenever** (cheap; reduces per-session context cost).
4. **§3.5 only with the operator.**

**General gate after any change:**
```
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --timeout=120 -q --tb=no tests/ | tail -3
```
Must stay at **7 failed** (§6), zero new. For the quarantined doc validators use
`GUARDKIT_NO_QUARANTINE=1 ... tests/unit/documentation/`.

---

## 5. Grep signatures (verify current state / find remaining rot)

```bash
# Command specs + published docs are graphiti-free (MUST be empty / 0):
grep -rl -i graphiti installer/core/commands/*.md
grep -rlnE "\]\((graphiti-[a-z-]+|system-overview-guide|impact-analysis-guide|relevance-tuning-testing)" \
  docs/guides docs/index.md CLAUDE.md   # broken links from live docs -> empty

# Remaining LIVE rot (the §3 surface):
grep -rn "mcp__graphiti__" installer/core/agents/*.md              # 3.1 (2 files today)
grep -rln graphiti_check\|graphiti_diagnose installer guardkit     # 3.2 (dead libs, 0 importers)
grep -rln graphiti guardkit/ --include='*.py' | grep -v fleet_memory_  # 3.3 (~20 modules)
ls .claude/rules/graphiti-knowledge*.md                            # 3.4

# Historical archives that MUST be left alone (records):
#   docs/reviews/ docs/research/ docs/state/ docs/retro/ docs/adr/ docs/features/ docs/decisions/
```

---

## 6. Pre-existing red tests — now **7** (was 8), DO NOT chase

Acceptance for any follow-up = "still exactly these 7, zero new". This session deleted
`tests/test_graphiti_navigation.py`, which held the env-only `test_mkdocs_can_build` failure
(it shells `mkdocs build` and gets `FileNotFoundError` because mkdocs isn't installed in the
venv) — so the baseline dropped 8→7:
```
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_testing_task_does_not_require_tests
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_alias_benchmark_maps_to_testing
tests/orchestrator/quality_gates/test_coach_validator_evidence_repos.py::TestRunEvidenceRepoTests::test_runs_declared_passing_suite
tests/orchestrator/test_agent_invoker_langgraph.py::TestSelectorRoutesToLangGraphHarness::test_env_var_routes_to_langgraph
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_passing_command
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_failing_command
tests/rules/test_no_dead_task_id_references.py::test_no_dead_task_id_references_in_orchestrator
```
(These need the guardkitfactory/langchain stack or are env-only; unrelated to de-graphiti. See
memory `[[main-has-preexisting-red-tests]]`.)

---

## 7. Commit / push hygiene (shared repo!)

- Branch is `main`; user commits directly to main (memory `[[git-workflow-commit-to-main]]`).
- **Explicit pathspecs**: `git add <your files>` then `git diff --cached --name-only` (must be
  exactly your files; **never** `docs/state/TASK-TEST-WORKFLOW/test_state.txt`), then commit.
- **Never `git stash`** (shared stack — `[[avoid-git-stash-shared-index-repo]]`).
- `git fetch` before push (a parallel session may have advanced origin).
- End commit messages with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## 8. Key pointers

- **This session's commits:** `git show 71becc51 ce914f7c 6f116157`.
- **Fleet-memory contract:** `docs/internals/commands-lib/memory-preamble.md`;
  `guardkit/knowledge/fleet_memory_mapping.py`; MCP tools in
  `../fleet-memory/src/fleet_memory/mcp/tools/{write,search}.py`; payloads in
  `../fleet-memory/src/fleet_memory/payloads/{base,models}.py`.
- **Disposition map (drives §3.3):** `FEAT-MEM-09-consumer-disposition-map.md`.
- **Prior handoffs:** `HANDOFF-FEAT-MEM-09-arch-design-command-specs-2026-07-02.md` (the one that
  kicked off this session), `HANDOFF-FEAT-MEM-09-WS2c-W3-2026-07-02.md` (the code cutover).
- **Agent memory to load:** `feat-mem-09-command-spec-fm-rewrite` (this session's full record),
  `FEAT-MEM-09 disposition map`, `falkordb-fleet-wide-not-guardkit-local`,
  `graphiti-cutover-qwen25-removal`, `main-has-preexisting-red-tests`,
  `git-workflow-commit-to-main`, `commit-with-explicit-pathspecs-shared-index`,
  `avoid-git-stash-shared-index-repo`, `check-existing-tasks-before-filing`.
- **Test runner:** `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider <paths>`
  (pytest.ini adds `--cov`; `-o addopts=""` strips it). Quarantine: `GUARDKIT_NO_QUARANTINE=1`.

---

## 9. Acceptance for the next chunk (§3.1 + §3.2 quick win) — ✅ DONE (commit `237f5d4c`)

- [x] `grep -rn mcp__graphiti__ installer/core/agents/` → empty (both agent tool-lists cleaned).
- [x] No graphiti prompt-body instructions existed in those 2 agents (only the `tools:` frontmatter).
- [x] `graphiti_check.py` + `graphiti_diagnose.py` deleted; no test references them.
- [x] Full installer surface de-graphiti'd too (`install.sh`, `init-project.sh`, `bin-entries.txt`) —
      see the ✅ UPDATE banner at the top for the (larger-than-scoped) detail + the one behavior change.
- [x] Full suite still exactly the 7 pre-existing fails (§6), zero new; collection clean.
- [x] Committed with explicit pathspecs; pushed after `git fetch`.
