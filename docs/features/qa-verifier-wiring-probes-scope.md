# Feature Scope: QA-Verifier Piece #2 — Stack-Agnostic Wiring Evidence

**Status:** Draft for `/feature-plan` → autobuild. **Replaces** the earlier Python-`ast` monolith draft that previously occupied this file (the stack-blindness anti-pattern; prior content in git history).
**Date:** 2026-06-12. **Estimated complexity:** ≥7 (multi-stack, cross-repo, new dependency, one deterministic hard-gate). Build per-probe / per-stack across waves (see §6).

---

## 1. Problem + the stack-agnostic-by-default principle

The dominant autobuild failure mode is **"90% complete, wiring undone, green over dead code."** A Player authors a new symbol, its unit tests are green, the Coach approves — but the running application can never reach the code: it was never registered into a composition root, never referenced by a non-test peer, or the acceptance test that "proves" it silently mocks the very seam it claims to exercise, or a tagged Gherkin scenario never produced an executed testcase at all. The unit oracle reports "all green" over code the running app will never execute. This is the inverse of the absence-of-failure family (`.claude/rules/absence-of-failure-is-not-success.md`): there the oracle reports "0 failures over 0 attempts"; here it reports "all green" over unreachable code.

The **superseded draft** answered this with a single-language `ast.parse` monolith (`PythonWiringInspector` day-one, "stack-agnostic generality is a LATER layer"). That is precisely the stack-blindness the newly-seeded governing rule forbids:

> **`.claude/rules/stack-plugin-architecture.md` (seeded this session):**
> Stack-agnostic mechanism is the **DEFAULT**; a per-stack plugin is a **LAST RESORT**, ONLY for irreducibly stack-specific **EXECUTION**. Static analysis (reachability, mock-seam, symbol/reference extraction) uses **ONE** multi-language parser (tree-sitter) + thin **DECLARATIVE** per-language dialect descriptors (**DATA**, not code plugins). Execution (running pytest-bdd vs reqnroll vs cucumber-js) is the only legitimate plugin case. Unsupported stack → **ABSENT-SIGNAL** via a status discriminator, never a false pass.

This rewrite obeys that mandate. All **analysis** (UNWIRED_PATH, MOCKED_SEAM) is one tree-sitter `WiringAnalyzer` over a multi-language Concrete Syntax Tree, parameterized by declarative per-language **dialect descriptors (DATA)**. The one concern that is irreducibly **execution** (SPEC_GAP's "which scenarios actually ran") **consumes** the existing factory `BDDRunResult` rather than re-parsing junit/TRX/cucumber-json per stack. Day-one language parity: **python, javascript, typescript, c_sharp** — all precompiled in `tree-sitter-language-pack`.

This scope **salvages only** the verified integration seams and acceptance criteria from the superseded draft. It **discards** the `PythonWiringInspector`, the `ast`-based `_SymbolIndex`, and the "stack-agnostic is a LATER layer" framing — that framing *is* the anti-pattern.

---

## 2. Relationship to the QA-Verifier program

This is **piece #2 of three** in the QA-Verifier program:

| Piece | Concern | In/Out |
|---|---|---|
| **#1** | Fine-tuned Coach (verdict synthesis model) | **OUT** of this scope |
| **#2** | **Stack-agnostic wiring evidence** (this scope) | **IN** |
| **#3** | BDD glue-policy enforcement | **OUT** of this scope |

This piece produces **evidence** (three new fields on `CoachEvidenceBundle`) that the synthesis Coach — whether today's LLM Coach or piece #1's fine-tuned Coach — weighs. It is decoupled from #1: the evidence is rendered into the `<evidence_bundle>` JSON regardless of which model consumes it. It is decoupled from #3: it observes wiring/mock/spec state but does not enforce glue-file naming policy.

**Hard dependency:** SPEC_GAP consumes `BDDRunResult`, which **TASK-HMIG-BDDWIRE** (`tasks/backlog/TASK-HMIG-BDDWIRE-wire-factory-bdd-plugins-into-coach.md`) plumbs into the Coach evidence path. SPEC_GAP must be sequenced **behind** BDDWIRE (see §6).

---

## 3. The stack-agnostic WiringAnalyzer (tree-sitter) + dialect descriptors as DATA

### 3.1 ONE analyzer, many languages

A single language-independent `WiringAnalyzer` operates over tree-sitter Concrete Syntax Trees. The **only** stack-specific input is a thin **declarative dialect descriptor (DATA)**. Adding a language is **a descriptor entry, not a code plugin** — the rule's mandate verbatim.

`tree-sitter` and `tree-sitter-language-pack` are **new dependencies** (verified absent from both `guardkit/pyproject.toml` and `guardkitfactory/pyproject.toml`). The pack ships precompiled grammars including python/javascript/typescript/csharp, so four-language parity is free at day one. **API path (pinned — verified end-to-end on the aarch64 runner):** load the grammar with `tree_sitter_language_pack.get_language(name)`, parse with the **standalone** `tree_sitter.Parser(lang)` (parse takes **bytes**; exposes `tree.root_node` *property* + `node.type`), and query with `tree_sitter.Query(lang, sexpr)` + `QueryCursor(query).captures(root)` (tree-sitter 0.25.x moved `captures` onto `QueryCursor`). **Do NOT use the pack's `get_parser()`** — it returns vendored bindings where `Tree.root_node` is a *method* and `Node` has no `.type`, incompatible with the standalone Query/Node API this design assumes.

**Fidelity caveat (documented in the `WiringAnalyzer` docstring):** tree-sitter yields a **Concrete Syntax Tree, NOT full semantic resolution**. Reachability is a **syntactic identifier-match heuristic across files** — the same fidelity as the prior python-ast plan, now multi-language. It cannot resolve aliased imports, dynamic dispatch, string-keyed registries, reflection-based DI, or entry-points outside the worktree. The FP/FN posture deliberately **biases toward WIRED** (substring fallback counts as referenced; `__all__` / entry-point-manifest names count as wired) so the heuristic produces accepted false-negatives, never false-red false-positives.

### 3.2 The dialect descriptor is DATA

A dialect is a frozen dataclass `WiringDialect`, one record per language, registered in a per-language module under `wiring/dialects/`. Every field is DATA — tree-sitter S-expression query strings and pattern lists, no executable plugin code:

```python
@dataclass(frozen=True)
class WiringDialect:
    language: str                        # "python" | "javascript" | "typescript" | "c_sharp"
    ts_language_name: str                # canonical pack key: "python"|"javascript"|"typescript"|"csharp" (use "csharp", NOT "c_sharp")
    file_globs: tuple[str, ...]          # ("**/*.py",) / ("**/*.ts","**/*.tsx") / ("**/*.cs",)
    public_symbols_query: str            # S-expr: public top-level def/class nodes + @name
    references_query: str                # S-expr: identifier / member-access nodes
    registration_queries: tuple[str, ...]# S-expr per composition-root binding shape
    mock_call_query: str                 # S-expr: mock/patch calls + @target literal arg
    test_path_markers: tuple[str, ...]   # ("test_","_test",".spec.","Tests/")
    acceptance_path_markers: tuple[str, ...] # ("features/","tests/integration/","/e2e/")
    external_mock_allowlist: tuple[str, ...] # ("httpx","requests","boto3","openai",...)
    external_mock_path_roots: tuple[str, ...]# ("adapters/","clients/","_external/")
    script_manifest_files: tuple[str, ...]   # ("pyproject.toml",)/("package.json",)/("*.csproj",)
```

**Day-one descriptor content (verified composition roots where applicable):**

- **PYTHON** — `public_symbols_query` captures module-level `function_definition`/`class_definition` names; honour `__all__` and leading-underscore-as-private. `registration_queries`: Click `cli.add_command(X)`, `@<group>.command()` decorator, `registry.register(...)`, FastAPI `include_router(...)`. **Composition root verified:** `guardkit/cli/main.py:108-132` (`cli.add_command(autobuild|feature|graphiti|init|review|system_plan|system_overview|impact_analysis|context_switch|task)`), `@cli.command()` decorators (main.py:140), and `pyproject.toml` `[project.scripts]` `guardkit-py = guardkit.cli.main:main`.
- **JAVASCRIPT + TYPESCRIPT** — two descriptor records sharing query bodies where grammars overlap (tsx/jsx extensions on the ts record). `public_symbols_query` captures `export_statement`-wrapped `function_declaration`/`class_declaration`/`lexical_declaration`. `registration_queries`: Express `app.use(...)` / `router.get|post(...)`, NestJS `@Module({providers:[...]})`, React `<Route element={<X/>}>`. `script_manifest_files`: package.json (`bin`, `main`).
- **C_SHARP** — captures `public`/`internal` `method_declaration`/`class_declaration`. `registration_queries`: .NET DI `services.AddScoped|AddSingleton|AddTransient<X>()`, minimal-API `app.MapGet|MapPost|MapGroup(...)`, FastEndpoints reachable-by-convention (treat any `public class : Endpoint<...>` as WIRED). `script_manifest_files`: `*.csproj` (`<StartupObject>`), Program.cs.

**Adding a new language = add one `WiringDialect` record (queries + pattern lists), zero analyzer code change.**

---

## 4. The three evidences

All three are gated to **FEATURE / REFACTOR / INTEGRATION** task types only (skip SCAFFOLDING / INFRASTRUCTURE / DOCUMENTATION / TESTING per `.claude/rules/anti-stub.md` — those legitimately produce un-wired stubs). All three honour the **absent-vs-empty discipline** `gathering_status` already enforces: a `findings:[]` with a positive status is a **real WIRED/clean verdict**, distinct from the field being `None` (probe didn't run).

The **authored set** is the presence-based fallback at `coach_validator.py:775-783` (inline inside `_compute_own_authored`, **not a reusable callable** — the build must extract a shared `_authored_set(task_work_results)` helper OR duplicate the ~9-line fallback): `files_authored` when the key is present, else `files_created ∪ files_modified`. It MUST NOT read the git-enriched `files_modified` (peer-contaminated, per TASK-FIX-CC-COND).

### 4.1 UNWIRED_PATH (tree-sitter analysis — advisory)

**Detects:** a public symbol (function/class/exported const/CLI command) the Player **authored this turn** with **green unit tests**, but with **zero non-test, non-self-module reference** anywhere in the worktree **AND zero registration call** into a known composition root for the detected stack. The deliverable is dead code: reachable only from its own tests.

**Pipeline (identical for every language):** (1) gate on task_type; (2) select targets = authored source files (per dialect `file_globs`) that exist under worktree, excluding test files; (3) parse each target with the dialect grammar — on parse error, skip the target, never raise; (4) extract public symbols via `public_symbols_query` + `is_public` predicate; (5) build a `_SymbolIndex` reference map by running `references_query` across all non-test, non-self files (ignoring `__pycache__`/`node_modules`/`bin`/`obj`/`.git`/`.guardkit`), with literal-substring grep fallback on parse-failed files (substring hit ⇒ referenced, biased WIRED); (6) detect registration via `registration_queries` + substring scan of `script_manifest_files`; (7) classify WIRED if referenced by ≥1 non-test non-self module OR named in a registration call; else emit one finding per UNWIRED public symbol.

### 4.2 MOCKED_SEAM (tree-sitter analysis — advisory)

**Detects:** acceptance/integration glue (BDD step defs under `features/` per `.claude/rules/bdd-per-task-glue.md`, or `tests/integration|acceptance|e2e/`) that **mocks/patches/stubs/fakes the very authored production seam** the scenario claims to verify — so the acceptance test goes green over un-wired code. Sibling of UNWIRED_PATH: UNWIRED_PATH detects the wiring is **absent**; MOCKED_SEAM detects the acceptance test **substitutes a fake** for it, hiding the absence.

**Pipeline:** for each authored acceptance file, parse → run the dialect's `mock_call_query` to capture mock-primitive calls + their literal target argument → **attribute** each target against the authored seam set → classify: target ∈ `external_mock_allowlist`/path-root ⇒ recorded under `external_mocks_ignored` (never flagged); target ∈ authored production seam ⇒ `severity:"warning"` finding; third-party-not-authored-not-allowlisted ⇒ `severity:"info"` (surfaced, not dropped). Mock primitives per dialect (DATA): python `patch(...)`/`patch.object`/`mocker.patch`/`monkeypatch.setattr`; js/ts `jest.mock`/`vi.mock`/`sinon.stub`; c_sharp Moq `new Mock<T>()`/`.Setup`, NSubstitute `Substitute.For<T>()`, FakeItEasy `A.Fake<T>()` (where `@target` is the generic TYPE arg, not a string literal — handled by the same attribution step against the seam set).

### 4.3 SPEC_GAP (consumes factory `BDDRunResult` — writes NO stack code)

**Detects:** a `@task:<TASK-ID>`-tagged Gherkin scenario that is **ground truth** (declared in a `features/**/*.feature` file) but **has no executed binding** — it never produced a passing/failing testcase in the run the stack's BDD plugin performed. Two members:
- **PER-SCENARIO gap** — a named tagged scenario absent from the executed set (**advisory**; name-matching carries FP risk).
- **WHOLE-FILE SILENT DESELECTION** — `ground_truth_count > 0` while the plugin reports **zero scenarios attempted** (the `-m @task` marker / per-task glue bound nothing). This is **absence-of-failure instance #2** (`scenarios_run==0` false-green) at scenario granularity, and is **the one case that hard-gates** (§5.3).

**Two agnostic halves, NEITHER writes per-stack code:**
- **Ground truth** is language-independent (Gherkin is Gherkin): a light tag-block-tracking scan of `.feature` files enumerates `Scenario:`/`Scenario Outline:` names whose own-or-inherited tag block contains `@task:<TASK-ID>`. ONE code path for all stacks — no dialect descriptor needed.
- **Executed evidence** is **CONSUMED, not computed**: it comes from the factory `BDDRunResult` produced by whichever plugin `guardkitfactory.bdd.discover(stack)` selected and ran (pytest-bdd / reqnroll / cucumber-js). `spec_gap = ground_truth − executed − pending`. The whole-file case is a pure count comparison (`ground_truth_count > 0 AND scenarios_attempted PRESENT-and-zero`), zero parse ambiguity.

> **VERIFIED BLOCKER (load-bearing open question, §10):** the current `BDDRunResult` (`bdd/plugin.py:43-66`) exposes **counts only** (`scenarios_attempted/passed/failed/skipped/errored`, `raw_report_path`, free-form `discoveries`) — it does **NOT** expose per-scenario executed **names** as a first-class field. Per-scenario diff is therefore impossible from the contract alone. Resolution must either (a) extend `BDDRunResult` with `executed_scenarios: list[{name, outcome}]` populated by each plugin (recommended; fold into TASK-HMIG-BDDWIRE so it is agnostic-by-construction), or (c) ship SPEC_GAP day-one with **only** the whole-file count check (the one hard gate needs only `scenarios_attempted`, already on the contract) and defer per-scenario findings. Option (b) — re-parsing `raw_report_path` (junit/TRX/JSON per stack) — is **forbidden** as the exact anti-pattern.

---

## 5. Integration

### 5.1 Bundle fields (`coach_evidence.py`)

Add **three sibling Optional fields** immediately after `tests: Optional[Dict[str, Any]] = None` at `coach_evidence.py:169` (so each probe's rollout, truncation, and guard wiring is independently testable), with docstring slots alongside lines 160-169:

```python
wiring: Optional[Dict[str, Any]] = None        # NEW — UNWIRED_PATH
mocked_seam: Optional[Dict[str, Any]] = None   # NEW — MOCKED_SEAM
spec_gap: Optional[Dict[str, Any]] = None      # NEW — SPEC_GAP
```

`to_dict()` (the `asdict` call at `coach_evidence.py:180-191`) needs **NO change** — `asdict` walks plain dict/list/str fields for free. **VERIFIED** by reading lines 160-191.

**Per-field dict shapes** (the guardkit→guardkitfactory seam returns a `WiringResult`/`MockSeamResult` whose `.to_dict()` produces these; guardkit stores the dict, never the dataclass, so `coach_evidence.py` keeps zero guardkitfactory import):

- `wiring`: `{status, dialect, language, targets_scanned, symbols_examined, findings: [{file, symbol, kind, module, lineno, registration_found: false, searched_refs, severity:"warning", pattern:"UNWIRED_PATH", why}], degraded_files}`
- `mocked_seam`: `{status, ran: bool, skip_reason?, dialect, findings: [{file, symbol, mock_kind, lineno, authored_this_turn: true, severity:"warning"|"info", why}], external_mocks_ignored}`
- `spec_gap`: `{status, ground_truth_count, executed_count, pending_count, findings: [{feature_file, symbol, severity, pattern:"SPEC_GAP", why}], whole_file_deselection: bool, bdd_plugin_name, executed_evidence:"full"|"partial"|"counts_only"}`

### 5.2 gather_evidence population point (`coach_validator.py`)

Populate all three fields at the **complete-path return only**: `coach_validator.py:2120-2135` (the single `return CoachEvidenceBundle(...)`, **VERIFIED** at lines 2120-2135 — probes run here after the independent-tests block). The partial returns at `2030`/`2058`/`2103` leave all three `None` — wiring is moot when honesty/gates already failed; **VERIFIED** those returns omit the fields. `detect_stack_template` (imported `coach_validator.py:64`, **VERIFIED**) supplies the language for dialect dispatch / unsupported-stack detection.

### 5.3 Render (`agent_invoker.py`)

`_render_evidence_bundle_section` (`agent_invoker.py:3098-3191`) JSON-dumps `bundle.to_dict()` at line 3178 — all three fields surface automatically. **Add findings-truncation** for `wiring.findings` / `mocked_seam.findings` / `spec_gap.findings` (keep first 20 + `"... and N more"`) mirroring the `bdd.discoveries` truncation at `agent_invoker.py:3138-3152` (**VERIFIED** pattern).

**Advisory guard sentence #7** appended to `_render_absence_of_failure_guards` after guard #6 (ends at `agent_invoker.py:3320-3332`, **VERIFIED**):

> "If wiring/mocked_seam/spec_gap findings are non-empty for a feature task, treat the named symbols as candidate dead code / suspect acceptance evidence and require evidence of registration / real-seam execution before approving; surface as feedback unless the Player demonstrates the wiring path."

### 5.4 The ONE deterministic hard-gate: SPEC_GAP whole-file deselection

UNWIRED_PATH and MOCKED_SEAM are **ADVISORY only** — no code override day one. Their reachability/attribution is a syntactic heuristic; a code override turning every heuristic finding into a turn-rejection would be a **false-red generator**, the exact harm `.claude/rules/path-string-mismatch-is-not-dishonesty.md` warns against (a low-fidelity oracle rejecting a turn it cannot prove wrong).

The **only** deterministic hard-gate is **SPEC_GAP whole-file deselection** — a pure count comparison (zero parse ambiguity), the documented false-green generator. NEW `_apply_spec_gap_absent_guard`, modelled **verbatim** on `_reconcile_absent_independent_test_signal` (`agent_invoker.py:5083-5191`, **VERIFIED**), wired at the same post-verdict seam (`agent_invoker.py:2233`, beside the COACHFG01 call):

- Fires **only** when `spec_gap.whole_file_deselection == True`.
- Overrides `approve → feedback`, prepends a `must_fix` `category:"absence_of_failure"` issue, re-persists `coach_turn_N.json` so Layer-4 late-approval reconciliation (`feature_orchestrator._check_late_approval`) cannot resurrect it.
- **None-safety mirrors `agent_invoker.py:5133-5139`**: no-op when `evidence_bundle is None`, `evidence_bundle.spec_gap is None`, or `whole_file_deselection` absent/falsey.
- **CRITICAL absent-key safety:** `whole_file_deselection` is set using `if "scenarios_attempted" in bdd_dict and bdd_dict["scenarios_attempted"] == 0 ...` — **never** `.get(..., 0)`, which coerces a missing key to 0 and fires a false-red. A missing key is UNKNOWN. (The factory `BDDRunResult.scenarios_attempted` is a non-Optional dataclass field, so it is always present once BDDWIRE lands — but a legacy/unsupported bundle lacking the key must never trip the gate.)

### 5.5 Placement + the guardkit←guardkitfactory seam

The `WiringAnalyzer` + dialect descriptors live in a **NEW** guardkitfactory subpackage, sibling of the proven `bdd/` and `harness/` subpackages (**VERIFIED** layout: `bdd`, `harness`, `__init__.py` present; **no `wiring/` yet**), consumed by guardkit exactly as TASK-HMIG-BDDWIRE consumes the BDD plugins:

- **NEW:** `guardkitfactory/src/guardkitfactory/wiring/__init__.py` — exports `WiringAnalyzer`, `WiringResult`, `WiringStatus`, `WiringDialect`, `analyze(...)`; side-effect import of `.dialects` registers built-ins.
- **NEW:** `guardkitfactory/src/guardkitfactory/wiring/analyzer.py` — the ONE stack-agnostic engine + `WiringResult`/`MockSeamResult`.
- **NEW:** `guardkitfactory/src/guardkitfactory/wiring/dialect.py` — `WiringDialect` frozen dataclass + plain `language → dialect` dict registry (inert DATA, no contract-gate).
- **NEW:** `guardkitfactory/src/guardkitfactory/wiring/parser.py` — a `get_language(lang)` + standalone `tree_sitter.Parser` cache over `tree-sitter-language-pack` (NOT the pack's `get_parser()`; see §3.1).
- **NEW:** `guardkitfactory/src/guardkitfactory/wiring/dialects/{python,javascript,typescript,c_sharp}.py` — one `WiringDialect(...)` literal each, registered at import.

**Public API** (mirrors `bdd.discover(stack, worktree)`):
`analyze_wiring(authored_files: list[str], worktree_path: Path, task_type: str, stack: StackProfile | None = None) -> dict | None`.

**guardkit→guardkitfactory seam:** `coach_validator` imports `from guardkitfactory.wiring import analyze_wiring` **lazily** with `try/except ImportError → all three fields None` (status-absent), so plain `pip install guardkit-py` (without `[autobuild]`) still works — the same one-way, lazy, optional pattern README documents for `LangGraphHarness`. guardkit stores the returned **dict**, never the dataclass, so `coach_evidence.py` keeps zero guardkitfactory import.

**Dependency add:** `tree-sitter` + `tree-sitter-language-pack` added to **guardkitfactory's core `dependencies`** (the package that owns the analyzer). NOTE (corrected): guardkitfactory has **no `[autobuild]` extra of its own** — that extra lives in *guardkit* (`guardkit/pyproject.toml`, which pulls in `guardkitfactory>=0.1,<1`), so guardkitfactory's core deps are already transitively gated behind guardkit's `[autobuild]` install. A dedicated guardkitfactory `[wiring]` extra is an acceptable tighter-gating alternative. Update guardkitfactory `[tool.setuptools] packages` (currently `guardkitfactory`, `guardkitfactory.bdd`, `guardkitfactory.bdd.plugins`, `guardkitfactory.harness`, `guardkitfactory.lib`) to add `guardkitfactory.wiring` + `guardkitfactory.wiring.dialects`.

### 5.6 Status discriminator (the absent-signal mechanism — prevents false pass)

Each result carries a `status`. **No status value EVER maps to "pass"** — the only positive verdict is `inspected`/`complete`/`ran` **with** `findings:[]`:

| status | meaning |
|---|---|
| `complete` / `inspected` / `ran` | analyzer ran, CST parsed, classification authoritative (empty findings = real positive) |
| `unsupported_stack` / `skipped_no_dialect` | detected language has NO registered dialect (Go, Rust day-two) → **ABSENT SIGNAL**, NEVER a pass — the load-bearing discriminator |
| `parse_degraded` | ≥1 file fell back to substring-grep; `degraded_files` populated; biased WIRED so degradation never manufactures a false UNWIRED |
| `skipped_no_targets` / `skipped_no_acceptance_files` / `skipped_no_features` | dialect exists but nothing to scan; absent ≠ pass |
| `partial_executed_evidence` / `counts_only` (SPEC_GAP) | executed names unavailable; per-scenario findings downgraded; only the whole-file count check is trustworthy |
| `error` | unexpected analyzer exception, caught at the seam → fail-open to absent-signal, NEVER blocks the turn |

`analyze_wiring` returns **`None`** (not a status dict) only for the task-type gate and the zero-authored-targets case — both are "probe legitimately did not run", distinguishable from "ran and found nothing." An `unsupported_stack` returns a **NON-`complete`** status with empty findings, so a downstream consumer that naively reads `findings == []` as "all wired" is corrected by the status check — exactly the false-green failure mode the rule warns against. SPEC_GAP inherits `unsupported_stack` for free when `guardkitfactory.bdd.discover(stack)` returns `None`.

---

## 6. Sequencing

**TASK-HMIG-BDDWIRE lands FIRST.** It wires the factory BDD plugins (`BDDRunResult`) into the Coach evidence path. SPEC_GAP **depends** on it (consumes `BDDRunResult.scenarios_attempted` + executed names). Building SPEC_GAP against the legacy pytest-hardcoded `bdd_runner.py` would re-import the absent-`scenarios_attempted` hazard.

Recommended decomposition (per-probe / per-stack waves):

- **Wave 0** — `tree-sitter` + `tree-sitter-language-pack` dep add; `WiringAnalyzer` engine; python/js/ts/c# dialects; `WiringResult`/`MockSeamResult`/`WiringStatus`. Agnostic core, fixture-tested, no guardkit integration.
- **Wave 1** — bundle fields (`coach_evidence.py:169`); gather_evidence population (`coach_validator.py:2120`); render + truncation (`agent_invoker.py:3098`); UNWIRED_PATH wired through the guardkit→factory seam.
- **Wave 2** — MOCKED_SEAM (analyzer + dialects already exist; adds the mock-seam scan path + field wiring). Not blocked on BDDWIRE.
- **Wave 3** — SPEC_GAP (Gherkin enumerator + `BDDRunResult` consume) + `_apply_spec_gap_absent_guard`. **GATED on TASK-HMIG-BDDWIRE merged.**

Overall order: **TASK-HMIG-BDDWIRE → Wave 0 → Wave 1 → Wave 2 → (BDDWIRE done?) → Wave 3.**

---

## 7. Scope boundaries

- **Plugins ONLY for execution.** No new per-stack **analysis** code paths. UNWIRED_PATH/MOCKED_SEAM are ONE analyzer + DATA dialects. The only per-stack execution code is the **existing** `bdd/` plugin layer, which SPEC_GAP **consumes** — it does not duplicate it.
- **No new per-stack plugins** introduced by this feature. New languages are descriptor records, not plugins.
- **QA-Verifier #1 (fine-tune)** and **#3 (glue-policy)** are **OUT**.
- **No code override** for UNWIRED_PATH / MOCKED_SEAM day one. Promotion to a load-bearing override is a deliberate LATER decision gated on field FP-rate telemetry, and even then only on the narrowest sub-case.
- **Not redesigned:** the verified, unchanged integration seams (`coach_evidence.py` `to_dict`, the `coach_validator.py:2120` complete-path return shape, `agent_invoker.py` render/guard archetype, `detect_stack_template`). Reuse, do not redesign.
- **Not consumed:** the legacy pytest-hardcoded `bdd_runner.py`. SPEC_GAP consumes the factory `BDDRunResult` via BDDWIRE.

---

## 8. Acceptance criteria

**Per-pattern positive + no-false-positive controls, ON MULTIPLE STACKS:**

- **AC-001 (UNWIRED positive — Python):** a fixture authoring an un-registered public CLI-command-shaped symbol with green unit tests yields **exactly one** `wiring` finding (`kind:"cli_command"|"function"`, `registration_found:false`, `searched_refs:0`, `status:"complete"`).
- **AC-002 (UNWIRED wired-control — Python):** a symbol registered via `cli.add_command(...)` (mirroring `guardkit/cli/main.py:108-132`) yields `wiring.findings:[]`, `status:"complete"` (no false positive).
- **AC-003 (UNWIRED positive + control — C#):** an un-registered `public` method/class yields one finding; a `services.AddScoped<X>()`-registered one yields `findings:[]` — proving multi-stack parity.
- **AC-004 (UNWIRED positive + control — TS/JS):** an un-exported-into-route symbol yields one finding; an `app.use(...)`/`<Route>`-registered one yields `findings:[]`.
- **AC-005 (MOCKED_SEAM positive — Python):** an acceptance file that `patch(...)`-es an authored-this-turn production seam yields one `mocked_seam` finding (`authored_this_turn:true`, `severity:"warning"`).
- **AC-006 (MOCKED_SEAM external-control — Python):** an acceptance file mocking `httpx`/`boto3` (allow-listed) yields `findings:[]`, target recorded under `external_mocks_ignored`.
- **AC-007 (MOCKED_SEAM positive — C#):** a `new Mock<IAuthoredSeam>()` against an authored interface yields one finding; a `Mock<HttpClient>` (allow-listed) does not.
- **AC-008 (task-type gate):** a SCAFFOLDING / DOCUMENTATION task, or a turn authoring zero non-test source targets, returns `None` for all three fields (probe did not run).
- **AC-009 (unsupported-stack → absent-signal):** a stack whose language has NO dialect (e.g. Go) returns `status:"unsupported_stack"`/`"skipped_no_dialect"` with `findings:[]`; a downstream reader checking `status` treats it as **unverified, NOT a pass**. Assert the status is **not** `complete`.
- **AC-010 (parse-degraded biases WIRED):** a target whose CST parse errors falls back to substring grep, sets `status:"parse_degraded"`, populates `degraded_files`, and never manufactures a false UNWIRED finding.
- **AC-011 (SPEC_GAP per-scenario positive):** a `@task`-tagged scenario in ground truth but absent from the executed set yields one advisory `spec_gap` finding (`pattern:"SPEC_GAP"`).
- **AC-012 (SPEC_GAP absent-`scenarios_attempted` control):** a `BDDRunResult` whose `scenarios_attempted` key is **absent** does NOT set `whole_file_deselection` and does NOT fire the hard gate (absent ≠ 0; `.get(...,0)` is forbidden).
- **AC-013 (SPEC_GAP hard-guard red→green reproducer):** `ground_truth_count > 0` with `scenarios_attempted` **present-and-zero** → `whole_file_deselection:true` → `_apply_spec_gap_absent_guard` overrides an `approve` to `feedback`, prepends a `must_fix` `category:"absence_of_failure"` issue, and re-persists `coach_turn_N.json`. (Red: without the guard, the approve stands.)
- **AC-014 (hard-guard None-safety):** the guard is a **no-op** when `evidence_bundle is None`, `evidence_bundle.spec_gap is None`, or `whole_file_deselection` absent/falsey — mirroring `agent_invoker.py:5133-5139`.
- **AC-015 (absent-vs-empty discipline):** for every probe, `findings:[]` with a positive status is asserted distinct from the field being `None`.
- **AC-016 (render + truncation):** `>20` findings render as first 20 + `"... and N more"`, mirroring `bdd.discoveries` at `agent_invoker.py:3138-3152`; advisory guard sentence #7 appears in `_render_absence_of_failure_guards` output.
- **AC-017 (graceful import absence):** with guardkitfactory / tree-sitter absent, the lazy seam catches `ImportError`, all three fields are `None`, and `gather_evidence` does not crash.
- **AC-018 (existing tests green):** the full existing guardkit + guardkitfactory suites remain green; the 42 factory BDD contract tests are unaffected.
- **AC-019 (tree-sitter API path pinned):** the analyzer parses via `tree_sitter_language_pack.get_language(name)` + standalone `tree_sitter.Parser` (bytes input) and captures via `QueryCursor(query).captures(root)` — **not** the pack's `get_parser()`. Each dialect exposes a `smoke_test()` that compiles its `public_symbols_query` against the live grammar and matches a canonical snippet, so a malformed S-expr or tree-sitter API drift fails in **Wave 0**, never masquerading as `unsupported_stack` (OQ#6).
- **AC-020 (dependency location + packaging hygiene):** the two deps are added to guardkitfactory's **core `dependencies`** (or a dedicated guardkitfactory extra) — NOT a non-existent guardkitfactory `[autobuild]` extra; `[tool.setuptools] packages` includes `guardkitfactory.wiring` + `guardkitfactory.wiring.dialects`; a render-and-import smoke test confirms the new module names (`wiring`/`dialect`/`parser`/`analyzer`) shadow no PyPI top-level package (`.claude/rules/namespace-hygiene.md`).
- **AC-021 (polyglot task — all matching dialects run):** a task authoring both `.py` and `.ts` runs BOTH dialects whose `file_globs` match; each finding carries its `dialect`/`language`; a monorepo is never silently half-analyzed (OQ#4).
- **AC-022 (SPEC_GAP inherits unsupported-stack):** when `guardkitfactory.bdd.discover(stack)` returns `None` (no plugin for the detected stack), `spec_gap.status` is `unsupported_stack` (absent-signal, not a pass) and `_apply_spec_gap_absent_guard` does **not** fire — asserted by test.

**Complexity:** ≥7 (multi-stack, cross-repo new subpackage, new dependency, one deterministic hard-gate touching the post-verdict seam). Build **per-probe / per-stack across waves** (§6): Wave 0 agnostic core, Waves 1-2 advisory probes, Wave 3 the hard-gated SPEC_GAP behind BDDWIRE.

---

## 9. Mark of proposed-new paths

**NEW:** `guardkitfactory/src/guardkitfactory/wiring/{__init__.py, analyzer.py, dialect.py, parser.py, dialects/{python,javascript,typescript,c_sharp}.py}` · the three `CoachEvidenceBundle` fields at `coach_evidence.py:169` · `_apply_spec_gap_absent_guard` in `agent_invoker.py` (wired at `:2233`) · advisory guard sentence #7 · `tree-sitter` + `tree-sitter-language-pack` deps in guardkitfactory `pyproject.toml`.
**REUSED, UNCHANGED:** `coach_evidence.py:180-191` (`to_dict`/`asdict`) · `coach_validator.py:2120-2135` (complete-path return) · `coach_validator.py:775-783` (authored-set fallback — extract or duplicate) · `coach_validator.py:64` (`detect_stack_template`) · `agent_invoker.py:3098-3191` / `3138-3152` (render + truncation) · `agent_invoker.py:5083-5191` / `5133-5139` (guard archetype + None-safety) · `guardkitfactory/bdd/{plugin.py,loader.py}` (`BDDRunResult`, `StackProfile`, `discover`).

---

## 10. Open questions (carry into `/feature-plan`)

1. **(Blocker-shaped)** `BDDRunResult` exposes counts only, no per-scenario executed names (VERIFIED at `bdd/plugin.py:43-66`). **Recommend** extending the contract with `executed_scenarios: list[{name, outcome}]` populated by each plugin, folded into **TASK-HMIG-BDDWIRE** (agnostic-by-construction). If BDDWIRE lands count-only first, ship SPEC_GAP Wave 3 as `counts_only` (whole-file hard gate only — it needs only `scenarios_attempted`). Re-parsing `raw_report_path` per stack is **forbidden**.
2. **StackProfile vs bare language at the call seam:** `detect_stack_template` returns a template **string** ("fastapi-python"), not a `StackProfile`. Recommend `analyze_wiring` accept a bare `language: str` day-one (thin, no cross-repo type coupling) with `StackProfile` as the optional richer input, and a shared `template → language` mapping (recommend a guardkitfactory `StackProfile.from_template(...)` classmethod so wiring and bdd don't drift).
3. **C# seam-symbol granularity:** Moq/NSubstitute targets are generic TYPE args, so the C# `production_seam_set` must include interface/type names, not just dotted import-paths. The file-path-based authored set (`coach_validator.py:775-783`) may need a per-dialect `seam_symbol_query` (a fourth dialect field). Flag for the implementer.
4. **Multi-language tasks:** a task authoring both `.py` and `.ts` — run ALL registered dialects whose `file_globs` match (each finding carries its `dialect`/`language`), not only the primary stack's dialect, so a polyglot monorepo isn't silently half-analyzed. Day-one the gather seam may pass only the primary language; flag.
5. **tree-sitter-language-pack version pin + wheel availability** on the deployment/runner arch — confirm manylinux wheels cover the targets; the guarded import must map `ImportError → status:"unsupported_stack"` (or all-`None`), NEVER an `ImportError`-crash of `gather_evidence`.
6. **Optional dialect self-test at import** (does `public_symbols_query` compile against the grammar + match a canonical snippet?) — recommend a `dialect.smoke_test() -> bool` logged-not-raised, so a malformed S-expr query is caught early rather than masquerading as `unsupported_stack`.
7. **Promotion telemetry:** advisory findings should at minimum be COUNT-logged (per status, per pattern) so a future UNWIRED/MOCKED override-promotion decision has FP-rate data. No telemetry sink exists yet — out of scope, noted.

---

**Files referenced (all absolute):**
- This scope (saved at): `/home/richardwoollcott/Projects/appmilla_github/guardkit/docs/features/qa-verifier-wiring-probes-scope.md` (replaced the prior Python-monolith content at this path; the superseded draft remains in git history).
- Hard dependency task: `/home/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-HMIG-BDDWIRE-wire-factory-bdd-plugins-into-coach.md`
- Governing rule: `/home/richardwoollcott/Projects/appmilla_github/guardkit/.claude/rules/stack-plugin-architecture.md`
- Verified seams: `coach_evidence.py:169,180-191` · `coach_validator.py:64,775-783,2120-2135` · `agent_invoker.py:3098-3191,3320-3332,5083-5191,2233` · `guardkitfactory/src/guardkitfactory/bdd/plugin.py:22-66`