# Handoff: qwen3-coder-30b Player experiment — session of 2026-06-13

> ## ✅ RAN 2026-06-13 — see [`coder-player-experiment-RESULT-2026-06-13.md`](coder-player-experiment-RESULT-2026-06-13.md)
> **Outcome (decomposition, not the handoff's binary):** the coder Player **converged
> FEAT-9DDE** where run-2's workhorse stalled → **H-Player confirmed as the build lever**
> (TSJ-001 is a REAL green: 9/9 tests pass, producer works). The `test-orchestrator`
> specialist **still hung deterministically (2/2)** → H-Harness real **but non-fatal**
> (Coach's own pytest routes around it). **Two new findings:** (a) **`direct` mode is a
> false-green vector** — TSJ-002 was APPROVED with a *broken* bin-entry wrapper +
> unmet AC (gates `required=False`); (b) **gemma4-31b drifted into reasoning mode**
> (~31 min/Coach turn).
>
> **Follow-up landed (2026-06-13):** TSJ-002 deliverable hand-fixed on
> `autobuild/FEAT-9DDE` (bin-entry → real producer, orphan removed) → **feature is
> now mergeable**. Coach reasoning tax fixed via
> `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1` (guardkitfactory `7526b55`,
> TASK-FIX-COACHREASON01). Follow-up tasks filed in
> [`tasks/backlog/feat-9dde-followups/`](../../tasks/backlog/feat-9dde-followups/)
> (DIRECTFG01 systemic false-green fix, SPECINVOKE01 specialist hang, COACHCWD01 cwd-leak).

> **Purpose.** Kick off the next autobuild experiment in a fresh session without
> this chat's history. Self-contained: the experiment, the exact recipe, what to
> watch, the infra context (we run on a **GB10**), and why this is the right next move.
> Pair with the prior handoff
> [`qa-verifier-autobuild-session-handoff.md`](qa-verifier-autobuild-session-handoff.md).

## TL;DR — the experiment to run

Swap the autobuild **Player to `qwen3-coder-30b`** (keep the **Coach on
`gemma4-31b`**) and re-run **FEAT-9DDE**, with the same monitoring as before.

**This is a controlled disambiguation, not a feature build.** The harness is
already validated (see below). The open question is *why the local substrate
can't finish a build*, and there are two hypotheses this experiment separates:

- **H-Player** — `qwen36-workhorse` is too weak for the Player role (poor
  structured self-reporting + weak agentic control of sub-specialists).
- **H-Harness** — the sub-specialist invocation path itself is fragile,
  independent of the Player model.

Outcome reading:
- Coder Player ⇒ honest reports **and** specialists stop hanging → **H-Player
  confirmed**; you've found the fix for free and know to spend Monday's hardware
  on the Player.
- Coder Player ⇒ specialists **still** run 700s+ / produce violations →
  **H-Harness confirmed**; no model upgrade fixes it, and the specialist-
  invocation path goes to the top of the code-work queue.

Either result is decisive and costs one run.

## Environment — we run on a GB10 (read this before launching)

- **Box:** NVIDIA **GB10** (`promaxgb10-41b1`), 128GB unified memory. Models are
  served by **llama-swap on `:9000`** (OpenAI-compatible), loaded on demand.
- **Real-world GB10 usage goldmine** (now in agent memory
  `nvidia-gb10-dgx-spark-forum`): the NVIDIA DGX Spark / GB10 forum —
  https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719
  Consult it before any serving-config / model-fit decision.
- **Model aliases on `:9000`** (verified 2026-06-13): `qwen36-workhorse`,
  `qwen3-coder-30b`, `gemma4-31b`, `gemma4-coach` (alias `gemma4:26b`),
  `gemma4-tutor`, `architect-agent`, `qwen-graphiti` (Qwen 2.5 — being retired,
  see below), `nomic-embed`.
- **⚠ gemma4:26b is mis-served right now** — after the 2026-06-13 GB10 restart it
  came up with **reasoning mode ON**, so it spends its token budget on a
  `reasoning_content` channel and emits **no parseable verdict** (the F2
  "0 AssistantMessageEvent" Coach failure). It was 3/3 reliable on 06-12.
  **Use `gemma4-31b` for the Coach** until 26b is pinned out of reasoning mode.
  `gemma4-31b` and `qwen3-coder-30b` both probe clean (immediate answer, no
  reasoning channel, `finish: stop`).
- **FalkorDB / Graphiti** on the NAS (`whitestocks:6379`); runs use `--no-context`
  so Graphiti is not on the critical path for this experiment.

## The exact recipe

```bash
cd /home/richardwoollcott/Projects/appmilla_github/guardkit

# 1) PRE-FLIGHT — FEAT-9DDE has a STALE worktree+branch from run 2 (status: failed).
#    --fresh will fail to create the worktree unless you remove these first
#    (we hit this twice this session). Clean them:
git worktree remove .guardkit/worktrees/FEAT-9DDE --force
git branch -D autobuild/FEAT-9DDE
git checkout -- .guardkit/features/FEAT-9DDE.yaml \
  tasks/backlog/task-status-json/TASK-TSJ-001-implement-task-status-json-producer.md 2>/dev/null || true

# 2) Verify infra is up (it's a GB10; models load on demand):
curl -s --max-time 10 http://promaxgb10-41b1:9000/v1/models | python3 -c "import json,sys; print(', '.join(m['id'] for m in json.load(sys.stdin)['data']))"
# Probe the two models this run uses — both should answer 'READY' with finish=stop and NO reasoning_content:
for M in qwen3-coder-30b gemma4-31b; do curl -s --max-time 120 http://promaxgb10-41b1:9000/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer llama-swap-local-key" -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly one word: READY\"}],\"max_tokens\":64}" | python3 -c "import json,sys;c=json.load(sys.stdin)['choices'][0];print('$M ->',repr((c['message'].get('content') or '')[:30]),'reasoning:',repr((c['message'].get('reasoning_content') or '')[:20]),c.get('finish_reason'))"; done

# 3) LAUNCH — Player=qwen3-coder-30b, Coach=gemma4-31b, GATHER unset (=0, the shipped default).
#    Run in BACKGROUND (it takes ~30-60+ min) and tee to a log.
#    NOTE (post-run-3 fix, TASK-FIX-COACHREASON01): gemma4-31b on this llama-swap
#    endpoint serves in reasoning mode → ~31-min Coach turns. Set
#    GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 to inject enable_thinking=false
#    (the toggle the server honours; reasoning_budget is IGNORED here).
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 \
GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-9DDE \
    --fresh --model qwen3-coder-30b --coach-model gemma4-31b \
    --task-timeout 4800 --sdk-timeout 3600 --no-context --max-parallel 1 \
    2>&1 | tee .guardkit/autobuild/FEAT-9DDE-run3-stdout.log
```

- **Do NOT set `GUARDKIT_COACH_GATHER=1`.** GATHER=0 is the shipped default and
  avoids the B-full Phase-A "Recursion limit of 12 → degrade to B-min" wall-time
  tax (per-turn ~450s of waste with zero investigation value). See
  TASK-PERF-COACHGATHER01.
- **`--max-parallel 1`** (serial) — the safe posture; also FEAT-9DDE Wave 1 is a
  single task anyway.
- The benign `deepagents` `Invalid pattern: '**'` glob **Traceback** in the log is
  caught/logged, **not fatal** — ignore it (filter it out of any monitor grep).

## What to watch (monitor + post-turn checks)

Tail the log with a grep that excludes the benign glob traceback, e.g.:
```
grep -E "ERROR:|WorktreeError|decision=|Wave [0-9]+ |Turn [0-9]+/5: (Player|Coach)|APPROVED|FAILED|verdict-emission|0 AssistantMessage|Running independent tests|partial_honesty|hang detected|unrecoverable_stall|✗ |✓ PASSED"
```

**Harness-health signals (should stay clean — these confirm the 06-12/06-13 fixes hold):**
- `grep -c "verdict-emission failed\|0 AssistantMessage"` → **0** (Coach emits; if not, gemma4-31b regressed too — re-probe it).
- `grep -c "degrading to B-min\|Recursion limit"` → **0** (GATHER=0).
- `grep -c "TASK-FIX-COACHNARR01: embedded"` → **>0 when honesty fires** (feedback quotes deterministic records verbatim, no fabricated "file does not exist" narrative).
- Host repo source clean: `git status --short | grep -E "guardkit/orchestrator|installer/core|guardkit/cli"` → **NONE** (WTESCAPE01; only `.guardkit/features/*.yaml` + the task file's `autobuild_state` frontmatter are legitimate orchestrator state writes).
- A specialist `validation=violation` injection must **not** become a Player honesty `must_fix` (SPECVIOL01) — real Player lies still can.

**The experiment's actual answer (H-Player vs H-Harness):**
- `grep -nE "specialist:(test-orchestrator|code-reviewer) invocation in progress.*\(([6-9][0-9][0-9]|[0-9]{4})s|hang detected|validation=violation"` — do the sub-specialists still run 700s+ / produce violations under the coder Player? **This is the headline result.**
- Did the task **converge** (APPROVED) rather than `unrecoverable_stall` / `timeout_budget_exhausted`? Coder Player reaching a clean approval = H-Player confirmed.

After each Coach turn, read `coach_turn_N.json` and confirm the verdict is
**evidence-based** (populated `criteria_verification`, `tests_run` real) — don't
trust an APPROVED at face value (this session caught a "green over broken seam"
that way; verify on disk).

## What's already done (context — don't redo)

- **All 5 harness/evidence follow-ups landed & validated** this session:
  TASK-FIX-SPECVIOL01, TASK-FIX-COACHNARR01, TASK-FIX-BDDROUTETEST01,
  TASK-FIX-WTESCAPE01, TASK-AB-XREPOEV01 (first four in `tasks/completed/`,
  WTESCAPE01 committed). FEAT-C332 (QA-Verifier wiring evidence) is **complete &
  merged** (analyzer in guardkitfactory; 3 evidence probes + 1 hard gate in the
  Coach path).
- **FEAT-9DDE run 2 (gemma4-31b Coach) result:** `unrecoverable_stall` at turn 3.
  Crucially this **validated the harness** — Coach emitted cleanly all 3 turns,
  honest populated criteria (got to **8/9 ACs by turn 3**), COACHNARR01 embedded
  records verbatim, no escape, the **stall detector correctly bailed early** (vs
  burning to a budget wall). The FAILURE was the **Player substrate**: poor report
  hygiene (claimed a nonexistent file; `tests passed` vs `tests_run: false`
  contradiction) + sub-specialists running 700s+ producing violation-grade output.
  That substrate failure is *exactly what this experiment re-tests with a stronger
  Player.* The run-2 worktree had an ~8/9-complete TSJ-001 (salvageable) but the
  pre-flight cleanup above will remove it — copy it out first if you want it.

## Why this is the right next move (strategic context)

The session's consistent finding: **the harness is solid; the bottleneck is the
local Player/specialist substrate.** Two things are about to change that substrate,
which is *why we don't deep-tune `qwen36-workhorse` now*:

1. **fleet-memory migration** (separate repo, in progress) retires Graphiti's
   `qwen-graphiti` (Qwen 2.5 Instruct) → frees **~28 GB** GPU on the GB10.
2. **NVIDIA DGX Spark arrives Mon 2026-06-15** → more compute / memory headroom.

Recommendation for the model-selection decision (informed by this experiment +
the GB10 forum): **spend the freed/new capacity on the Player** (the role where
intelligence moves build success) — `qwen3-coder-30b` is the prime candidate to
validate now; a larger Qwen3 (32B/72B) is the upgrade path if it fits. **Keep
`gemma4-31b` as the reliable Coach** (make it co-resident default once memory
allows; it doesn't need to be bigger — the QA-Verifier evidence bundle lets a
modest Coach stay honest). Re-evaluate specialists only after this experiment
says whether they're Player-driven or harness-bound.

## Cheap durable wins still pending (do anytime, model-independent)

- **Pin `gemma4:26b` out of reasoning mode** on llama-swap (10-min config fix) →
  the fast Coach (~30-60s synthesis vs 31b's 3.5-6.5 min) becomes usable again.
- **Fix the synthetic-feedback misattribution string**: when the Coach fails to
  emit, the orchestrator's fallback rationale hardcodes "qwen36-workhorse F2 at
  Coach level" even when the Coach was a different model (e.g. gemma4:26b) — a
  COACHNARR-class misdirection. Make it name the actual coach model.

## Key references

- Prior handoff: [`docs/retro/qa-verifier-autobuild-session-handoff.md`](qa-verifier-autobuild-session-handoff.md)
- Coach B-full gather decision: `TASK-PERF-COACHGATHER01` (medium; GATHER=0 is safe default)
- Coach reliability scope (F2, specialist axis): `FEAT-F022` (needs re-plan; task files missing)
- Build-ready feature inventory: only **FEAT-9DDE** had all task files on disk;
  most other planned FEATs need `/feature-plan` re-run before they're buildable.
- GB10 real-world usage: agent memory `nvidia-gb10-dgx-spark-forum` (forum URL above).
