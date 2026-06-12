# Handoff: QA-Verifier + autobuild generalization — session of 2026-06-12

> **Purpose.** Continue this work in a fresh session without the prior chat history.
> Self-contained: where we are, what's committed, what's open, and the exact next
> moves. Pair with the corrected retro at
> [`player-coach-why-so-hard-verdict.md`](player-coach-why-so-hard-verdict.md).

## TL;DR — where we are

The Player-Coach **oracle honesty problem is effectively solved and now
*generalizes*.** The remaining work is (a) ordinary infra/substrate blockers in
autobuild, and (b) building the **QA-Verifier** (the next oracle layer: catch
"green over un-wired/dead code"). The first real generalization autobuild run
(FEAT-E2CB, 2026-06-12) **failed to build but the Coach was honest** — no
false-green, populated `criteria_verification`, accurate feedback, correctly
treated "couldn't verify" as absent-signal. The failures were a harness crash
(now fixed) + a bootstrap gap (task filed) + a weak Player on a hard task.

## What this session established (all committed to `main`)

1. **Corrected retro verdict** ([`docs/retro/player-coach-why-so-hard-verdict.md`](player-coach-why-so-hard-verdict.md)):
   the hard part was *a trustworthy gating verdict over a mutating substrate*
   (H2/H3), NOT a missing fine-tune (H1, refuted). Both false-greens are closed:
   `signal_absent` (TASK-FIX-COACHFG01, done) + empty-criteria (TASK-ARCH-COACHBFULL,
   done; validated by TASK-OPS-COACHMOE01 — the **26B-A4B MoE works as Coach**).
2. **Stack-agnostic principle** (the operator corrected me twice): analysis is
   stack-agnostic **tree-sitter** + declarative dialect descriptors; plugins are a
   **last resort, only for irreducible execution** (the existing
   `guardkitfactory/bdd/` plugins). Seeded as `.claude/rules/stack-plugin-architecture.md`
   + a Graphiti node (`guardkit__project_decisions`). This lands TASK-REV-STKB
   Workstream D, which had never shipped.
3. **Graphiti is working** (was never disabled — migrated to llama-swap; extraction
   model is `qwen-graphiti`, embeddings `nomic-embed` 768-dim on `:9000`). Config:
   `scripts/graphiti-mcp-config.yaml`. Capture verified end-to-end this session.
4. **QA-Verifier piece #2 scope** ([`docs/features/qa-verifier-wiring-probes-scope.md`](../features/qa-verifier-wiring-probes-scope.md)):
   one tree-sitter `WiringAnalyzer` + dialects (py/js/ts/csharp) emitting
   UNWIRED_PATH / MOCKED_SEAM / SPEC_GAP evidence into `CoachEvidenceBundle`;
   SPEC_GAP consumes the factory `BDDRunResult` (via BDDWIRE). Adversarially
   path-verified; tree-sitter feasibility empirically confirmed (use
   `get_language()` + standalone `tree_sitter.Parser` + `QueryCursor.captures`,
   NOT the pack's `get_parser()`).
5. **Two features planned + committed:**
   - **FEAT-E2CB** (BDDWIRE) — `.guardkit/features/FEAT-E2CB.yaml`, 2 tasks/2 waves:
     wire `guardkitfactory.bdd.discover(stack)→BDDRunResult→bundle.bdd` into the
     Coach (makes .NET/JS BDD verification reachable). Source design:
     `tasks/backlog/TASK-HMIG-BDDWIRE-*.md`; subtasks in `tasks/backlog/bddwire/`.
   - **FEAT-C332** (wiring evidence) — `.guardkit/features/FEAT-C332.yaml`, 4 tasks/3 waves;
     subtasks in `tasks/backlog/qa-wiring-evidence/`. Wave 4 (SPEC_GAP) is gated on
     BDDWIRE merged.

## The first generalization run (FEAT-E2CB run 1) — what happened

FAILED via `decision=timeout` on TASK-BDDW-001 after 3 turns (recipe below).
Honest analysis (log: `.guardkit/autobuild/FEAT-E2CB-run1-stdout.log`; coach
verdicts under `.guardkit/worktrees/FEAT-E2CB/.guardkit/autobuild/TASK-BDDW-001/`):

- ✅ **Coach honest on novel work** (the H6 generalization question = YES on the
  honesty axis): turns 1-2 `decision=feedback`, **criteria_verification 6/6
  populated**, accurate rationales, correctly treated "missing pytest → can't
  verify" as absent-signal → feedback (not pass). **No false-green.**
- ❌ **Three failure modes**, none of them Coach dishonesty:
  1. **Harness crash** (P1, **FIXED this session**): LangSmith's async tracing
     wrapper dispatches to the loop's default ThreadPoolExecutor unconditionally;
     the `task_timeout` teardown shut it down → `cannot schedule new futures after
     shutdown` killed turn 3's Player+Coach `ainvoke`. → **TASK-FIX-LSTRACE01
     (DONE)**: `guardkitfactory/.../harness/langgraph_harness.py`
     `_install_langsmith_executor_guard()` registers a `langsmith.set_runtime_overrides`
     inline `aio_to_thread` (disabling tracing alone does NOT fix it). 4 regression
     tests + 34 existing harness tests green. **Live via editable install — the
     next run picks it up.**
  2. **Worktree venv missing pytest on early Coach turns** → **TASK-FIX-BOOTPYTEST01
     (filed, OPEN, high priority)** — the Coach couldn't run independent tests
     turns 1-2.
  3. **Weak Player** (qwen36-workhorse) didn't converge on a hard cross-repo task
     in 3 turns / 80 min — substrate/task-sizing, not infra.

## Immediate next steps (priority order)

1. **TASK-FIX-BOOTPYTEST01** (high) — ensure the worktree venv has pytest+test deps
   from turn 1, so the Coach can actually verify. This is the lever most likely to
   turn "timeout" into "honest convergence." (LSTRACE01 already removed the crash.)
2. **Re-run FEAT-E2CB** with the recipe below. With the crash gone + pytest present,
   expect a clean convergence-or-feedback signal. If the Player still can't build
   it, the lever is Player-side (more turns, or a stronger Player for cross-repo
   tasks) — **not** the Coach.
3. **Then FEAT-C332** (the QA-Verifier wiring evidence) — Waves 1-3 are independent
   of BDDWIRE; Wave 4 (SPEC_GAP) after BDDWIRE merges. Note OQ#1 in the scope:
   `BDDRunResult` has no per-scenario executed names — fold `executed_scenarios`
   into BDDWIRE if you want per-scenario SPEC_GAP (else it ships count-only).

## Validated autobuild recipe (COACHMOE01-proven; run on the GB10 `promaxgb10-41b1`)

```bash
GUARDKIT_COACH_GATHER=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-E2CB \
    --fresh --model qwen36-workhorse --coach-model gemma4:26b \
    --task-timeout 4800 --sdk-timeout 3600 --no-context --max-parallel 1 \
    2>&1 | tee .guardkit/autobuild/FEAT-E2CB-run2-stdout.log
```

- `autobuild task` does NOT work on the local substrate (pre-loop design phase
  isn't migrated + local models can't do it). Only `autobuild feature` works.
- `/feature-plan` runs in-session (strong model) → produces the FEAT YAML;
  `autobuild feature` runs the local build loop. Commit feature YAML + task files
  to `main` first (worktree branches from main HEAD).
- Coach = `gemma4:26b` MoE (fast B-min, co-resident, validated). `gemma4:31b` is
  the higher-reliability fallback. Models served by llama-swap on `:9000`.

## Open task backlog (this thread)

| Task | What | Status |
|---|---|---|
| TASK-FIX-LSTRACE01 | LangSmith executor-teardown crash | **DONE** (committed guardkitfactory `189ece6`) |
| TASK-FIX-BOOTPYTEST01 | worktree venv missing pytest early | **OPEN, high** |
| FEAT-E2CB (BDDWIRE) | wire factory BDD plugins into Coach | planned; run 1 timed out; re-run after BOOTPYTEST01 |
| FEAT-C332 (wiring evidence) | QA-Verifier piece #2 (tree-sitter) | planned; build after/with BDDWIRE |
| TASK-OPS-COACHGEN01 | generalization run (this IS it; partly answered) | superseded by FEAT-E2CB runs |
| TASK-PERF-COACHGATHER01 | B-full Phase-A always degrades (GATHER) | open |
| TASK-DATA-COACHHARVEST | Coach fine-tune (base = 26B MoE) | future lever (per ai-transition findings doc) |

## Broader program (not in this repo)

The QA-Verifier is part of a bigger "fine-tuned judgment agents" program captured
at `../ai-transition/docs/fine-tuned-judgment-agents-findings.md` (QA Verifier +
Product Owner fine-tunes). Piece #1 (fine-tune) and #3 (glue-policy) are out of
scope for FEAT-C332; #2 (this scope) is the deterministic evidence layer.
