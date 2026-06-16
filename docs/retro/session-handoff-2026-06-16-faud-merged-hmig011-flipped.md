# 🚀 Session Handoff — FEAT-FAUD merged + HMIG-011 cutover FLIPPED (2026-06-16)

> **How to use:** open a fresh session and say *"Read
> `docs/retro/session-handoff-2026-06-16-faud-merged-hmig011-flipped.md` and continue."*
> Self-contained. Supersedes `CONVERSATION-STARTER-2026-06-16-gptoss-player-validated-cutover.md`
> (its "one thing to do" — build FEAT-FAUD — is done).
>
> **You are running ON the GB10** (`promaxgb10-41b1`), llama-swap on `:9000`.

---

## 🎯 THE BIG NEWS

1. **GPT-OSS-120B validated as the autobuild Player a second time** — FEAT-FAUD
   (3 tasks / 3 waves) built fresh→green end-to-end (Wave 1 turn 1; Waves 2 & 3
   converged in 3 turns each). This is the harder data point HMIG-010 "condition 1"
   wanted, on top of FEAT-9DDE.
2. **HMIG-011 cutover is FLIPPED** — LangGraph is now the **default** autobuild
   harness. The SDK path is an opt-in fallback (`GUARDKIT_HARNESS=sdk`).
3. **FEAT-FAUD's deliverable shipped to main** — but only after a hand-fix: the
   green autobuild had produced a **functionally broken** `guardkit feature audit`
   (passed synthetic tests, wrong on real data). See "green ≠ correct" below.

---

## ✅ WHAT LANDED ON MAIN (this session, committed; NOT pushed)

| Commit | What |
|---|---|
| `1ffe0c5a` | **FEAT-FAUD** — `guardkit feature audit [--fix]` (stale feature-YAML detector) + tests + docs. Hand-corrected over the raw gpt-oss output. FAUD task files → `tasks/completed/2026-06/`. |
| `3caeb93e` | **HMIG-011 cutover** — default harness flipped `sdk`→`langgraph` via a single `DEFAULT_HARNESS` constant; consumers + tests updated. |

HEAD = `3caeb93e`. Local main is ahead of origin (these two + the prior ~40).

### FEAT-FAUD: green ≠ correct (the lesson)
The gpt-oss green build's deliverable iterated `tasks` as **id strings**, but the
real feature-YAML schema is a **list of dicts** (`{id,…}`) — so every feature
inferred `planned` (0 completed). The **synthetic unit-test fixtures encoded the
same wrong assumption**, so the tests validated the bug. Hand-fixes: dict-or-string
`_task_identifier`, AC-004 exit code (1 when stale & no `--fix`), removed a dead
duplicate `audit` command + a malformed CLAUDE.md section + a non-portable
worktree-path-coupled doc test, added a real dict-schema regression test. Now
correct (`guardkit feature audit` → exit 1, FEAT-CD4C `completed` 9/9 not stale,
etc.). Captured in memory `[[gptoss-player-autobuild-traits]]`. **Takeaway: a
green autobuild validates Player *mechanics*, not deliverable correctness —
review the deliverable against real inputs.**

---

## 🔭 HMIG-011 CUTOVER STATUS

**Done + verified (AC-001/002/003/004/007)** — see the task's "Cutover execution
note (2026-06-16)" in
`tasks/backlog/autobuild-harness-migration/TASK-HMIG-011-...md`:
- **AC-001** flip lives in `guardkit/orchestrator/harness/selector.py` as
  `DEFAULT_HARNESS = "langgraph"` (single source of truth). **Rollback = change
  that one constant back to `"sdk"`.** Consumers (`cli/doctor.py`,
  `coach_validator.py` snapshot + `_is_langgraph_harness`) read the constant.
- **AC-002** falsifier verified (no env var → `LangGraphHarness`, `claude_agent_sdk`
  never imported during select). **AC-007** rollback verified (`=sdk` →
  `ClaudeSDKHarness`). **AC-003** suite green (SDK tests opt into `=sdk`).
  **AC-004** docs in selector docstring + CLAUDE.md AutoBuild section.

**Remaining = operator / calendar (AC-005/006/008):** send the cutover announce;
run the D-2→D-0 observation window (FEAT-9DDE+FEAT-FAUD green are supporting
evidence); mark complete + file Phase-3 (remove `ClaudeSDKHarness` +
`claude-agent-sdk` dep) once the window is clean. Deadline **2026-06-22**.

**Two PRE-EXISTING test reds (NOT cutover-caused; verified failing pre-flip):**
`test_agent_invoker_langgraph.py::...::test_env_var_routes_to_langgraph` (calls
`select_harness(langgraph)` with no `cwd=`) and
`test_autobuild_context_opt.py::...::test_task_work_sdk_max_turns_is_50` (stale
`assert 100 == 50`). Left untouched — fix separately if desired.

---

## 🖥️ BOX STATE → RESTORE WHEN READY

The GB10 is still **in autobuild-mode** (left from the FEAT-FAUD run): the
**`llama-swap-keepalive.timer` is STOPPED** and the fleet
(qwen-graphiti/qwen36-workhorse/nomic-embed) is **EVICTED** — so Jarvis / graphiti
/ LPA are paused. The validated `gpt-oss-120b` llama-swap config is KEPT (on-demand,
ttl 600; doesn't disturb the fleet). To restore:

```bash
# bring the fleet back (no sudo):
systemctl --user restart llama-swap
# re-enable crash-revival (YOUR sudo — I can't run it):
sudo systemctl start llama-swap-keepalive.timer
```

(User freed memory mid-session by closing other Claude/Firefox/VSCode instances;
swap pressure dropped 5 GB→2.6 GB. Peak under the run was ~110-114 GB / 121 GB.)

---

## 📋 OPEN ITEMS / SUGGESTED NEXT STEPS

1. **Push `main` → origin** (not done this session; push only on request). Closes
   **CIGUARD01 AC-6** (turns seam guards green on the shared branch) AND exposes
   the cutover default to downstream consumers (jarvis/forge/dataset-factory). The
   2026-06-15 Anthropic API-key enforcement means SDK-path consumers without
   `GUARDKIT_HARNESS=sdk` should migrate.
2. **AC-005 announce + AC-006 observation window** (operator) → then AC-008 close +
   file Phase-3 dep-removal as TASK-HMIG-012.
3. **FAUD auditor limitation** (minor): `infer_status_for_feature` only emits
   `completed`/`planned`/`in_progress`, so a feature declared `merged`/`failed`/
   `superseded` reads as "stale". Fine for now; widen the terminal-status set if
   `feature audit` is wired into CI.
4. **FEAT-9DDE fully cleaned up (2026-06-16, later in session).** Its deliverable
   (TSJ-001/002 producer + unit tests + bin-entry) was already merged to main and
   works; the leftover worktree + 4 branches (`autobuild/FEAT-9DDE`,
   `feat9dde-rerun-base/run8-base/run9-base`) were a redundant 2026-06-15 Player
   re-validation rerun — removed. TSJ task files now live only in
   `tasks/completed/2026-06/` (the stale `tasks/backlog/task-status-json/` dupes
   were deleted, commit `e5c59d69`). `FEAT-9DDE.yaml` churn discarded (committed
   `status: completed`, audit-consistent). Run logs `FEAT-9DDE-run*.log` kept;
   autobuild state archived to `.guardkit/archive/FEAT-9DDE/`. **Working tree is
   clean.**
5. Stale autobuild worktrees remain for **FEAT-AOF / TASK-GLI-004 / TASK-OBS-ABST**
   (`git worktree list`) — clean up if their work is merged (same pattern as the
   FEAT-9DDE cleanup above; verify each deliverable is on main first).

---

## 🔗 KEY REFERENCES
- **Memory:** `[[gptoss-player-autobuild-traits]]` (Player traits + green≠correct),
  `[[dgx-spark-player-model-selection]]` (model pick + llama-swap config recipe).
- **Cutover task:** `tasks/backlog/autobuild-harness-migration/TASK-HMIG-011-...md`
  (Cutover execution note + rollback).
- **Flip point:** `guardkit/orchestrator/harness/selector.py` (`DEFAULT_HARNESS`).
- **Prior handoff (superseded):** `CONVERSATION-STARTER-2026-06-16-gptoss-player-validated-cutover.md`.
