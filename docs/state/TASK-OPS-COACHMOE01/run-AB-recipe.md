# Step-2 live A/B recipe — gemma4-coach (MoE) Coach vs run-25 (g31)

> One flag changed from the run-25 baseline: `--coach-model gemma4:31b` →
> `--coach-model gemma4:26b` (`gemma4:26b` is the alias for `gemma4-coach`, the
> 26B-A4B MoE). `GUARDKIT_COACH_GATHER=1` kept so the Phase-A→B-min
> graceful-degradation path is exercised identically to run-25.

## Command (run from the orchestrator host — the Mac, as run-25 was)

```bash
GUARDKIT_COACH_GATHER=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-AOF \
    --fresh --model qwen36-workhorse --coach-model gemma4:26b \
    --task-timeout 4800 --sdk-timeout 3600 --no-context --max-parallel 1 \
    2>&1 | tee .guardkit/autobuild/TASK-OPS-COACHMOE01-AB/run-moe-stdout.log
```

### Optional Lever-2 leg (AC-003 — already characterised as a no-op single-shot)
Add to ONE leg's environment to exercise `reasoning_budget` end-to-end through
the orchestrator (the single-shot probe showed the gc route ignores it; this
confirms the orchestrator wiring does not error):

```bash
GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET=0 ...   # (or 2048)
```

## Why this is operationally SAFER than run-25 (g31)

| | run-25 (g31 dense) | this A/B (gc MoE) |
|---|---|---|
| Coach model footprint | ~28 GB | ~17 GB |
| matrix set | minimal `coach31: "qw & g31"` (evicts gc) | default `all: "qg & ne & qw & gc & dl"` — **gc already co-resident** |
| keepalive | **MUST be OFF** (g31 evicts gc; keepalive revives gc on top → OOM) | **stays ON** (it keeps gc warm = the Coach we want) |
| set-switch / eviction risk | high (the F23A OOM class) | none — no switch needed |
| `--no-context` | required (else graphiti/embed switch sets, evict g31) | kept for parity, but gc evicts nothing in `all` either way |

The GB10 already runs the `all` family (~80 GB + gc) as steady state, so this
A/B is the box's normal load profile — no special quiescing required.

## PASS / FAIL (the task falsifier)

PASS = 3/3 verdicts that are **(a)** schema-valid first try, **(b)** honest
(independent oracle ran; no signal_absent green), **(c)** substantive
(`criteria_verification` 100% populated with per-AC evidence) — at materially
lower Coach wall-time than run-25's 3.5–6.5 min legs.
FAIL = any ramble past max_tokens, empty `criteria_verification`, or false-green.

## Running on the GB10 instead of the Mac

The GB10 repo `.venv` is the **inference** host and lacks the orchestrator stack
(`guardkitfactory` + langchain 1.x / langgraph 1.x / deepagents are not
installed). To run the orchestrator here instead of the Mac:

```bash
.venv/bin/pip install -e ../guardkitfactory   # pulls langgraph>=1, langchain>=1.2, deepagents>=0.6.7
```

Caveat: this adds orchestrator (Python/langgraph) load to the inference box
during the run, a different host-load profile than run-25 (Mac orchestrator →
GB10 inference). Prefer the Mac for strict comparability.
```
