# QA Verifier — State Consolidation · 2026-07-04

**Purpose:** the QA-Verifier thread forked. The 12 June session scoped and largely *built* the wiring-evidence layer (FEAT-C332, FEAT-E2CB), but the 2 July Phase-0 starter was written without that context and partially re-ideates the same layer under different names. This document reconciles them into one current state and one execution order. **Start here. Read the 2 July starter only through this reconciliation.**

**Sources consolidated (dated):** `docs/retro/qa-verifier-autobuild-session-handoff.md` (12 June) · `docs/retro/player-coach-why-so-hard-verdict.md` (9–11 June) · `docs/features/qa-verifier-wiring-probes-scope.md` (FEAT-C332 scope, 12 June) · `.claude/rules/stack-plugin-architecture.md` (12 June) · `docs/research/ideas/qa-verifier-behavioural-evidence-gates-conversation-starter.md` (2 July — unaware of FEAT-C332/E2CB) · code verified 2026-07-04.

---

## 1 · Verified current state (code + tasks, 2026-07-04)

| Component | Status | Evidence |
|---|---|---|
| Oracle honesty (false-green classes `signal_absent` + empty-criteria) | ✅ CLOSED (10–11 June; N=1 frozen fixture) | TASK-FIX-COACHFG01, TASK-ARCH-COACHBFULL; 26B-A4B MoE validated as Coach (COACHMOE01) |
| Coach honesty on **novel** work (H6, honesty axis) | ✅ Demonstrated once (FEAT-E2CB run 1: no false-green, 6/6 criteria populated, honest timeout) | run log `.guardkit/autobuild/FEAT-E2CB-run1-stdout.log` |
| **WiringAnalyzer** (stack-agnostic tree-sitter core + py/js/ts/csharp dialect DATA) | ✅ **BUILT** | `guardkitfactory/src/guardkitfactory/wiring/` (169f16c 12 June; 4122a2f 17 June ctor-arity) |
| Evidence bundle fields `wiring`, `mocked_seam`, `spec_gap` (Optional, absent-signal-safe) | ✅ **BUILT** | `guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py` ~L277–279 (a11708d0, 13 June) |
| Coach-validator wiring bridge (lazy import, `_run_wiring_analysis()`, `_compute_spec_gap()`) | ✅ **BUILT** | `coach_validator.py` L584–611 (0fadbd4f, 13 June) |
| BDDWIRE (factory BDD plugins → Coach) | ✅ Landed (f93e56b 12 June; guardkit side TASK-FIX-BDDFW01 15 June) | tasks/completed |
| TASK-FIX-LSTRACE01 (LangSmith executor crash) · TASK-FIX-BOOTPYTEST01 (worktree pytest) | ✅ Both FIXED 12 June | guardkitfactory 189ece6; completed task files |
| **FEAT-E2CB re-run** (the H6 generalization proof, post-fixes) | ✅ **EXECUTED 2026-07-04** — SUCCESS 2/2 tasks, 2 turns, 17m27s, first-attempt pass 100%; criteria 6/6 + 3/3 `verified`, honesty 1.00, independent tests RAN (8 passed, 3-4s), evidence_repos declared, no crash / no false-green. Caveat: deliverable already on main since June, so this validates the harness+Coach pipeline half of H6; Player-authoring half remains the June evidence | recipe verbatim; log `.guardkit/autobuild/FEAT-E2CB-run2-stdout.log`; durable record `docs/retro/evidence/FEAT-E2CB-run2-review-summary.md` |
| TASK-QAWE-004 (Wave 4: SPEC_GAP hard gate) | ✅ **ALREADY COMPLETED 2026-06-12 20:06** — this table's original "⏳ gated" row was stale (second fork instance). Code-verified 2026-07-04: `_apply_spec_gap_absent_guard` (`agent_invoker.py:6080`, wired `:2398`), `whole_file_deselection` absent-key safety, reproducer `tests/orchestrator/test_qawe_004_spec_gap.py`. §3.2 is a no-op | `tasks/completed/qa-wiring-evidence/TASK-QAWE-004-*.md` |
| Anti-stub body scan · runtime coverage/reachability gate · behavioural round-trip oracle | ✅ **L2 + L3 BUILT & MERGED 2026-07-04** (FEAT-10AC run 3: 5/5 approved, merged `888906f2` after operator review). **L4 = guard only**: `_apply_behavioural_oracle_guard` landed (tested, absent-signal-safe no-op) but the PRODUCER was never wired — `gather_evidence` hardcodes `behavioural_oracle=None`; the QAV-005 Player soft-pedaled the fs-01 AC to match. Runner-without-producer, caught at merge review by applying the feature's own ethos. Producer = **TASK-QAV-006 / FEAT-0E6D**: ✅ **BUILT + MERGED same night** (`fe949bb0`, 4 adversarial turns, 291 tests green; fs-01 verdict-flip now real, dogfood un-softened). **Phase 0 is code-complete: L1+L2+L3+L4 all merged.** Merge-review catch #2: the Player committed an intentionally-failing oracle to the repo tree (`tests/acceptance/x_roundtrip.py`) — excluded; it had survived its own build only via the independence check (live AC-3 proof). Build cost 3 runs + 2 orchestrator fixes: TASK-FIX-XREPOPROM01 (sibling-relative Player claims false-red → honesty collapse) and TASK-FIX-SIBTESTENV01 (sibling test_command pinned to wrong venv → stall; FIXED 2026-07-05: per-repo interpreter resolution + absent-signal stall immunity, in_review) | merged code: `coverage_gate.py`, `coach_evidence.py:319-321`, `coach_validator.py:3441/3471/3581`, `agent_invoker.py:6510`; evidence `docs/retro/evidence/FEAT-10AC-run3-review-summary.md` |
| TASK-AB-XREPOEV01 (cross-repo evidence architecture) | Filed, not detailed | backlog |

**Correction to the 2026-07-04 SPL/panel docs:** their "QAV Phase 0 gates absent in code" row is wrong as stated — the *wiring-evidence* layer is built; what's absent is the *stub/behaviour* layer below.

## 2 · The reconciliation — the two framings are complementary layers, not duplicates

FEAT-C332 answers "**is this code wired into the system?**" (syntactic: reference graph, composition roots, mocked seams, BDD scenario coverage). The Phase-0 starter answers "**does this code actually do anything when executed?**" (semantic: empty bodies, runtime reachability, behavioural round-trip). **FEAT-C332 does not catch a correctly-wired stub; the Phase-0 gates do not catch unwired code. Closing the fs-01 class needs both.**

| Layer | Question | Status | Names |
|---|---|---|---|
| L1 Wiring probes | referenced anywhere non-test? composition root reached? seam mocked? | ✅ built (Wave 4 pending) | UNWIRED_PATH, MOCKED_SEAM, SPEC_GAP (FEAT-C332) |
| L2 Anti-stub body scan | does the body contain executable logic (vs pass/…/bare return/TODO)? | ❌ new | Phase-0 gate 1 |
| L3 Runtime coverage/reachability | do tests actually execute the public surface (pytest --cov)? | ❌ new | Phase-0 gate 2 |
| L4 Behavioural round-trip oracle | does an oracle the Player didn't author pass against the live dependency? | ❌ new | Phase-0 gate 3 (parity-harness pattern) |

**Binding constraints on the new work:**
- **Stack-agnostic rule governs L2** (`.claude/rules/stack-plugin-architecture.md`): the anti-stub scan is **tree-sitter + dialect data**, NOT Python's `ast` module — the starter's "deterministic Python" phrasing must not be read as Python-ast. Extend the existing WiringAnalyzer dialect descriptors; do not build a parallel analyzer.
- **Schema decision (resolves starter OQ#1 + sweep contradiction #4):** extend the existing `CoachEvidenceBundle` sibling-field pattern (`stub_scan`, `coverage`, `behavioural_oracle` as Optional, absent-signal-safe) — the single `behavioural_evidence` block the starter sketched is superseded; what forge's seam consumes is the bundle. Record as an additive, versioned seam change in the dependable-forge overview when it lands.
- **A1–A6 stand unchanged** (LLM judge + deterministic evidence; oracle the Player didn't author; Phase 0 before fine-tune; 26B-A4B MoE base; golden set opportunistic; B-min only). Nothing in the June work conflicts with them.
- Missing-vs-failed oracle policy (starter OQ#4): default per the June absent-signal discipline — **failed oracle = hard RED; absent oracle = WARN in v0**, revisit once one real feature has shipped with an oracle.

## 3 · Execution order (Fable window, priority order)

1. **Re-run FEAT-E2CB** with the documented recipe (handoff §"Validated autobuild recipe", GB10, blockers fixed, live via editable install). Cheapest, highest-value: proves H6 generalization post-fix and unblocks Wave 4. If the Player still can't converge, the lever is Player-side (turns/model) — not the Coach.
2. **TASK-QAWE-004** (SPEC_GAP hard gate) once FEAT-E2CB merges.
3. **`/feature-spec` for the NEW gates only** (working name FEAT-QAV-001: L2 anti-stub + L3 coverage + L4 behavioural oracle), with **this document + the FEAT-C332 scope + the 2 July starter** as context, explicitly excluding L1 (built) and adopting the schema decision above. `/feature-plan`, then autobuild per the recipe.
4. **Update the 2 July starter** with a banner pointing here (one line, no rewrite), and mark the SPL/panel docs' QAV state rows corrected (done in ai-transition same day).

## 4 · Do not re-derive

The hard verdict is already in: the difficulty was a trustworthy gating verdict over a mutating substrate (H2/H3), not a missing fine-tune (H1 refuted); judgment erred strict, the shared oracle held the false greens; the fine-tune (TASK-DATA-COACHHARVEST) is a future lever, not the stub-catcher. The wiring layer exists — extend it, don't rebuild it.

---

*Prepared 2026-07-04 from a five-source sweep + code verification. Supersedes-for-orientation all QAV docs above; they remain the detail record.*
