# 🚀 Conversation Starter — GPT-OSS-120B Player validated; autobuild cutover unblocked (2026-06-16)

> ⛔ **SUPERSEDED (2026-06-16):** its "one thing to do" (build FEAT-FAUD) is done —
> FEAT-FAUD built green, was hand-corrected, and merged to main; HMIG-011 cutover
> is flipped. Read **`session-handoff-2026-06-16-faud-merged-hmig011-flipped.md`**
> instead. Kept for historical context (config recipe + gotchas).

> **How to use:** open a fresh session and say *"Read
> `docs/retro/CONVERSATION-STARTER-2026-06-16-gptoss-player-validated-cutover.md`
> and continue."* Self-contained.
>
> **You are running ON the GB10** (`promaxgb10-41b1`), llama-swap on `:9000`.
> Predecessor: [`session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md`](session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md).

---

## 🎯 THE ONE THING TO DO NEXT

**Build `FEAT-FAUD` end-to-end with the GPT-OSS-120B Player** — a fresh, bounded,
hand-crafted feature (`guardkit feature audit`, a stale-feature-status detector),
created this session as a *harder* second validation of the gpt-oss Player before
the cutover flip. Exact command (box is already in autobuild-mode; see state below):

```bash
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 PYTHONUNBUFFERED=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-FAUD --fresh --base-branch main \
    --model gpt-oss-120b --coach-model gemma4-coach \
    --max-turns 8 --task-timeout 7200 --sdk-timeout 3600 --no-context --max-parallel 1 \
    > .guardkit/autobuild/FEAT-FAUD-gptoss-run1-stdout.log 2>&1
```

**Before launching:** (1) confirm `systemctl is-active llama-swap-keepalive.timer` ==
`inactive` (it must stay paused — see gotchas); (2) probe `gemma4-coach` returns
reasoning-free (serving config drifts); (3) `git worktree remove .guardkit/worktrees/FEAT-FAUD --force; git branch -D autobuild/FEAT-FAUD` only if a stale one exists.
**Watch for:** Wave-1 TASK-FAUD-001 (auditor module + tests) converges → Wave-2
TASK-FAUD-002 (CLI `feature audit` + `--fix`) → Wave-3 TASK-FAUD-003 (docs, direct)
→ `FEATURE RESULT: SUCCESS`. 3 tasks / 3 waves — harder than FEAT-9DDE's 2.
**Watch mem** (peak ~100-105 GB / 121 GB; 0 OOM last run but headroom is ~17 GB).

---

## ✅ THE BIG WIN THIS SESSION

**GPT-OSS-120B is validated as the autobuild Player on the existing GB10 — the
DGX Spark was not needed.** FEAT-9DDE ran **fully green end-to-end** (run 13/13b),
the first *honest* (no hand-isolation) green of the whole campaign:

- **Wave 1 (TASK-TSJ-001 producer):** gpt-oss converged in **2 turns** — turn 1 passed
  pytest but failed runtime-parity → arm-b **overrode approve→feedback** (first live
  firing of that branch); turn 2 it **applied the dual-mode-import fix incrementally**
  (2 files *modified*, not rewritten) → runtime-parity passed → Coach approved →
  **smoke gate passed**. *This is exactly what `qwen3-coder-30b` could NOT do across
  8 turns × multiple runs (it rewrote from scratch every turn).*
- **Wave 2 (TASK-TSJ-002, direct mode):** wired bin-entry + `--json` specs → **DIRECTFG01
  gate verified** → Coach approved (2 turns). `FEATURE RESULT: SUCCESS, 2/2, 0 OOM`.
- **Clears HMIG-010 "condition 1"** (a stronger Player driving a fresh feature end-to-end
  on the local LangGraph+GB10 substrate) — the one gate that was blocking the cutover.

Bonus validations seen live: **arm-b** (runs 10/12/13), **EVBINST02 both legs** (`.claude/task-plans/`
AND `large_tool_results/` now filtered live), tool-calling round-trips (harmony→OpenAI
`tool_calls`), warm decode **~43 tok/s**.

**Model-selection research** (GB10 forum + spark-arena): see memory
[[dgx-spark-player-model-selection]]. spark-arena.com is bot-blocked/client-rendered (useless).
GPT-OSS-120B was the top pick and is now live-validated. Backups: GLM-4.5-Air, Nemotron-3-Super.

---

## 🖥️ BOX STATE — READ BEFORE TOUCHING

The GB10 is **in autobuild-mode** right now (left intentionally for the next run):

| Thing | State | Note |
|---|---|---|
| `llama-swap-keepalive.timer` | **STOPPED** (system timer) | **MUST stay paused during gpt-oss runs** — else it revives the ~80 GB fleet on top of gpt-oss → OOM. Re-enable only when done: `sudo systemctl start llama-swap-keepalive.timer` (needs YOUR sudo — I can't). |
| Fleet (qwen-graphiti/qwen36-workhorse/nomic-embed) | **EVICTED** | Other workloads (Jarvis/graphiti/LPA) are paused until the fleet is restored. |
| `gemma4-coach` | loaded | the Coach |
| `gpt-oss-120b` | unloads after 10 min idle (ttl 600) | cold-loads (~60s, warm shards) on the next Player request |
| llama-swap service | `--user`, `active`, `-watch-config` | **`-watch-config` does NOT catch edits** (atomic-save inode quirk) → after any config edit, `systemctl --user restart llama-swap` (no sudo) to apply. |
| `mem` | ~37 GB / 121 GB idle | peak under run ~100-105 GB |

### The gpt-oss-120b llama-swap config (KEEP it — it's validated)
Added to `/opt/llama-swap/config/config.yaml` (backup: `config.yaml.bak-preGPTOSS-*`):
- a **`gpt-oss-120b`** model entry: llama.cpp `llama-server`, MXFP4 GGUF
  `/opt/llama-swap/models/gpt-oss-120b/gpt-oss-120b-mxfp4-00001-of-00003.gguf`
  (from `ggml-org/gpt-oss-120b-GGUF`, ~63 GB), **`--ctx-size 98304`**, q8_0 KV,
  flash-attn, `--jinja`, aliases `gpt-oss` / `openai/gpt-oss-120b`, ttl 600.
- matrix var `go: gpt-oss-120b` + exclusive set **`autobuild_go: "go & gc"`**
  (gpt-oss Player + gemma4-coach Coach; evicts the fleet when gpt-oss is requested).

### Config gotchas (all hit + fixed this session — don't relearn)
1. **Alias collision** — do NOT give gpt-oss the `autobuild-player` alias (already on
   `qwen36-workhorse`) → llama-swap "duplicate alias" crash-loop. Use `--model gpt-oss-120b`.
2. **ctx must be ≥98304** — 65536 hit **F20 overflow** on the TSJ-002 direct-mode prompt
   (67,209 tokens). 98304 is set and proven.
3. **Exclusive set + `--no-context` + keepalive paused** are all load-bearing (else OOM).

---

## 🔭 CUTOVER STATUS (HMIG-010 / HMIG-011)

- **HMIG-010 "condition 1" = MET** (gpt-oss drove FEAT-9DDE fresh→green). Optionally
  confirm with the FEAT-FAUD run above (the user wanted a *harder* second data point).
- **HMIG-011 = the flip**, still pending: `guardkit/orchestrator/.../selector.py:309`
  still defaults to `"sdk"`; change `os.environ.get(env_var, "sdk")` → `"langgraph"`,
  then run AC-002..008 (falsifier: no `claude_agent_sdk` import during Player invoke;
  docs; observation window ≥75% first-pass; rollback dry-run). **Deadline 2026-06-22.**
  SDK stays as instant fallback (`GUARDKIT_HARNESS=sdk`).
- Architecture already clears the GO bar (FEAT-AOF runs 19/20/25 were 3/3). The only
  remaining risk was Player quality → now answered.
- **Recommended next sequence:** FEAT-FAUD green → flip HMIG-011 → restore box.

---

## ⚠️ HONEST GAPS

- **arm-a** (post-approval bounded smoke-feedback-retry) still **not live-exercised** —
  arm-b catches the defect earlier so no run reached arm-a. 32 unit tests; low priority.
- The whole campaign exposed **repo feature/task-status rot**: every "planned"
  `.guardkit/features/*.yaml` is actually a feature **built ~4 months / 772 commits ago**
  (tasks already in `tasks/completed/`, deliverables in main). FEAT-FAUD exists to give
  `guardkit feature audit --fix` to detect/reconcile exactly this. (This is *why* there
  was no ready fresh feature to validate against — had to hand-craft FEAT-FAUD.)

---

## 🌳 REPO / FIXTURE STATE

- **Uncommitted (this session, not yet committed):** `.guardkit/features/FEAT-FAUD.yaml`
  + `tasks/backlog/feature-audit/TASK-FAUD-00{1,2,3}-*.md` (the new feature). Also
  `.guardkit/features/FEAT-9DDE.yaml` (left `completed` after the green run).
- HEAD = `71db6d26` (CIGUARD01). Local main is ~40 commits ahead of origin (validated
  work incl. COACHRUNPARITY01, EVBINST02, FRESHCLEAN01, BDDFW01/SEAM01/CIGUARD01).
  **Pushing main→origin closes CIGUARD01 AC-6** (turns the seam guards green on the shared branch).
- Run logs: `.guardkit/autobuild/FEAT-9DDE-run13-stdout.log` (Wave-1 green),
  `FEAT-9DDE-run13b-stdout.log` (Wave-2/DIRECTFG01 green).
- FEAT-9DDE rerun branches kept: `feat9dde-rerun-base`, `feat9dde-run8/9-base`.

### Restore the box to normal (when done validating)
```bash
# bring the fleet back (no sudo):
systemctl --user restart llama-swap
# re-enable crash-revival (YOUR sudo):
sudo systemctl start llama-swap-keepalive.timer
# KEEP the gpt-oss-120b config (validated; on-demand, doesn't disturb the fleet).
# Optionally tidy FEAT-9DDE.yaml back to its committed state if desired.
```

---

## 🔗 KEY REFERENCES

- **Player-model memory:** [[dgx-spark-player-model-selection]] (config recipe + gotchas).
- **Cutover-readiness assessment** (full matrix/critical-path): produced 2026-06-15 via
  the `autobuild-cutover-readiness` workflow — key facts folded into this doc.
- **Prior handoff:** `session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md`.
- **Rules in play:** `absence-of-failure-is-not-success.md`, `path-string-mismatch-is-not-dishonesty.md`,
  `evidence-boundary-narrower-than-write-surface.md`, `namespace-hygiene.md`, `harness-cancellation-contract.md`.
- **gpt-oss GGUF source:** `ggml-org/gpt-oss-120b-GGUF` (MXFP4, public). SM121 kernels are in the
  `llama.cpp-new` build, not the GGUF.
