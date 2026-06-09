# Conversation starter: why has Player-Coach been *so* much harder than specialist-agent / agentic-dataset-factory?

> **Purpose.** A framing document to drive a focused retrospective. It does NOT
> answer the question — it sharpens it, lays out the (quantified) contrast,
> seeds the candidate hypotheses, and proposes discriminating tests so the
> analysis converges on *which* factors actually dominate. Drafted 2026-06-09
> after the run-13→20 arc finally produced two consecutive green autobuild runs.

## The question

GuardKit's autobuild Player-Coach loop took **~20 runs (13→20), a 24-entry
failure taxonomy (F1–F24), and a 15-file "design-rule" scar-tissue directory**
to reach two consecutive green end-to-end runs — and it's still not 100%
(open: COACHBFULL, COACHSYNTH, BDD-wire). The same author built
**agentic-dataset-factory** and **specialist-agent** with "nothing like a
fraction of the issues."

**Why is the contrast so stark?** Is Player-Coach *inherently* a much harder
problem — or is most of the pain *incidental* to a stack of surrounding choices
that the other two repos didn't make?

## The contrast, quantified (from a 2026-06-09 fingerprint)

| | autobuild (guardkit) | specialist-agent | agentic-dataset-factory |
|---|---|---|---|
| orchestrator/src size | **~53,000 LOC** orchestrator | 299 py files | 111 py files |
| "scar-tissue" design rules | **15** `.claude/rules/*.md` | — | — |
| topology | **closed-loop adversarial** (Player↔Coach, verdict gates progression) | **generative roles** (architect→ADRs, product_owner); NOT a gating adversarial loop | pipeline / ingestion |
| substrate | local Gemma/Qwen on llama-swap, self-hosted | **same local llama-swap** (`localhost:9000`); architect = fine-tuned Gemma 4 26B (`architect-agent`) | mostly pipeline (langgraph) |
| **model posture** | **BASE** Gemma 4 26B-A4B-IT (config: chosen base *deliberately*; the existing fine-tunes have "wrong posture", "do not inherit JSON-discipline") | **FINE-TUNED for the role** (architect-agent = DDD; gemma4-tutor = Socratic) | n/a |
| role demand on the model | **adjudicate** + emit terse **gating** JSON verdict + use tools | **generate** a design doc / ADR (forgiving — any sane output is usable) | transform/ingest |
| autonomy | fully autonomous multi-turn, multi-wave, resumable | role invocation (single/iterative generation) | batch pipeline |
| dogfooding | **builds GuardKit itself** (self-referential worktrees) | external artefacts | external datasets |

**The load-bearing clue (corrected 2026-06-09 after operator feedback —
the original "specialist-agent runs on cloud" claim was wrong):**
specialist-agent's architect runs the **same local Gemma 4 26B family on the
same llama-swap** — but it is **fine-tuned for a generative role**, whereas the
Coach is a **base** model asked to **adjudicate** and emit a **gating** JSON
verdict. Same substrate, opposite posture. So the differentiator is **not**
substrate strength and **not** "multi-agent vs pipeline" — it's
**(fine-tuned-for-role + generative) vs (base + adjudicative-gating)**. The
clincher is in GuardKit's own `llama-swap config.yaml`: the Coach was put on
**base** Gemma *deliberately* because the existing fine-tunes (`architect-agent`,
`gemma4-tutor`) have the "wrong posture" and "do not inherit that JSON-
discipline" — i.e. **there is no fine-tuned Coach model yet.**

## Candidate hypotheses (seeds — the convo should weight these, not just list them)

- **H1 — Model *posture*, not substrate strength (the leading candidate).**
  Same local Gemma 26B, opposite outcome: specialist-agent **fine-tuned** its
  model for a **generative** role and was smooth; the Coach runs a **base**
  model for an **adjudicative, gating, schema-disciplined, tool-using** role and
  was fragile. A huge share of the F-taxonomy (F24 schema-emission, run-13
  grammar no-op, run-18 tool-parse-500, the whole COACHSPLIT/COACHTESTTO saga)
  is exactly the JSON/verdict *discipline* that fine-tuning instils and a base
  model lacks. *Implication if true:* the highest-leverage fix is
  **fine-tuning/distilling a Coach** (the already-noted TASK-DATA-COACHHARVEST
  direction) — and you've proven it works on this stack twice (`architect-agent`,
  `gemma4-tutor`). The substrate was never the problem; the **missing role-
  specific fine-tune** was.
- **H2 — The Coach is an automated JUDGE, and reliable LLM-as-judge is
  frontier-hard.** A verdict that **gates progression** (approve = ship) makes
  every oracle weakness load-bearing. The entire design-rule family
  (`absence-of-failure-is-not-success`, `path-string-mismatch-is-not-dishonesty`,
  the false-green/false-red meta-frame) is scar tissue from *exactly this*: an
  oracle that can't distinguish "no signal" from "pass/fail." A generation
  pipeline never has to adjudicate with these stakes.
- **H3 — Trust boundary.** Player-Coach is adversarial: the Coach must
  *independently verify* the Player's self-report (honesty checks, independent
  test execution — cf. COACHTESTTO). "Trust but verify" spawns a whole failure
  class a *cooperative* pipeline doesn't have.
- **H4 — State/autonomy surface.** Worktrees, waves, turns, checkpoints,
  resume, state_bridge, verdict-emission contracts → many producers/consumers
  of state (the "runner without producer" and orchestrator-induced ghost-path
  bugs live here). 53k LOC is itself a signal.
- **H5 — Incidental compounding.** Mid-flight **harness migration**
  (SDK→LangGraph) + **self-referential dogfooding** (autobuild builds guardkit,
  hence the `lib/` namespace shadowing, worktree-venv issues) + **self-hosting
  the model**. None of these is *Player-Coach* per se; all three multiplied the
  surface.
- **H6 — It genuinely is frontier-hard.** Autonomous adversarial code synthesis
  is recent (the Block "Adversarial Cooperation" paper is Dec 2025). The other
  two solve better-understood problems (dataset gen, single-role specialist).

## Discriminating tests (how to *tell* which hypotheses dominate)

1. **Fine-tune/distill a Coach (TASK-DATA-COACHHARVEST) and re-run.** If a
   role-specific fine-tune collapses the schema/verdict F-failures the way it
   did for `architect-agent`, **H1 dominates** and the missing Coach fine-tune
   was the core cost. Highest-leverage *and* highest-information experiment —
   you have the harvesting infra already.
2. **Run the *base* Coach on a strong model (Claude) as a control.** If the
   JSON/verdict fragility vanishes on a strong base model → it's a model-
   *discipline* problem (base posture), which fine-tuning fixes on local. If it
   *doesn't* vanish → the hard part is the adjudication/gating *contract*
   itself (H2), independent of the model.
3. **Confirm the specialist-agent delta (now grounded).** Its architect is a
   **fine-tuned, generative** role emitting ADRs — **not** a gating adversarial
   verdict. So the comparison repos don't run a gating loop *at all*; "multi-
   agent vs pipeline" isn't even the right axis. The right axis is
   **generate vs adjudicate** × **fine-tuned vs base**.
3. **Map the F-taxonomy onto layers.** Tag each of F1–F24 + the 15 design rules
   as: substrate / oracle-gating / state-machine / harness-migration /
   dogfooding / genuine-adversarial-logic. The histogram answers "inherent vs
   incidental" directly.
4. **Count where the scar tissue concentrates.** If the design rules cluster on
   the **verdict/oracle** layer (they do — false-green/false-red), the hard part
   is *automated adjudication*, not *multi-agent* — a sharper, more actionable
   conclusion.

## What a good answer should produce (so the convo is actionable)

A verdict on the mix, and the implication of each:
- **Inherent (H2/H6)** → accept the cost; invest in the oracle (B-full
  investigation, richer `criteria_verification`, adversarial verification of the
  Coach itself).
- **Model posture (H1)** → the *missing role-specific Coach fine-tune* is the
  main self-inflicted cost; prioritise TASK-DATA-COACHHARVEST (distil/fine-tune
  a Coach), as proven viable by `architect-agent`. Local stays; the base model
  was the gap, not the locality.
- **State/incidental (H4/H5)** → simplify: shrink the 53k-LOC orchestrator,
  finish the harness migration, stop dogfooding-on-self for validation.
- **Implementation debt** → the run-by-run accretion (24 F-numbers, 15 rules)
  may itself be the cost of *evolving* the design under fire rather than
  designing the oracle contract up front.

## The reframe to open with

> The same author ran the **same local Gemma 4 26B family** for both. The one
> that was smooth was **fine-tuned for a generative role**; the one that was a
> nightmare is a **base** model asked to **adjudicate and emit a gating JSON
> verdict**. So the question isn't "is Player-Coach hard" or "is the local model
> weak" — it's: **how much of the F-taxonomy is just "we never fine-tuned a
> Coach"?** If most of it collapses under a role-specific Coach fine-tune, the
> stark contrast was largely a *missing-fine-tune* artifact, not an inherent
> property of adversarial cooperation — and the residue (the adjudication/gating
> *contract*, H2) is the genuinely-hard, possibly-irreducible core.

## Evidence pointers

- Failure taxonomy + run arc: `docs/state/TASK-REV-HMIG/run-1{3..9}-artifacts/`,
  `run-20-artifacts/`, `docs/reviews/autobuild-migration/`.
- The oracle scar tissue: `.claude/rules/absence-of-failure-is-not-success.md`,
  `path-string-mismatch-is-not-dishonesty.md`, `harness-cancellation-contract.md`,
  `namespace-hygiene.md`, `feature-build-invariants.md` (+ 10 more).
- The D-3 saga (verdict reliability on local): TASK-ARCH-COACHSPLIT,
  TASK-FIX-COACHTESTTO, TASK-ARCH-COACHBFULL, TASK-PERF-COACHSYNTH.
- Comparison repos: `../specialist-agent/` (roles, cloud),
  `../agentic-dataset-factory/` (pipeline).
