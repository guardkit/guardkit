---
title: "Lessons learned — FEAT-J004-702C wave-4 double timeout (run-3 fail → run-4 green)"
date: 2026-04-28
review: TASK-REV-WORS (v1 → v2)
fix: TASK-ABSR-FLOR (MAXT ceiling floor 150 + task_timeout floor 3000s)
sidequest: TASK-REV-OCRC (orchestrator cancellation residual cleanup, low-priority follow-up filed)
deferred: TASK-ABSR-WTKS (worktree isolation per parallel task — design-approved, post-demo)
escalated: TASK-ABSR-CMPL (Phase-2.5 effective-complexity heuristic — priority MED → HIGH, post-demo)
outcome: jarvis FEAT-J004-702C run-4 = 20/20 green, 0 SDK ceiling hits, 100% success rate (run-2 was 12/20 with wave-5 fail; run-3 was 12/20 with wave-4 double-fail)
---

# Lessons learned — FEAT-J004-702C wave-4 double timeout

## TL;DR

Run-3 of `guardkit autobuild feature FEAT-J004-702C` failed at Wave 4 with **both** parallel tasks (J004-011 + J004-012) hitting `timeout_budget_exhausted` — a regression from run-2 where these tasks passed. The original diagnostic brief framed it as "1.66× per-SDK-turn slowdown" and asked which orchestrator change in commit `87c27e60` caused it.

The brief's framing was wrong on three counts:
1. **The 1.66× was apples-to-oranges** (J004-013 run-2 vs J004-011 run-3 — different tasks).
2. **`87c27e60` could not have caused longer iteration** because the SDK's `max_turns` parameter is invisible to the model — it's a Python loop counter, not a prompt token.
3. **The actual binding constraints were different for each failing task** — J004-011 hit the wall, J004-012 hit the ceiling — and those constraints are independently observable without resolving the upstream "why does the Player need more turns" question.

v1 of the review reached a recommendation (FLOR: ceiling floor + wall floor) with weak evidence. v2 strengthened the diagnosis with C4 + sequence diagrams and SDK code analysis without changing the fix. Run-4 then went 20/20 green on first attempt with 0 SDK ceiling hits — including J004-013, which would have hit the **original fixed-100 ceiling** with its 136-turn run. **The MAXT bundle from `87c27e60` plus FLOR is what made wave 5 even reachable.**

The most important lesson is **about diagnostic discipline under conflicting hypotheses**, not the bug itself.

## What actually happened

### Three-run timeline

| Run | Date | Outcome | Wave 4 | Wave 5 | Notable |
|---|---|---|---|---|---|
| run-2 | 2026-04-27 22:48 BST | 12/20, wave-5 fail | J004-011=91 turns ✓<br/>J004-012=92 turns ✓ | J004-013=101 turns ✗ ceiling-hit + post-Player specialist stall | Drove TASK-REV-9D13, R1-R6 fixes (87c27e60) |
| run-3 | 2026-04-28 08:47 UTC | 12/20, wave-4 fail | J004-011=116 turns ✗ wall<br/>J004-012=141 turns ✗ ceiling | never reached | Drove TASK-REV-WORS (v1, v2) and TASK-ABSR-FLOR |
| run-4 | 2026-04-28 09:48 UTC | **20/20 green** | J004-011=107 turns ✓<br/>J004-012=100 turns ✓ | J004-013=136 turns ✓ | First complete success. FLOR shipped. |

### Same task, three runs, three turn counts

J004-012's SDK turn count across the three runs: **92 → 141 → 100**. Range ±25% from the median. This is normal variance for a 100+ turn agentic task — and it's the load-bearing observation behind the FLOR floor recommendation.

### What changed between runs

The only orchestrator commit between run-2 (22:48 BST) and run-3 (08:47 UTC next morning) was `87c27e60` ("autobuild fixes"), which merged R1-R6 from the prior TASK-REV-9D13 review:
- **R1 CEIL** — skip Phase 4/5 specialists on `sdk_ceiling_hit`
- **R2 WALL** — cap specialist `sdk_timeout` at remaining wall budget
- **R3 FRSH** — refresh `remaining_budget` post-Player
- **R4 MAXT** — complexity-scale `TASK_WORK_SDK_MAX_TURNS` from fixed 100 to `int(100 × (1 + complexity/10))`
- **R5 MTBC** — env-overridable `MIN_TURN_BUDGET_SECONDS` for turn-2+ retry decisions
- **R6 DIAG** — heartbeat label fix for orchestrator-invoked specialists

All six fired correctly in run-3. They prevented further damage. They could not unwind J004-012's half-edited worktree, and the half-edit poisoned J004-011's parallel pytest run via the shared FEAT-J004-702C worktree.

### What FLOR shipped

A 10-LOC source change + 5 unit tests (~80 LOC total) under `TASK-ABSR-FLOR`:
- **MAXT floor** in `_calculate_sdk_max_turns`: `effective_max_turns = max(150, int(100 × (1 + complexity/10)))`. Gated on `not _SDK_MAX_TURNS_IS_OVERRIDE` so env-var overrides still win.
- **task_timeout floor** of 3000s for autobuild orchestration.

Run-4 validated: J004-012 used 100 of 150 turns (floor explicitly logged firing — `floored from 140 to 150`); J004-011 used 107 of 170 (floor not bound at c=7); J004-013 used 136 of 160 (would have hit the original 100 ceiling without MAXT itself).

## Lessons

### 1. Apples-to-apples comparison is non-negotiable for cross-run diagnostics

The brief's headline claim of "1.66× per-SDK-turn slowdown" came from comparing **J004-013 run-2** (11.5 s/turn) to **J004-011 run-3** (19.1 s/turn) — two different tasks, two different runs. Apples-to-oranges. Apples-to-apples J004-011 was 15.1 → 19.1 s/turn (+26.5%, real but smaller) and J004-012 was 15.3 → 13.9 s/turn (−9%, actual *speedup*).

v1 of the review dismissed the per-turn slowdown entirely on the basis of cross-task comparison being unsound. v2 corrected to "REFUTED in size, partially CONFIRMED in direction for J004-011 only." The earlier dismissal would have hidden a real (if smaller) signal.

**Rule of thumb**: when comparing performance across runs, the unit of comparison must be the same task. Cross-task comparison is meaningful only for *normalized* metrics (percentile latency, success rate), not absolute turn counts or wall times.

### 2. SDK `max_turns` is a stop-condition, not a strategy-signal

CONFIRMED via code analysis: `agent_invoker.py:2208` passes `max_turns` to `ClaudeAgentOptions(...)` as a Python configuration field. The SDK uses it as a hard-stop counter in its internal turn loop. The model **never sees** this value — it is not injected into the system prompt or any conversation context. Therefore raising the ceiling cannot *cause* longer iteration; it can only *permit* it.

This refutes a whole class of hypothesis: "changing the turn ceiling will change Player strategy." It will not. The model's awareness of conversation length comes only from the conversation itself (number of AssistantMessage/ToolResult pairs in context). It has no signal for "X turns remaining."

**General principle** (applies to any agentic system using an SDK with a turn-cap parameter): clearly distinguish *stop-conditions* (loop counters, wall-clock budgets) from *strategy-signals* (anything injected into the prompt). Conflating them produces wrong hypotheses.

### 3. Multi-agent investigations can hallucinate facts; verify before believing

During v2 deep-investigation, three Explore agents ran in parallel. One reported: "Run-2 artifacts located in git history at commits `5f4765b` (J004-011) and `5156dd5` (J004-012)... SDK turns used: 116 and 141 in both runs." This contradicted the brief's "91/92 in run-2" claim.

A direct `git log` check showed commit `5f4765b` is dated **2026-04-28 09:24:31 BST** — that is the *end* of run-3, not run-2. The agent had picked up `[guardkit-checkpoint]` commits from run-3 and mis-attributed them to run-2. The actual run-2 evidence lives in `jarvis/docs/history/autobuild-FEAT-J004-702C-run-2-history.md`, which records `91 SDK turns (15.1 s/turn avg)` for J004-011 and `92 SDK turns (15.3 s/turn avg)` for J004-012.

If I had trusted the agent's claim, v2 would have concluded "no turn-count regression — the brief's premise is false" and stopped. The actual diagnosis (real regression: 91→116 and 92→141) would have been buried.

**Lesson**: subagent reports are ranked-text drafts, not verified evidence. For load-bearing claims, do a direct verification (`git log`, `Read`, `grep`) before integrating them into a diagnostic conclusion.

### 4. Variance amplification through long agentic pipelines is normal — design ceilings to absorb it

J004-012's three runs needed 92 / 141 / 100 SDK turns. Median 100, range 49 (about ±25%). This is not a regression; it is variance.

For a 100+ turn agentic task running on a stochastic LLM, ±25% variance per run is plausible from:
- LLM sampling variation (different routes through the decision tree)
- Anthropic-side model snapshot or routing differences across sessions
- Cumulative drift from upstream-wave outputs (waves 1-3 produce slightly different worktree state each run, which feeds into wave 4)

**Implication for ceiling design**: a ceiling formula that matches the *median* observed turn count guarantees ~50% of runs hit it. A ceiling formula that matches *p95* + a safety floor absorbs natural variance. FLOR's choice (formula-output ∨ floor-of-150) is closer to p95 + safety; the original fixed-100 was below median for several tasks.

**Generalization**: any threshold for "is this task done?" or "is this run reasonable?" against a stochastic LLM needs to be sized at p90–p95 plus a floor, not at the median.

### 5. The [R]evise → C4 + sequence diagrams cycle deepens diagnostic confidence non-trivially

v1 of TASK-REV-WORS reached the same fix recommendation as v2 (FLOR: ceiling floor + wall floor) with weaker evidence. The v1 → v2 transition cost ~2 hours of additional investigation. That investigation:

- Refuted the MAXT-causes-more-turns hypothesis via SDK code analysis (would have remained UNVERIFIED in v1).
- Surfaced J004-012's silent schema regression (Player emitted 0 completion_promises in run-3 vs 8 in run-2).
- Corrected the per-turn rate analysis from "comparable" to "+26.5% for J004-011 only" (apples-to-apples).
- Drew the L1/L2/L3 C4 diagrams that explicitly placed the shared FEAT-XXX worktree as the only mutable state shared across parallel Players — the structural class-of-defect that anchored TASK-ABSR-WTKS.
- Drew the §4.3 sequence diagram showing how J004-012's mid-edit poisoned J004-011's pytest run via shared filesystem state.

The C4 + sequence diagrams **revealed mechanisms invisible to text-only analysis**. They also raised the architect's confidence enough that subsequent decisions (CMPL escalation, WTKS design-first deferral) could be made with less hedging.

**Process lesson**: for diagnostic reviews of complex distributed systems (orchestrator + SDK + cloud API + filesystem + multiple subprocess tools), C4 + cross-boundary sequence diagrams are not optional. They are how you spot mechanisms that text-only analysis hides. Make them part of the standard `--depth=comprehensive` diagnostic template.

### 6. Bind-constraint-targeted fixes are robust to upstream-cause uncertainty

v2 reached LOW–MEDIUM confidence on the upstream cause of "the Player needed more turns" — it remained bounded to three candidates (worktree-state drift through waves 1-3, Anthropic-side variance, per-turn tool-call regression) without empirical disambiguation.

The fix shipped anyway because the **binding constraints were independently observable**:
- J004-011 used 116 of 170 turns and 2235s of 2400s wall → wall-bound. Raising wall to 3000s buys 765s headroom.
- J004-012 used 141 of 140 turns → ceiling-bound. Raising ceiling floor to 150 buys 9 turns.

Whichever upstream mechanism is at play (LLM stochasticity, Anthropic variance, drift), all three manifest as "task budget overflow." The floors absorb the overflow without needing to identify which mechanism caused it.

**Generalization**: when a system has multiple plausible upstream causes but a single observable binding constraint, target the constraint. Don't block shipping a constraint-targeted fix on root-cause certainty.

### 7. CEIL/WALL/FRSH/MTBC are response guards, not root-cause fixes

All four guards from `87c27e60` fired correctly in run-3:
- R1 CEIL skipped J004-012's Phase 4/5 on ceiling-hit.
- R3 FRSH skipped J004-011's Phase 4/5 on `post_player_remaining < 600s`.
- R5 MTBC blocked turn-2 retry for both tasks at `remaining < min_turn_budget`.
- R2 WALL was not exercised because R1/R3 short-circuited specialists earlier.

Each guard prevented further damage. Together they could not recover the half-edited worktree that J004-012 had left behind. The cascade still produced two task failures.

**Lesson**: response guards (the things you do *after* a Player exhausts its budget) are necessary but not sufficient. They prevent escalation; they don't fix the root cause. The complete fix requires *also* addressing the upstream allocation (FLOR floors), the upstream estimation (CMPL heuristic redesign), and the structural contention (WTKS worktree isolation). Guard-only thinking produces local wins that compound into global failures.

### 8. Shared filesystem under parallel agents is a class-of-defect

The §4.3 sequence diagram exposed: two parallel Players in Wave 4 share a single FEAT-XXX worktree filesystem. When J004-012 hit its ceiling mid-edit (deleting `_REFRESH_OK_MESSAGE` from `capabilities.py` without yet updating the test that imports it), the Player loop terminated cleanly per CEIL guard. But the *worktree* was left in inconsistent state. J004-011's Coach pytest run then imported `capabilities.py` transitively and failed with `AttributeError: '_REFRESH_OK_MESSAGE'` — even though J004-011's own work was correct.

The Coach correctly classified this as `parallel_contention`. But there is no way for J004-011 to *avoid* J004-012's broken state when they share a filesystem.

This is a **structural class-of-defect**, not a one-off. It will surface again whenever:
- Multiple Players run in parallel within a wave
- One of them is cut mid-edit by a ceiling hit, timeout, or cancellation
- The other(s) have transitive imports that touch the half-edited file

Anchored in TASK-ABSR-WTKS (design-approved Option C+A two-phase). Sibling of `post-player-specialist-stall` from TASK-REV-9D13.

### 9. Per-process vs per-worktree git primitives

The WTKS Phase-2.5 architectural review rejected Option B (transaction-boundary semantics on Player edits via `git stash` / `git reset --hard`) because:
- `git stash` and `git reset --hard` are *worktree*-scoped operations, not *process*-scoped.
- Two parallel Players can't each maintain their own stash/reset boundary in the same worktree.
- Bash subprocesses (including pytest) always see the underlying filesystem, so a Python-level overlay can't protect Coach.
- Linux `overlayfs` could provide per-process isolation but **macOS dev hosts don't have it** (macFUSE alternatives are unmaintained on Apple Silicon).

The architect substituted Option A (per-task subworktrees, sibling pattern `FEAT-X-TASK-Y/`) as the structural fix, since git worktrees natively provide per-process filesystem isolation.

**General principle**: when designing per-task isolation in shared filesystems, the right primitive is often "more worktrees" not "smaller transaction scope." Identify what isolation primitive your storage layer natively supports at the right scope (process / task / wave / feature) before choosing an overlay or staging strategy.

### 10. CONFIRMED / REFUTED / UNVERIFIED labelling forces precision

TASK-REV-9D13 v2 introduced explicit CONFIRMED/REFUTED/UNVERIFIED labels on every claim. WORS v2 continued and expanded this — every cell of the §2 hypothesis table carries one label plus file:line evidence.

This forced precision in two ways:
- Claims that would otherwise be hand-waved into the analysis (e.g., "MAXT raise *probably* caused longer iteration") had to be explicitly UNVERIFIED, which prompted the SDK code-analysis spike that REFUTED it.
- The label set is small enough (3 categories) that disagreements become tractable. "Why is this REFUTED rather than UNVERIFIED?" is a specific, answerable question.

**Process recommendation**: make CONFIRMED/REFUTED/UNVERIFIED a standard convention for `task-review --depth=comprehensive`. The slight overhead per claim pays for itself within one diagnostic cycle.

### 11. Two different counters named "max_turns" cause real user confusion

The user's terminal displayed `Turn 1/30` and they passed `--max-turns 30`. They asked: *"is that ignored anyway or am I getting confused?"*

Reasonable confusion. There are two different counters:

| Counter | Layer | What it caps |
|---|---|---|
| CLI `--max-turns` | Orchestration (`feature_orchestrator.py`) | Player↔Coach **adversarial iterations** per task |
| SDK `max_turns` | SDK options (`agent_invoker.py`, FLOR-affected) | **Internal turns within ONE Player invocation** (model→tool→model loop) |

These are *unrelated* counters at different layers. FLOR fixes the SDK layer; the CLI flag is independent.

**Naming/UX recommendation**: rename them in CLI/docs to reduce confusion. Suggested: `--orchestration-max-iterations` for the Player-Coach iteration cap, reserve `--max-turns` for the SDK loop cap (or vice versa). The shared name is doing real damage to user mental models.

### 12. Schema regressions can be invisible without cross-run comparison

J004-012's Player emitted **8 well-formed `completion_promises`** in run-2 (history line 2551: `Recovered 8 completion_promises from agent-written player report`). In run-3, it emitted **zero** (history: `Generated 8 file-existence promises for TASK-J004-012 (agent did not produce promises)`) — the orchestrator silently fell back to file-existence heuristics.

The fallback was logged but not flagged as a regression. Without explicit cross-run log comparison, this would have been invisible: run-3's coach output looks "complete" because it has 8 promises; only by reading the per-line phrasing do you realize they were *generated by the orchestrator*, not *recovered from the agent*.

**Observability lesson**: silent fallbacks should emit a metric or warning, especially when the fallback masks a behavior change. A dashboard counter like `player_promise_emit_failure_total` would have surfaced this immediately.

## What I'd do differently next time

1. **Demand intra-task cross-run comparison up front** — even a single grep over both history files for `[TASK-J004-011] SDK invocation complete` would have settled the per-turn analysis in 30 seconds. v1 lost ~45 minutes to the misleading 1.66× framing.

2. **Verify subagent fact-claims before integrating** — the "5f4765b is run-2" claim could have been settled with one `git log -1 5f4765b` invocation. Easy to forget when the agent's report sounds confident.

3. **Build C4 + sequence diagrams in v1, not as a [R]evise** — the diagrams revealed the shared-worktree class-of-defect that v1 had only hand-waved. Earlier diagrams = earlier discovery = less rework.

4. **Default to bind-constraint-targeted fixes** — don't gate ship on root-cause certainty when the binding constraint is observable. v1's "MEDIUM confidence on upstream cause" could have shipped FLOR immediately; the v2 deepening was useful but not necessary for the fix.

## Cross-references

- [TASK-REV-WORS report v2](/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/reviews/TASK-REV-WORS-report.md) — full diagnostic with 12 CONFIRMED/REFUTED/UNVERIFIED entries, 3 C4 diagrams, 4 sequence diagrams.
- [TASK-REV-9D13 report v2](/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/reviews/TASK-REV-9D13-report.md) — prior diagnostic that drove the R1-R6 bundle.
- [TASK-REV-OCRC report](/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/reviews/TASK-REV-OCRC-report.md) — sidequest triage (orchestrator cancellation residual cleanup).
- [POST-DEMO-RESUMPTION-NOTES.md](/Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/autobuild-stall-resilience/POST-DEMO-RESUMPTION-NOTES.md) — backlog state after FLOR shipped.
- Previous lessons: [forge-run-6 process-vs-outcome](2026-04-25-forge-run-6-process-vs-outcome.md) — a prior diagnostic-discipline retrospective worth re-reading.
