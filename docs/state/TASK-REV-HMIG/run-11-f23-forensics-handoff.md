# Run-11 F23 forensics handoff — substrate failure at 22-minute Coach scale

> **Purpose**: capture run-11 findings and the GB10-side forensic
> commands needed to discriminate root cause of F23 (HTTP 502 from
> llama-swap after sustained Coach reasoning). Read on the GB10
> (`promaxgb10-41b1`) and run the commands in §3.
>
> **Status**: awaiting GB10 forensics; audit-trail updates
> (`feature-run-incidents.md` / `feature-run-analysis.md` /
> `TASK-REV-HMIG-feature-results.json`) **not yet drafted** — they
> need the substrate root cause to land first so I-012 (F23) can be
> recorded with the correct class-of-defect tag.
>
> **Branch state at handoff**: `main @ 26b5310b` audit-trail commit +
> `cc3b2164` SPECCOCH01 fix landed. Run-11 log at
> [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md`](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md).

## 1. What just happened (one-line summary)

Run 11 empirically validated **TASK-FIX-SPECCOCH01** (F22 RESOLVED:
Coach got `budget_cap=4799s`, not the 120s grace cap) — but the
substrate failed at scale: HTTP 502 Bad Gateway from llama-swap after
**~55 successful HTTP 200s** over **~19 minutes** of Coach LLM
invocation under `gemma4:26b --reasoning auto`. New finding **F23**
(candidate, substrate-class). AC-009 still not definitively answered
because the Coach never got to emit its fenced-JSON verdict.

## 2. Evidence summary

| Metric | Value | Source (run-11 log line) |
|---|---|---|
| Task budget | 4800s (per-task frontmatter override) | [73](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L73) |
| Turn 1 Player wall | 342s | [85-191](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L85-L191) |
| SPECHANG fired (test-orchestrator) | 150s no-model-activity, terminated | [232](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L232) |
| **SPECCOCH01 decoupling worked** | Coach `budget_cap=4799s` (NOT 120s grace) | [263](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L263) |
| Coach independent tests | 224.8s (pinned bootstrap venv) | [262](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L262) |
| Coach LLM start | 13:11:47 (UTC) | derived from line 263 |
| Coach LLM successful HTTP 200s | ~55 over 1110s of progress | [265-343](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L265-L343) |
| **F23: HTTP 502 Bad Gateway** | at 1110s elapsed (13:30:36 UTC) | [344](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L344) |
| OpenAI client retries | 4 attempts, all failed | [345-348](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L345-L348) |
| Coach verdict file emitted | NO — no `coach_turn_1.json` artifact | `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/` |
| Wall-clock total | 30m 55s | [395](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L395) |
| Feature status | FAILED (Coach `error`, not `feedback`) | [349, 353, 388-401](../../reviews/autobuild-migration/autobuild-FEAT-AOF-run11.md#L349) |

## 3. GB10 forensics — run these on `promaxgb10-41b1`

The 502 came from llama-swap or its llama.cpp upstream. We need to
discriminate four hypotheses (RAM/KV OOM, llama-swap eviction, llama.cpp
crash, network blip). Run **all four blocks** in order — they are cheap
and read-only.

**Time window of interest: 2026-06-07 13:11 → 13:31 UTC** (Coach LLM
invocation start through 502).

### 3.1 Was it OOM (most likely if it's a recurring substrate envelope)?

```bash
# Kernel OOM killer activity around the failure window
sudo dmesg -T | grep -iE 'killed|oom|out of memory|invoked oom-killer' \
  | awk -v from='Jun  7 13:00' '$0 ~ from || NR > line' | tail -40

# Or simpler if you don't care about the time-window filter:
sudo dmesg -T | grep -iE 'killed|oom' | tail -20

# Current RAM state (compare against the §9.13 budget — 111GB pre-bump)
free -h
```

**Interpretation**:
- `killed process N (llama-server)` or similar → OOM kill of llama.cpp serving gemma4-coach → **F23A (substrate-sizing under sustained load)**. Action: reduce gemma4-coach `n_ctx` from current bumped value or accept the 20-min Coach wall as the gemma4 envelope.
- No OOM lines, RAM well below 128GB → not OOM, move to §3.2.

### 3.2 Was llama-swap routing another model into the slot?

```bash
# llama-swap service activity in the failure window
sudo journalctl -u llama-swap.service --since '2026-06-07 13:10:00' \
  --until '2026-06-07 13:31:00' \
  | grep -iE 'swap|evict|load|unload|crash|panic|gemma4-coach|architect-agent|qwen36-workhorse'

# Or for the user-systemd variant if that's the launch mode:
sudo journalctl --user -u llama-swap --since '2026-06-07 13:10:00' \
  --until '2026-06-07 13:31:00' \
  | grep -iE 'swap|evict|load|unload|crash|panic'

# Keepalive timer fires (5-min cadence per §9.13) — what was probed?
sudo journalctl -u llama-swap-keepalive.timer --since '2026-06-07 13:10:00' \
  --until '2026-06-07 13:31:00' || true
sudo journalctl -u llama-swap-keepalive.service --since '2026-06-07 13:10:00' \
  --until '2026-06-07 13:31:00' || true
```

**Interpretation**:
- An `unload gemma4-coach` or `evict gemma4-coach` line near 13:30:36 → keepalive race evicted Coach mid-generation → **F23B (operator config)**. Action: confirm TTL=0 on gemma4-coach (§9.13 says it is — verify hasn't drifted) and tune keepalive cadence. File as TASK-OPS-COACHTTL.
- Matrix-set transition lines (e.g. `set=all → set=arch`) → confirms a routing race. Same F23B path.
- No swap/evict lines → llama-swap held the slot stable; move to §3.3.

### 3.3 Did llama.cpp itself crash?

```bash
# Full system journal in the failure window for anything llama-related
sudo journalctl --since '2026-06-07 13:11:00' --until '2026-06-07 13:31:00' \
  | grep -iE 'llama.cpp|llama-server|gemma|abort|segfault|crash|panic|backtrace'

# Direct llama.cpp logs if they're separate from systemd
sudo find /var/log /opt/llama-swap/logs ~/.local/share/llama* -type f -name '*.log' \
  -newer /tmp/run11-anchor 2>/dev/null | head -20
# (skip if you don't have /tmp/run11-anchor — equivalent: filter by date range)
```

**Interpretation**:
- `Aborted`, `Segmentation fault`, or stack-trace lines → llama.cpp crashed under sustained reasoning load → **F23C (substrate stability)**. Action: file as substrate-escalation, candidate for AC-007 fallback to `nemotron-3-super:120b-a12b`.
- No crash lines → llama.cpp held stable; move to §3.4.

### 3.4 Network / Tailscale stutter?

```bash
# Tailscale connection state — were we connected to whitestocks the whole time?
tailscale status | grep -E 'whitestocks|promaxgb10'

# Any network errors in the kernel ring buffer?
sudo dmesg -T | grep -iE 'eth|wlan|enp|tailscale|network|tcp' \
  | tail -30

# llama-swap upstream HTTP errors
sudo journalctl -u llama-swap.service --since '2026-06-07 13:25:00' \
  --until '2026-06-07 13:31:00' | grep -iE 'upstream|502|connection|timeout'
```

**Interpretation**:
- Network errors in the 13:30 window → transient, unlikely to recur → **F23D (transient)**. Action: just re-run.
- All clean → genuinely don't know root cause. Re-run and watch live.

## 4. Decision matrix (after running §3)

| Forensic finding | Class | Next code action | Next operator action |
|---|---|---|---|
| §3.1 OOM kill of llama.cpp | F23A substrate-sizing | none | Reduce gemma4-coach `n_ctx` OR accept 20-min Coach as envelope. Update §9.13. |
| §3.2 llama-swap evicted gemma4-coach | F23B operator config | none | File TASK-OPS-COACHTTL. Confirm TTL=0, tune keepalive. |
| §3.3 llama.cpp crash | F23C substrate stability | none | AC-007 escalation surface — start nemotron-3-super:120b-a12b investigation (gated on 2nd GB10 + ConnectX-7 ETA) |
| §3.4 network blip | F23D transient | none | Re-run 12, watch live |
| All four clean, no signal | F23E mystery | none yet | Re-run 12, instrument heavily, treat as a recurrence question |

## 5. What's NOT a problem (resolved this run — don't waste time on these)

- **F20** (gemma4-coach n_ctx) — RESOLVED, no `HTTP 400` in run 11. §9.13 bump still validated.
- **F21** (turn-2 Coach stall) — RESOLVED, was purely downstream of F20.
- **F22** (SPECHANG → Coach grace cascade) — **RESOLVED EMPIRICALLY by SPECCOCH01** in this run. Coach got `budget_cap=4799s`, NOT 120s. SPECCOCH01 task can move to `tasks/completed/2026-06/` once audit-trail updates land.
- **F17** (Coach prose-without-fenced-JSON under `--reasoning off`) — DID NOT FIRE in this run (Coach was on `--reasoning auto`). Whether `--reasoning auto` solves F17 is still unanswered because the 502 hit before Coach could emit.
- **F13** (SPECHANG 600s duration cap) — replaced by the new 150s no-activity watchdog which fired correctly and was contained by SPECCOCH01.

## 6. What COACHSF01 didn't catch (architecture note, not a code defect now)

The Coach's `Connection error` from `agent.ainvoke` did NOT trigger
COACHSF01's synthetic-feedback safety net — by design. Per
[`.claude/rules/feature-build-invariants.md`](../../../.claude/rules/feature-build-invariants.md):

> the parser's raise sites MUST emit the literal substrings
> `'Coach decision not found'` and `'Coach decision invalid'`

A substrate Connection error is a different shape. The orchestrator
correctly classified the failure as `error` rather than `feedback`,
which preserves the "synthetic feedback means substrate-emission
failure, not substrate-connection failure" invariant.

**Worth a post-cutover design conversation** (potentially file as
**TASK-REV-COACH-RETRY-CONTRACT**): should sustained-substrate Connection
errors after substantive Coach work also fall through to a "retry-next-turn"
synthetic-feedback? The 19 minutes of wasted Coach work is operationally
expensive. But this is a design question for post-2026-06-15, not a fix
gating cutover.

## 7. Next-step pointers after forensics

Once §3 forensics produce a class assignment (§4), the next steps are:

1. **Report class back to Claude session on Mac**. The decision matrix in §4 determines whether the next action is "run 12 (transient)", "file an operator-config task" (F23B), or "escalate to AC-007 nemotron-3-super path" (F23C).
2. **Audit-trail updates will be drafted with the class-tag finalised**:
   - `feature-run-incidents.md` — annotate I-011 (F22) as RESOLVED 2026-06-07 (run 11), add I-012 (F23) with correct class
   - `feature-run-analysis.md` — run-11 status header, F22 RESOLVED, F23 paragraph
   - `TASK-REV-HMIG-feature-results.json` — run_attempts[11] + task_outcomes[IA03 run 11]
   - SPECCOCH01 task file → `tasks/completed/2026-06/`
3. **Run 12 invocation** (only after substrate root cause is known) — same shape as run 11:
   ```bash
   mkdir -p .guardkit/autobuild/TASK-REV-HMIG-feature-run/
   GUARDKIT_HARNESS=langgraph \
     OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
     OPENAI_API_KEY=llama-swap-local-key \
     guardkit autobuild feature FEAT-AOF \
       --fresh --model qwen36-workhorse --coach-model gemma4:26b \
       2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-12-stdout.log
   ```
   With `GUARDKIT_COACH_GRACE_PERIOD_SECONDS=1500` as a defensive
   backstop if SPECCOCH01's Shape B is in (verify with
   `git log --oneline | grep SPECCOCH01` on the Mac; if commit
   message mentions only Shape A then env-tunable backstop is not yet
   in and the env var won't be read).

## 8. Cutover-deadline status (2026-06-15)

- **Architecture**: ready. Every F1-F22 code finding closed empirically across runs 1-11.
- **Substrate**: unanswered. F23 is the load-bearing question for the cutover-now-vs-wait decision.
- **Hardware ETA**: 2nd GB10 + ConnectX-7 "~next week" per earlier briefing — would land approximately at the 2026-06-15 deadline. Cutting it close.

If F23 turns out to be F23A (OOM) or F23C (llama.cpp crash) and the
sustainable Coach-reasoning envelope under gemma4 is <20 min, the
single-GB10 + gemma4-coach posture may not survive the operator-load
of a real cutover Day 1. The AC-007 escalation path
(`nemotron-3-super:120b-a12b`) becomes the dominant question.

If F23 turns out to be F23B (operator config) or F23D (transient),
single-GB10 cutover is still on the table for 2026-06-15.

Forensics in §3 decide which path.
