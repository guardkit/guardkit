# AutoBuild Player–Coach: journey, current state, and recommendations (2026-06-11)

> **Why this exists.** A handoff written as the working session's context filled
> up. It captures the run-13→25 + FEAT-9DDE arc, the architecture as it actually
> stands, what's solved vs open, the meta-lessons (including corrections to our
> own earlier conclusions), and a prioritized recommendation list. Pairs with
> `player-coach-why-so-hard-conversation-starter.md` (framing) and
> `player-coach-why-so-hard-verdict.md` (the mid-arc evidence audit). Read those
> for the "why is this hard" analysis; read this for "where we are and what next."

---

## 1. State of play (one paragraph)

The AutoBuild Coach now produces **honest, schema-valid, substantive verdicts**
on the local gemma4:31b substrate, and the **false-green is closed** — run-25
was a real 3/3 (oracle actually ran, 100% per-AC verified, real evidence), and
on a **fresh** feature (FEAT-9DDE) the Coach stayed honest *and* the multi-layer
design caught a real bug. **But** three things are unresolved: the **B-full
investigation phase is effectively disabled** (degrades 100% at
`recursion_limit=12`), so the substance is really coming from the cheap **B-min**
path; the Coach's **bug-detection is bounded by its deterministic evidence** (it
approved code that didn't run; a *smoke gate*, not the Coach, caught it); and we
have **not** yet seen a clean **fresh-feature green** or an end-to-end
**catch→fix** cycle. The biggest open architectural question is now sharp:
**grow the deterministic evidence bundle vs. keep the expensive/flaky B-full
investigation.**

---

## 2. The run arc

FEAT-AOF is the **frozen quartet** (IA03/GD02/TP05 — hand-authored, the loop was
tuned against it). FEAT-9DDE (`/task-status --json`) is the **first fresh
feature**.

| Run | Build | Result | What it taught |
|---|---|---|---|
| 19 | D-3 toolless synthesis (COACHSPLIT) | 3/3 "approve", 52m | Verdict *emission* fixed — but a **FALSE-GREEN**: independent test timed out, Coach approved anyway, **0/5 criteria verified** |
| 20 | + COACHTESTTO (subprocess tests, 3.9s) | 3/3 "approve", 52m | Tests now run — **still false-green** (criteria empty). Wall-time wash: synthesis latency ate the saved 15 min |
| *(retro)* | evidence audit + red-team | — | Diagnosed the false-green; **refuted** the "missing-fine-tune" and "generative-vs-adjudicative" framings; hard core = *trustworthy gating verdict over a mutating substrate* |
| 21 | + COACHBFULL (B-full gather) | 1/3 | B-full **enriches** (IA03 `criteria_verification` populated); Wave-2 failure (later understood as F20 + a display bug) |
| 22 | B-full | 2/3 | TP05 **F20 ctx overflow** (108k/98k); discovered `--max-parallel` was display-only; F20 is **parallel/wave-pressure amplified** |
| 23 | B-full | FAILED (right reason) | 🎯 **Coach catches a REAL bug** (TP05 feedback, critical `TypeError`) — adversarial value proven. But the **41-min** turn exhausted budget before turn-2 could fix |
| 24 | + COACHTURNBUDGET | **25s crash**, 0/3 | Cross-repo regression: `build_autobuild_backend()` didn't accept the new `max_tool_result_chars` kwarg (BACKENDKWARG) |
| 25 | + BACKENDKWARG fix | 🎉 **3/3 real green**, 45m (fastest) | First **honest + substantive** green (oracle ran, 100% verified, real evidence). **BUT B-full degraded on all 3** (`recursion_limit=12`) → it's a **B-min green**; substance comes from B-min |
| 9DDE-1 | fresh feature, B-full→B-min | FAILED (right reason) | **Generalization:** Coach honest + 10/10 verified on unseen task — **but approved code that doesn't run** (import-path bug); the **smoke gate** caught it post-approval |

---

## 3. The architecture as it stands

```
Player (qwen36-workhorse, task-work delegation) ── creates code, tests
   │
test-orchestrator specialist (SPECHANG-contained)
   │
Coach — DETERMINISTIC layer  (CoachValidator.gather_evidence, pure Python)
   ├ independent tests (subprocess, COACHTESTTO ~3s)   ← honest oracle
   ├ coverage / honesty (CoachVerifier) / plan_audit / bdd / arch_review
   ├ COACHFG01 fail-closed: signal_absent ⇒ feedback (deterministic, not prompt)
   └→ CoachEvidenceBundle
   │
Coach — LLM verdict layer  (gemma4:31b, GBNF grammar)
   ├ Phase-A B-full gather (tool-using investigation)
   │     └ DEGRADES 100% at recursion_limit=12 (COACHTURNBUDGET Lever 3) → never runs
   └ Phase-B B-min synthesis (TOOLLESS + grammar) → verdict + populated criteria_verification
   │
Smoke gate (post-Coach, deterministic): runs the ACTUAL deliverable/CLI
   └ caught the FEAT-9DDE import bug the Coach + unit tests missed
   │
stop_on_failure → halts on gate failure
```

Substrate: gemma4:31b (dense QAT, q4_0) on llama.cpp/llama-swap on the GB10
(`promaxgb10-41b1:9000`); Player on qwen36-workhorse; LangGraph harness
(`GUARDKIT_HARNESS=langgraph`).

**Key truth to internalize:** the populated `criteria_verification` (the
"substance") comes from **B-min** (toolless grammar synthesis over the
deterministic bundle), **not** from B-full's investigation — B-full degrades
every run. B-full's *only* demonstrated unique value is the run-23 bug-catch,
which required it to actually run.

---

## 4. What's solved (and the task that did it)

| Capability | Status | Task(s) |
|---|---|---|
| Reliable verdict **emission** (no F24/empty-verdict) on the local substrate | ✅ | TASK-ARCH-COACHSPLIT (D-3, toolless GBNF synthesis) |
| Coach **independent tests** run (subprocess, ~3s, not a 300s LLM timeout) | ✅ | TASK-FIX-COACHTESTTO |
| **Fail-closed** on absent oracle (the false-green) — deterministic, not prompt | ✅ | TASK-FIX-COACHFG01 |
| Populated **`criteria_verification`** (per-AC, with evidence) — from B-min | ✅ | TASK-ARCH-COACHBFULL (+ the B-min prompt/grammar that graduated) |
| **F20** ctx overflow mitigated by **sequencing** (it's parallel-amplified) | ✅ | TASK-FIX-MAXPARALLEL01 (display fix; execution was already serial) |
| Cross-repo **kwarg regression** (run-24 25s crash) | ✅ | TASK-FIX-BACKENDKWARG (version-skew guard, non-silent) |
| **Green-gating pytest CI** + Python ≥3.11 floor | ✅ | TASK-INFRA-CIGREEN (CI landed; confirm task-file archival) |

---

## 5. What's open (the real frontier)

1. **The strategic call — deterministic-bundle-enrichment vs B-full investigation.**
   The bugs we actually catch are **mechanical** (run-23 `TypeError`; FEAT-9DDE
   import error), and **deterministic checks catch them cheaper and more
   reliably** than the flaky 41-min B-full gather. The smoke gate caught the
   FEAT-9DDE bug in ~1s. Strong lean: **grow the deterministic bundle** (fold
   runtime/CLI smoke checks in, fail-closed) over investing in B-full.
2. **B-full's fate.** It degrades **100%** at `recursion_limit=12` (COACHTURNBUDGET
   Lever 3), so it's effectively dead code carrying cost. Either **raise the
   limit** (and pay the latency — needs resident-g31) so it can converge + catch
   bugs, or **drop it**. Don't leave it half-on by default.
3. **Coach coverage is bounded by its evidence.** FEAT-9DDE: honest Coach,
   real verification, **approved code that doesn't run**. The Coach is **not the
   last line of defence** — a smoke gate is. Move that catch *earlier* (into the
   Coach's evidence).
4. **Catch→fix cycle never demonstrated end-to-end.** Run-23 caught but couldn't
   fix (budget); run-25 had no bug; FEAT-9DDE the *gate* caught it. We've shown
   the loop can *verify* and (once) *catch*; we've not shown *catch→fix→approve*.
5. **No clean fresh-feature green yet.** FEAT-9DDE-1 correctly FAILED on the
   import bug. Re-run after the fix for the first true generalization green.

---

## 6. Meta-lessons (including our own corrections)

- **The hard core (retro verdict):** ~40% *inherent* — emitting a **trustworthy
  gating verdict over a mutating, shared, stateful substrate** where a wrong
  "approve" ships broken code; ~48% *incidental* and mostly closed (mid-flight
  harness migration + dogfooding-on-self + self-hosting the judge); ~12% genuinely
  unknown (generalization). The two easy sibling repos run the *same* base local
  models in the *same* kind of gating loop — they were smooth because their Coach
  scores a **disposable in-context artefact**, not a verified claim about a
  mutating filesystem. **Substrate strength was never the differentiator.**
- **The false-green family is real and recurring** (absence-of-failure,
  path-string-mismatch, harness-cancellation). The project's *own design rules
  predicted its own failures.* COACHFG01 is the canonical remediation (wire the
  verifier into the *code* path; never trust the LLM to honour a prompt-only guard).
- **Cross-repo contract drift is a standing hazard** (BACKENDKWARG kwarg,
  model-threading F1/F9/F10/F12/F19, cancel-asymmetry). Unit tests mock
  guardkitfactory and miss it → TASK-INFRA-XREPOCONTRACT (CI smoke-test) is the
  durable guard.
- **Test/runtime divergence** (FEAT-9DDE: unit tests pass via pytest's import
  magic, CLI fails) — the `namespace-hygiene` rule's exact shape. Coverage that
  passes the *function* but not the *invocation* is a green that lies.
- **Our own wire-monitoring over-claimed twice** — "serial avoided the crash"
  (`--max-parallel` was display-only) and "COACHSYNTH solved F20" (isolation was
  the cause). **The Mac-side `coach_turn`/run-log snapshot is authoritative; the
  GB10 wire is an early signal, not a causal one.**

---

## 7. Recommendations (prioritized)

1. **Fold runtime/CLI smoke checks into the Coach evidence bundle, fail-closed.**
   *Highest leverage.* Moves the FEAT-9DDE-class catch from a post-hoc gate to
   the Coach layer (so it surfaces as *feedback* → turn-2 fix, not a post-approval
   failure). Same shape as COACHFG01. *(File a task.)*
2. **Make the B-full-vs-bundle decision deliberately, with a falsifier.** Take a
   *known-buggy* task; run **B-min (`GATHER=0`)** with the enriched bundle vs
   **B-full (raised recursion_limit)**. If enriched-B-min catches it → **drop
   B-full** and keep the fast/cheap path. If only B-full catches it → invest in
   making it actually run. *(Don't let `recursion_limit=12` decide this by
   default.)*
3. **Land TSJ-002 (bin-entry) or a `sys.path` shim → re-run FEAT-9DDE** for the
   first clean fresh-feature green (the real generalization result).
4. **Resolve B-full's half-on state.** If keeping it: raise `recursion_limit` +
   resident-g31 (the unshipped COACHTURNBUDGET latency levers) so a Coach turn
   leaves budget for turn-2. If dropping it: default `GUARDKIT_COACH_GATHER=0` and
   delete the dead path.
5. **Run TASK-INFRA-XREPOCONTRACT** (cross-repo contract CI) so the next
   signature drift is a 10s red build, not a 25s wasted run. Confirm CIGREEN's
   task-file archival.
6. **Deprioritize TASK-DATA-COACHHARVEST.** The retro refuted "missing fine-tune"
   as the cause; B-min already produces the substance. A Coach fine-tune is a
   *maybe-later speed/depth lever*, not the headline fix.
7. **Lower priority / housekeeping:** TASK-HMIG-BDDWIRE (multi-stack BDD oracle,
   fail-closed on `scenarios_run==0`); TASK-FIX-FRESHRESET01 (`--fresh` no-op on
   completed feature); **close TASK-OPS-COACHGRAMMAR** as superseded (the
   per-request grammar from D-3 replaced the route-level `--grammar-file`).

---

## 8. Task ledger

**Completed:** COACHSPLIT · COACHTESTTO · COACHFG01 · COACHBFULL · COACHSYNTH ·
COACHTURNBUDGET · MAXPARALLEL01 · BACKENDKWARG · XREPOCONTRACT *(filed; verify
landed)* · CIGREEN *(CI landed; verify task-file moved)*

**Backlog / open:** TASK-TSJ-001 *(deliverable buggy — import path)* ·
TASK-TSJ-002 *(bin-entry; fixes the import bug)* · TASK-HMIG-BDDWIRE ·
TASK-DATA-COACHHARVEST *(deprioritize)* · TASK-FIX-FRESHRESET01 ·
TASK-OPS-COACHGRAMMAR *(close as superseded)* · TASK-HMIG-011 *(cutover ceremony
— gated on a stable fresh-feature green)*

**To file (from §7):** "smoke check into Coach evidence bundle" (#1) · a short
B-full-vs-bundle **decision note** (#2).

---

## 9. The two decisive next experiments

1. **First fresh-feature green** — re-run FEAT-9DDE after the import fix. A clean
   3/3 here is the first evidence the loop generalizes beyond the frozen quartet.
2. **The bug-catching falsifier** — does deterministic-bundle-enriched **B-min**
   catch a *known* injected bug? This single experiment decides whether B-full
   stays or goes, and whether the future is "grow the bundle" (likely) or "fix the
   investigation."

---

## 10. Honest caveats for whoever picks this up

- **Runs 19–25 were all the frozen quartet.** "3/3 green" there proves *mechanics*,
  not *generality*. FEAT-9DDE is the first fresh feature — and it immediately
  surfaced a real bug, which is exactly what a generalization test should do.
- **Trust the Mac-side snapshot over the GB10 wire.** We over-read the wire twice.
- **False-green vigilance is permanent.** For any "green," check three things in
  the `coach_turn` JSON + run log: did the **oracle run** (`Independent tests
  passed in Xs`, no `signal_absent`)? is **`Criteria Progress` 100% verified**
  (not `0/N`)? and does the **deliverable actually run** (smoke gate)? A green that
  fails any of these is hollow.
- **"FAILED" is often the *right* outcome.** Run-23 and FEAT-9DDE-1 both "failed"
  because the system correctly refused to ship broken code. That is the loop
  working, not the loop breaking.
