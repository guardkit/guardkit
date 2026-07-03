# HANDOFF — FEAT-MEM-09: de-graphiti (§3.1/§3.2/§3.4) + §3.3 scoping + §3.3 W1 code — 2026-07-03

Pick-up doc for a **fresh conversation**. Assumes no prior context. This session took
FEAT-MEM-09 from "command specs + docs de-graphitied" through **the entire remaining code-layer
cleanup that was safe to do without the operator**, ending with the **§3.3 W1 read-consumer-settle
wave fully implemented (5/5 tasks) via `/task-work`**. Everything below is committed + pushed.

---

## 0. Current state (verify first)

- **`HEAD == origin/main == 685ded20`.** Working tree clean except the perennial
  `D docs/state/TASK-TEST-WORKFLOW/test_state.txt` — **NEVER stage it** (it's a parallel-session
  artefact). `.guardkit/memory-query-log.jsonl` is a gitignored test side-effect; ignore.
- **Full suite baseline: exactly `7 failed, ~12484 passed`** in default config. The 7 are
  **pre-existing** (langchain/guardkitfactory-dependent + env-only + a dead-task-id lint) — see §6.
  Acceptance for any follow-up = "still exactly those 7, zero new".
- **Test runner** (pytest.ini adds `--cov`; strip it):
  ```
  .venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --timeout=120 -q --tb=line tests/ | tail -3
  ```
  Doc validators are quarantined; run with `GUARDKIT_NO_QUARANTINE=1` to include them.
- **A parallel session is active on this repo.** Commit `1de01bc4` (`guardkit init` nats-core
  import guard) is theirs, landed mid-session. Always `git fetch` before push; use explicit
  pathspecs; the push guard `git merge-base --is-ancestor origin/main HEAD` has been reliable.

---

## 1. What this session shipped (commit-by-commit, all on origin/main)

| Commit | Chunk | Summary |
|---|---|---|
| `237f5d4c` | **§3.1 + §3.2 + installer** | Removed dead `mcp__graphiti__*` tool grants from `architectural-reviewer.md` + `code-reviewer.md`; `git rm` `graphiti_check.py` + `graphiti_diagnose.py`; **full installer de-graphiti** (`install.sh` 6 blocks — the removed `graphiti-core` pip-install flow, `guardkit graphiti` help + dispatcher case, `graphiti-check` wrapper heredoc, init comments; `init-project.sh` `--copy-graphiti` flag + 3 helpers writing the retired `graphiti.yaml`; `bin-entries.txt`). **The handoff's "0 importers" for §3.2 was wrong** — a broken grep (`grep -rln a|b path` — unquoted `\|`) hid the installer surface. |
| `b5fd892e` | docs | Marked §3.1/§3.2 done in the prior handoff + corrected the §3.2 scope. |
| `7594c19e` | **§3.4** | Retired the 2 `.claude/rules/graphiti-knowledge*.md` files (superseded by `docs/internals/commands-lib/memory-preamble.md`; the underscore-only identifier convention already lives there) + deleted the orphan `scripts/check-graphiti-doc-drift.py`; repointed CLAUDE.md's 2 Knowledge-Capture citations. |
| `8d4e021c` | **§3.3 scoping** | Current-state (post-WS-2c) reconciliation of the disposition map via a 6-classifier import-graph audit. **Headline: ZERO modules import a removed graphiti symbol** — every remaining ref is a fleet-memory-shim legacy name, a docstring, a telemetry enum, or a live read-via-shim. W2/W3/W4 already done. |
| `871d15ad` | docs | Resolved the two operator Fork A/B concerns (verified in code — see §3 of the scoping doc). |
| `007a62e6` | **§3.3 W0** | Fixed the stale `fleet_memory_client.py` factory docstring (dual-backend → fleet-memory-unconditional); removed the empty `integrations/graphiti/` husk (untracked pycache — no diff); **recorded the confirmed Fork A/B decisions**. |
| `d34ba412` | task files | Drafted the 5 W1 task files (`tasks/backlog/mem09-w1-read-consumer-settle/`). |
| `ab0f609c` | **W1 MODEDET** | Dropped the dead `graphiti_client` param from `planning/mode_detector.detect_mode` + unused `Any` import; converted 2 param-passing tests to a `pytest.raises(TypeError)` regression guard. |
| `906d61bc` | **W1 CTXLOAD** | (no prod change) added real-seam boundary + live tests to `context_loader`. |
| `1f94173a` | **W1 FPCTX** | **Real strip:** removed the 4 RETIRE-group reads from `feature_plan_context.build_context` (patterns/role_constraints/quality_gate_configs/implementation_modes); kept fields defaulting empty (zero API break); fixed a *second* test file (`test_feature_plan_context_builder.py`) I'd missed; added boundary/strip-proof/live tests. |
| `bc7d8bca` | **W1 JOBCTX** | (no prod change) added GROI real-seam boundary + delegation + live tests. |
| `685ded20` | **W1 TURNSTATE** | (no prod change, Fork B keep) added the **write-seam** boundary (real `add_episode`→publish, only the NATS edge stubbed) + read boundary + live. **Completes §3.3 W1 (5/5).** |

---

## 2. FEAT-MEM-09 §3.3 — the disposition, current state

Drive from [`FEAT-MEM-09-3.3-code-scoping-2026-07-03.md`](FEAT-MEM-09-3.3-code-scoping-2026-07-03.md)
(reconciles the older [`FEAT-MEM-09-consumer-disposition-map.md`](FEAT-MEM-09-consumer-disposition-map.md),
which predates WS-2c). Key current-state facts:

- **W2 (factory simplification), W3 (delete graphiti impl), W4 (docs/rules): DONE** (WS-2c + this session).
- **W1 (read-consumer settle): DONE this session** — the only substantive remaining code work.
- **Forks C (interactive capture) + D (planning knowledge) were already resolved by WS-2c**
  (`interactive_capture.py`, `planning/graphiti_arch.py`/`graphiti_design.py` are gone; the arch
  command specs were repointed to fleet-memory in the prior session).
- **Operator-confirmed decisions:** **Fork A = Hybrid/repoint** (keep the high-value autobuild
  read-enrichment; drop only dead vestiges), **Fork B = follows A** (keep `turn_states`).

**The recurring W1 finding:** 4 of the 5 consumers needed **no production change** — their reads were
already correctly wired to fleet-memory via the shim during FEAT-MEM-08 (TASK-MEM08-006). The W1 value
was **closing the `per-task-green-is-not-feature-green` gap**: every existing consumer test
**MagicMocks the fleet-memory client** (the primary first-party seam = absent integration evidence).
Only **FPCTX** was a real refactor (strip the 4 RETIRE reads).

---

## 3. THE REUSABLE TEST PATTERN (critical — reuse for any future consumer work)

The FM read/write seam and how to test it **without a live store** (the store is `DISABLED` locally
and in autobuild worktrees — `guardkit memory status` → `Status: DISABLED`):

- **Read seam:** `FleetMemoryClient.search(query, group_ids=[...])`
  ([`fleet_memory_client.py:227-322`](../../../guardkit/knowledge/fleet_memory_client.py#L227)) resolves
  each `group_id` via `fleet_memory_mapping.resolve()`: **migrate** → adds `payload_type` (+ always
  `"document"`) and `domain_tags`; **retire/unmapped** → contributes no filter → **whole-store semantic
  search** (which includes the harvest corpus). Then it calls the external
  `fleet_memory.retrieval.search(request, store)` (line 304) — **this is the edge to stub.**
- **Write seam:** `FleetMemoryClient.add_episode(name, episode_body, group_id=...)`
  ([`fleet_memory_client.py:324+`](../../../guardkit/knowledge/fleet_memory_client.py#L324)) → `resolve()`
  (retire/unmapped → `None` no-op) → `build_memory_episode()` → external
  `guardkit.memory.harvest_publisher.publish_episodes([episode])` — **that publish call is the edge to stub.**

**Canonical boundary-test helper** (mirror it; already copied into 3 test files):
`_install_fake_fleet_memory_retrieval(monkeypatch, *, context_block, coverage, captured)` in
[`tests/unit/knowledge/test_fleet_memory_client.py:67`](../../../tests/unit/knowledge/test_fleet_memory_client.py#L67)
— injects a fake `fleet_memory.retrieval` module via `monkeypatch.setitem(sys.modules, ...)` whose
`SearchRequest` stashes its kwargs into `captured["request"]`. Pair it with a **real** enabled
`FleetMemoryClient` (`enabled=True`, `_read_available=True`, `_nats_available=True`, `_store=object()`)
— **NOT a MagicMock** (that's the anti-pattern the whole wave fixed). Then assert
`captured["request"]["payload_types"] / ["domain_tags"]` — that proves the *real* mapping+shim ran.

**Two-test contract per consumer** (both baked into all 5 W1 tasks):
1. a **boundary test** (real client + only the external edge stubbed — runs everywhere), and
2. a **`@pytest.mark.live`** round-trip (the `live` marker is registered in `pytest.ini:37`) that
   `pytest.skip(...)`s when the store is disabled and is the **operator's post-merge proof** — the
   FEAT-MEM-08 `operator_handoff` split.

Group→payload examples (from `fleet_memory_mapping.py`, verified live): `task_outcomes`→
`build_outcome`+`document`/`[task]`; `architecture_decisions`→`adr`+`document`/`[system]`;
`failure_patterns`→`warning`+`document`/`[failure,pattern]`; `feature_specs`→`document`/`[feature,spec]`;
`turn_states`→`document`/`[state,turn]` (sorted). `patterns`/`role_constraints`/`quality_gate_configs`/
`implementation_modes`/`product_knowledge`/`command_workflows` = **retire** → empty filters.

---

## 4. What remains

### 4.1 Operator live-proof for W1 (⚙️ operator, post-merge)
Every W1 live test **skips** because the store is disabled. With the store up, run the real round-trips:
```bash
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/knowledge/ tests/unit/knowledge/ -v
```
(Env for the CLI: `set -a; . ./.env; set +a`.) This is the FEAT-MEM-08 MEM08-007-style acceptance gate.
The 5 W1 task files (in `tasks/backlog/mem09-w1-read-consumer-settle/`, all `status: in_review` with
Outcome notes) each list the exact live command in their "Operator verification" section.

### 4.2 §3.5 — infra (⚙️ operator-only, one-way, NOT a code session)
Per memory `[[falkordb-fleet-wide-not-guardkit-local]]` + `[[graphiti-cutover-qwen25-removal]]`:
- **FalkorDB decommission** (fleet-wide: 11.8k nodes / ~18 projects) — gated on a fleet-wide
  FalkorDB→fleet-memory migration; guardkit's 4,154 nodes were **not** migrated.
- **Drop the `qwen-graphiti` LLM** from the personal llama-swap config (KEEP the `embed` embedder —
  fleet-memory needs it); coordinate the global Qwen2.5 pull with the other 4 graph consumers
  (forge/jarvis/specialist-agent/study-tutor).
- The `scripts/graphiti-mcp*.sh` + `graphiti-mcp-config.yaml` server-stack tooling is **left for §3.5**
  (it manages the still-running FalkorDB; it has a stale in-comment ref to a deleted rule that goes away
  when §3.5 removes the stack).

### 4.3 Optional low-value follow-ups (surfaced during the wave, deliberately deferred)
- **Cosmetic legacy-name renames** (not required): the `graphiti_client` property on
  `feature_plan_context.py` (public, has call-sites — FPCTX Non-Goals said don't rename); `loader.graphiti`
  in `autobuild.py`; `self.graphiti` in `job_context_retriever`/`turn_state_operations`. All are FM-shim
  legacy names, not bugs.
- **Instrumentation telemetry enums** (`GraphitiQueryType`, `"digest+graphiti"` in
  `orchestrator/instrumentation/schemas.py` + `prompt_profile.py`) — **LEAVE**; renaming breaks
  stored-telemetry/profile continuity (a schema-migration task, low value).
- **The `graphiti.yaml`-copy / durable autobuild-session dataset sink** — a separate archival concern
  (the `.guardkit/autobuild/{task}/{player,coach}_turn_N.json` teacher-pairs are gitignored + machine-local;
  they're the coach fine-tune source, NOT `turn_states`-in-FM).
- **`tech_stack` param on `feature_plan_context.build_context`** is now unused (was only the stripped
  patterns read) — kept for API stability; a future cleanup could drop it + its callers.

---

## 5. Gotchas / must-knows (save the next session time)

1. **Single-task `guardkit autobuild task` does NOT work for this user** (long unattended loop, VS Code
   10-min timeout, GB10/harness dependency). **Use `/task-work TASK-XXX`** — runs the same quality gates
   in-session. The W1 task files' "Run" sections already say `/task-work`.
2. **The `/task-work` command spec is itself still graphiti-laden** (Phase 1.7 `graphiti-check`/MCP). It
   gracefully degrades to a no-op (graphiti is gone) — it's dead surface, not a blocker. (De-graphiti-ing
   the *command specs* was a prior session; this residual Phase-1.7 block could be a future §3-adjacent tidy.)
3. **W1 tasks live in a feature subfolder**, so `/task-work`'s flat glob won't find them — load the task
   file by path. Status was updated **in-place** (`backlog`→`in_review`) to keep the feature folder intact
   (not physically moved to `tasks/in_review/`).
4. **FPCTX's fix-loop lesson:** when you change a consumer's reads, grep **all** its test files
   (`test_<x>.py` AND `test_<x>_builder.py` AND `test_<x>_fleet_memory.py`) — I broke 2 tests in a second
   file I hadn't opened. `TestGraphitiQueries` in `test_feature_plan_context_builder.py` asserted the
   stripped groups *are* queried.
5. **Live tests need `nats_core`** for the write path (`build_memory_episode`). It IS importable in this
   venv (from `../fleet-memory` / the `memory` extra). If a minimal env lacks it, write-boundary tests
   would need a skipif.
6. **`fleet_memory` is importable** here (`../fleet-memory/src/fleet_memory`) — that's why the boundary
   tests can `monkeypatch.setitem(sys.modules, "fleet_memory.retrieval", ...)`.

---

## 6. Pre-existing red tests (7 — DO NOT chase)

```
tests/orchestrator/quality_gates/test_coach_validator_evidence_repos.py::TestRunEvidenceRepoTests::test_runs_declared_passing_suite
tests/orchestrator/test_agent_invoker_langgraph.py::TestSelectorRoutesToLangGraphHarness::test_env_var_routes_to_langgraph
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_passing_command
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_failing_command
tests/rules/test_no_dead_task_id_references.py::test_no_dead_task_id_references_in_orchestrator
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_testing_task_does_not_require_tests
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_alias_benchmark_maps_to_testing
```
Need the guardkitfactory/langchain stack or are env-only. See memory `[[main-has-preexisting-red-tests]]`.

---

## 7. Key pointers

- **This session's commits:** `git show 237f5d4c b5fd892e 7594c19e 8d4e021c 871d15ad 007a62e6 d34ba412 ab0f609c 906d61bc 1f94173a bc7d8bca 685ded20`.
- **§3.3 scoping (drives everything code-layer):** [`FEAT-MEM-09-3.3-code-scoping-2026-07-03.md`](FEAT-MEM-09-3.3-code-scoping-2026-07-03.md) (incl. §3.1 the two operator Fork A/B answers, and the confirmed decisions).
- **W1 task set + guide:** `tasks/backlog/mem09-w1-read-consumer-settle/` — `README.md`, `IMPLEMENTATION-GUIDE.md` (the shared shim-routing + two-test contract), 5 `TASK-MEM09-*.md` (each `in_review` with an Outcome).
- **Fleet-memory contract:** `docs/internals/commands-lib/memory-preamble.md`; the mapping Rosetta stone `guardkit/knowledge/fleet_memory_mapping.py`; the shim `guardkit/knowledge/fleet_memory_client.py`.
- **Prior de-graphiti handoff (superseded by this one):** `HANDOFF-FEAT-MEM-09-docs-and-code-degraphiti-2026-07-03.md`.
- **The rule the whole wave enforced:** `.claude/rules/per-task-green-is-not-feature-green.md` (mocked primary seam = absent integration evidence).
- **Agent memory to load:** `feat-mem-09-command-spec-fm-rewrite`, `FEAT-MEM-09 disposition map`, `falkordb-fleet-wide-not-guardkit-local`, `graphiti-cutover-qwen25-removal`, `main-has-preexisting-red-tests`, `git-workflow-commit-to-main`, `commit-with-explicit-pathspecs-shared-index`, `avoid-git-stash-shared-index-repo`.

---

## 8. If you continue — recommended next move

Nothing code-side is *blocking*. The highest-value next step is **operator-run**: enable the fleet-memory
store and run `pytest -m live tests/knowledge/ tests/unit/knowledge/` to convert the W1 live-skips into real
proof, then flip the 5 W1 tasks `in_review`→`completed` and move the folder to `tasks/completed/`. After
that, §3.5 infra is the only FEAT-MEM-09 work left, and it's operator-gated. Autonomous code sessions have
essentially exhausted the safe surface.
