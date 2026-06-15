# 🧾 Session handoff — COACHRUNPARITY01 validated + DIRECTFG01 live-exercised (2026-06-15)

> **How to use this doc:** open a fresh session and say *"Read
> `docs/retro/session-handoff-2026-06-15-coachrunparity-validated-directfg01-exercised.md`
> and continue."* Self-contained; deeper detail cross-linked.
>
> **Predecessor:** [`CONVERSATION-STARTER-2026-06-14-coachrunparity-and-directfg01.md`](CONVERSATION-STARTER-2026-06-14-coachrunparity-and-directfg01.md)
> (the "one thing to do next was implement COACHRUNPARITY01"). This session
> validated it and got DIRECTFG01 to actually run.
>
> **You are running on the GB10** (`promaxgb10-41b1`), llama-swap on `:9000`.
> Player = `qwen3-coder-30b`, Coach = `gemma4-coach` + `disable_thinking`.

---

## 🎯 HEADLINE — both goals reached

1. **COACHRUNPARITY01 arm-b (per-task runtime-parity guard) is LIVE-VALIDATED** —
   it catches the run-8/9 "passes pytest but won't run standalone" defect
   **pre-approval, in the Wave-1 turn loop**, and feeds the runtime error back
   to the Player as a critical issue.
2. **DIRECTFG01 (direct-mode AC/wiring/bin-entry gate) has now run for the
   first time in 11 attempts** — TSJ-002 executed in direct mode, the gate
   fired its three probes (AC delivery + wiring analysis + bin-entry
   resolution) and passed on real wiring; FEAT-9DDE completed 2/2.

**The one residual blocker is not a GuardKit bug:** the Player
(`qwen3-coder-30b`) **cannot converge the TSJ-001 producer** — it rewrites the
producer from scratch each turn and never derives the dual-mode-import fix from
the runtime-parity feedback (it even broke pytest collection by turn 5). This
is a Player-capability gap, not an orchestrator defect; COACHRUNPARITY01 fixed
the orchestrator side (the Coach now *catches* the non-runnable deliverable and
feeds it back), but it can't make a weak Player act on the feedback.

---

## ✅ WHAT WAS VALIDATED THIS SESSION

| Item | How validated | Evidence |
|------|---------------|----------|
| **COACHRUNPARITY01** committed | 180 unit/integration tests green on HEAD | commit `a11708d0`; `test_runtime_parity.py`, `test_smoke_feedback_retry.py` |
| **arm-b runtime-parity guard** | **Run 10** (live): producer passed pytest, `python3 …/task_status_json.py` raised `ModuleNotFoundError: No module named 'installer'` → Coach emitted it as a **critical** issue every turn (2,3,4,5) → reached Player in-loop | `FEAT-9DDE-run10-stdout.log`; `coach_turn_2.json` critical `ModuleNotFoundError` |
| **DIRECTFG01 direct-mode gate** | **Run 11** (live, isolate): TSJ-002 ran in direct mode; `_direct_mode_evidence_gate` ran AC1 (5/5 ACs verified) + AC2 (wiring) + AC3 (`_check_direct_mode_bin_entries`) → approve | `FEAT-9DDE-run11-stdout.log`; `FEATURE RESULT: SUCCESS`, `status=completed, completed=2/2` |
| **TASK-FIX-WTESCAPE01** write-confinement | **Run 11** (live): Player's main-repo edit of `bin-entries.txt` rejected; Player recovered into the worktree | run-11 log line 135 |
| **SPECLAT01** specialist cap | **Run 10** (live): every specialist capped …→600s | run-10 log |
| **TASK-FIX-EVBINST02** noise strip | **Run 12** (in progress at handoff time) — see "EVBINST02" below | `FEAT-9DDE-run12-stdout.log` |

---

## 🔬 HOW DIRECTFG01 WAS REACHED (the isolate mechanism — reusable)

The literal "remove smoke_gates" alternative from the predecessor doc **does not
work** — the Player can't pass Wave 1 at all (it broke even pytest collection),
so the Coach rejects TSJ-001 regardless of smoke_gates, and TSJ-002 (which
`depends_on` TSJ-001) is **dependency-skipped** (`⏭ Skipping … (dependency
failed)`, `feature_orchestrator.py:2514`). To actually exercise DIRECTFG01 you
must **bypass the unbeatable Wave 1**:

1. Base on **`feat9dde-run9-base`** — it has the *working* dual-mode producer
   committed (runs standalone: verified `schema_version: 1.0` JSON, no
   ModuleNotFoundError). DIRECTFG01's AC3 bin-entry probe needs the producer to
   exist at `installer/core/commands/lib/task_status_json.py`.
2. **Pre-complete Wave 1** in `FEAT-9DDE.yaml`: `TASK-TSJ-001 status: completed`,
   `completed_waves: [1]`, feature `status: in_progress`. `get_resume_point`
   then computes `resume_wave = max([1]) + 1 = 2`.
3. Remove the stale worktree/branch so `--resume` rebuilds fresh from run9-base
   (`feature_orchestrator.py:1041` "Previous worktree not found, creating new
   one").
4. Launch with **`--resume`** (NOT `--fresh` — `--fresh` resets TSJ-001 back to
   pending and re-runs the unbeatable producer).

Result: Wave 1 skipped (TSJ-001 already-completed → `success=True`,
`feature_orchestrator.py:2492`), dependency satisfied, **Wave 2 / TSJ-002 runs
in direct mode → DIRECTFG01 fires**.

**Exact run-11 recipe:**
```bash
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 PYTHONUNBUFFERED=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-9DDE --resume --base-branch feat9dde-run9-base \
    --model qwen3-coder-30b --coach-model gemma4-coach \
    --max-turns 8 --task-timeout 7200 --sdk-timeout 3600 --no-context --max-parallel 1 \
    > .guardkit/autobuild/FEAT-9DDE-run11-stdout.log 2>&1
```

---

## 🧠 KEY LEARNINGS / GOTCHAS (new this session)

1. **`--fresh` only resets state for *incomplete* features.** `_clean_state`
   (worktree cleanup + `reset_state`) is gated on `FeatureLoader.is_incomplete`,
   which is False for `status: completed`/`merged`/`planned`. So `--fresh` on a
   **completed** feature does NOT clean the old worktree/branch (→ "branch
   `autobuild/FEAT-9DDE` already exists" failure) and does NOT reset task
   statuses (→ all tasks skipped as already-completed). After a successful run,
   manually `git worktree remove … --force` + `git branch -D autobuild/FEAT-9DDE`
   and reset the YAML to a clean `planned`+`pending` fixture before re-running.
   *(This bit run 12's first launch.)*
2. **The Player can't converge TSJ-001** (see headline). Confirmed across runs
   7–10. arm-b feedback is clear and critical, but `qwen3-coder-30b` doesn't act
   on it. A more capable Player model — or spelling the dual-mode import fix
   into TASK-TSJ-001's ACs — is needed for honest Wave-1 convergence.
3. **HEAD's committed `FEAT-9DDE.yaml` is `status: merged`** (the feature was
   genuinely merged in reality). `git checkout -- .guardkit/features/FEAT-9DDE.yaml`
   restores *that* merged state — it is the **final teardown**, not a runnable
   rerun fixture. The runnable rerun fixture (planned + pending + smoke_gates)
   lives only in the working tree and must be reconstructed if mutated.
4. **arm-b is downstream of quality gates** — the runtime-parity check only runs
   once the Player's pytest passes (correct ordering: "does it run standalone"
   is checked only after "does it pass tests").
5. Coach model probe still drifts — re-probe `gemma4-coach` +
   `enable_thinking=false` (must return reasoning-free) before every run.

---

## ⚠️ HONEST GAPS / OPEN FOLLOW-UPS

- **arm-a (bounded smoke-feedback-retry) was NOT live-exercised.** arm-b catches
  the defect earlier (pre-approval), so run 10 never reached an
  approval-then-post-wave-smoke-failure; run 11 had no smoke gate. arm-a remains
  32-tests-green but unproven live. Low priority (it's the post-approval
  backstop). To exercise it live you'd need a deliverable that passes pytest AND
  arm-b's runtime-parity but fails the *post-wave* smoke command for a different
  reason.
- **Player-convergence on TSJ-001** is the standing blocker to an *honest*
  end-to-end FEAT-9DDE (Wave 1 + Wave 2 both via the Player). Needs a stronger
  Player model or a prescriptive producer spec.

---

## 🌳 REPO & RUN STATE (at handoff)

- **Branches kept** (rerun lineage): `feat9dde-rerun-base` (`740e1585`, clean
  pre-merge — Player builds producer from scratch), `feat9dde-run8-base`,
  `feat9dde-run9-base` (`7bb3e2de`, **working** hand-fixed producer — the
  isolate base).
- **Logs:** `.guardkit/autobuild/FEAT-9DDE-run{10,11,12}-stdout.log`.
- **`.guardkit/features/FEAT-9DDE.yaml`** + `tasks/backlog/task-status-json/TASK-TSJ-00{1,2}-*.md`
  are the uncommitted rerun fixtures.

**Full teardown to pristine (run when done with FEAT-9DDE validation):**
```bash
git checkout -- .guardkit/features/FEAT-9DDE.yaml      # → committed 'merged' state
rm -f tasks/backlog/task-status-json/TASK-TSJ-00{1,2}-*.md
git worktree remove .guardkit/worktrees/FEAT-9DDE --force 2>/dev/null; git branch -D autobuild/FEAT-9DDE 2>/dev/null
git branch -D feat9dde-rerun-base feat9dde-run8-base feat9dde-run9-base
git worktree prune
```

---

## 📊 EVBINST02 VALIDATION (run 12)

**TASK-FIX-EVBINST02** (commits `bfe4e0fa` + `d51eda3b`) extends
`_ORCHESTRATOR_MANAGED_PATH_PATTERNS` in `agent_invoker.py` with two anchored
patterns — `^large_tool_results/` (harness tool-result spillover) and
`^\.claude/task-plans/` (orchestrator plan stubs) — consumed by both the
Player-report writer and the Coach claim audit. 61/61 path-filter tests green.

**Run 12** = run-10 replica (`--fresh` from `feat9dde-rerun-base`, smoke_gates
present) with only EVBINST02 changed, to confirm the residual
`claim_audit_unmodified (should_fix)` noise is gone live.

- **Run-10 baseline:** `coach_turn_2.json` carried `claim_audit_unmodified`
  records for `.claude/task-plans/TASK-TSJ-001-implementation-plan.md` and
  `large_tool_results/fc_*`; `coach_turn_5.json` had 9 such records. The
  post-turn ghost-path filter caught **3** paths (none of them the two above).

**RESULT — EVBINST02 VALIDATED (run 12, killed after turn 1).** Verified
rigorously against the absence-of-failure trap (a zero count must be "stripped",
not "audit didn't run"):

| Leg | run 10 | run 12 (EVBINST02) |
|-----|--------|--------------------|
| Ghost-path filter list | **3** paths (`.guardkit/bootstrap_state.json` + 2 task files) | **4** paths — now **includes `.claude/task-plans/TASK-TSJ-001-implementation-plan.md`** |
| Path exists on disk (would otherwise leak) | yes | **yes** (`.claude/task-plans/` present in worktree) |
| Appears in Player report `files_*` | yes (leaked) | **NONE** (stripped at the report writer) |
| `claim_audit_unmodified` records in Coach turn | accumulated (3 at turn 2, 9 at turn 5) | **0** in `coach_turn_1.json` |

- `^\.claude/task-plans/` is **proven live**: existed on disk → now in the
  filtered ghost-path list → absent from the Player report → 0 claim_audit.
- `^large_tool_results/` is validated **by mechanism + unit tests** (same
  committed `_ORCHESTRATOR_MANAGED_PATH_PATTERNS` constant + anchored pattern;
  61/61 `test_orchestrator_induced_path_filter.py` pass incl.
  `TestResidualHarnessNamespaceFilter`). No large-tool spill occurred on turn 1
  to show it live; the filter is demonstrably consulted live (the
  `.claude/task-plans/` leg proves it), so the sibling pattern behaves
  identically. *If you want it live too, run a few more producer turns and
  grep the "Filtered N ghost path(s)" line for a `large_tool_results/fc_*`
  entry.*
- Arm-b re-confirmed a third time in run 12 (turn-1 runtime-parity FAILED with
  a *different* bug — `TypeError: Object of type datetime is not JSON
  serializable` — showing it catches whatever runtime defect the Player ships).

---

## 🔗 KEY REFERENCES

- COACHRUNPARITY01 task + plan: `tasks/completed/TASK-AB-COACHRUNPARITY01/`,
  `docs/state/TASK-AB-COACHRUNPARITY01/implementation_plan.md`.
- DIRECTFG01 gate: `guardkit/orchestrator/autobuild.py` `_direct_mode_evidence_gate`
  (≈6199), `_check_direct_mode_bin_entries` (≈641), wired at `:5747`/`:5959`.
- Resume / wave-skip: `feature_loader.py::get_resume_point`,
  `feature_orchestrator.py:2492` (already-completed skip), `:2514` (dependency-skip).
- Rules in play: `absence-of-failure-is-not-success.md`,
  `evidence-boundary-narrower-than-write-surface.md` (EVBINST01/02),
  `namespace-hygiene.md` (tests-pass/production-fails), and the newly-seeded
  `smoke-gate-is-feedback-not-terminator` rule (commit `0000f862`).
