# Structural defence beats a prompt instruction when the behaviour is LLM-chosen

> **Source**: Seeded by TASK-FIX-SPECHANG (commit `5c3ebcbe6`, 2026-06-03).
> Pair with the Graphiti design-rule node *"Orchestrator-side cap beats prompt
> instruction when behaviour is LLM-chosen"* under `guardkit__project_decisions`.
> Sibling of [`namespace-hygiene.md`](namespace-hygiene.md) — both are instances
> of the meta-rule *local decisions touching externally-defined behaviour (Python
> namespaces; LLM emergent tool patterns) need structural defences, not advisory
> ones*.

## The rule

When a specialist's pathological runtime behaviour is **LLM-chosen** (emergent
from the tool surface the SDK exposes) rather than **prompted** (present in the
agent definition or the focused prompt), a deterministic orchestrator-side cap
beats a probabilistic prompt instruction.

An LLM can ignore a negative prompt instruction ("do NOT use X") — the known
compliance gap for negative instructions. A structural bound applied from
*outside* the LLM's control loop fires regardless of what the LLM decides, and
its falsifier is deterministic.

So: pair every *"ask the LLM not to do X"* instinct with a check on whether X can
be made **structurally impossible (or structurally bounded) from outside the
LLM's control loop**.

- If **yes** → prefer the structural fix. It does not depend on LLM compliance,
  and the falsifier is a deterministic invariant.
- If **no** → the prompt instruction is the only lever, but pair it with
  monitoring that detects when the LLM ignores it.

## Why this rule exists

In the TASK-HMIG-009A AC-003 canary batch (2026-06-03,
`docs/reviews/autobuild-migration/long-run-1.md`), the Phase 4 test-orchestrator
specialist hit the **2340s SDK timeout on every turn** — contributing ~115 min
of a 159 min run across 3 turns. It was **not genuinely hung**: heartbeats
continued and tool blocks fired. The pattern was the specialist launching pytest
via Claude Code's `Bash run_in_background=true`, then polling `TaskOutput` until
the SDK timeout fired — even when pytest itself would finish in under 2 minutes.

AC-001 confirmed the behaviour was **LLM-chosen, not prompted**:

- `installer/core/agents/test-orchestrator.md` shows only synchronous pytest
  examples; it never instructs `run_in_background=true` or `TaskOutput` (grep
  count for `run_in_background` in that file is **0** today).
- The focused prompt builder `_build_test_orchestrator_prompt`
  (`guardkit/orchestrator/specialist_invocations.py:678`) says "run the test
  suite" but does not constrain *how*.
- `invoke_test_orchestrator` passes `allowed_tools=["Read", "Write", "Bash",
  "Search"]` (`specialist_invocations.py:1248`). `Bash.run_in_background` is a
  *parameter* of the `Bash` tool, not a separately-denyable tool, and
  `TaskOutput` was observed callable even without being in the allow-list — so
  the allow-list could not suppress the pattern.

Three fix shapes were weighed (AC-002):

- **(a)** a prompt instruction telling the specialist not to background pytest —
  rejected: known reliability gap (the LLM may ignore a negative instruction);
- **(b)** an orchestrator-side per-specialist SDK-timeout cap — **chosen**;
- **(c)** specialist-level stall detection counting identical polls —
  disproportionate for a complexity-3 fix.

The chosen fix added the module constant
`_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS = 600`
(`specialist_invocations.py:88`) and a `min(sdk_timeout, cap)` call in
`invoke_test_orchestrator`
(`capped_sdk_timeout = min(sdk_timeout, _TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS)`,
`specialist_invocations.py:1232`), with an INFO log when the cap fires. When the
cap forces the SDK timeout, `run_specialist`'s existing exception path converts
it into a `status="failed"` Phase 4 block that the Coach already handles — so the
2340s burn becomes a fast Phase 4 failure with no new failure-routing plumbing.

The cap has since been extended to the symmetric Phase 5 code-reviewer
(`_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS`, `specialist_invocations.py:106`, from
TASK-PERF-SPECLAT01) and complemented by a no-model-activity watchdog
(TASK-FIX-SPECHANG2, `_no_activity_watchdog_exceeded` at
`specialist_invocations.py:243`) for the residual genuine-hang case the blunt
duration cap cannot see — but the structural-cap-over-prompt decision is the one
this rule captures.

## Symptom

- A specialist consumes (nearly) the full `sdk_timeout` on every turn while
  heartbeats/tool blocks keep firing — i.e. it is *busy*, not hung.
- The tool blocks show `Bash run_in_background=true` followed by repeated
  `TaskOutput` polls of the same background task.
- The underlying work (pytest, review) would finish far faster if run
  synchronously / inline.
- The pathological pattern is **absent** from the agent definition and the
  focused prompt — it is emergent from the SDK tool surface.

## Detection recipe

```bash
# 1. Is the pathological pattern prompted, or LLM-chosen? Grep the agent def
#    and the focused prompt builder — a zero count means it is NOT prompted.
rg -c "run_in_background|TaskOutput" installer/core/agents/test-orchestrator.md
rg -n "def _build_test_orchestrator_prompt" guardkit/orchestrator/specialist_invocations.py

# 2. Does the specialist runner apply a per-specialist SDK-timeout ceiling,
#    independent of the caller-supplied sdk_timeout?
rg -n "_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS|_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS" \
   guardkit/orchestrator/specialist_invocations.py

# 3. Is the cap actually applied before the specialist is invoked?
rg -n "capped_sdk_timeout = min\(sdk_timeout" guardkit/orchestrator/specialist_invocations.py
```

## Remediation

1. **Establish provenance first.** Confirm whether X is prompted or LLM-chosen
   (grep the agent def and the focused prompt). Only LLM-chosen behaviour
   justifies a structural cap over a prompt fix.
2. **Prefer the structural bound.** Apply a deterministic ceiling from outside
   the LLM's control loop — here `min(caller_sdk_timeout, per_specialist_cap)` —
   so any caller-supplied timeout above the cap is forced down before the
   specialist runs. The invariant (`effective_timeout <= cap`) is the falsifier.
3. **Route the cap-triggered failure through an existing path.** Do not add new
   failure plumbing: a capped timeout should surface as the same `status="failed"`
   block the normal timeout path already produces, so downstream (Coach) handling
   is unchanged.
4. **Log when the cap fires** so operators can correlate fast-failed specialist
   turns with the cap.
5. **When X cannot be made structurally impossible,** the prompt instruction is
   the only lever — but pair it with monitoring that detects when the LLM ignores
   it (e.g. the no-model-activity watchdog added in TASK-FIX-SPECHANG2).
6. **Decompose, don't inflate the cap.** A suite that legitimately needs longer
   than the cap should be split at the task level, not accommodated by raising
   the ceiling.

## Grep-able signature (for next agent)

```bash
# Structural-cap fingerprint (MUST MATCH; absence = the cap was removed):
rg -n "capped_sdk_timeout = min\(sdk_timeout" \
   guardkit/orchestrator/specialist_invocations.py            # -> 1232 (test-orch), 1356 (code-reviewer)
rg -n "_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS" \
   guardkit/orchestrator/specialist_invocations.py            # -> 88 (const), 350, 1043, 1232

# Provenance fingerprint (the behaviour is NOT prompted; expect 0):
rg -c "run_in_background" installer/core/agents/test-orchestrator.md   # -> 0

# Sibling-rule lookup:
rg "structural-defence-beats-prompt-instruction|namespace-hygiene" .claude/rules/
```

## When this rule triggers

- Before adding a prompt instruction of the form "do NOT do X" to an agent
  definition or a focused prompt to curb a specialist's runtime behaviour — first
  check whether X can be bounded structurally from the orchestrator.
- Before introducing a new orchestrator specialist: it should inherit the same
  per-specialist SDK-timeout cap (and no-activity watchdog) as its siblings.
- During Phase 2.5 architectural review for any task that touches
  `specialist_invocations.py` timeout handling or the specialist prompts/agent
  definitions.
- During any diagnostic session investigating a specialist that burns its full
  `sdk_timeout` while remaining *busy* (heartbeats/tool blocks continuing).

## What it does NOT cover

- **Genuinely-hung specialists.** A specialist that stops calling the model
  entirely is the no-model-activity watchdog's territory (TASK-FIX-SPECHANG2),
  not this duration-cap rule. The duration cap bounds a busy-but-wasteful loop;
  the watchdog catches a true idle hang far sooner.
- **Prompted pathological behaviour.** If the pattern *is* in the agent def or
  prompt, remove it from the prompt — a structural cap on top of a
  prompt-induced problem masks the real cause.
- **Choosing the cap value.** `600s` (and its
  `GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP` override for the code-reviewer) is
  operator policy; this rule governs the *shape* (a deterministic ceiling
  applied outside the LLM loop), not the number.
- **Root-causing throughput.** The cap converts a slow specialist into a fast
  failure; it does not make the specialist faster. Reaching for a faster model is
  a separate, deferred concern (see TASK-PERF-SPECLAT01, which chose bounding
  over a faster-model override for the same offline-testability reason).
