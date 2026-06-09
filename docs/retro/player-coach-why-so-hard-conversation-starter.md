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
| topology | **closed-loop adversarial** (Player↔Coach, verdict gates progression) | roles-based; coach/player/verdict markers in **54** files | pipeline / ingestion; adversarial markers in **4** files |
| substrate | **weak LOCAL model** (gemma4:31b / qwen36 on llama.cpp, self-hosted) | **cloud** (gpt-5.5, claude-sonnet-4) | mostly pipeline (langgraph) |
| autonomy | fully autonomous multi-turn, multi-wave, resumable | (characterise in the convo) | (characterise) |
| dogfooding | **builds GuardKit itself** (self-referential worktrees) | external artefacts | external datasets |

**The load-bearing clue:** specialist-agent *also* has coach/player/verdict
machinery (54 files) and was *smooth* — but it runs on **cloud** models. That
single fact lets us separate "the adversarial pattern is hard" from "the way
*we ran* it was hard."

## Candidate hypotheses (seeds — the convo should weight these, not just list them)

- **H1 — Substrate, not architecture.** A large share of F20 (ctx overflow),
  F23A (GPU OOM), F24 (schema-emission unreliability), the run-13 grammar
  no-op, and the run-18 tool-parse-500 were **weak-local-model + llama.cpp**
  failures, not Player-Coach failures. specialist-agent avoided them by using
  cloud APIs. *How much of the F-taxonomy is substrate vs architecture?*
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

1. **Run the SAME Player-Coach loop on a cloud model** (Claude/gpt-5.5) instead
   of gemma-local, on a known feature. If most of the F-failures vanish → H1
   dominates and much of the pain was the local substrate (a *choice*), not
   Player-Coach. This is the single highest-information experiment.
2. **Dissect specialist-agent's coach/player.** It has the markers but was
   smooth — *what's structurally different?* Is its "coach" **advisory** (not a
   hard gate), **single-turn**, **cloud**, **stateless between turns**? Pin the
   exact deltas; each one that explains away pain is an *incidental* cost, not
   an inherent one.
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
- **Substrate (H1)** → the local-model insistence is the main *self-inflicted*
  cost; default autobuild to cloud and treat local as an opt-in experiment.
- **State/incidental (H4/H5)** → simplify: shrink the 53k-LOC orchestrator,
  finish the harness migration, stop dogfooding-on-self for validation.
- **Implementation debt** → the run-by-run accretion (24 F-numbers, 15 rules)
  may itself be the cost of *evolving* the design under fire rather than
  designing the oracle contract up front.

## The reframe to open with

> Is **Player-Coach** hard — or is **"running an automated adversarial *judge*
> on a weak *local* model, *self-hosted*, while *migrating harnesses* and
> *dogfooding on itself*"** hard? specialist-agent ran a coach/player on cloud
> and was smooth. So the real question may not be "is the pattern hard" but
> "how many of our incidental choices each cost us a multiplier — and which one
> would, if removed, collapse most of the F-taxonomy?"

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
