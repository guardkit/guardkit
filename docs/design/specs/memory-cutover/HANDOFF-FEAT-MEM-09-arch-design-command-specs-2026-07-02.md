# HANDOFF — Fix `/system-design` & `/arch-refine` (and the graphiti-coupled command specs) — 2026-07-02

Pick-up doc for a **fresh conversation**. Assumes no prior context. The FEAT-MEM-09
graphiti **code + dependency** removal is **DONE and pushed** (see §1). This doc is the
follow-up the operator asked for: **fix the command specs that still reference the
deleted Graphiti classes / CLI / config.** Named targets: **`/system-design` and
`/arch-refine`**. But read §3 first — the same rot runs through the whole
architecture-command family and a shared preamble, so scope it deliberately.

---

## 0. TL;DR

- **Done (pushed to origin/main):** guardkit's Graphiti **implementation** is gone —
  54 modules deleted, `graphiti-core` dropped, docs + cosmetic sweep. 5 commits
  `b57e8815`→`9f3472ba`. Suite green (only 8 pre-existing fails). See §1.
- **This task:** the `installer/core/commands/*.md` **command specs** (agent-executed
  markdown) still tell the agent to use `SystemDesignGraphiti` / `SystemPlanGraphiti`
  (deleted classes), `get_graphiti()` (deleted), `guardkit graphiti add-context`
  (deleted CLI), and `.guardkit/graphiti.yaml enabled:` (retired stub) via a shared
  `graphiti-preamble.md`. The specs **degrade to markdown-only at runtime** (the
  availability check now always resolves `graphiti_available = false`, so the agent
  takes the fallback branches), so they are **misleading, not hard-broken** — but they
  reference dead symbols and a dead CLI, and their **spec tests assert the graphiti
  text is present**, so nothing has flagged the rot.
- **Decision to make with the operator (§4):** for each target command, **rewrite to
  fleet-memory**, **simplify to markdown-only**, or **retire** — and **how wide**
  (just the 2 named commands, the whole family, and/or the shared preamble).
- **Recommended:** markdown-only simplification for `/system-design` + `/arch-refine`
  (drop the graphiti knowledge-graph integration entirely; keep the design/ADR
  markdown-artefact generation), update their 2 spec tests, and rewrite the shared
  `graphiti-preamble.md` into a short "memory is fleet-memory / markdown-only" note so
  the other 10 consumers stop pointing at dead Tier-1/Tier-2 graphiti checks. Confirm
  before starting — it touches user-facing command specs.

---

## 1. Exact current state (2026-07-02) — cutover is DONE

`origin/main` (`git log --oneline`, newest first):
```
9f3472ba refactor(FEAT-MEM-09): WS-2c/W4 cosmetic graphiti->memory cleanup   <- me
48556470 qa verifier research plus DF006                                     <- parallel session (Richard)
b94c330c docs(FEAT-MEM-09): WS-2c/W4 update knowledge-capture docs to graphiti-removed  <- me
73ee16f7 build(FEAT-MEM-09): WS-2c drop graphiti-core dependency             <- me
c40324d9 refactor(FEAT-MEM-09): WS-2c/W3b delete graphiti implementation     <- me
b57e8815 refactor(FEAT-MEM-09): WS-2c/W3a de-graphiti surviving CLI consumers <- me
4575be0b docs(FEAT-MEM-09): WS-2c/W3 pickup handoff
```
- **HEAD == origin/main** (in sync, nothing to push).
- Working tree clean **except** `D docs/state/TASK-TEST-WORKFLOW/test_state.txt`
  (unrelated, some other machine deleted it — **never stage it**), plus untracked
  `.claude/hooks/.state/`, `docs/history/`, `tasks/backlog/memory-cutover/`.
- **`graphiti_core` is uninstalled** from the `.venv` (`import graphiti_core` →
  ModuleNotFoundError; `import falkordb` OK). `falkordb>=1.6,<2` is now a direct dep.
- **Suite:** `pytest -o addopts="" -p no:cacheprovider tests/` → 12497 passed,
  **8 pre-existing failures** (allowlist in §7), 0 new. Collection clean (13962).

**Shared-repo hazard is REAL and active.** A parallel session (author "Richard
Woollcott", same user) pushed `48556470` mid-session. Also `stash@{0}` holds a
parallel session's **TASK-BDDW-001** work (`git stash list`) — **do not pop/drop it**.
**Never `git stash`** in this repo (shared stack — see memory
`avoid-git-stash-shared-index-repo`). Commit with **explicit pathspecs** and verify
`git diff --cached --name-only` before every commit (memory
`commit-with-explicit-pathspecs-shared-index`).

---

## 2. What is broken (the symptom)

The **command specs** under `installer/core/commands/` are markdown that the agent
reads and executes for slash commands. Several still instruct the agent to use Graphiti
primitives that **no longer exist**:

| Dead thing the specs reference | Deleted by | Status now |
|---|---|---|
| `SystemDesignGraphiti`, `SystemPlanGraphiti` (`.search_design_context()`, `.has_architecture_context()`) | W1b `60ebde5d` (`planning/graphiti_design.py`, `planning/graphiti_arch.py`) | gone |
| `get_graphiti()` | W3b `c40324d9` (`knowledge/graphiti_client.py`) | gone |
| `guardkit graphiti add-context` (+ the whole `guardkit graphiti` group) | W3b `c40324d9` (`cli/graphiti.py`) | gone |
| `.guardkit/graphiti.yaml` `enabled: true` availability flag | W4 `b94c330c` (slimmed to a retirement stub — no `enabled:` key) | always resolves false |
| `docs/internals/commands-lib/graphiti-preamble.md` (Tier-1/Tier-2 graphiti checks) | still present (8947 bytes) | describes dead checks |

**Runtime effect:** because `.guardkit/graphiti.yaml` no longer has `enabled: true`, the
specs' availability check sets `graphiti_available = false`, so the agent **should** take
the "markdown-only" fallback branches and skip the graphiti seeding/prereq steps. So the
commands mostly **degrade gracefully** rather than crash — but the spec text is wrong,
points at a dead CLI, and will confuse (or mislead an agent into trying a dead class).

**Why nothing flagged it:** the spec tests (`tests/unit/commands/test_*_spec.py`) only
assert on the **markdown text** — e.g. `test_system_design_spec.py:59-62` asserts
`"SystemPlanGraphiti" in spec_content`. They pass precisely *because* the dead reference
is still in the file. So rewriting a spec will **fail its spec test** until you update the
test too.

---

## 3. The verified surface (trust these counts — grepped 2026-07-02)

**The operator named `/system-design` + `/arch-refine`:**
- `/system-design` → `installer/core/commands/system-design.md` — **~40 graphiti refs**
  (Phase 5 "Graphiti Seeding", `guardkit graphiti add-context ×3`, `SystemDesignGraphiti`
  seeding class, `SystemPlanGraphiti` prereq check at :45, availability gates, error paths,
  `pip install guardkit-py[graphiti]` at :1228).
- `/arch-refine` → `installer/core/commands/arch-refine.md` — **~62 graphiti refs**
  (`guardkit graphiti add-context ×4` at :424/:428/:822/:826, `sanitise_for_graphiti()`
  note at :418, "Graphiti seeding" step at :913, availability gates).

**The SAME rot is in the rest of the family** (the operator did not name these — decide
scope in §4):
- `system-arch.md` — **65 refs**   ·   `system-plan.md` — **50 refs**
  · `design-refine.md` — **50 refs** (this is `/design-refine`, distinct from `/arch-refine`)
  · `system-overview.md` — refs too (but `/system-overview` was **retired** in W1b — the
  spec file lingers; may just delete it).

**Shared preamble — high leverage:** `docs/internals/commands-lib/graphiti-preamble.md`
is referenced by **12 command specs**: system-overview, system-design, context-switch,
impact-analysis, **task-work**, system-arch, arch-refine, **feature-plan**, **task-complete**,
system-plan, **task-review**, design-refine. It documents the Tier-1 (`read graphiti.yaml
enabled:`) / Tier-2 (graphiti connectivity) availability pattern. Rewriting this ONE file
into a "memory is fleet-memory, env-driven; degrade to markdown-only" note fixes the
availability-check pattern for all 12 at once (the task-*/feature-* commands already
degrade fine; they just shouldn't cite a graphiti preamble).

**Spec tests that will need updating** (assert the graphiti text):
- `tests/unit/commands/test_system_design_spec.py` (34 graphiti/Graphiti refs; e.g.
  `test_spec_uses_graphiti_arch_for_prerequisite` asserts `"SystemPlanGraphiti" in spec`).
- `tests/unit/commands/test_arch_refine_command_spec.py` (grep it — same shape).
- (family, if in scope) `test_system_arch_command_spec.py`, `test_design_refine_spec.py`.

**Surviving planning code (markdown-artefact generators — the "use instead" set):**
`guardkit/planning/{system_plan.py (run_system_plan, async), architecture_writer.py,
arch_spec_parser.py, design_writer.py (DesignWriter — kept, orphaned), complexity_gating.py,
mode_detector.py, context_switch.py}`. None import graphiti (verified — the whole cutover
suite is green). `/system-plan` has a Python entrypoint `run_system_plan()`;
`/system-design` and `/arch-refine` are **agent-executed markdown specs** (no Python
`run_*` for them), so "fixing" them = editing the markdown + their spec tests.

---

## 4. The decision to make with the operator (do this FIRST)

Two axes. **Confirm both before editing** — these are user-facing command specs.

**Axis A — per-command disposition:**
1. **Markdown-only (recommended)** — strip ALL graphiti (seeding phases, `guardkit
   graphiti add-context`, `SystemDesignGraphiti`/`SystemPlanGraphiti`, `get_graphiti()`,
   `graphiti_available` gating, `[graphiti]` extra). Keep the design/ADR/contract
   **markdown artefact** generation (that is the actual deliverable; the knowledge-graph
   seeding was always the optional tail). Simplest, lowest-risk, matches how the commands
   already run today (degraded).
2. **Rewrite to fleet-memory** — replace graphiti seeding with `guardkit memory
   capture-outcome` / `mcp__fleet_memory__memory_write_payload` and the prereq/search
   with `guardkit memory search` / `mcp__fleet_memory__memory_search`. More faithful to
   the original intent, but fleet-memory's payload model is not a drop-in for the old
   design-artefact groups (`project_design`, `api_contracts`, `project_architecture`),
   so this needs a payload-shape design pass. Bigger.
3. **Retire the command** — if `/system-design` and/or `/arch-refine` are not actually
   used. Delete the spec + its skill dir under `.claude/commands/` (if present) + the
   spec test. Check usage with the operator.

**Axis B — scope:**
- **Just the 2 named** (`/system-design`, `/arch-refine`) — smallest.
- **The family** (also `system-arch`, `system-plan`, `design-refine`; delete the retired
  `system-overview.md`) — consistent, larger.
- **+ the shared `graphiti-preamble.md`** (recommended regardless) — rewrite it once so
  all 12 consumers stop citing dead graphiti checks. Low-risk, high-leverage.

**Recommended plan:** Axis A option 1 (markdown-only) for `/system-design` +
`/arch-refine`; **+** rewrite `graphiti-preamble.md` to a fleet-memory/markdown note; flag
the rest of the family as a fast follow. Get the operator to confirm markdown-only vs
fleet-memory before you start.

---

## 5. Execution recipe (once the decision is made)

Per target command (assuming **markdown-only**):
1. `grep -n -i graphiti installer/core/commands/<cmd>.md` — every hit is a delete/rewrite site.
2. Remove the "Graphiti availability" preamble references, the `graphiti_available`
   variable and both branches (keep only the markdown/glob branch), the "Phase N:
   Graphiti Seeding" / "Graphiti Persistence" sections, the `guardkit graphiti
   add-context` command blocks, the `SystemDesignGraphiti`/`SystemPlanGraphiti`
   prerequisite/search steps, the `[graphiti]` install hints, and the graphiti error-path
   sections. Keep the design/ADR/contract markdown generation, the C4 review gate, the
   user-approval gates, the file-tree summary.
3. Replace the "prerequisite: architecture context via SystemPlanGraphiti" with a
   **filesystem** check (Glob `docs/architecture/**` / `docs/design/**`) — the fallback
   the spec already documents.
4. Update the matching `tests/unit/commands/test_<cmd>_spec.py`: delete/replace the
   assertions that require graphiti text (`SystemPlanGraphiti`, `graphiti add-context`,
   `graphiti_available`, `pip install ...[graphiti]`), keep the assertions on the
   surviving structure (prereq gate exists, `/system-arch` chain ref, bounded-contexts,
   ADR/API-contract sections, user-approval gate).
5. If rewriting `graphiti-preamble.md`: replace the Tier-1/Tier-2 graphiti checks with a
   short "knowledge capture is fleet-memory (env-driven, `guardkit memory` /
   `mcp__fleet_memory__*`); if unavailable, continue markdown-only" note. Then either
   update the 12 consumers' one-line references or leave them (they'll now cite a correct
   note). Consider **renaming** it to `memory-preamble.md` (update the 12 refs) — optional.

**Gate after each command (fast — spec tests are markdown-only, no service needed):**
```
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider \
  tests/unit/commands/test_system_design_spec.py \
  tests/unit/commands/test_arch_refine_command_spec.py -q
```
Then confirm no dead refs remain:
```
grep -rn "SystemDesignGraphiti\|SystemPlanGraphiti\|get_graphiti\|guardkit graphiti\|graphiti-preamble\|\[graphiti\]" \
  installer/core/commands/system-design.md installer/core/commands/arch-refine.md
```
Full-suite gate before commit (must stay at the 8 pre-existing fails, §7):
```
.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider --timeout=120 -q --tb=no tests/ | tail -3
```

---

## 6. Commit / push hygiene (shared repo!)

- Branch is `main`; user commits directly to main (memory `git-workflow-commit-to-main`).
- **Explicit pathspecs**: `git add installer/core/commands/... tests/unit/commands/...`
  then `git diff --cached --name-only` (must be exactly your files; **no**
  `docs/state/TASK-TEST-WORKFLOW/test_state.txt`), then
  `git commit -m ... -- <paths>`.
- `git fetch` before push (a parallel session may have advanced origin — it did this
  session). Push is a fast-forward if origin hasn't diverged; if it has, the parallel
  commits are disjoint files → clean.
- End commit messages with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## 7. Pre-existing red tests — DO NOT chase (verified identical on pre-W3 `4575be0b`)

The full suite has **8 failures unrelated to any of this** (proven pre-existing via a
`git worktree` at `4575be0b`). Your acceptance = "still exactly these 8, zero new":
```
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_testing_task_does_not_require_tests
tests/unit/test_autobuild_orchestrator.py::TestResolveTestsRequired::test_alias_benchmark_maps_to_testing
tests/orchestrator/quality_gates/test_coach_validator_evidence_repos.py::TestRunEvidenceRepoTests::test_runs_declared_passing_suite
tests/orchestrator/test_agent_invoker_langgraph.py::TestSelectorRoutesToLangGraphHarness::test_env_var_routes_to_langgraph
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_passing_command
tests/orchestrator/test_evidence_repos.py::TestRunRepoTests::test_failing_command
tests/rules/test_no_dead_task_id_references.py::test_no_dead_task_id_references_in_orchestrator
tests/test_graphiti_navigation.py::TestNavigationIntegration::test_mkdocs_can_build
```
(`test_graphiti_navigation.py` tests `mkdocs.yml` nav for `guides/graphiti-integration-guide.md`
etc. — docs that still exist; it's a pre-existing mkdocs-strict failure, not yours.
`test_no_dead_task_id_references` = the dangling-task-id lint, pre-existing per memory
`main-has-preexisting-red-tests`.)

---

## 8. Acceptance

- [ ] Operator confirmed disposition (markdown-only / fleet-memory / retire) + scope.
- [ ] `/system-design` (`system-design.md`) + `/arch-refine` (`arch-refine.md`) rewritten
      per the decision; **no** references to `SystemDesignGraphiti`, `SystemPlanGraphiti`,
      `get_graphiti`, `guardkit graphiti`, `[graphiti]` extra remain.
- [ ] Their spec tests (`test_system_design_spec.py`, `test_arch_refine_command_spec.py`)
      updated + green.
- [ ] (recommended) `graphiti-preamble.md` rewritten to a fleet-memory/markdown note (or
      renamed `memory-preamble.md` with the 12 refs updated).
- [ ] (if scoped in) `system-arch` / `system-plan` / `design-refine` done;
      `system-overview.md` spec deleted (command already retired W1b).
- [ ] Full suite still exactly the 8 pre-existing fails (§7); collection clean.
- [ ] Committed with explicit pathspecs; pushed after `git fetch`.

---

## 9. Key pointers

- **Deleted-class origin:** `git show 60ebde5d` (W1b) — `planning/graphiti_arch.py`
  (`SystemPlanGraphiti`, `has_architecture_context`), `planning/graphiti_design.py`
  (`SystemDesignGraphiti`, `search_design_context`). Read these if you need to know what
  the old prereq/search did before deciding the markdown/fleet-memory replacement.
- **This cutover's commits:** `git show b57e8815 c40324d9 73ee16f7 b94c330c 9f3472ba`.
- **Prior handoff (the code cutover, now done):**
  `docs/design/specs/memory-cutover/HANDOFF-FEAT-MEM-09-WS2c-W3-2026-07-02.md`.
- **Disposition map:** `docs/design/specs/memory-cutover/FEAT-MEM-09-consumer-disposition-map.md`.
- **Env for `guardkit memory` (if you go fleet-memory route):**
  `set -a; . ./.env; set +a; export FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory`
  then `guardkit memory status` (→ REACHABLE) / `guardkit memory search --help`
  (options: `--token-budget`, `--payload-types`, `--domain-tags`; NO `--limit`).
- **Agent memory to load:** `avoid-git-stash-shared-index-repo`,
  `commit-with-explicit-pathspecs-shared-index`, `check-existing-tasks-before-filing`,
  `main-has-preexisting-red-tests`, `git-workflow-commit-to-main`,
  `graphiti-cutover-qwen25-removal`, `falkordb-fleet-wide-not-guardkit-local`.
- **Test runner:** `.venv/bin/python -m pytest -o addopts="" -p no:cacheprovider <paths>`
  (pytest.ini adds `--cov`; `-o addopts=""` strips it).
