---
task_id: TASK-REV-F6E1
title: forge-run-6 fix-or-revert decision
review_mode: decision
review_depth: standard
created: 2026-04-25T13:30:00Z
revised: 2026-04-25T14:30:00Z
status: review_complete
deadline: 2026-04-25T23:00:00Z
---

# forge-run-6: Fix-or-Revert Decision Report

> **Revision 2 (2026-04-25 14:30)** — Supersedes the recommendation
> below. See **§ Revision 2** at the end of this document. Original
> v1 retained for audit. Two corrections from user feedback:
>
> 1. **Timeline**: this is 3-4 days of work, not three weeks. The
>    "fix-class genealogy" calendar I cited was wrong. forge-run-1 was
>    yesterday (2026-04-24), not week 3.
> 2. **Strategy**: today's window allows 3-4 fix/test iterations, not
>    one. Push for a real fix today, not a tactical bypass + revert.
>
> And one diagnostic correction: the *real* defect is structural —
> the agent-invocations gate **short-circuits before AC verification
> runs**. That's why "we keep iterating and quality stays at 80%."

## TL;DR — Recommendation (v1, superseded)

**[I]mplement F2' (per-task direct-mode bypass)** — set
`implementation_mode: direct` in the frontmatter of TASK-NFI-003,
TASK-NFI-006, TASK-NFI-007 (and any subsequent NFI tasks of the same
shape) in the FEAT-FORGE-002 feature manifest. Re-run forge.

**Why this not the alternatives**: this is option (b) the stall message
itself surfaces — the system designers built this exact escape hatch.
ETA ≤ 30 min including forge re-run. Touches **zero AutoBuild code**
(blast radius: three task files in the forge repo). All four refuted
prompt-class fixes have proven that *every gate built on Player
tool-use discretion is one stochastic choice from the failure mode we
just hit*; adding a fifth attempt today does not change that. The
structural answer (mirror FEAT-AB59 to Phase 3) is filed as F1 —
**tomorrow's workstream, not today's.**

**Pivot rule**: if forge-run-7 does not reach Wave 2 green by **20:30**,
freeze AutoBuild on commit `73a12c00` (current HEAD, FEAT-AB59 wiring
intact) and resume tomorrow with F1. Do **not** revert FEAT-AB59:
there is no green forge state to revert to.

---

## AC-001 — Failure signature confirmed end-to-end

forge-run-6 (1575 lines, 2026-04-25 11:22–11:55) fully read.

The three Wave-2 stalls (TASK-NFI-003, NFI-006, NFI-007) share an
**identical signature** across the full Coach-stall → orchestrator
unrecoverable → on-disk gate-block chain:

| Stage | Evidence |
|-------|----------|
| Player implementation | All three turns succeeded — 32/41/37 files created, 47–67 modified, 0–1 tests passing per turn (lines 1298–1307, 1398–1407, 1481–1489) |
| Coach validation | `Agent-invocations gate rejected: missing phases 3` × 3 consecutive turns (lines 1376, 1459) |
| Stall classification | `coach_agent_invocations_stall` co-fired with `context_pollution_stall_no_checkpoint` (lines 1322, 1422, 1505) |
| Orchestrator decision | `Unrecoverable stall detected … context pollution but no passing checkpoint` (lines 1291, 1391, 1474) |
| On-disk block | `agent_invocations_validation: missing_phases ['3'], expected 3, actual 2` (gate-block schema confirmed at `agent_invoker.py:5562–5656`) |

**FEAT-AB59 wiring fired correctly** on every non-direct task:

> 9× `Injected orchestrator specialist records into … task_work_results.json (merged=2, validation=violation)` — lines 683, 755, 853, 951, 1046, 1171, 1254, 1354, 1437.

`merged=2` confirms Phase 4 + Phase 5 records were written
orchestrator-side as designed. **The problem moved to Phase 3.**

---

## AC-002 — Fix-class genealogy (the meta-pattern)

The Coach's `agent_invocations_validation` gate is a single defect
family with five iterations in 12 days:

| # | Date | Commit | Workstream | Outcome |
|---|------|--------|------------|---------|
| 1 | 2026-04-23 08:00 | `7c14c01d` | RWOP1.3.1 — wire validator into producer | Gate becomes load-bearing for first time |
| 2 | 2026-04-24 14:23 | `7b730c72`–`c40d9340` | 7A0x stability series (sdk pin, message-types, bootstrap, stall classification) | Forge runs 1/2 still failed on infrastructure; runs 3/4/5 hit gate |
| 3 | 2026-04-24 19:25 | `7f8f14ba` | TASK-FIX-7A08 — mandate Task-tool invocation in Player prompt | **Refuted** — reverted same-day (`9d304ed9`/`d58b91a1`/`a8789317`) |
| 4 | 2026-04-25 09:30–10:41 | `f62047b3` → `355e439d` | FEAT-AB59 / OSI-001..006 — orchestrator-side specialist invocation for Phases 4 & 5 | **Verified working** by TASK-REV-45750 + forge-run-6 incidental live-SDK confirmation. Phase 3 untouched by design |
| 5 | 2026-04-25 11:22 | (forge-run-6) | The Phase 3 variant of the same defect class surfaces as the new bottleneck | **Today's decision point** |

**Meta-rule**: every gate that depends on the Player LLM choosing to
invoke a specialist via the `Task` tool is *prompt-class-fragile*. We
have proven this twice (TASK-FIX-7A08 refuted; today's Phase 3 stall is
the same shape). **The only fixes that have stuck are structural ones
that remove the Player from the tool-call loop entirely** (FEAT-AB59 for
Phases 4/5).

---

## AC-003 — Bisect anchor: where was the last known green?

**The user's anchor is correct**: the last known-green AutoBuild
predates forge entirely.

Evidence (autobuild events.jsonl across all sibling repos):

| Repo | Feature | Run timestamp | Result |
|------|---------|---------------|--------|
| nats-core | FEAT-2637 | 2026-04-08 19:25–19:37 | ✅ tasks_completed=2, failures=0 |
| nats-core | FEAT-310F / DCBD / DD0E / 3845 / BEA5 | 2026-04-08 19:58 → 23:49 | ✅ all green, 1 task each |
| nats-infrastructure | FEAT-B464 / 7044 / 7B86 | 2026-04-13 20:19 → 23:01 | ✅ green, 2–4 tasks each |
| forge | FEAT-FORGE-002 run 1 | 2026-04-24 12:32 | ❌ rate_limit_event SDK error |
| forge | FEAT-FORGE-002 run 2 | 2026-04-24 ~11:32 | ❌ authentication_failed |
| forge | FEAT-FORGE-002 runs 3/4/5 | 2026-04-24 → 25 | ❌ Phase 4/5 prompt-class stalls |
| forge | FEAT-FORGE-002 run 6 | 2026-04-25 11:22 | ❌ Phase 3 prompt-class stall |

**Last green AutoBuild: 2026-04-13 ~23:01 (nats-infrastructure FEAT-7B86).** 11-day gap to the first forge attempt.

**Pivotal commit that made the gate load-bearing**: `7c14c01d`
(2026-04-23 08:00:38) `fix(autobuild): wire agent_invocations validator
into producer (TASK-FIX-RWOP1.3.1)`. Before this commit, the validator
function existed but was not written to the producer's task_work_results
output, so the Coach had no on-disk gate-block to reject on. After it,
every task carries a gate verdict that can either pass, no_data, or
violate.

**What reverting `7c14c01d` would lose** (one-line diff-summary): the
producer-wiring of `agent_invocations_validation` and the downstream
RWOP1.3.2 (`plan_audit producer`, `83831b48`) and OSI-002
(`a0c08fb8`, credit orchestrator-invoked Phase 4/5 in the gate). Net
effect: the Coach loses ALL phase-invocation evidence, including the
Phase 4/5 evidence that FEAT-AB59 was just built to provide. **This
makes a clean revert mutually exclusive with FEAT-AB59.** That's why
revert is not the recommended path — the only thing it achieves
that F2' doesn't is also undoing useful phase-4/5 verification.

---

## AC-004 — Options scored

Window remaining after this review: **~7 h** (review consuming 60 min,
2 h slack reserved for "fix didn't work, revert anyway").

| | F1 — Mirror FEAT-AB59 to Phase 3 | F2 — Widen direct-mode autodetect (`agent_invoker.py:3753`) | F2' — Per-task `implementation_mode: direct` on NFI-003/006/007 | F3 — Soften gate: `violation` → `warning` when files modified > 0 | F4 — Revert `7c14c01d` + dependents (loses FEAT-AB59) |
|---|---|---|---|---|---|
| **ETA** | 6–8 h focused | 2–3 h (`scaffolding+complexity≤1` predicate needs care) | **10 min + 30 min forge re-run** | 1.5–2 h | 1.5 h |
| **Probability forge Wave 2 unblocks today** | ~30 % | ~50 % (predicate may not match feature-typed NFI tasks) | **~75 %** (uses system's own designed escape hatch) | ~55 % (Player attention shifts off unsolvable gate; criteria progression still uncertain) | ~70 % (gate goes silent globally) |
| **Regression risk** | Medium-high (new orchestrator-side runner under time pressure) | Medium (changes auto-detect for all stacks/tasks) | **Very low** (3 task files in forge repo only) | Medium-high (softening gate is hard to reverse later) | High (loses verified-good FEAT-AB59 phase-4/5 verification) |
| **Reversibility** | Easy (revert OSI-Phase3 commit) | Easy | **Trivial** (delete 3 lines of frontmatter) | **Hard** (gate-as-warning becomes load-bearing) | Easy in code, hard in trust |
| **Survives next failure variant?** | **Yes** — structural for Phase 3 | No (still LLM-prompt-class) | No (per-task — doesn't generalise) | No (silences the signal) | No (silences globally) |
| **Pivot wall-clock if chosen** | n/a (don't start today) | 18:30 abandon → fall to F2' | **20:30** abandon → freeze AutoBuild | 19:00 abandon → fall to F2' | 21:00 abandon → freeze |

---

## AC-005 — Recommendation + the honest answer

**Choose F2': set `implementation_mode: direct` on TASK-NFI-003,
TASK-NFI-006, TASK-NFI-007 in the forge feature manifest, then re-run
`guardkit autobuild feature FEAT-FORGE-002 --resume`.** File F1
(structural Phase 3 fix) as tomorrow's calmer-waters workstream.

**Why this is right under time pressure** (all four reasons):

1. **The system already provides this escape hatch.** The stall message
   itself names `implementation_mode: direct` as remediation option (b)
   on lines 1320, 1420, 1503 of forge-run-6. The direct path
   (`agent_invoker.py:_invoke_player_direct` + `_write_direct_mode_results`)
   writes a `quality_gates_relaxed: True` results file with no
   `agent_invocations` block, and the gate's `_extract_invocations_from_result_data`
   correctly returns `status: "no_data"` (skip-block, line 5594) — by
   design.
2. **No code change to AutoBuild today.** Three task-file frontmatter
   edits in the *forge* repo. Zero risk of touching the wiring that
   FEAT-AB59 just verified-working.
3. **The "revert to last green" instinct doesn't apply here.** Forge
   has never been green. The only green-anchored sibling repos
   (nats-core, nats-infrastructure) ran on simpler features that
   pre-date the gate becoming load-bearing. Reverting AutoBuild reverts
   into a state that is *worse* (loses FEAT-AB59 Phase 4/5 verification)
   without unblocking the structural problem (Phase 3 prompt-class
   fragility persists).
4. **F1 is the right answer, just not today.** Phase 3 has more variance
   than Phases 4/5 had — per-stack specialist routing, larger allowed_tools
   set, larger prompt context, and a genuine open design question
   ("orchestrator runs the Phase-3 specialist *alongside* the Player or
   *instead of* the Player?"). FEAT-AB59 took ~5 h of focused work for a
   simpler design space; mirroring it to Phase 3 in the remaining window
   is a high-variance bet, and a botched F1 lands worse than
   a clean F2' bypass.

**Honest answer to "why is this proving so difficult?"**

Because we keep trying to fix prompt-class problems with prompt-class
fixes. TASK-FIX-7A08 was the first refutation of the cheap path
("just tell the Player harder"). FEAT-AB59 is the proof that the
expensive path (remove the Player from the tool-call loop entirely)
*does* work. But FEAT-AB59 only fixed Phases 4 and 5, because those
were the visible bottleneck at the time. Phase 3 is now the bottleneck,
and it has the same shape. Until every Player-tool-use gate is removed
or made non-load-bearing, each forge run will surface the next variant.

The cumulative debugging cost is high not because any individual fix
is hard, but because the meta-question — *which gates rest on Player
tool-use discretion?* — was never answered systematically. F1 is the
answer for Phase 3, but the broader systematic answer (audit every
gate; either remove Player discretion or make the gate evidence-based)
is the real follow-up workstream.

---

## AC-006 — Handoff follow-up tasks

**Today's tactical action** (out of scope for this review; user
authorises and runs):

> **TASK-FIX-{hash}**: *forge-FEAT-FORGE-002: bypass Phase 3 stall via per-task direct mode.*
> Edit TASK-NFI-003/006/007 frontmatter in `forge/.guardkit/features/FEAT-FORGE-002.yaml` (or
> the source task files at `tasks/backlog/nats-fleet-integration/`) to add
> `implementation_mode: direct`. Re-run `guardkit autobuild feature
> FEAT-FORGE-002 --resume`. Document outcome at
> `docs/reviews/bdd-acceptance-wired-up/forge-run-7.md`.

**Tomorrow's structural workstream**:

> **TASK-FEAT-{hash}**: *FEAT-AB60: mirror FEAT-AB59 to Phase 3 — orchestrator-side stack-specialist invocation.*
> Design + implement orchestrator-side Phase 3 specialist runner (analogous
> to OSI-004/005 for Phases 4/5). Resolves the
> last LLM-discretion gate in the Player-Coach loop. Estimated 1–2 days.
> Spec at `tasks/backlog/orchestrator-side-specialist-invocation-phase3/`.

**Calmer-waters retrospective** (non-urgent):

> **TASK-REV-{hash}**: *Audit: every Coach gate that depends on Player
> LLM tool-use discretion.* Inventory gates; for each, either
> document the structural alternative (FEAT-AB59 pattern) or rewrite
> the gate to be evidence-based. Avoids the "next forge run, next
> prompt-class variant" treadmill.

---

## Bootstrap-nuisance one-paragraph

forge-run-6 lines 46–48 show the PEP-668 fallback `pip install -e .`
into `.guardkit/venv` failed with `Could not find a version that
satisfies the requirement nats-core<0.3,>=0.2.0`. This is a forge-repo
dependency-availability issue (no published `nats-core` 0.2.x; only
0.0.0 / 0.1.0 / 0.2.0 / 0.3.0 exist with conflicting `Requires-Python
>=3.13` constraints); it is **independent of the Phase 3 stall**. The
SDK exit-code-1 errors at lines 207, 272 are coach_validator pytest
runs producing non-zero exits because the Player-implemented module
under test has unresolved imports — also a downstream symptom of the
nats-core resolution failure, not a cause. Neither contributes to the
Phase 3 gate-rejection: the gate fires *before* tests run, on the basis
of the agent_invocations record alone. Track separately as a
forge-side deps issue.

---

## Decision Checkpoint (v1, superseded — see Revision 2 below)

---

# Revision 2 — Honest answer to "why is this proving so difficult?"

## What I got wrong in v1

| v1 framing | Correction |
|---|---|
| "Three weeks of debugging cost has crossed a threshold" | **3–4 days.** RWOP1.3.1 landed 2026-04-23 08:00; first forge run was yesterday 2026-04-24 12:32; today is the second day of forge attempts |
| "Bypass via F2', plan F1 for tomorrow, accept Coach is at 80%" | The 80% Coach quality and the "Phase 3 stall" are **the same defect** — see § The Diagnostic below. Fixable today |
| "Reversibility risk if we soften the gate" | The gate is 2 days old. There is no historical "trust" in it to preserve. Softening a load-bearing gate that just landed and is now systematically blocking your actual goal is *appropriate*, not concerning |

## The Diagnostic — what your "overly complex" instinct is detecting

The Coach has **four gate stages**, evaluated in this order
([coach_validator.py:647–838](guardkit/orchestrator/quality_gates/coach_validator.py#L647-L838)):

| Position | Gate | Type | Verifies |
|---|---|---|---|
| 1 | `agent_invocations_validation` | **PROCESS** | Did the Player call specialists via the Task tool? |
| 2 | `verify_quality_gates` | OUTCOME | Tests passing, coverage met, etc. |
| 3 | `independent_test_verification` | OUTCOME | Coach re-runs tests itself |
| 4 | criteria-matching against ACs | OUTCOME | Does the implementation actually meet the BDD/AC text? |

When position 1 returns `violation`, the Coach **early-returns with
feedback**. Positions 2–4 never execute (line 720,
`return self._feedback_result(...)`). This means:

> **For every forge-run-6 task that stalled, the Coach never once
> verified whether the AC was met.** It only verified whether the Player
> followed the prescribed delegation pattern. The actual quality
> question — "does this implementation match the BDD acceptance
> criteria you spent feature-spec generating?" — was never asked.

**That is exactly the source of your frustration**:

- You want to use feature-spec → BDD AC to drive quality from 80% to higher.
- The Coach's AC-verification machinery (positions 3–4) is the thing
  that would do that.
- A *process* gate (position 1) was added 2 days ago and is now
  *short-circuiting* the AC-verification machinery before it runs.
- Every forge-run since then has been failing on the process check
  without the AC check ever firing — so each fix attempt looks like
  it's "circling" because we keep iterating on the wrong layer.

The C4 diagrams and execution-flow tracing aren't wasted; they're
needed because the system genuinely has many moving parts. What's
been missing is the question *which gates verify outcome and which
verify process, and is process being treated as a hard reject when
outcome-success would otherwise pass?* The honest answer: yes, that
inversion happened in commit `7c14c01d` two days ago.

## Recommendation (Revision 2)

**Choose F3c — strip `agent_invocations_validation` from being a
blocker; keep it as feedback enrichment.** This is a ~30–60-minute
targeted change to one Coach early-return.

**The change**: in
[coach_validator.py:657–738](guardkit/orchestrator/quality_gates/coach_validator.py#L657-L738),
when `status == "violation"`:

- **Before**: early-return with `_feedback_result(...)`, blocking
  positions 2–4.
- **After**: capture the same enriched description as a *soft warning
  message* into a buffer; let positions 2–4 run; if those gates also
  produce feedback, append the soft warning to the feedback's
  description (the Player still sees "you should also call Phase-3
  specialist via Task tool"); if positions 2–4 *pass*, approve with
  the soft warning attached as informational note.

Net behaviour:

- Player still gets process feedback (so the structural drift toward
  "skip the specialist" doesn't go silent).
- Coach can now reach AC verification (position 4), which is the
  thing you actually want it doing.
- The "missing Phase 3" pattern stops being an unrecoverable_stall
  generator — it becomes routine quality feedback.

## Why F3c over the alternatives (revised scoring)

| | F1 (mirror FEAT-AB59 to Phase 3) | F2' (per-task direct mode) | **F3c (gate → feedback-only)** | F4 (revert `7c14c01d`+deps) |
|---|---|---|---|---|
| ETA | 6–8 h | 10 min + run | **30–60 min + run** | 1.5 h |
| Solves the *actual* user problem (BDD AC verification reaches positions 3–4) | ✅ | ❌ — only works for these 3 tasks; AC-quality stays untouched | **✅ — directly unblocks AC verification** | ✅ — but loses Phase 4/5 verification too |
| Generalises beyond NFI-003/006/007 | ✅ | ❌ | **✅** | ✅ — overshoots |
| Touches FEAT-AB59 | No (extends it) | No | **No (FEAT-AB59 wiring intact; gate output is now feedback not blocker)** | Yes — undoes OSI-002 |
| Iteration window fit (3–4 attempts × 1.5 h each) | No (one attempt at most) | Yes — but no learning | **Yes — and each attempt teaches what positions 3–4 say** | Yes |
| Reversibility | Easy | Trivial | **Trivial — flip blocking back on if needed** | Loses real work |
| Process drift visibility preserved | ✅ | ❌ (silenced for 3 tasks) | **✅ (still surfaced as feedback)** | ❌ (gate gone entirely) |

**F3c is the right shape for today.** It does what the gate
*should have done from the start*: enrich the Coach's feedback with
process observations, without short-circuiting outcome verification.

## Iteration plan for the rest of the day

| Wallclock | Target | Decision |
|---|---|---|
| 14:30–15:30 | **Iteration 1** — implement F3c, run targeted tests | If targeted tests pass → forge-run-7 |
| 15:30–16:30 | forge-run-7 | If forge stalls on the same Phase-3 process check → F3c implementation bug, fix |
| 16:30–18:00 | **Iteration 2** — based on what positions 3–4 reveal in run-7 | Likely AC-matching tuning (the original 80% problem) |
| 18:00–19:30 | forge-run-8 | |
| 19:30–21:00 | **Iteration 3** — final tuning on whatever positions 3–4 surface | |
| 21:00 | Hard stop | If not green, freeze AutoBuild on commit 73a12c00 + F3c, resume tomorrow on whatever the position-3/4 evidence pointed at |

**You get to actually run the AC verification today** — that's the
prize. F2' bypass would have skipped it.

## Honest answer to "why is this proving so difficult?"

Three contributing causes, in descending order of weight:

1. **A process-check was wired in front of outcome-checks two days ago
   and short-circuits them on failure.** That single ordering decision
   (`coach_validator.py:720`) is most of the pain. Every forge run
   since then has been measuring the wrong thing. The fix is targeted
   and small.
2. **The two problems got conflated.** "Coach AC verification at 80%"
   and "Player must invoke Task-tool specialists" are different
   problems. Bundling them produced the gate that's now blocking. They
   should be solved separately: gate-as-feedback (today, F3c) +
   AC-matching quality (tomorrow onwards, calmer iteration).
3. **The recent fix-class genealogy created an availability bias toward
   prompt-class fixes.** TASK-FIX-7A08 was a prompt fix (refuted).
   FEAT-AB59 was the structural fix for *Phases 4/5 only*. The natural
   continuation was "FEAT-AB60 mirrors that for Phase 3" — F1, the
   high-variance bet. But F1 isn't actually needed today. The gate
   doesn't have to be load-bearing on Phase-3 process; making it
   non-blocking is sufficient.

The C4 diagrams, execution traces, and reviews aren't wasted ceremony —
they're how you isolated the problem precisely enough that today's
fix can be 30 minutes of code instead of two days of guesswork. The
"why is this so hard?" answer is *because we've been iterating on the
wrong layer*. The diagrams pointed at the right layer; we just needed
one more review (this one) to act on what they showed.

## Revised handoff tasks

**Today's tactical-but-real fix**:

> **TASK-FIX-{hash}**: *Coach gate-block: demote
> `agent_invocations_validation` violation from blocker to feedback-enricher.*
> Edit `coach_validator.py:657–738`: replace early-return with soft-warning
> capture; let positions 2–4 run; append warning to whatever
> feedback those gates produce (or attach as info if they pass).
> Add a regression test fixture that asserts a Player report with
> `agent_invocations_validation: violation` AND criteria_progress
> 100% gets `approved + info_warning`, not `feedback`. ETA 60 min including test.

**Tomorrow's structural workstream (only if Phase-3 process drift
turns out to actually hurt Coach AC quality)**:

> **TASK-FEAT-{hash}**: *FEAT-AB60 — orchestrator-side Phase-3
> specialist invocation* — only if forge-run-7/8/9 evidence shows the
> Player skipping Phase-3 specialists actually produces worse AC
> verification outcomes. If the evidence shows AC quality is unaffected
> by Phase-3 specialist skip, **don't build F1** — drop the gate entirely
> rather than extending the orchestrator.

**Refocus task**:

> **TASK-FEAT-{hash}**: *Coach AC verification: improve criteria
> matching for synthetic and full-promise paths.* The original 80%
> problem. Driven by what positions 3–4 surface in forge-runs 7/8/9
> once F3c lets them run.

## Decision Checkpoint (Revision 2)

- **[A]ccept** — Approve revised report. You action F3c yourself in [coach_validator.py:657](guardkit/orchestrator/quality_gates/coach_validator.py#L657) and proceed with the iteration plan
- **[R]evise** — Request further refinement
- **[I]mplement** — Auto-create the F3c tactical task + the AC-verification refocus task via the [I]mplement pipeline
- **[C]ancel** — Discard

**Recommended**: **[I]mplement** (creates the F3c task and the
refocus task; F1 deferred until evidence justifies it). Or **[A]ccept**
if you'd rather edit `coach_validator.py` directly and skip the
task-creation overhead.

**Time consumed by this review**: ~70 min total (50 min v1 + 20 min revision). Window remaining: **~8 h to deadline**, enough for 3 iteration cycles.

---

# Revision 3 — User reframing: AutoBuild is solid; this is targeted unblocking

## What the user clarified

| v2 framing | Correction |
|---|---|
| "3 iteration cycles available (~1.5 h each)" | **Test runs are 30–40 min, not 90 min.** With 8 h remaining and 60 min for F3c implementation, that's **~10 forge iteration cycles** available, not 3 |
| "We've been iterating on the wrong layer for 3-4 days" | **AutoBuild has been solid for weeks.** Only the BDD-AC verification work (the past 3-4 days) regressed. Don't conflate "recent BDD-AC bridge work" with "AutoBuild quality" |
| "Why is this proving so difficult? — process-vs-outcome inversion" | Right diagnostic, missing context: the BDD-AC work was specifically built to bridge a **known integration-test gap** (unit tests pass in isolation, components fail when combined). The recent work isn't gold-plating — it's targeted at a real quality leak |
| "Tomorrow's structural workstream — FEAT-AB60 (mirror FEAT-AB59 to Phase 3)" | **Probably never needed.** The right next workstream after AC verification works is **higher-level test coordination** (forge or QA-Tester agent invoking `/task-review` and `/task-work`) — out of scope today |

## What the recent work was actually trying to fix

> "Oftentimes the testing was isolated and when put together
> components failed, so we tried to leverage the BDD A/C which weren't
> being checked to help things along. That's all this work was supposed
> to do."

Reframed problem statement:

- **Pre-existing pain**: unit tests passing × N tasks → integration breaks.
- **Hypothesis**: BDD AC text describes cross-component contracts.
  Verifying it task-by-task catches integration leaks earlier than
  waiting for whole-feature integration tests to fail.
- **Recent work**: wire feature-spec → BDD AC → Coach AC verification
  into the existing Player-Coach loop, so each task's completion
  promises get matched against AC text per turn.
- **Bug introduced 2 days ago**: the agent_invocations gate was added
  alongside, *in front of* the AC verification it was meant to
  empower. The gate now blocks the very pipeline the rest of the
  work was building.

This is a small fix (F3c) that completes a small, well-scoped feature
(BDD AC bridge). Not an architectural rewrite.

## Updated iteration math (8 h × 30–40 min cycles)

| Cycle | Wallclock | Activity | Likely position 3–4 finding |
|---|---|---|---|
| 1 | 14:30–15:30 | Implement F3c + run targeted Coach test fixture | (no forge run yet) |
| 2 | 15:30–16:10 | forge-run-7 | Likely: criteria-matching surfaces real AC gaps; some completion_promises don't textually match AC text |
| 3 | 16:10–16:50 | Tune AC matching threshold OR Player completion_promise generation | New problem revealed by run-7 |
| 4 | 16:50–17:30 | forge-run-8 | Either green or surfaces secondary AC quality issues (synonym matching, structural promises) |
| 5 | 17:30–18:10 | Iterate on AC verifier or completion_promise quality | |
| 6 | 18:10–18:50 | forge-run-9 | |
| 7 | 18:50–19:30 | Iterate | |
| 8 | 19:30–20:10 | forge-run-10 | |
| 9 | 20:10–20:50 | Iterate | |
| 10 | 20:50–21:30 | forge-run-11 (final attempt) | |
| - | 21:30–22:00 | Buffer / write-up | |
| - | 22:00 | Hard stop. If forge isn't green, you have rich evidence (4–5 runs of position 3-4 output) for tomorrow's calmer review |

Every iteration produces *new* evidence (positions 3-4 actually
running) — unlike the past 4 forge runs which all produced the same
"missing Phase 3" stall. **The signal-per-iteration goes up dramatically
the moment F3c lands.**

## Out-of-scope but explicitly named (so we don't lose it)

The user's correct framing of where the *real* gains come from, filed
for after AC verification works:

> **Future workstream (NOT today)**: Higher-level test coordination —
> a forge orchestrator or QA-Tester agent that can invoke `/task-review`
> and `/task-work` to run integration-level and e2e tests after a
> feature's individual tasks complete. Bridges from "task-level AC
> verification" (today's work) to "feature-level integration verified"
> (the actual gap).
>
> Likely shape: a new agent role with `Bash` permission to invoke
> guardkit CLI commands; a new Coach-equivalent for feature-level
> verification that runs *after* all tasks in a feature pass; an e2e
> phase in the AutoBuild feature orchestrator.
>
> File as **TASK-FEAT-{hash}: Feature-level integration verification
> via QA-Tester agent** — for the calmer-waters planning session
> after today's AC work lands.

This is the answer to "we only get 80% complete." Today's F3c gets
AC verification running; this future workstream gets integration
verification running. Two distinct quality gates, both currently
absent.

## Final recommendation (Revision 3 — no change to F3c, refined plan)

**Implement F3c**: demote `agent_invocations_validation` from blocker
to feedback-enricher in [coach_validator.py:657–738](guardkit/orchestrator/quality_gates/coach_validator.py#L657-L738).
Run forge-run-7. Iterate on whatever positions 3–4 reveal.

**Discipline**: each forge run produces a one-line note in
forge-run-N.md saying "this run showed X about AC verification
quality." That's the per-iteration learning artifact. Avoids the
"keep iterating without converging" trap.

**No revert. No bypass. No structural rewrite. No FEAT-AB60.** Today
is small targeted unblocking + iterative AC-quality tuning. Tomorrow's
review (driven by today's evidence) decides whether AC matching needs
deeper work or whether the Coach can graduate to integration-level
verification.

## Decision Checkpoint (Revision 3)

- **[A]ccept** — Approve report. Action F3c yourself in [coach_validator.py:657](guardkit/orchestrator/quality_gates/coach_validator.py#L657), run forge-run-7, iterate
- **[R]evise** — Further refinement
- **[I]mplement** — Auto-create the F3c task + the named-but-out-of-scope feature-level-integration task
- **[C]ancel** — Discard

**Recommended**: **[A]ccept**. F3c is small enough that direct edit is
faster than task-creation overhead, and the iteration plan is yours
to drive. Reserve task-creation for the bigger out-of-scope workstream
(QA-Tester agent / feature-level integration) once today's evidence
informs its design.

**Cumulative review time**: ~80 min. Window remaining: **~7.5 h**, enough for ~10 forge iterations.
