# Verdict: why Player-Coach was *so* much harder than specialist-agent / dataset-factory

> **Companion to** [`player-coach-why-so-hard-conversation-starter.md`](player-coach-why-so-hard-conversation-starter.md).
> Where the starter *sharpened* the question and seeded H1-H6, this doc *answers*
> it from evidence. Produced 2026-06-09 by a fan-out audit (six parallel readers
> classifying all 24 F-failures, the 15 design rules, the live model config, both
> sibling repos, and the run-13→20 arc), a synthesis, and an **adversarial
> red-team pass** whose job was to stop us rubber-stamping the starter's own
> preferred answer. Three of the starter's load-bearing claims did not survive.

## The one-line answer

It was **not** hard because Player-Coach is inherently hard, and **not** because
"we never fine-tuned a Coach." It was hard because the Coach must emit a
**trustworthy *gating* verdict over a *mutating, shared, stateful* substrate**
(git worktree + test runner + disk) where a wrong "approve" ships broken code —
and we did that while **simultaneously** migrating the harness (SDK→LangGraph),
**dogfooding** the tool on its own source, and **self-hosting** the judge. The
two easy repos run the **same base models** in the **same kind of gating loop**;
they were smooth because their Coach scores a throwaway in-context text blob with
no external oracle and a blast radius of one discarded artefact.

## Three corrections to the conversation starter

**1. The model-posture framing (H1) is stale and refuted *as a cause*.**
- The starter names base **Gemma-4 26B-A4B-IT**. The green runs it celebrates
  actually run on **Gemma-4 31B dense QAT**, swapped in by **TASK-OPS-COACH31B
  (2026-06-08)** because the 26B-A4B MoE could not emit a verdict at all (run-14:
  a **49,720-char ramble**, zero fenced JSON). The starter never mentions the swap.
  Per-run grep: runs 7-14 = `gemma4:26b`, runs 15-20 = `gemma4:31b`.
- "No grammar" is wrong — **GBNF grammar enforcement is live** (toolless verdict
  synthesis, `GUARDKIT_COACH_SYNTHESIS` default ON; `grammar=present` in the green
  logs at [run-19:200](../reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md#L200)).
- **F24 was collapsed by model-upsize (26B→31B) + GBNF grammar, with no fine-tune.**
  So "the difficulty was mostly a missing Coach fine-tune" is undercut: a fine-tune
  was never the bottleneck for getting a verdict *out*. The only surviving sub-claim
  is "no role-fine-tuned Coach exists yet" (true, but not load-bearing).

**2. "Generative vs adjudicative-gating" is factually wrong.** Both sibling repos
run *genuine* adversarial gating loops on *base* models: specialist-agent scores
REVISE/ACCEPTABLE/GOOD on a 0.6 threshold with a read-only (`tools=[]`) Coach;
agentic-dataset-factory has an accept/revise `CoachVerdict`. Neither "no gating
loop" nor "fine-tuned-in-the-loop" distinguishes the siblings. The real
differentiator is **what the Coach adjudicates over** (a disposable in-context doc
vs a verified claim about a mutating filesystem) and **what a wrong verdict costs**.

**3. "Scar tissue clusters on the oracle layer" is only narrowly true.** By
**primary** failure count the oracle-gating layer has **zero** F-numbers (it is
only ever a *secondary* tag); failures cluster on **substrate-model-quality (11/24)**
and **harness-migration (7/24)**. Only **3 of 15** design rules are oracle scars;
8 are ordinary process/reference docs. What *is* true: the 3 deepest,
most-cross-linked rules (the `IS_INVERSE_SHAPE_OF` cluster —
`absence-of-failure-is-not-success`, `path-string-mismatch-is-not-dishonesty`,
`harness-cancellation-contract`) are all oracle scars. The system bled hardest
there; the *volume* of pain was substrate + migration plumbing.

## The shape of the pain (histograms)

| Layer | F-failures (of 24) | Design rules (of 15) | What it was |
|---|---:|---:|---|
| substrate-model-quality | **11** | 0 | local model can't reliably emit a schema-valid gating verdict (F2→F17→F24 = one defect at three scopes) |
| harness-migration | **7** | 1 | SDK→LangGraph model-threading/selector family (F1/F9/F10/F12/F19) + DeepAgents path + cancel asymmetry |
| state-machine-autonomy | 4 | 1 | worktree/branch/stall machinery (two were *positive* findings) |
| genuine-adversarial-logic | **1** | 2 | …and the one F-finding was a *pass* (the honesty guard caught a fabricated Player report) |
| oracle-gating-verdict | 0 (primary) | **3** | zero *failures* by primary count; but the 3 *deepest* rules live here |
| process/reference docs | — | 8 | not born from autobuild pain |

Run-13→20 arc (8 runs): **5 substrate-quality, 1 migration, 2 "green."** The
failure frontier migrated *down the stack* over time — harness/timeout plumbing
(13-14) → raw substrate quality in four HTTP costumes, 502/502/400/500 (15-18) →
"green" once D-3 made verdict *emission* deterministic.

## The kicker: the "green" is a false-green

> **Now resolved — see [Update 2026-06-11](#update-2026-06-11--task-ops-coachmoe01-reconciliation) below.**
> Both halves of this finding are closed: the *empty-criteria substance* half by
> COACHBFULL (validated by the MoE A/B — 100%-populated verdicts, caught real
> dishonesty), and the *`signal_absent` deterministic-backstop* half by
> **TASK-FIX-COACHFG01 (completed 2026-06-10)**. The only item this section
> flagged that is still open is the *N=1 frozen-fixture* generalization gap (H6).

The whole retro is premised on "the run-13→20 arc finally produced two
consecutive green runs." **By the project's own `absence-of-failure-is-not-success`
rule, those greens are hollow.** Verified directly in the logs:

- **Run-19**: the Coach's independent test oracle
  `SDK coach test execution timed out after 300s` → `SDK independent tests failed
  in 300.0s` → **`Coach approved`** → `Criteria Progress (Turn 1): 0/5 verified (0%)`
  ([run-19:197-218](../reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md#L197-L218)).
- **Run-20-2nd**: independent tests passed (3.9s) but the verdict was still
  **`0/5 verified (0%)`**
  ([run-20-second-attempt:202-219](../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20-second-attempt.md#L202-L219)).

So the Coach approves with **zero per-AC verification whether the oracle passes
*or* fails to run.** "Green" currently means *the orchestrator printed APPROVED*,
not *the Coach verified the work*. And it is an **N=1 frozen fixture** — the same
hand-authored quartet (GD02/IA03/SPECHANG/TP05) passing twice after the harness
was tuned to it. We have **no evidence the loop generalizes.**

**The most damning detail — and the clearest proof of the inherent core.** The
guard against exactly this case *already exists*. `agent_invoker.py:3230-3241`
("INDEPENDENT-TEST ABSENT GUARD") instructs the Coach: *"if
`independent_tests.signal_absent == true` … do NOT approve … surface as feedback,"*
and cites `absence-of-failure-is-not-success.md` by name. But the guard is written
as a **natural-language instruction to the local LLM**, and in run-19 gemma4:31b
**ignored it and approved anyway.** The GBNF grammar constrains the verdict's
*shape* (`approve|feedback`), not whether the model *honored the guard*. There is
**no deterministic code backstop**: `signal_absent` is *set* at six sites in
`coach_validator.py` and *read by nothing* — the post-synthesis decision path
(`agent_invoker.py:2189`) only schema-checks the verdict. The oracle contract is
correctly specified and then delegated to an adjudicator that cannot be trusted to
follow it. That is H2/H3 in one sentence.

→ Fix filed as **TASK-FIX-COACHFG01** (fail-closed: enforce guard #6 in code).

## Reconciled hypothesis weights

(Synthesis weights, adjusted by the red-team's de-double-counting of H2/H3 and its
"difficulty-experienced ≠ difficulty-inherent" correction.)

| H | Factor | Weight | Verdict |
|---|---|---:|---|
| **H2+H3** | Trustworthy gating verdict **over a mutating shared substrate** (one coin, two faces) | **~40%** | **Dominant — and *not yet solved*** (the green is hollow; guard #6 is prompt-only) |
| H5 | Incidental compounding: mid-flight harness migration + dogfooding-on-self + self-hosting | ~18% | Largest self-inflicted bucket; the migration was the *vehicle* that surfaced H2/H3, not the cause — every migration bug was code-fixable and closed |
| H4 | 53k-LOC state surface | ~17% | **Symptom, not cause** (277 TASK-ids ≈ 279 fixes — code grown under fire); but a *live* force-multiplier (the ghost-path filter still fires in the green run) |
| H1 | Model posture / missing fine-tune | ~13% | Refuted as the *cause*; the fine-tune/gather is now the **leading untested fix for the *empty-verdict* problem**, not the headline cause |
| H6 | Frontier-hard / generalization | ~12% | Genuinely open — the N=1 frozen fixture means the green runs *cannot* tell us if this works at all |

**Inherent vs incidental: ~40% inherent (and unsolved), ~48% incidental/self-inflicted
(and mostly closed), ~12% genuinely unknown.** The starter's framing made the pain
feel like "a missing fine-tune + frontier-hard." The honest read: a hard oracle
contract we have **not** actually cracked, surfaced by three self-inflicted
multipliers we mostly *have*.

## What to do next (priority order)

1. **Treat the empty/false verdict as the open P0, not residue.**
   - **TASK-FIX-COACHFG01** (filed): make the INDEPENDENT-TEST ABSENT GUARD
     deterministic — downgrade `approve`→`feedback` in code when
     `evidence_bundle.independent_tests.signal_absent` is true, regardless of what
     the LLM emitted. This closes the run-19 false-green directly.
   - **TASK-ARCH-COACHBFULL** (done; AC-3 live leg pending): populate
     `criteria_verification` so a verdict has *substance*, not just shape.
2. **Re-frame the Coach fine-tune (TASK-DATA-COACHHARVEST), don't defer it.**
   Upsize+grammar fixed *emission*; a role fine-tune / the gather leg is the
   leading candidate to fix *substance* (populated per-AC verification). It is the
   most promising untested lever for the actual open problem — not the headline cause.
3. **Bound COACHSYNTH cost** by keeping `gemma4:31b` resident (stop llama-swap
   cold-loading ~50GB every Coach turn) and capping the synthesis prompt/generation.
4. **Close BDD-wire** so the BDD leg contributes a *falsifiable* signal (guard
   `scenarios_run == 0` the same way `absence-of-failure` mandates) rather than
   passing vacuously.
5. **Institutionalize the one migration meta-rule that paid for itself:** "audit
   *all* invocation sites of a migrated contract boundary" (the F1/F9/F10/F12/F19
   six-instance cadence) — a CI check that every new `HarnessAdapter` substrate
   implements `cancel()` and threads `model=` at every call site.
6. **Generalization test before declaring victory:** run the loop on a *fresh*,
   un-tuned task set. Two greens on a frozen quartet is a tuned-to-fixture pass,
   not a solved problem (H6).

## Evidence pointers

- False-green proof: [run-19:197-218](../reviews/autobuild-migration/autobuild-FEAT-AOF-run-19.md#L197-L218),
  [run-20-second-attempt:202-219](../reviews/autobuild-migration/autobuild-FEAT-AOF-run-20-second-attempt.md#L202-L219).
- Prompt-only guard #6: [`agent_invoker.py:3230-3241`](../../guardkit/orchestrator/agent_invoker.py).
- `signal_absent` set-but-never-read: `coach_validator.py:240-260` (def),
  `:2698,2778,3012,3023,3255,3266` (set sites); `coach_evidence.py:171` (bundle field).
- Model swap: `docs/state/TASK-OPS-COACH31B/README.md`. Live config:
  `/opt/llama-swap/config/config.yaml` (`gemma4-31b` block; no `gpt-oss-120b` entry —
  that grouping is in the *historical* `docs/research/dgx-spark/llama-swap-config.yaml`).
- Sibling repos: `../specialist-agent/` (0.6 threshold gating loop, base model),
  `../agentic-dataset-factory/` (accept/revise CoachVerdict, base model).
- Oracle scar cluster: `.claude/rules/absence-of-failure-is-not-success.md`,
  `path-string-mismatch-is-not-dishonesty.md`, `harness-cancellation-contract.md`.

## Update 2026-06-11 — TASK-OPS-COACHMOE01 reconciliation

Two days after this verdict, [`docs/state/TASK-OPS-COACHMOE01/README.md`](../state/TASK-OPS-COACHMOE01/README.md)
ran the first live A/B of the base **26B-A4B MoE** (`gemma4-coach`) as Coach on the
shipped B-min toolless+grammar path, with COACHBFULL's gather leg enabled. It moves
two of this doc's findings and **strengthens** the central thesis. What changed:

**1. The substance half of the false-green is closed (on the fixture).** With the
gather leg live, the MoE Coach produced **100%-populated `criteria_verification`**
(5/5, 7/7, 6/6 per-AC), ran a genuine **catch→fix→approve** loop — it caught a real
Player honesty discrepancy *twice* on IA03 and approved only when fixed — and
delivered **3/3 approvals with zero false-greens**. The run-19 `0/5 verified`
rubber-stamp was a pre-COACHBFULL B-min artefact; it does not reproduce now. The
verdict's "irreducible core is *not yet solved*" should be read as *"demonstrated
working on the frozen fixture; generalization still untested,"* not *"unsolved."*

**2. Correction #1 sharpens — and the anti-H1 conclusion gets *stronger*.** This doc
said "F24 was collapsed by model-upsize (26B→31B) + grammar." That is imprecise: the
**26B-A4B MoE itself passes** on the toolless+grammar path (grammar contains the
ramble; zero `finish=length`; ~24-40s substantive synthesis). The 49,720-char run-14
ramble was in the **tool-bound agentic loop** that D-3 *removed* — not a model-size
ceiling. So the real bottleneck was **architecture (tool-bound vs toolless+grammar),
not the model**, and the 31B upsize was a reliability margin, not a necessity.
H1 (model posture) is *more* refuted as a cause, not less.

**3. The fine-tune direction is now decided** — TASK-DATA-COACHHARVEST base ← the
26B MoE (the only base with a validated 71-min GB10 LoRA recipe *and* now empirically
validated as a working Coach). HMIG-013 is superseded. The fine-tune is confirmed as
a *hardening/quality* lever, not a prerequisite — exactly this doc's framing.

**Both false-green halves are now closed (the COACHFG01 backstop landed too):**
- **TASK-FIX-COACHFG01 completed 2026-06-10** — the day before COACHMOE01. The
  deterministic backstop now exists: `agent_invoker.py:5085-5165`
  (`_apply_independent_test_absent_guard`, wired at `:2232`) overrides an
  `approve`→`feedback` in code whenever
  `evidence_bundle.independent_tests.signal_absent is True`, independent of what the
  LLM emitted, and re-persists `coach_turn_N.json` so the Layer-4 late-approval path
  cannot resurrect it. Reproducer at
  `tests/orchestrator/test_coach_independent_test_absent_guard.py` (red→green). Guard
  #6 is no longer advisory. COACHMOE01's caveat #1 — **1 of 6 turns emitted malformed
  JSON despite `grammar=present`**, caught only by the COACHSF01 net — is the live
  evidence that this class of deterministic backstop is load-bearing on the MoE.

**What is genuinely still open:**
- **N=1 frozen fixture (H6)** — the A/B ran the same IA03/GD02/TP05 family. Two more
  greens on the frozen quartet is still not a generalization signal. This is now the
  single highest-value open question: run the loop on a *fresh, un-tuned* task set.
- **B-full `GATHER=1` overhead (operational, not a blocker)** — wasted wall-time on
  *both* substrates: Phase-A degrades to B-min on 100% of turns (recursion_limit=12
  reached). Either raise/scale `recursion_limit` so Phase-A can converge, or default
  to `GATHER=0` (where the MoE's ~30-60s synthesis is ~6-10× faster than g31).
- **Player-side drift** (independent of the Coach): qwen36-workhorse honesty drift
  (avg 0.75 < 0.8) and the SPECHANG `test-orchestrator` hang — worth their own tasks.

**Net:** COACHMOE01 confirms the verdict's framing (the oracle contract over a
mutating substrate was the hard part; once shape (grammar) + substance (gather) +
the deterministic absent-signal backstop are enforced, a *base* model adjudicates
honestly and catches real dishonesty) and converts "the green is hollow" into "the
green is now substantive on the frozen fixture — the remaining question is whether it
generalizes." The irreducible H2/H3 core has moved from *unsolved* to *demonstrated
on N=1*; H6 (generalization) is what's left to prove.
