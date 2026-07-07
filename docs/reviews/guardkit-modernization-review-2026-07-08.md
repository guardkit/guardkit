# GuardKit Modernization Challenge Review — 2026-07-08

> **Charge** (Prompt 11, `ai-transition/docs/kickoff-prompts-fable-sessions-2026-07-07.md:606-698`):
> challenge guardkit's template and command architecture (written Sept 2025 – Jan 2026) against
> 2026 state of the art AND against the fleet's own operating record. **Propose, never refactor.**
> Discipline: "newer exists" is NOT a finding — every finding carries a committed-record incident
> or a testable measurable benefit, and every finding was attacked by an independent skeptic
> before entering this report.
>
> **Method:** 4 scouting agents (evidence base) → 5 independent dimension reviewers →
> 1 adversarial skeptic per finding (refuted-by-default; anchors re-opened and verified,
> frozen-item fence enforced, already-solved-in-repo checked). 28 findings filed →
> **6 CONFIRMED · 21 WEAKENED (survive with the skeptic's corrections, applied below) ·
> 1 KILLED**. The kill and every correction are recorded — including where the skeptics
> corrected this review's *own* working narrative (§1) and its own brief (the 32k figure, §3.2).
>
> **DO-NOT-REOPEN fence honoured throughout:** DF-001..DF-009 (`ai-transition/docs/decisions/REGISTER.md`);
> integration seam v1 (forge consumes guardkit as a subprocess black box); WS3's calibrated
> autobuild baseline; the FEAT-SPL-007/008 output contracts PINNED 2026-07-07
> (`specialist-agent/docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md` @ guardkit
> `ce914f7c`/`5ad48fcf`/`28587b61`); the frozen fleet-evals suites; the F1–F5 qa formats
> (`b9f5eff8`). Proposals that touch pinned bytes are framed as **versioned migrations with the
> G2b re-freeze cost stated** (§8, ADR-B/ADR-D).

**Reading key per finding:** `[ID] priority/estimate/owner/model — SKEPTIC VERDICT`. Evidence
anchors below are the **post-skeptic corrected** anchors; where the skeptic changed a claim, the
corrected form is what is printed and the correction is noted.

---

## 0. The evidence base (verified facts this review stands on)

- **Command surface:** 29 markdowns under `installer/core/commands/`, **32,281 lines total**.
  task-work.md 4,480 (164,187 B) · feature-plan.md 2,910 (118,405 B) · agent-validate.md 2,871 ·
  task-review.md 2,059 · template-create.md 1,535 · feature-spec.md 937 (36,345 B).
- **Wheel gap:** `pyproject.toml:149-150` `[tool.hatch.build.targets.wheel] packages = ["guardkit"]` —
  `installer/` is not in the wheel. Verified empirically by a skeptic: a wheel built from main
  (199 files) contains zero `installer/` entries while shipping the F1–F5 *validator* code.
- **Two confirmed drift sites** (both refused by Session C's loader): repo-local
  `.claude/commands/feature-spec.md` (856 lines, only-ever commit `3a524edc1`, 2026-02-22) vs
  installer 937 (`ce914f7c`, 2026-07-02); and `~/.agentecflow/commands` (installed 2026-05-14,
  feature-plan.md there 2,868 lines, pre-`5ad48fcf`).
- **The pins:** Session C (`specialist-agent/docs/design/ws1-session-c-mode-registry-and-template-loader-2026-07-07.md`,
  `25e4e4b`) pins by **sha256 content hash** (feature-spec `79a6c306…`, feature-plan `cb440952…`),
  resolves via `importlib.resources` on the **installed** guardkit distribution, refusal-only
  (no override flag), and permits slicing only as "a pure function of pinned content".
- **The planning defect record** (`docs/guides/feature-plan-task-classification.md` — now FOUR
  classes): A invented paths (forge FEAT-DEA8 Run 2 — 17 min burned, 10/11 tasks blocked);
  B temporal mis-sequencing (study-tutor FEAT-FD32 Run 2 — 4/5 blocked); C task-design mismatch
  (TASK-GR-SEED/DEMO — ~110 min SDK burned, ~3 hrs debugging); D transient boundary assertions
  (FEAT-SMP-001). Baseline ~50–75 min per missed task (cited from the guide; not independently
  re-measured by this review).
- **False-green record:** ABL-001 `nats_core` `sys.modules` stub (fs-01 class; corpus
  `fleet-evals/tasks/abl-fs01-coach-false-approval/`); TASK-AB-PERTASKFG01 fabricated
  quality_gates; FEAT-POC-006 "345 tests green, feature dead"
  (`.claude/rules/per-task-green-is-not-feature-green.md`).

---

## 1. The precedent case: how the build loop actually consumes methodology (CORRECTED)

Rich's clarification scoped the SLM question to the planning side and named the Player's
migration off the task-work skill as the precedent case. The scouting pass initially
reconstructed that migration as "delegation flag off → 58-line prompt is the production path."
**A skeptic killed that narrative against committed code** (this is the review's one KILLED
finding, DIM2-F1, and the kill is more informative than the finding was):

- The AutoBuild orchestrator **hardwires `use_task_work_delegation=True`** at all three
  `AgentInvoker` construction sites (`autobuild.py:2086`, `:2118`, `:8146`) — the env default
  `"false"` at `agent_invoker.py:518` is only the constructor fallback.
- But since **TASK-ACO-002**, that "delegation" path does **not** shell `/task-work` and does
  **not** read `installer/core/commands/task-work.md` at all. It builds an inline SDK prompt
  from purpose-built protocol files:
  `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (17,198 B) /
  `_medium.md` (9,321 B) / `_slim.md` (3,929 B), **backend-selected** at
  `agent_invoker.py:7866-7876` — the in-code comment records the measured cost that motivated
  the tiers: **"24–174% turn inflation observed in vLLM Runs 5-6."**
- The 58-line / 2,341-char purpose-built prompt (`_build_player_prompt`,
  `agent_invoker.py:2874-2931`) serves the `implementation_mode: direct` path
  (`_invoke_player_direct`, TASK-FB-2D8B `09f399768`) and the branch the code itself labels
  "Legacy direct SDK invocation".
- The GB10 analysis (`tasks/review_complete/TASK-REV-GB10-…md:113-116`) recorded the ~19 KB
  inline protocol as the **primary root-cause hypothesis** for local-model stream truncation
  (hypothesis, not confirmed break — skeptic correction).

**The corrected precedent, stated precisely:** the build loop *never* consumes the 4,480-line
task-work.md wholesale. What it consumes is a **purpose-built, deterministic-gate-backed
protocol, tiered by backend capability** (17.2 KB → 9.3 KB → 3.9 KB), with quality enforcement
relocated from prompt prose into orchestrator code and Coach evidence. Specialists mirror the
same shape (`_build_test_orchestrator_prompt` ~1,180 chars, hard-capped 2,000 at
`specialist_invocations.py:713`; documented in
`.claude/rules/structural-defence-beats-prompt-instruction.md`).

This corrected precedent is **KEEP list item K1** and the evidentiary basis for the planning-side
consumption findings (§3): the fleet has already run the experiment "big methodology prose vs
sized purpose-built consumption" on the build loop, measured the cost, and chose sized
consumption — under DF-001's local-inference mandate. The open question this review addresses is
whether the *planning-side* consumption (007/008 templates-as-data) wants the same treatment
(it does — via loader-side slicing, §3.2, *not* via editing the pinned files).

---

## 2. Dimension 1 — Template harvesting (`/template-create` + friends)

**Dimension verdict.** The Player consumes exactly one thing from a template at build time: the
pattern layer — `.template` files selected by domain hints under a 3,000-token budget
(`template_pattern_loader.py:245-275`, wired via `autobuild_context_loader.py:506-540`).
Config-layer agents/rules/CLAUDE.md serve interactive sessions only. Harvested content has **no
verification story**: zero qa/ artifacts in any of the 14 non-common template dirs, and no
deterministic validation of `.template` files at harvest time. Harvest-by-example vs
distilled-rules: **complements serving different consumers** — but the build-time/SLM primitive
is the exemplar layer, and harvest effort should follow the consumer.

### [DIM1-F1] P1/M/WS2/sonnet — WEAKENED (survives; anchors corrected)
**Harvest captures zero verification data — extend `/template-create` to emit stack-typed qa/
seeds plus the source codebase's OBSERVED suite baseline.**
- **Evidence:** grep for qa/pass-bar/known-failures/leak-sweep across template-create.md's 9
  phases = 0 hits (Phase 4 settings generation `:542-583` emits naming/layer/code-style only —
  no coverage thresholds; coverage appears only as prose at `:687`, `:719-733`, `:1196`).
  `common/qa` stubs are placeholder-only (`known-failures.yaml:12` "passed: 0 # PLACEHOLDER",
  `23ae2ddb`); **zero of the 14 non-common template dirs ship qa/**. Incident classes the
  missing data permits: ABL-001 stub false-green (fs-01 corpus) — F3 deny-strings is the
  designed counter; FEAT-POC-006 — the F2 ledger + F4 registry class.
- **Benefit (testable):** after harvest, `guardkit qa validate known-failures` passes on an
  instance whose `expected.passed` equals the suite count actually observed by running the
  source codebase's tests once during Phase 1 (framework detection already exists,
  template-create.md:427); first autobuild run diffs against a ledger instead of "all green";
  ST-01 satisfiable at init+0. Also seed F3 deny-strings from real mock identities and ST-10
  discovery-gate stubs per `layer_mapping`.
- **Cost/risk:** one suite run at harvest (skippable); red-baseline enshrinement mitigated by
  F2's mandatory `owner`+`review_by` fields (`known_failures.py:65-67`). Templates ship
  stack-typed *stubs*; only the source repo gets observed *instances* (keep K5).
- **Migration:** additive Phase in template-create.md + qa-seed generator. No 007/008 touch, no
  G2b re-freeze. Builds ON F1–F5 (`b9f5eff8`) and `qa_scaffold.py` per-file-if-absent semantics.
  WS2 coordinates schema-version discipline.

### [DIM1-F2] P1/S/WS2/sonnet — WEAKENED (survives; repro corrected) → consolidated into PB-1
**qa/ scaffold (and all template resolution) rides a `__file__`-relative `installer/` path
absent from the wheel — wheel installs silently get zero qa scaffolding.**
- **Evidence:** `pyproject.toml:149-150`; `guardkit/templates/resolver.py:23-34`
  (`__file__`-relative → `installer/core/templates/`); `qa_scaffold.py:41-43` silent
  info-level skip on miss. Skeptic built the wheel from main: **zero installer/ entries, while
  `guardkit/qa/formats/*` validator code ships** — enforcement code without the data it enforces.
- **Benefit (testable, corrected):** clean-venv repro is `pip wheel . && pip install <wheel> &&
  guardkit-py init default` (the wheel's only console script is `guardkit-py`,
  `pyproject.toml:137-138`; the `guardkit` command comes from install.sh) → no qa/ today; passes
  after packaging fix. A CI job pins it.
- **Cost/risk:** the silent info-level skip is itself the absence-of-failure shape applied to
  distribution — promote to WARNING at minimum.
- **Migration:** no contract breaks; fold into the single packaging ADR (ADR-A) rather than
  fixing qa/ piecemeal.

### [DIM1-F3] P2/M/WS4/fable — CONFIRMED
**Rebalance harvest investment toward the exemplar (pattern) layer — the ONLY build-time Player
input from a template — away from agent prose with no autobuild consumer at an admitted 6/10.**
- **Evidence:** template-create.md:650-676 quality-tier table ("6/10 generic");
  `select_patterns` max_tokens=3000 + domain hints (`template_pattern_loader.py:245-275`);
  `_append_template_patterns` is the sole template→Player wiring
  (`autobuild_context_loader.py:506-540`). Precedent: §1's corrected consumption story + DF-001.
- **Benefit (testable):** exemplar coverage matrix (≥1 validated `.template` per
  settings.json `layer_mapping`; fastapi-python: 13 templates vs 9 layer_mappings, unaudited) is
  mechanically checkable; WS4 can A/B Player success with pattern context on/off per stack.
  Proposal: promote harvest-by-example to first-class (coverage matrix + selection metadata);
  demote Phase 6/5.5 agent generation to opt-in.
- **Cost/risk:** interactive users still value harvested agents — reprioritise, don't remove.
  Over-fitting exemplars to the source codebase's quirks — curation mitigates.
- **Migration:** additive. **WS3 coordination required if loader selection behaviour changes**
  (what the Player sees per turn is behavioural for the calibrated baseline) — flag-gated,
  calibrate via a WS3-coordinated run before any default flip.

### [DIM1-F4] P2/S/WS2/sonnet — WEAKENED (baseline corrected)
**Harvested `.template` files have a near-zero eval story — nothing renders or parses them at
harvest, validate, or CI time for 10 of 13 stacks.**
- **Evidence:** template-create.md Phase 5 step 5 "Validate template quality" is a bare AI-judgment
  list item; `/template-validate` is a 16-section AI prose audit with no deterministic tier;
  committed failure: **TASK-LCL-001** — the placeholder sweep rewrote
  `from deepagents.backends` → `from {{ProjectName}}.backends` and shipped, because nothing
  rendered+imported templates. **Corrected baseline:** `tests/integration/test_template_render_import.py`
  already sample-renders + import-checks **3 of 13** templates (langchain family) — Python-import-only,
  CI-skipped when langchain deps absent, and never at harvest time.
- **Benefit (testable):** promote the existing `_render_template` helper + extend fleet-wide
  (tree-sitter parse for non-importable stacks per `.claude/rules/stack-plugin-architecture.md`)
  → 3/13 → N/N with coverage at harvest/CI time; partially delivers the R4 render spike. Seed
  registry = the existing TEMPLATES/ENTRYPOINTS_BY_TEMPLATE config; add an opt-out marker for
  non-parseable-by-design fragments before enforcing red.
- **Migration:** additive; natural home is a deterministic tier of `template-validate`,
  mirroring `guardkit qa validate` (`b9f5eff8`).

### [DIM1-F5] P3/S/WS2/sonnet — WEAKENED (drift is three-way, worse than filed)
**Template-layer docs drifted from shipped reality.** `docs/guides/template-two-layer-model.md:26-27`
still claims init "optionally seeds project-level Graphiti knowledge" AND "optionally writes
.mcp.json" — both retired by FEAT-MEM-09 per `guardkit/cli/init.py:9`, the very file the doc
cites — and omits the new qa/ scaffold install (`init.py:775-780`, `23ae2ddb`). Docs-only fix;
verifiable by diffing doc claims against an actual `guardkit init` file list. Tracker-rot
precedent: gap-analysis §4(a).

**Dimension 1 KEEP candidates → consolidated into §7:** two-layer split (K3), pattern-loader
budget/degradation (K4), qa/ per-file-if-absent + DF-007 (K5), two-tier agent quality (K6),
settings.json layer_mappings (K7).

---

## 3. Dimension 2 — Command-template architecture (the slash-command markdowns)

**Dimension verdict.** The methodology content is largely load-bearing (every §4-contract and
diagram mandate in feature-plan.md traces to a committed incident) — but the **packaging** is
monolithic in a way the fleet has already paid for once (§1) and is about to pay for again on
the planning side. The defect record's most important lesson: all four A–D planning defect
classes occurred with **frontier models consuming the full prose** — the methodology text did
not prevent them; the fixes that worked were deterministic validators
(`generate-feature-yaml --validate-smoke-gates`, `guardkit feature validate` at
`cli/feature.py:204`). Prose instructs; validators enforce.

### [DIM2-F1] — KILLED (see §1 for the corrected precedent; refiled narrowly as PB-16)
The "stale docs describe a dead delegation path" finding was killed: delegation is the live
default architecture (hardwired True at `autobuild.py:2086/:2118/:8146`). What survives as a
P3 docs-truth refile: `.claude/rules/autobuild.md` + `installer/core/agents/autobuild-player.md`
describe the **mechanism** stale — "100% code reuse of quality gates" and literal
`guardkit task-work --implement-only` subprocess wording, when the path has been an inline
protocol via the SDK harness since TASK-ACO-002 (`agent_invoker.py:8123-8172`; stale comment at
`:516`) — and neither doc mentions direct-mode routing.

### [DIM2-F2] P1/M/WS1(loader)+WS4(SLM)/26B-target — WEAKENED (arithmetic + provenance corrected)
**feature-plan.md is a 118 KB (~30k-token) monolith with two entry-ish regions (Execution Flow
at :796, CRITICAL EXECUTION INSTRUCTIONS at :1980) — a large, avoidable fixed cost for any
local-window consumption in the 007/008 port; propose pinned header-sliced disclosure.**
- **Evidence:** 2,910 lines / 118,405 chars verified; protocol header at `:1980`; Steps 1–6 at
  `:796-1525`; diagrams `:1774-1930`. The A–D record (10/11 blocked; 4/5 blocked; ~110 min
  burned) happened with wholesale frontier consumption — prose scale did not prevent them.
  §1's corrected precedent (tiered protocol, "24–174% turn inflation") is the fleet's own
  measurement of oversized-prompt cost on local backends.
- **Honesty note (skeptic):** the "26B/**32k**-window" figure has **circular provenance** — it
  appears only in this review's own kickoff prompt (`kickoff-prompts…:653`); no committed serving
  config or WS4 doc pins the Gemma 4 26B window at 32k. The claim is therefore stated as:
  wholesale ≈30k tokens is a large avoidable fixed cost for any local window; the protocol slice
  (:1980-2910 = 47,223 chars ≈ **11–12k tokens**, corrected from ~9k) + one phase-relevant
  reference slice fits budgets wholesale consumption cannot. **Action for WS4: commit the
  serving-window figure** so this class of claim stops being un-anchorable.
- **Benefit (testable):** token cost per planning session measured before/after slicing;
  each slice independently gradable under a G2b-style suite.
- **Cost/risk:** slicer bugs could omit load-bearing prose — the A–D-derived sections (§4
  contract mandates, validator hooks) must ride in every task-generating slice. Header hygiene
  is currently insufficient for naive slicing (DIM2-F4 is the prerequisite).
- **Migration:** **consumption-mechanism change only** — the file stays byte-identical, the
  TemplatePin (`cb440952…`) does NOT change, no versioned migration. Session C's constraint is
  satisfied by a deterministic header-offset slicer (slice = pure function of pinned content).
  If the file were instead physically split, that IS a pin change: WS1 re-pins, G2b re-freezes
  FEAT-EVAL-SPEC — state that cost before choosing the split variant. Autobuild untouched.

### [DIM2-F3] P2/M/WS1/frontier-interactive — WEAKENED (migration risk shrank)
**task-work.md defines flag semantics three times** — declarative table (`:109`), a ~2,700-line
imperative pseudocode parser (`:1189+`, verbatim `design_only = "--design-only" in user_input`
at `:1196-1247`), and reference re-documentation (`:3925+`, modes again at `:3929-4028`).
~41k tokens loaded per attended `/task-work` invocation.
- **Benefit (testable):** one normative definition site per flag (grep-count CI oracle);
  per-invocation load drops toward the protocol core.
- **Migration (corrected):** consolidation **cannot** break the autobuild delegation path — no
  orchestrator path parses task-work.md at all (§1); pre-merge check is an interactive
  `/task-work` flag-parse smoke + fixing the stale subprocess comment at `agent_invoker.py:516`.
  Only remaining coupling is documentary step-name refs (`agent_invoker.py:86/:9185/:10457`) —
  keep step names stable or update comments (pairs with PB-12). No pin covers task-work.md.

### [DIM2-F4] P2/M/WS2+fleet-evals/tooling — CONFIRMED
**Nothing grades the templates THEMSELVES — and ambiguous anchors already exist.**
feature-plan.md carries FOUR near-colliding Integration-Contracts headers: a real document
header `## Integration Contracts` at `:1827`, `### 4. §4: Integration Contracts` at `:1888`,
and `## §4: Integration Contracts` at `:1895` AND `:1918` (those two inside ````markdown
fences). A fence-naive header-regex slicer — the natural first implementation of DIM2-F2 —
grabs the wrong block. No template-structure lint exists anywhere (guardkit, fleet-evals
harness, siblings — G2b grades OUTPUTS only).
- **Benefit (testable):** a CI lint asserting (a) unique normative anchors, (b) presence+location
  of the execution-protocol section, (c) per-section token budgets, (d) example blocks marked
  non-normative — turns template drift from a live-run failure into a red CI build, and is the
  **prerequisite** for DIM2-F2's slicer.
- **Migration:** the lint is additive. Anchor **de-duplication edits are byte changes to a
  pinned file** → versioned migration: batch with any other byte-touching template edits into
  ONE re-pin + G2b re-freeze event (ADR-D).

### [DIM2-F5] P2/M/WS1/frontier-now — WEAKENED (re-scoped; half was already specified)
**Plan-side assumptions ledger — re-scoped to the guardkit template side.** The pinned
FEAT-SPL-008 spec **already** requires every auto-resolved planning decision be recorded in the
returned plan document and marked deferred for human review (the @key-example scenario;
12 assumptions confirmed 2026-07-07) — so the "headless Stage 8 gap" half of the original
finding was redundant. What survives: (a) `installer/core/commands/feature-plan.md` has no
assumptions ledger for **interactive and `--no-questions`** runs (only `:754` mentions
assumptions non-structurally; its only escape hatch is operator_handoff `:1312-1511`);
(b) a sibling `{feature}_plan_assumptions.yaml` manifest would **extend** (not create) 008's
in-document deferred-decision mechanism. **Causal honesty (skeptic):** classes A/C are *silent*
inference errors a planner doesn't know it is making — the committed defences for them are the
deterministic validators + operator_handoff detection; the ledger surfaces clarification-point
and low-confidence-inference guesses, and must be claimed as complement, never substitute.
- **Migration:** sibling file = additive, no 008 contract break, no G2b re-freeze. If the plan
  YAML schema itself gained an assumptions field, that would be a versioned migration — avoid;
  use the sibling file. Any template-file edit batches into the ADR-D re-pin event.

**Dimension 2 KEEP candidates → §7:** corrected Player/build-loop architecture (K1), --auto +
assumptions manifest (K2), in-house progressive-disclosure primitives (K13), feature-plan's
load-bearing content vs packaging (K14), the imperative execution-instructions pattern (K14).

---

## 4. Dimension 3 — Distribution + versioning

**Dimension verdict.** Copy topology verified from `install.sh` (2,058 lines) + `init.py` +
`resolver.py`: Gen 0 = repo `installer/core` (truth) → Gen 1 = `~/.agentecflow` via `cp`
(stamped only with a hardcoded "2.0.0"; `~/.claude/commands` is a **symlink** to it, not a copy)
→ Gen 1b = 9+ committed shadow copies in guardkit's own repo-root `.claude/commands/` →
Gen 2 = target-project `.claude/` via per-file-if-absent copy with no update path. Compounding
facts found beyond the brief: the resolver's user fallback is `~/.guardkit/templates`, which
**no installer ever populates** (install.sh writes `~/.agentecflow`); and install.sh,
init-project.sh and hatch carry **3–4 unrelated version numbers** (install.sh:23 "2.0.0",
install.sh:851 "1.0.0", init-project.sh:405 "1.0.0", `guardkit/__init__.py` "0.1.0").

### [DIM3-F1] P1/M/WS1/sonnet — WEAKENED (remediation corrected) → PB-1 / ADR-A
**Wheel omits installer/ AND the resolver fallback points at a never-populated directory —
pip-installed guardkit cannot resolve templates, qa scaffold, conftest bridge, or bin-entries.**
- **Evidence:** `pyproject.toml:149-150`; `resolver.py:33-43`; consumers `qa_scaffold.py:40`,
  `conftest_bridge.py:93`, `autobuild.py:952`; Session C §4.1 documents the gap + fix and its
  loader is the intended consumer of the fix.
- **CRITICAL correction (skeptic):** the remediation must **NOT** be
  `packages = ["guardkit","installer"]` — top-level `installer` **collides with PyPI
  `pypa/installer` 1.0.1** (`namespace-hygiene.md` violation, same class as the `mcp` shadowing
  incident). Instead relocate template data under the guardkit namespace (hatch `force-include`
  mapping `installer/core` → `guardkit/_installer_core`, or a `guardkit.templates.data`
  subpackage) and resolve via `importlib.resources` over that guardkit-namespaced package.
- **Benefit (testable):** clean-venv wheel install resolves templates; Session C's loader gains
  a canonical non-editable-install channel — removing the hard editable-install dependency of
  seam v1.1.
- **Migration:** pinned template **content** unchanged → TemplatePins do NOT change, no re-pin,
  no G2b re-freeze. **Exclusion:** `bin-entries.txt` runtime read stays worktree-relative
  (WS3-calibrated — see K11); explicitly exclude it from the resolver migration. Resolve the
  `~/.guardkit/templates` fallback (document as user-override or remove — not two disjoint
  namespaces).

### [DIM3-F2] P1/S/WS1/human — CONFIRMED → merged with DIM4-F1 into PB-2
**Committed shadow copies in guardkit's own `.claude/commands/` actively override installer
specs in-repo.** The skeptic strengthened it: the 856-line feature-spec copy still mandates
Graphiti queries removed by FEAT-MEM-09, lacks the single-physical-line Gherkin invariant
(whose absence causes a hard CompositeParserException downstream), and lacks the @task: BDD
tagging section. Duplicate skill registration is live and observable. Audit each of the 9
before deleting (some may be deliberate repo-local overrides — stamp divergence-by-intent).

### [DIM3-F3] P2/M/WS2/sonnet — CONFIRMED → PB-3
**No copy generation carries provenance** — 3–4 unrelated hardcoded version numbers; the
`~/.agentecflow` drift sat undetected ~7 weeks until Session C's loader refused it.
CI-generated MANIFEST (per-file sha256 + source commit) copied by install.sh; `guardkit doctor`
reports "N command files differ from source @ <commit>" in <1s; derive all stamps from
`guardkit/__init__.py`. Manifest is hash-of-content only, never a second content source.

### [DIM3-F4] P2/S/WS2/human — WEAKENED (anchor corrected) → ADR-D
**Pinned-by-hash templates have no semantic format_version** — consumers cannot distinguish
editorial edits from contract breaks. (Corrected anchor: `28587b61` pins the *oracle* files;
the template pins are `ce914f7c`/`5ad48fcf`; the contract-pin commit is specialist-agent
`e1081aa`.) Two-phase: (1) NOW add format_version to the 27 unpinned command specs — zero
external impact; (2) fold into the two pinned templates only at the next coordinated semantic
change, as a versioned migration with the full re-pin + G2b re-freeze cost stated.

### [DIM3-F5] P2/S/WS1/sonnet — WEAKENED (anchor corrected) → PB-3
**No release gate on template-touching commits.** ce914f7c (Jul 2), 111b02ac (Jul 4), 5ad48fcf
(Jul 5) all edited the now-pinned templates; the contract was pinned after the fact. A CI check
reading a committed PINNED-FILES list (six artifacts per the contract §0) that fails any PR
touching them without a dated correction note makes an uncoordinated pin break un-mergeable.
Name G2b in the failure message. ("008-008" = 008-ASSUM-008, the drift-tripwire assumption.)

### [DIM3-F6] P3/M/WS2/sonnet — WEAKENED (doctor exists; scope corrected) → PB-3 phase 2
**Gen-2 project copies are write-once with no staleness signal.** `_copy_file_if_not_exists`
(`init.py:99-119`) is the sole copy path; zero provenance recorded. Corrected: `guardkit doctor`
EXISTS (`cli/doctor.py`) but checks environment/dependency/existence only — extend it with the
PB-3 manifest comparison (report-only; never auto-refresh — see K10).

**Dimension 3 KEEP candidates → §7:** the `~/.claude` symlink (K8), refusal-only pins (K9),
per-file-if-absent init semantics (K10), worktree-relative bin-entries.txt (K11), Player/markdown
split as distribution-risk bound (K1).

---

## 5. Dimension 4 — Skills surface coherence

**Dimension verdict — the consumption tags the charge demanded** (verified against orchestrator
code + git history):

| Tag | Commands |
|---|---|
| **OUTER-LOOP (machinery-consumed)** | feature-spec.md (TemplatePin + `assumption_confidence_checker.py:3`, `coach_validator.py:2894/8766`, `agent_invoker.py:113`), feature-plan.md (TemplatePin + `feature_complete.py:92-104` parses operator_handoff), feature-complete.md (backed by `orchestrator/feature_complete.py`) |
| **ATTENDED (interactive spec layer)** | task-create, task-work (normative spec + step-name anchors in gate code; build loop consumes the tiered protocol files instead, §1), task-review, task-status, task-complete, task-refine, debug, context-switch, feature-build (outer loop invokes `guardkit autobuild` CLI directly), system-plan/system-arch/system-design, arch-refine, design-refine, template-create, template-validate, agent-enhance/format/validate, agentic-init |
| **DEAD-OR-DOUBTFUL** | figma-to-react, zeplin-to-maui, mcp-zeplin (2,307 lines frozen since initial clone `77f865f07` 2025-10-28, zero `.py` consumers — the live design path is design_url/Phase-0 via `mcp_design_extractor.py`, `autobuild.py:2306`); template-create-qa, template-init, template-qa (dormant ~7 months; standing MODIFY verdict never executed) |
| **RETIRED-BUT-INSTALLED** | impact-analysis + system-overview — deleted from installer (`ce914f7c`, `71becc51`) yet still present AND invocable in `~/.agentecflow` and repo `.claude/commands` (duplicate skill registration observed live in this session) |
| **NEVER-CANONICAL ORPHANS** (repo `.claude/commands` only) | execute-tests, formalize-ears, gather-requirements, generate-bdd, update-state, task-work-specification (require-kit era, frozen at `77f865f07`) |

The emerging non-markdown surface is the CLI (`guardkit qa`, `guardkit feature`, `guardkit
memory`, `guardkit autobuild` — `cli/main.py:106-130`): outer-loop invocation lives in the CLI;
the markdowns are increasingly the attended/spec layer. The tagging above formalises that split.

### [DIM4-F1] P1/S/WS1/sonnet — CONFIRMED (strengthened) → PB-2
**Repo's own `.claude/commands/` is a stale third fork, actively loaded.** 421-line task-work.md
(`42a07adda`, 2026-02-15) vs 4,480 canonical; the confirmed feature-spec drift site; two RETIRED
commands still invocable; six require-kit orphans. **Not mere staleness:** the stale
impact-analysis.md instructs `from guardkit.knowledge.graphiti_client import get_graphiti` — a
module FEAT-MEM-09 WS-2c **physically removed** — so an attended invocation loads a spec whose
implementation stack is deleted. Corrections folded in: the duplicate retired entries prove a
SECOND stale source (the installed `~/.claude`/agentecflow surface) — the fix must cover
install-time sync/removal of retired names too; acceptance test scoped to shared names; the six
orphans need explicit disposition (repo-local manifest or move to require-kit).

### [DIM4-F2] P1/S/WS1/sonnet — WEAKENED (retirement commits corrected) → PB-3
**install.sh command distribution is additive-copy with no manifest or prune.** `install.sh:567`
find|cp of `*.md`, zero removal logic; the proven manifest-plus-prune pattern already exists for
`.py` bins (`prune_stale_bin_symlinks`, install.sh:1694, TASK-ISH-D09E, bin-entries.txt "SOLE
source of truth") — extend it to `.md`. Corrected retirement provenance: impact-analysis.md
deleted in `ce914f7c`; system-overview.md deleted in `71becc51`; the Python planning stack
retired earlier in `60ebde5d`. Design the manifest once for both prune and future wheel
packaging (ADR-A).

### [DIM4-F3] P2/S/WS2/sonnet — WEAKENED (drift already live) → PB-12
**Orchestrator code is coupled to command-markdown LINE NUMBERS — and the rot is already
committed fact.** All 5 `feature-spec.md:337` code anchors (`assumption_confidence_checker.py:3`,
`coach_validator.py:2894/:8766` — the latter a runtime f-string operators see —
`agent_invoker.py:113/:10506`) point **2 lines stale**: at introducing commit `fb37f72fd` the
Gating-rule sentence was at :337; at HEAD it sits at :339. Zero-re-freeze remediation: anchor on
existing heading text (code-side change only) + a CI grep asserting the anchored heading exists —
the grep-able-signature discipline `.claude/rules/` already uses.

### [DIM4-F4] P3/S/WS1/human — WEAKENED (decision already filed, lapsed) → PB-17
**Design-tool trio vs the live design_url pipeline.** The disposition decision ALREADY EXISTS as
`tasks/backlog/design-url-integration/TASK-UX-2DAB-deprecate-old-commands.md` (2025-11-11,
`removal_planned: 2026-06-01` — **lapsed unexecuted**; mcp-zeplin.md not covered; a sibling
task still recommends both commands). Refile = revive and execute TASK-UX-2DAB with the PB-3
tombstone mechanism, extend to mcp-zeplin.md.

### [DIM4-F5] P2/M/WS4/fable — WEAKENED (remediation precedent corrected) → PB-13
**Skills-shaped restructuring of the attended heavyweights (task-work 164 KB, agent-validate
87 KB, task-review 69 KB) — wave-1 excludes the two pinned templates.** Corrected precedent: the
fleet's remediation of oversized protocol is the **tiered protocol files** (17.2/9.3/3.9 KB,
"24–174% turn inflation" measured) — that, not the 58-line prompt alone, is the sizing evidence.
The in-house split primitives (agents core/`-ext` — 13 `-ext` files shipped; rules `paths:`
frontmatter) mean this is a restructure, not new infrastructure. Do DIM4-F3 (anchors) first or
together. Pinned templates are wave-2-only via ADR-D with re-freeze cost stated.

### [DIM4-F6] P3/M/WS2/human — WEAKENED (nuances) → PB-18
**Post-Graphiti overlap clusters need a filed consolidation decision:** the arch/design cluster
(system-arch/system-design/system-plan/arch-refine/design-refine — 5,558 lines, rewritten to
fleet-memory 2026-07-02, so alive but 5 entry points for one workflow) and the template quartet
(standing MODIFY verdict from `template-create-pivot-review.md` 2025-11-20 never executed;
dormant ~7 months). Sequence template consolidation AFTER WS2 qa-format direction lands so the
surviving command harvests qa/ artifacts once.

---

## 6. Dimension 5 — Templates as producers (the retros as the spec)

**Dimension verdict.** The seam is real, acknowledged in three shipped places, and implemented
in zero. `pass_bar.py:9-18` names the headless `/feature-spec` + `/feature-plan` tools as the
**named WRITERS** of F1 ("WS1 CONTRACT … flagged for the WS1 sessions"); `common/qa/README.md:19`
says "will emit it" (future tense); both command specs contain zero qa-format references. The
WS2 scope-design already records the delta (line 346: WS1 owes the emission). The emittability
matrix from the authoritative docstrings: **F1 = spec/plan-time YES** (named writer);
**F3 = plan-time PARTIAL** (surface claims only; Player maintains entries);
**F2 = FORBIDDEN** (human/Coach at triage only — LPA-09); **F4 = build-time** (Player +
merge-review curation); **F5 = runner-only**. **F13 is NOT a plan output** — WS2 pins the writer
as the forge Mode P dispatcher. The eval story is unusually good: `guardkit qa validate pass-bar`
is a shipped zero-marginal-cost oracle, so emitted F1s are immediately G2b-gradeable.

### [DIM5-F1] P1/M/WS1(emitter)+WS2(schema)/opus-authoring+Rich-refreeze — WEAKENED (incident cite corrected) → ADR-B
**Author the v2 output-contract ADR: /feature-spec + /feature-plan emit F1 pass-bar SIDECARS per
task (`qa/pass-bar-<TASK-ID>.yaml`, plus `checkpoint_list_ref` for walk-bearing features),
leaving the pinned three-file/FEAT-yaml shape untouched.**
- **Evidence:** pass_bar.py WS1-CONTRACT docstring; README future tense; zero emission steps in
  either command spec; WS2 scope-design line 346 records the unlanded delta. Corrected incident
  cite: the fs-01 Coach false-approval (2026-06-13, FEAT-MEM-04/TASK-RLY-006 — all-green
  reported while wave-4 wiring broke `test_app_lifespan`; `pre_fix_pin 92ef8979`) is the
  committed incident class that ST-01's pre-committed observable bars counter; ABL-001's
  nats_core stub is the *separate* env-tamper instance of the same class.
- **Benefit (testable):** every task in a headless plan carries a validator-green F1 whose
  `registered_at` predates the first implementation commit → B2's Coach task-start precondition
  becomes enforceable instead of vacuous; G2b grades emitted bars as first-class eval artifacts.
- **Migration:** this IS a change to the pinned 007/008 output inventory → **versioned
  migration**: dated correction note in CONTRACT-feature-spec-plan-outputs.md; re-run round-trip
  fixtures (expected unchanged — run to prove it); G2b/FEAT-EVAL-SPEC eval-seed extension;
  Rich approves the re-freeze. Sidecar strategy keeps the FEAT yaml + oracle byte-identical.
  **All D5 contract items ride this ONE ADR = one re-freeze event, not four.**

### [DIM5-F2] P2/S/WS1+WS2(B3)/sonnet — WEAKENED (delta already filed; verify unlanded) → ADR-B
**F3 leak-sweep names /feature-plan as writer of claimed-real surfaces; feature-plan.md has no
producing step — runner-without-producer.** The gap is already filed as an open WS1↔WS2 delta
(scope-design line 346, build-plan line 213, dated 2026-07-07); this review verifies it has NOT
landed. Contract must split "plan claims surfaces" from "Player maintains entries" exactly as
the docstring does. Rides ADR-B.

### [DIM5-F3] P2/S/WS2/sonnet — WEAKENED (narrowed to the surviving delta) → ADR-B + B2
**Plan-time authorship guard for known-failures.yaml.** The F1–F5 writer matrix is ALREADY
normative (WS2 scope-design line 72 "a format written by 'whoever' is written by no one" +
per-format writers :81-145) — the v2 contract should REFERENCE it, not restate it. The surviving
unenforced channel: B2 as specified guards Player-mid-build writes and the run-vs-ledger sweep —
**neither checks who authored ledger entries at plan time**. A headless 007/008 planner writing
`known-failures.yaml` would be treated as expected failures by the sweep. Remedy: a path-based
reject-lint failing any /feature-spec|/feature-plan session whose diff touches
`qa/known-failures.yaml`, landing WITH session B2 (B2 is specified-not-built, scheduled ~07-09).
ABL-001 is the class analogy (env-tamper channel, caught); the planner-ledger channel is
hypothesized-but-plausible and currently unenforced.

### [DIM5-F4] P2/S/WS2(seam)+WS1(fields)/sonnet — WEAKENED (anchor sharpened) → ADR-B
**/feature-plan must NOT become a second F13 kickoff-prompt writer.** WS2 scope-design line 154
pins the F13 writer as the forge Mode P dispatcher ("render fails on missing sections"). The v2
contract should instead guarantee plan outputs carry the **dispatcher-renderable fields**
(`deliverable.gate_ref` → emitted F1 id; `decisions_already_made` ← the assumptions manifest).
Dual-writer F13 = a drift generator and a seam-v1 violation (couples guardkit to forge's session
model). Near-zero cost if DIM5-F1 lands first.

### [DIM5-F5] P2/S/WS2(schema authority)/opus — WEAKENED (shape corrected) → PB-14
**F1's validator hard-requires five auth-surface-shaped negative paths for EVERY pass bar** —
(`pass_bar.py:41-49` REQUIRED_NEGATIVE_PATHS: wrong_credential, anonymous_deep_link,
post_logout_401, unauthorized_403_ui, dependency_down_degradation). Corrected: not "web-app-
shaped" — the committed counterexample `tests/fixtures/qa_formats/study-tutor/pass-bar-p2-wave-7.yaml`
shows a Flutter feature mapping all five honestly; the unmappable class is **authless** features
(CLI/library/pipeline/guardkit-internal). A headless emitter for those can only validate by
fabricating paths — polluting G2b's eval corpus with criteria that can never be evidenced.
Remedy via the schema's own evolution channel (dated note in WS2 scope-design §2 + validator
conditionality keyed on an auth-surface-bearing flag for the four auth paths; B2/B3 coordinate).
NOT a reopen of b9f5eff8 — this is the dated-note evolution path the format itself specifies.

### [DIM5-F6] P3/S/WS1+WS2(B2)/sonnet — CONFIRMED → ADR-B
**`registered_at` fill mechanics are unspecified for a self-referencing pin.** The stub ships
sha `"00000000"` with the comment "the commit that pinned this bar" — unknowable pre-commit.
The v2 contract must define fill/verify order (e.g. sha = HEAD-at-emit parent; B2 verifies via
`git log --follow --diff-filter=A`) or every emitted bar ships an unverifiable placeholder and
ST-01's "committed BEFORE implementation" degrades to an honor-system date string.

---

## 7. KEEP LIST — dated-looking but load-bearing (do not "modernize" these)

| # | What | Why it is load-bearing |
|---|---|---|
| **K1** | **The build-loop prompt architecture** (corrected, §1): tiered inline protocol (17.2/9.3/3.9 KB backend-selected, `agent_invoker.py:7866-7876`) + direct-mode 58-line prompt + quality in deterministic gates/Coach evidence — never the 164 KB markdown | The fleet's own completed experiment: "24–174% turn inflation" measured on vLLM; DF-001 mandates local inference; WS3's baseline is calibrated against THIS. Any "consistency" push to make the Player consume command markdowns reverses a committed, incident-driven decision — and imports the whole distribution drift class into the WS3 baseline. |
| **K2** | `--auto` + "mark everything as assumptions" + `{feature}_assumptions.yaml` (feature-spec.md `:9/:34/:250/:919-925`) | Just carried FEAT-SPL-003 (14 assumptions curated) and 007/008 (12 confirmed) end-to-end; enforced in code (`assumption_confidence_checker.py`, warn-mode Coach gate); inside the PINNED contract. Extend (DIM2-F5), never restructure mid-freeze. |
| **K3** | Two-layer config/pattern split — init deliberately does NOT render the pattern layer (TASK-INST-010; `template-two-layer-model.md:50-72`) | The un-rendered pattern layer is the Player's only canonical, non-drifting stack-context source. Rendering at init would fork canonical shapes into per-project copies — recreating exactly the drift class Session C refuses. |
| **K4** | Pattern loader's 3,000-token budget + never-raise degradation (`template_pattern_loader.py:245-275`) | The hard budget IS the SLM-compatible bounded-context discipline (same lesson as K1); degradation keeps autobuild working on manifest-less projects. Fix content upstream (DIM1-F4), don't make the consumer loud. |
| **K5** | qa/ instances per-repo, per-file-if-absent, never clobbered (`qa_scaffold.py`; DF-007) | The property that makes harvest-seeding (DIM1-F1) safe: a repo's committed verification truth always wins over template content. Templates ship stubs/patterns, never authoritative instances. |
| **K6** | Two-tier agent quality: auto-format to 6/10 at harvest, `/agent-enhance` to 9/10 post-init (template-create.md:631-676) | Deliberate cost control validated on the record: the pivot review found template-create succeeded 4/4 in 1hr–1day precisely because harvest makes no AI enhancement calls. |
| **K7** | settings.json harvested `layer_mappings` + `naming_conventions` | The machine-readable skeleton of the codebase's architecture — the join key for ST-10 discovery-gate seeding and the exemplar coverage matrix; the harvest product most ready to become eval-seed data as-is. |
| **K8** | `~/.claude/commands` → `~/.agentecflow/commands` **symlink** (install.sh:1668) + init-project.sh's refusal to create project-level command symlinks | The reason the global surface has ONE copy generation, not two. Replacing it with copies during packaging modernization would add a drift generation back. |
| **K9** | Session C's refusal-only content-hash pinning — no override flag | The only drift detector that has actually worked: both confirmed drift sites were caught because the loader refuses non-canonical sources. A "convenience override" reopens the exact false-input class the pin closes. |
| **K10** | Per-file-if-absent copy semantics in `guardkit init` (`_copy_file_if_not_exists`) | Project copies are designed to be operator-edited. The fix for gen-2 staleness is detection (manifest + doctor, PB-3), never clobbering copy semantics. |
| **K11** | `bin-entries.txt` read from the WORKTREE's path at runtime (`autobuild.py:943-952`) | Deliberately worktree-relative: the direct-mode evidence gate reads the manifest as authored in the task's worktree (`direct-mode-relaxed-gates-require-positive-evidence.md`). **Explicitly excluded from the ADR-A resolver migration — WS3-frozen.** |
| **K12** | task-work.md as the attended normative spec (4,480 lines) | Cited as normative by live gate code (step-name anchors); the attended flag surface is real. Restructure/single-source (PB-9, PB-13) with anchor re-pointing — never delete. |
| **K13** | In-house progressive-disclosure primitives: agents `{name}.md`/`{name}-ext.md` (13 `-ext` files shipped) + rules `paths:` frontmatter | The same three-level shape the 2026 Agent Skills standard converged on, already exercised by tooling. Adopt Skills *packaging* around it; adding the external format as a second convention and re-migrating every agent is the wrong move. |
| **K14** | feature-plan.md's load-bearing CONTENT: §4 Integration-Contracts + mandatory-diagram mandates (`:1774-1930`), operator_handoff machinery (`:1312-1511`), and the imperative "CRITICAL EXECUTION INSTRUCTIONS" orchestration pattern (`:1980+`) | Every one traces to a committed incident (classes A–D; FEAT-DEA8/GR-SEED). The monolithic PACKAGING is under challenge (DIM2-F2); the content must ride in every task-generating slice. The imperative pattern is what keeps /feature-plan an orchestrator rather than an inline analyst. |
| **K15** | known-failures.yaml's human/Coach-at-triage-only writer restriction | The LPA-09 guard against the ABL-001 false-green class. Extend explicitly to headless planners (DIM5-F3's lint); never automate this writer. |
| **K16** | The pinned 007/008 three-file shape + `feature_loader.py` oracle + round-trip fixtures | Machine-checked, not prose (gold trace exit 0, mutants exit 1). Its stability is what makes sidecar emission (ADR-B) cheap: additive files, oracle untouched. |

---

## 8. Prioritized proposal backlog

P1 gate honoured: every P1 names its fleet incident or measured cost, and states what breaks /
who re-freezes. Overlapping findings are consolidated; source finding IDs given.

| ID | Proposal (sources) | Pri | Est | Owner | Model | Motivating incident / measured cost | Freeze impact |
|---|---|---|---|---|---|---|---|
| **PB-1** | Package template data into the wheel under the **guardkit namespace** (hatch force-include → `guardkit/_installer_core` or `guardkit.templates.data`; NOT top-level `installer` — PyPI `pypa/installer` collision) + switch resolver to `importlib.resources`; resolve the never-populated `~/.guardkit/templates` fallback; promote qa-scaffold silent skip to WARNING (DIM3-F1, DIM1-F2) | P1 | M | WS1 | sonnet | Wheel built from main: 0 installer/ entries while F1–F5 validator code ships; Session C names editable install as the v1 prerequisite; qa scaffold silently inert on wheel installs | None: pinned template content unchanged → no re-pin. **Exclude bin-entries.txt (WS3-frozen, K11).** File as **ADR-A**. |
| **PB-2** | Disposition + de-fork the repo-local `.claude/commands/` (9 stale/shadow, 2 retired, 6 orphans) AND prune retired names from installed surfaces (DIM4-F1 CONFIRMED, DIM3-F2 CONFIRMED) | P1 | S | WS1 | human+sonnet | Stale impact-analysis.md imports physically-removed `graphiti_client`; 856-line feature-spec predates the pinned contract (missing Gherkin single-line invariant → CompositeParserException class); duplicate skill registration observed live | None: Session C already refuses these sources; installer copies untouched. Deprecation: tombstone README one release, then removal; orphans dispositioned explicitly. |
| **PB-3** | Command-distribution manifest + prune + provenance: extend the bin-entries.txt manifest/prune pattern to `.md`; CI-generated MANIFEST (sha256 + source commit); align the 3–4 version stamps to `guardkit/__init__.py`; extend existing `guardkit doctor` with drift reporting; CI gate on PINNED-FILES commits requiring the dated correction note (DIM4-F2, DIM3-F3 CONFIRMED, DIM3-F5, DIM3-F6) | P1 | M | WS1+WS2 | sonnet | `~/.agentecflow` drift undetected ~7 weeks; retired commands persist in every install; pinned templates were edited 3× before the pin existed | None: manifest/tombstones are new files; the CI gate encodes the EXISTING re-freeze procedure. |
| **PB-4** | **The v2 emission-contract ADR** (ONE versioned migration, ONE G2b re-freeze): /feature-spec + /feature-plan emit F1 pass-bar sidecars per task; F3 surface-claims plan step; `registered_at` fill/verify mechanics; F13 renderable-fields guarantee (NOT a second F13 writer); plan-time known-failures reject-lint landing with B2 (DIM5-F1/F2/F3/F4/F6, referencing not restating the WS2 writer matrix) | P1 | M | WS1 emitters + WS2 schemas | opus authoring; Rich approves re-freeze | pass_bar.py names WS1 the writer (shipped 07-07); WS2 scope-design line 346 records the unlanded delta; fs-01 Coach false-approval (FEAT-MEM-04/TASK-RLY-006) is the incident class ST-01 counters | **Versioned migration**: dated correction note in CONTRACT-feature-spec-plan-outputs.md + round-trip fixtures re-run (expected unchanged) + G2b eval-seed extension. Sidecars keep FEAT-yaml + oracle byte-identical. File as **ADR-B**. |
| **PB-5** | Sliced consumption for the 007/008 port: deterministic, fence-aware header-offset slicer in Session C's loader (slice = pure function of pinned content) + the **template-structure lint prerequisite** (unique normative anchors — 4 colliding Integration-Contracts headers exist today; protocol-section presence; per-section token budgets; non-normative example marking) (DIM2-F2, DIM2-F4 CONFIRMED) | P1 | M | WS1 loader + WS4 consumption; WS2 lint | sonnet tooling; 26B target | A–D defects occurred under wholesale frontier consumption; "24–174% turn inflation" is the fleet's measured oversized-prompt cost; wholesale ≈30k tokens vs ~11–12k protocol slice. **WS4 must commit a serving-window figure — the 32k number currently has circular provenance** | Lint: additive. Slicing: none (file bytes unchanged, pin intact). Anchor DE-DUP edits = byte changes → batch into the ADR-D re-pin event. |
| **PB-6** | Harvest emits verification seeds: observed suite baseline (F2 instance for the source repo), stack-typed qa/ stubs in templates, F3 deny-strings from real mock identities, ST-10 discovery-gate stubs per layer_mapping (DIM1-F1) | P1 | M | WS2 | sonnet | ABL-001 fs-01 (F3's designed counter); FEAT-POC-006 "345 green, feature dead" (F2/F4 class); guardkit's own main has 7 pre-existing red tests that a ledger would triage | None: additive harvest phase; F1–F5 semantics untouched; per-file-if-absent preserved (K5). |
| PB-7 | Exemplar-layer rebalance: coverage matrix (≥1 validated .template per layer_mapping) + loader selection metadata; agent generation opt-in (DIM1-F3 CONFIRMED) | P2 | M | WS4 | fable | 6/10 admitted agent quality with no autobuild consumer vs the only build-time input capped at 3,000 tokens | **WS3 coordination if loader selection behaviour changes** — flag-gated + calibrated run first. |
| PB-8 | Deterministic .template render+parse gate: promote `_render_template`, extend 3/13 → N/N via tree-sitter per stack-plugin-architecture; opt-out marker; partially delivers R4 (DIM1-F4) | P2 | S | WS2 | sonnet | TASK-LCL-001: placeholder sweep broke SDK imports and shipped unrendered | Additive deterministic tier of template-validate. |
| PB-9 | task-work.md single-source flag semantics (3 definition sites → 1) + slice reference sections (DIM2-F3) | P2 | M | WS1 | frontier-interactive | ~41k tokens per attended invocation; triple definition = drift surface | None: no pin covers task-work.md; delegation path never reads it (§1). Keep step names stable (PB-12). |
| PB-10 | format_version two-phase: NOW on the 27 unpinned command specs; pinned two only at the next coordinated semantic change (DIM3-F4) | P2 | S | WS2 | human policy + sonnet | Pin refusals are currently unclassifiable (editorial vs semantic) | Phase 2 only inside the ADR-D batched re-pin. |
| PB-12 | Line-anchor hygiene: heading-text anchors + CI grep (already 2 lines stale across all 5 feature-spec.md:337 code sites, incl. a runtime f-string) (DIM4-F3) | P2 | S | WS2 | sonnet | Committed drift at `fb37f72fd`→HEAD; grep-able-signature discipline precedent | Zero re-freeze variant chosen: code-side only. |
| PB-13 | Skills-shaped restructure of attended heavyweights, wave 1 = task-work/task-review/agent-validate/template-create (core <5k tokens + on-demand refs, using K13 primitives); wave 2 (pinned templates) only via ADR-D (DIM4-F5) | P2 | M | WS4+WS1 | fable design, sonnet execution | 164 KB/87 KB/69 KB monoliths vs the K1 tiering lesson; prerequisite for any attended 26B use under DF-001 | Wave 1: none. Wave 2: full re-pin + G2b re-freeze, batched. |
| PB-14 | F1 negative-path conditionality: dated note in WS2 scope-design §2 + validator keying the four auth paths on an auth-surface flag (DIM5-F5; study-tutor Flutter fixture is the honest-mapping counterexample; authless features are the unmappable class) | P2 | S | WS2 | opus judgement | Headless emitter for authless features must fabricate or refuse; fabrication pollutes G2b's corpus | Uses the format's own dated-note evolution channel; not a b9f5eff8 reopen. B2/B3 coordinate. |
| PB-15 | Plan-side assumptions ledger for interactive/`--no-questions` runs — extends 008's in-document deferred-decision mechanism with a sibling manifest; complement to validators, never substitute (DIM2-F5 re-scoped) | P2 | M | WS1 | frontier | Classes A/C cost record; 008 already specifies the headless half — this ports it to the guardkit template side | Sibling file = additive; template edit batches into ADR-D. |
| PB-16 | Docs-truth sweep (refile of killed DIM2-F1 + DIM1-F5): autobuild.md/autobuild-player.md mechanism wording (inline protocol since TASK-ACO-002, not `--implement-only` subprocess; direct-mode routing absent), stale `agent_invoker.py:516` comment, two-layer-model doc (3 drift directions incl. qa/ scaffold omission) | P3 | S | WS3 docs | sonnet | The killed finding's residue: docs describe a mechanism the code retired; two-layer doc contradicts the file it cites | Docs-only. |
| PB-17 | Revive + execute lapsed TASK-UX-2DAB: design-tool trio disposition (extend to mcp-zeplin.md), via PB-3 tombstones (DIM4-F4) | P3 | S | WS1 | human decision | 2,307 frozen lines documenting an MCP integration the orchestrator does not implement; removal_planned 2026-06-01 lapsed | Decision candidate; no freeze impact. |
| PB-18 | Command-surface consolidation decision: arch/design cluster 5→≤3 front doors; template quartet per the standing MODIFY verdict — sequenced AFTER WS2 qa-format direction (DIM4-F6) | P3 | M | WS2+human | human decision | 5,558-line cluster; MODIFY verdict from 2025-11-20 never executed | ADR-C candidate; attended-only surface. |

(PB-11 folded into PB-3; DIM3-F6 doctor work is PB-3 phase 2.)

---

## 9. Candidate decision/ADR filings for Rich

> **2026-07-08 update:** ADR-A and ADR-B are now DRAFTED as full decision candidates for the
> register queue — `docs/decisions/DECISION-DF-011-template-data-ships-in-the-wheel-under-the-guardkit-namespace.md`
> and `docs/decisions/DECISION-DF-012-planning-commands-emit-the-pass-bar-v2-emission-contract.md`
> (CANDIDATE status, not filed in REGISTER.md; numbers tentative behind the DF-010 A2A candidate).
> DF-012 carries PB-14 and the ADR-D batching as binding riders. ADR-C/ADR-D remain listed-only.

1. **ADR-A — Template-data packaging & distribution** (PB-1 + PB-3 manifest): wheel ships
   template data under the guardkit namespace via importlib.resources (Session C's own
   mechanism); one provenance manifest serves prune, doctor, and packaging include-list.
   Explicitly out of scope: bin-entries.txt runtime read (WS3-frozen). *Names the
   namespace-hygiene constraint: never a top-level `installer` package (PyPI collision).*
2. **ADR-B — The v2 emission contract for planning outputs** (PB-4): F1 sidecars + F3 surface
   claims + registered_at mechanics + F13 renderable-fields guarantee + plan-time F2 reject-lint.
   ONE versioned migration; the G2b re-freeze cost stated and paid once. WS1 emits, WS2 owns
   schemas, forge stays the only F13 writer (seam v1 preserved).
3. **ADR-C — Attended command-surface consolidation** (PB-17, PB-18, PB-2 orphan disposition):
   which arch front door survives; template quartet per the standing MODIFY verdict; design-tool
   trio via the revived TASK-UX-2DAB; require-kit orphans dispositioned.
4. **ADR-D — Batched re-pin policy for pinned-template byte changes**: format_version phase 2
   (PB-10), anchor de-duplication (PB-5), any pinned-template split (PB-13 wave 2), and any
   assumptions-ledger template edits (PB-15) accumulate into ONE coordinated re-pin event —
   dated correction note + fixtures re-run + Session C re-pin + G2b re-freeze — instead of four
   separate specialist-tool-down windows.

---

## 10. Where proposals land in existing lanes (cross-links, not duplicates)

- **WS1** (`ai-transition/docs/ws1-outer-loop-completion-build-plan-2026-07-07.md`): PB-1
  (Session C §4.1 documents the packaging gap + fix), PB-4 emitter half (scope-design line 346
  delta), PB-5 loader slicing (§3 Session C design, §4.3 assembler-owned injection), PB-15.
- **WS2** (`ws2-qa-verifier-and-last-mile-scope-design-2026-07-07.md` + build plan): PB-4 schema
  half + the B2-landing reject-lint (B2 scheduled ~07-09); PB-6 (F1–F5 seeds); PB-8; PB-14 (the
  §2 F1 field-list dated-note channel); PB-3 manifest formats.
- **WS3** (`ws3-autobuild-reliability-scope-and-build-plan-2026-07-07.md`): PB-16 docs-truth;
  the K1/K11 freeze exclusions; PB-7's coordination requirement (loader selection behaviour is
  baseline-calibrated).
- **WS4** (`ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md`): PB-5 consumption half
  (**and the action item: commit the serving-window figure**), PB-7, PB-13.
- **Contract:** `specialist-agent/docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md`
  (ADR-B's correction-note target; ADR-D's re-pin procedure source).
- **Gap analysis:** `ai-transition/docs/factory-gap-analysis-2026-07-07.md` Stage 8 (headless
  spec/plan) is the umbrella gap PB-4/PB-5 serve; §4(a) tracker rot is PB-16's cousin; §4(c)
  contracts-are-prose is answered by PB-3's manifest + ADR-D.

---

## Appendix — method & verification ledger

- 4 scouting agents (exec-plan/lanes; contracts/Session C; Player-precedent; defect record).
- 5 dimension reviewers, one lane each, independent; max 6 findings + keep candidates each.
- 28 skeptic runs, one per finding, refuted-by-default (anchor re-opened and verified; committed
  failure or testable claim required; frozen-item fence enforced; already-solved-in-repo
  checked). Verdicts: **6 CONFIRMED** (DIM1-F3, DIM2-F4, DIM3-F2, DIM3-F3, DIM4-F1, DIM5-F6;
  DIM4-F1's skeptic was re-run after an API failure), **21 WEAKENED** (corrections applied
  in-place above), **1 KILLED** (DIM2-F1 — the kill corrected the review's own precedent
  narrative, §1; refiled narrowly as PB-16).
- Skeptic quality highlights: empirically built the wheel to verify the packaging gap; found the
  live 2-line anchor rot at `fb37f72fd`→HEAD; caught the PyPI `pypa/installer` namespace
  collision in a proposed fix; caught the circular provenance of the 32k-window figure in the
  review's own brief; found the lapsed TASK-UX-2DAB disposition task; corrected the
  Player-migration mechanism against committed code.
- Full per-finding raw records (original finding text, full skeptic reasoning, corrections):
  session workflow journal (28 agents, ~5.5M tokens). This report prints the corrected forms.

*Review executed 2026-07-07 night → 2026-07-08 by the P11 Fable session. Lane claimed and
released in `ai-transition/docs/fable-window-execution-plan-2026-07-04.md`.*
