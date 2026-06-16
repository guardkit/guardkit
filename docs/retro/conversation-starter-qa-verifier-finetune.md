# Conversation Starter — QA-Verifier Fine-Tune (piece #1) + Glue Policy (piece #3)

**Status when this was written:** BLOCKED on a decision, not on effort. Do not write the fine-tune spec yet — read why below.

## Where this thread is

The QA-Verifier is the second fine-tuned judgment agent (after the architect). It has three pieces:
- **Piece #2 — deterministic wiring evidence — ✅ BUILT.** Tree-sitter `WiringAnalyzer` + dialect descriptors emitting `UNWIRED_PATH` / `MOCKED_SEAM` / `SPEC_GAP` into the CoachEvidenceBundle. Shipped as FEAT-C332 + FEAT-E2CB (BDDWIRE), now in `guardkit/tasks/completed/`.
- **Piece #1 — the fine-tune scope — NOT WRITTEN (this thread).**
- **Piece #3 — the glue policy — NOT WRITTEN (this thread).**

## Why #1 and #3 are not written yet — the live dependency

The QA-Verifier fine-tune trains a dataset whose **input contract is the B-phase Coach synthesis shape**. That shape is contingent on an unmade decision: **TASK-PERF-COACHGATHER01** (Phase-A gather degrades to B-min 100% of the time on the 26B MoE — `Recursion limit of 12 reached`).
- **Option A** (make gather converge) → the verifier trains on gather-*enriched* bundles.
- **Option B** (retire B-full, ship B-min-only) → it trains on the B-min contract, and the "gather-probe" framing collapses into "the probes already run deterministically."

Writing the fine-tune spec before this decision means guessing the dataset's input shape. So: **decide COACHGATHER01 first, then write #1 and #3 in the same session as the findings-doc sync.**

Rich's stated plan: action COACHGATHER01 **after the next autobuild run completes**, to address the root cause.

## The most recent work (context, already done)

A batch of four trust-boundary fixes surfaced by the FEAT-C332 build was reviewed and saved. Headline: **none was a false-GREEN** — the Coach stayed conservative under genuine cross-repo stress; only the scaffolding around the verdict (attribution, evidence scope, narration) broke and got hardened. Three of the four name COACHGATHER01 as the upstream cause — i.e. four guards now sit atop the one unaddressed degradation, which is the argument for fixing it sooner than its "medium" priority implies.

## Do this when the thread resumes (in order)

1. **After the next autobuild run:** action **COACHGATHER01** — decide Option A (make Phase-A converge; re-check the 98K-window budget = `recursion_limit × max_tool_result_chars`) vs Option B (retire B-full). Its investigate-first step has four documented run-2 failure cases as input.
2. **Then, in one session:** sync the findings doc (it's stale in three places — see its own header notes: §2.4 H1-refuted / 26B-MoE validated / 31B demoted; §3.1 C332 built; §3.2 taxonomy implemented) **and** write QA-Verifier piece #1 (fine-tune scope) + piece #3 (glue policy) against the now-settled contract.
3. Recommended while BDDWIRE is still open: C332 OQ#1 — fold `executed_scenarios` into BDDWIRE for per-scenario `SPEC_GAP` vs count-only.

## Key docs

- **Trust-boundary batch review (most recent):** `guardkit/docs/reviews/feat-c332-trust-boundary-batch-review.md`
- **The blocking decision/task:** `guardkit/tasks/backlog/autobuild-harness-migration/TASK-PERF-COACHGATHER01-resolve-bfull-phase-a-always-degrades.md`
- **Piece #2 scope (built, for reference):** `guardkit/docs/features/qa-verifier-wiring-probes-scope.md`
- **Session handoff:** `guardkit/docs/retro/qa-verifier-autobuild-session-handoff.md`
- **Findings doc (needs the sync in step 2):** `ai-transition/docs/fine-tuned-judgment-agents-findings.md`

## Working notes

- Claude Desktop authors docs via Filesystem MCP; bash container can't reach `/Users`. Claude Code/OpenCode implements.
- Base model for the judgment fleet is **Gemma 4 26B-A4B MoE** (COACHMOE01 refuted H1; schema enforced at serving via GBNF, not the fine-tune).
- The two fine-tune threads (QA-Verifier, PO) meet at the `/feature-spec` boundary: PO `extract` emits `feature_spec_inputs/*.md` → `/feature-spec` curates to Gherkin → QA-Verifier validates against it.
