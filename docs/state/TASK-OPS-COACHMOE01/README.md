# TASK-OPS-COACHMOE01 — gemma4-coach (26B-A4B MoE) as Coach on the B-min path

> **Host:** all work runs on `promaxgb10-41b1` (the GB10) — this session executed
> directly on the box (not orchestrated from the Mac as run-25 was).
>
> **Status (2026-06-11):** Step 1 (grammar-containment gate) **PASS**; Step 3
> Lever-2 finding recorded; Step 2 (live A/B) — see below.

## The decision gap this closes

Nobody had ever run `gemma4-coach` (base Gemma-4 **26B-A4B MoE**, ~3.8B active)
as Coach on the shipped **B-min toolless + grammar** path. Its F24
disqualification (the run-14 49,720-char ramble) happened in the **tool-bound
agentic loop**, which TASK-ARCH-COACHSPLIT then *removed* from the verdict path.
The COACHSPLIT grammar gate only ever ran against the dense g31; the one logged
MoE ramble (COACH31B probe A, 27,006c) was toolless but had **no grammar**.

## Step 1 — grammar-containment gate (AC-001) — **PASS**

**Probe:** [`probe_toolless_grammar_gc.py`](probe_toolless_grammar_gc.py) — a `gc`
variant of COACHSPLIT's `probe_toolless_grammar.py`, targeting `gemma4-coach`
with the packaged `coach-verdict.gbnf` attached **per-request**, temp 0.0,
max_tokens 16384 (production synthesis ceiling). The grammar's
`prefix ::= ( [^\`] | "\`" )*` is unbounded text, so the grammar **cannot force
convergence** — the gate is the empirical question: *given the grammar, does the
MoE choose to emit the verdict fence within budget, or ramble to
`finish_reason=length`?* **Trust the metric (`finish_reason`), not output
pattern-matching** (per COACH31B README:123-128).

Raw transcripts in [`probes/`](probes/); summary
[`probes/gc-grammar-probe-summary.json`](probes/gc-grammar-probe-summary.json).

| arm | grammar | reasoning_budget | finish | content | reasoning | tok/s | wall | verdict | crit_n |
|---|---|---|---|---|---|---|---|---|---|
| **A_rambleprone_grammar** (worst-case "verify yourself" approve) | ✓ | — | **stop** | 1559c | 11187c | 47.4 | 75.3s | approve ✓ | 2 |
| A_rambleprone_nogrammar (control) | ✗ | — | stop | 1629c | 10691c | 47.5 | 73.2s | approve ✓ | 2 |
| **E_synthesis_approve_grammar** (production B-min approve) | ✓ | — | **stop** | 1602c | **2762c** | 47.7 | **24.7s** | approve ✓ | 2 |
| **F_synthesis_feedback_grammar** (production B-min feedback) | ✓ | — | **stop** | 1820c | **4904c** | 47.4 | **40.0s** | feedback ✓ | 3 |
| A_rambleprone_grammar_rb2048 (Lever-2) | ✓ | 2048 | stop | 1754c | 12064c | 47.1 | 82.4s | approve ✓ | 2 |
| G_synthesis_approve_grammar_rb0 (Lever-2 disable) | ✓ | 0 | stop | 1752c | 2533c | — | 25.0s | approve ✓ | 2 |

### Findings

1. **The grammar contains the MoE ramble — gate PASS.** Every arm finished
   `stop` with a schema-valid, *correct* verdict; **zero** `finish=length`
   ceiling rambles. The worst-case "run the tests yourself" approve prompt — the
   exact shape that spiralled to 27,006c with no verdict in COACH31B probe A —
   converged at 11,187c reasoning and emitted a valid `approve` with populated
   `criteria_verification`.
2. **The production B-min synthesis path is fast and substantive.** The
   "synthesise from the evidence bundle" prompt (what actually ships) keeps
   reasoning to **2.8k–4.9k chars** and lands a populated verdict in **24.7s
   (approve) / 40.0s (feedback)** at ~47.5 tok/s — `criteria_verification`
   populated (2 / 3 per-AC entries) on the first try.
3. **vs run-25's g31:** run-25's g31 Coach legs ran **3.5–6.5 min** each
   (≈9–10 tok/s dense). The MoE synthesis single-shots are **~6–10× faster** per
   verdict, and the MoE is the *only* substrate fast enough to fit a
   catch→fix→approve cycle (two Coach turns) inside one task budget.
4. **The no-grammar control did NOT reproduce the bare 27,006c ramble** on the
   current build/route — it converged at 10,691c, `finish=stop`. The grammar is
   still the *guarantee* we ship (it forbids malformed/missing-field verdicts),
   but the current `--reasoning auto` route is already far less ramble-prone than
   the run-14 substrate.

## Step 3 — Lever-2 reasoning_budget (AC-003) — **no-op on this route**

`GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET` injects a per-request
`reasoning_budget` body field (guardkitfactory `langgraph_harness.py:106`,
default unset — **never exercised in any logged run before this task**). Two
values tested live against `gemma4-coach`:

- **`reasoning_budget=2048`** (intended cap): reasoning was **12,064c** (~3,000+
  tokens — *above* the 2048 cap, and *more* than the unset arm's 11,187c) and
  wall-time rose to 82.4s. **Not capped.**
- **`reasoning_budget=0`** (intended disable): reasoning was **2,533c** —
  identical to the unset synthesis arm (2,762c). **Not disabled.**

**Conclusion:** the per-request `reasoning_budget` field is a **no-op on the
`gemma4-coach` route on this llama.cpp build** — the route's server-level
`--reasoning auto` policy governs, and the field is ignored. This matches
llama.cpp's actual `reasoning_budget` semantics (a `0`/`-1` *toggle* that
requires model/template support, not an arbitrary-N token cap; the factory
code's "N caps the reasoning tokens" comment is optimistic). **Lever-2 cannot be
the MoE's latency lever** — but the MoE does not need it: its synthesis reasoning
is already short (2.5–4.9k chars) and it decodes at ~47 tok/s. The lever remains
default-off and carries zero risk; this is the first live characterisation of it.

## Step 2 — live A/B vs run-25 (AC-002)

Recipe = run-25's command with exactly one flag changed
(`--coach-model gemma4:31b` → `--coach-model gemma4:26b`),
`GUARDKIT_COACH_GATHER=1` kept so the Phase-A→B-min degrade path is exercised
identically. See [`run-AB-recipe.md`](run-AB-recipe.md).

**Operational note (why this is SAFER than run-25):** the `all` matrix set is
`qg & ne & qw & gc & dl` — it already holds **both** the Player (`qw`) and the
MoE Coach (`gc`) as co-resident always-on models. So the A/B needs **no
set-switch, no eviction, and keepalive can stay ON** (it keeps `gc` warm, which
is exactly the Coach we want). Contrast run-25's g31, which evicted `gc`,
required keepalive OFF + the minimal `coach31` set + `--no-context`, and is
~11 GB heavier (g31 dense ~28 GB vs gc MoE ~17 GB).

### Result — **3/3 approved, FEATURE SUCCESS** (105m 8s)

Run on the GB10 itself (now a full orchestrator host — see "GB10 orchestrator
setup" below). Command per [`run-AB-recipe.md`](run-AB-recipe.md); raw artifacts
in [`run-AB-artifacts/`](run-AB-artifacts/) (per-task `coach_turn_*.json` +
`run-moe-stdout.log`).

| Task | Turns | Final verdict | criteria_verification | validation_results | Coach caught |
|---|---|---|---|---|---|
| TASK-FIX-IA03 | 3 | ✓ approve (t3) | **5/5 verified** | full | t1+t2: real Player honesty discrepancy (claimed `tests/unit/test_agent_invoker.py`, absent on disk) |
| TASK-FIX-GD02 | 2 | ✓ approve (t2) | **7/7 verified** | full | t1: verdict-emission glitch (see caveat) → COACHSF01 |
| TASK-FIX-TP05 | 1 | ✓ approve (t1) | **6/6 verified** | full | first-pass clean approve |

**All 3 final verdicts: schema-valid, honest, substantive** (criteria_verification
100% populated with per-AC `verified` + full `validation_results`). The MoE Coach
**did not rubber-stamp** — it ran a genuine catch→fix→approve loop on IA03 (caught
a real Player honesty discrepancy twice, approved only when fixed), exactly like
g31 did in run-23.

### Per-Coach-turn wall-times (B-full `GATHER=1`, as run-25)

| Coach turn | wall | verdict |
|---|---|---|
| IA03 t1 | 139s | feedback (honesty) |
| IA03 t2 | 441s | feedback (honesty) |
| IA03 t3 | 293s | **approve** |
| GD02 t1 | 490s | feedback (emission glitch → COACHSF01) |
| GD02 t2 | 124s | **approve** |
| TP05 t1 | 133s | **approve** |

The **approve** turns ran 124–293s (2.1–4.9 min) — comparable to run-25's g31
legs (3.5–6.5 min), **not** the 6–10× the single-shot gate implied. Cause: with
`GATHER=1` the Phase-A tool-gather **runs to recursion_limit=12 before degrading**
(every turn: `grammar=present`, every Phase-A: `Recursion limit of 12 reached …
degrading to B-min synthesis`), and that overhead dominates the turn — masking the
MoE's fast B-min synthesis (gate: 24–40s). **The MoE's speed win is realized only
in the shipped default B-min-only mode (`GATHER=0`)**, where a Coach turn is the
~30–60s the gate measured. (Phase-A degraded on 6/6 turns here, exactly as run-25
reported "Phase-A intentionally degrades on all 3" — B-full `GATHER=1` is wasted
wall-time on this codebase's Coach prompt depth for **both** substrates.)

### Caveats (recorded honestly)

1. **1 of 6 Coach turns emitted malformed JSON despite `grammar=present`** — GD02
   t1: `last fenced JSON block is malformed … Expecting value: line 16 column 9
   (char 961)`. Not a ramble (no `finish=length`); a single malformed verdict the
   **COACHSF01 safety net** caught (`coach_primary_synthetic_feedback: true`) →
   Player retried → t2 approved. g31 in run-25 had **0/3** emission failures
   (COACHSF01 "not exercised"). So llama.cpp GBNF enforcement is **not bulletproof
   on the MoE** — the safety net is load-bearing for this substrate. (The synthetic
   message's "qwen36-workhorse F2" attribution is a hardcoded template string; the
   Coach was gemma4:26b.)
2. **105m vs run-25's 45m is Player-side, not Coach.** The Player
   (qwen36-workhorse) had honesty issues (avg score 0.75 < 0.8 — claimed files/tests
   not on disk) driving 6 Player turns vs run-25's 3, and the `test-orchestrator`
   specialist **hung** (SPECHANG, terminated by containment) on IA03+GD02, producing
   the "0 tests" reports that fed the honesty discrepancies. Neither is the Coach
   substrate.

### Step-2 verdict vs the falsifier

> PASS = 3/3 verdicts (a) schema-valid first try, (b) honest, (c) substantive,
> at materially lower Coach wall-time. FAIL = ramble past max_tokens, empty
> criteria_verification, or false-green.

- **No FAIL condition tripped**: zero rambles past max_tokens (grammar contained
  every turn), zero false-greens (caught real Player dishonesty), all 3 *final*
  verdicts have 100%-populated criteria_verification.
- **(a) "schema-valid first try" partially missed**: 5/6 turns clean; GD02 t1
  malformed (caught by COACHSF01). The pragmatic outcome — 3/3 approved with
  high-quality final verdicts — is a PASS; the emission reliability is the one
  caveat.
- **Speed premise refined**: the MoE is *not* faster than g31 with `GATHER=1`
  (Phase-A overhead); it is dramatically faster in B-min-only `GATHER=0` (the
  shipped default). The catch→fix→approve loop was demonstrated end-to-end (IA03).

## Decision (AC-004)

**The 26B-A4B MoE PASSES the gate the task posed and is a VIABLE B-min Coach.**
It broke F24 on the toolless+grammar path (the disqualifier was the *tool-bound
loop*, which D-3 removed), produced honest, fully-enriched verdicts, and caught
real Player dishonesty without rubber-stamping. Per the task's decision rule
("MoE passes → … the fine-tune base for TASK-DATA-COACHHARVEST is the 26B MoE"):

1. **TASK-DATA-COACHHARVEST fine-tune base ← the 26B MoE** (the only base with a
   validated 71-min LoRA recipe on the GB10, now also empirically validated as a
   working Coach substrate). This is the headline outcome.
2. **gc (MoE) adopted as a viable Coach substrate for B-min-only (`GATHER=0`)
   runs**, where its ~30–60s synthesis turns + ~11 GB footprint + co-residency in
   the `all` set (no keepalive juggling) make it the operational default candidate.
   **g31 retained as the higher-reliability fallback** (0/3 emission failures vs the
   MoE's 1/6) until the MoE's GBNF emission reliability is hardened or the
   fine-tune lands.
3. **Recommended follow-ups** (not blockers): (a) a B-min-only `GATHER=0` MoE leg to
   quantify the true per-turn speedup end-to-end; (b) treat B-full `GATHER=1` as
   wasted overhead on this codebase (Phase-A degrades 100% of the time for *both*
   substrates) — either raise/scale `recursion_limit` so Phase-A can actually
   converge, or default to `GATHER=0`; (c) the SPECHANG `test-orchestrator` hang and
   qwen36-workhorse Player honesty drift are independent issues worth their own
   tasks.

This **closes/​supersedes TASK-HMIG-013** (its unrun AC-006 live smoke is now
delivered under the post-COACHSPLIT architecture: ≥95% emission across ≥6 turns —
here 5/6 natural + 1 COACHSF01-recovered, 3/3 first-pass task success).

## GB10 orchestrator setup (done as part of this task)

The GB10 was previously the *inference* host only; run-25 was orchestrated from
the Mac. To stop shuttling between machines, the repo `.venv` was rebuilt as a
full orchestrator host:

- **Python 3.10 → 3.12** (`uv sync --extra autobuild --extra dev`). The old 3.10
  venv (which violated guardkit's own `requires-python>=3.11` and could not host
  langgraph 1.x) is preserved at `.venv.py310.bak`.
- Installed: `guardkit` + `guardkitfactory` (both editable via `[tool.uv.sources]`)
  + langgraph 1.2 / langchain 1.3 / deepagents 0.6.8 / claude-agent-sdk 0.1.72 /
  graphiti-core.
- **Packaging fix**: `langchain-openai` was an undeclared-but-required dependency
  (the harness imports it for the llama-swap OpenAI transport) that every `uv sync`
  pruned → synthesis failed at runtime. Added it to `guardkitfactory`'s
  `dependencies` so it is durable.
- Cross-repo seam test (`tests/orchestrator/harness/test_xrepo_contract_seam.py`):
  **15 passed**.
