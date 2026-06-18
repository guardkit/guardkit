# 🚀 Session Handoff — autobuild per-task verification false-green CLOSED + CI green (2026-06-18)

> **How to use:** open a fresh session and say *"Read
> `docs/retro/session-handoff-2026-06-18-pertaskfg01-false-green-closed.md` and continue."*
> Self-contained. Supersedes `session-handoff-2026-06-16-faud-merged-hmig011-flipped.md`.
>
> **You are running ON the GB10** (`promaxgb10-41b1`), llama-swap on `:9000`.

---

## 🎯 THE BIG NEWS

1. **A real autobuild defect was found AND fixed: the per-task verification
   FALSE-GREEN.** A validation smoke (`guardkit autobuild task`, LangGraph /
   gpt-oss-120b / gemma4-coach) **APPROVED a deliverable the pipeline never
   verified** — the same `green ≠ correct` class as FEAT-FAUD/FEAT-POC-006, now
   reproduced live on the per-task path. Root-caused (4 holes) and **fixed +
   live-validated**: the run that used to APPROVE now FEEDBACKs. Tracked in
   **`TASK-AB-PERTASKFG01`** — **all 4 ACs landed, task COMPLETE**
   (`tasks/completed/TASK-AB-PERTASKFG01/`).
2. **CI is fully green again.** It had been silently red for ~59 tests since the
   HMIG-011 cutover (2026-06-12); fixed first thing this session, plus 3 filed
   follow-ups implemented.
3. **Autobuild remains tech-stack-agnostic** — audited + empirically verified:
   Python / .NET / TS-JS / Go / Rust / Flutter all still build.

**State:** guardkit `main` @ `5e160198`, **in sync with origin**, CI green
(Tests py3.11/py3.12 + Seam). Working tree clean.

---

## ✅ WHAT LANDED ON MAIN (this session, pushed)

Two halves. Newest first.

| Commit | What |
|---|---|
| `5e160198` | **TASK-AB-PERTASKFG01 COMPLETE** — task → `tasks/completed/` |
| `982a0209` | **AC-004** — deterministic Phase-4 test execution (venv-pinned `pytest` subprocess; no LLM → can't hang; reuses Coach's `run_independent_tests`; env-revert `GUARDKIT_PHASE4_TEST_EXECUTION=sdk`). +14 tests |
| `93c8d633` | fix CI dead-task-id lint (a comment referenced the unfiled throwaway `TASK-SMOKE-REDACT01`) |
| `b793b2d2` | **AC-003** — env bootstrap detects non-standard `requirements*.txt` additively (lpa's `requirements.poc.txt`). +4 tests |
| `3b3ba070` | **AC-001/002** — close the false-green (3 deterministic gates, see below). +10 tests |
| `11501cd5`,`e7dad1be` | file + enrich `TASK-AB-PERTASKFG01` with investigated root causes |
| `21d5ee2c` | TASK-FIX-DIGESTTOK01 — deterministic digest token-budget test |
| `38195dbd` | TASK-FIX-WIREGATECI01 — gate `test_wiring_gate.py` in `seam-tests.yml` |
| `51d1df40` | TASK-FIX-SDKPINCLEAN01 — drop redundant per-test sdk pin |
| `36d72623` | file the 3 CI follow-up tasks |
| `4831563a` | flaky `test_concurrent_generation` made deterministic |
| `4d478818` | **green the Tests suite after the HMIG-011 cutover (59 reds)** |

---

## 🔬 THE FALSE-GREEN: root cause + the 4 fixes (all model-independent)

**Reproduction (TASK-SMOKE-REDACT01, a throwaway smoke — now deleted from lpa):**
Coach APPROVED on turn 1; the code was correct *by luck*; the pipeline never
verified it. Chain: (1) the LLM `test-orchestrator` specialist **hung** (gpt-oss
emitted no tool call → watchdog at 162s → `tests_run=0`); (2) the Player
`quality_gates` were **fabricated from narrative regex** (`all_passed:true,
coverage:100, tests_passed:0`); (3) the Coach's own independent test **couldn't
run** (worktree venv missing deps) and it **rationalised the env error and
approved** on the Player's claim.

**The defect was STRUCTURAL, not the Coach model.** The LLM Coach merely narrated
a deterministically-fabricated false-green — a smarter/fine-tuned Coach would
approve the same input. (Investigation also **corroborated** that `gemma4-31b` is
*slower, no better* than the `gemma4-coach` MoE → **keep the MoE; fine-tuned
coach `TASK-DATA-COACHHARVEST` stays deprioritized** for false-greens.)

| # | Fix (file:loc) | What |
|---|---|---|
| **#2** | `agent_invoker._inject_specialist_records_into_task_work_results` | reconcile `quality_gates` vs the authoritative `phase_4` specialist record — `status=failed` ⇒ override `all_passed→False` so the false-green never reaches the Coach. (Only the false-green direction; passed/skipped untouched.) |
| **#3b** | `coach_validator._check_zero_test_anomaly` | drop the `coverage is None` clause so a **fabricated** coverage number can't mask `all_passed=True` + 0 tests |
| **#4** | `coach_validator.run_independent_tests` | widen the `signal_absent` classifier — a **conftest/collection import failure** (exit 2/4 + "ImportError while loading conftest", 0 tests) is ABSENT, not "ran-and-failed" → re-arms `_reconcile_absent_independent_test_signal` so the LLM Coach can't rationalise it away |
| **#4 (AC-004)** | `specialist_invocations._run_deterministic_phase_4` | Phase-4 EXECUTION is now a deterministic subprocess (root cause: "running tests must not be able to hang") |

**Live validation:** re-ran the smoke after #2/#3b/#4 → turn-1 **APPROVE became
FEEDBACK** (the `Reconciling quality_gates … overriding to NOT passed` warning
fires), with a substantive Coach feedback message. ✅

**Discarded as too aggressive:** a `verify_quality_gates` `tests_run>0`
precondition (#3a) — it false-RED'd when independent tests genuinely passed but
the Player's self-reported counts were 0. Reverted; #2+#3b+#4 close the repro.

---

## 🧱 STACK-AGNOSTIC AUDIT (the answer to "did we tie autobuild to Python?")

**No.** Verified by reading + empirically:
- **Bootstrap (AC-003)** detects all stacks (`dotnet restore`, `npm/pnpm/yarn`,
  `go mod download`, `cargo fetch`, `flutter pub get`); the `requirements*.txt`
  change is python-branch-only.
- **Phase-4 (AC-004)** deterministic pytest is **gated** on the Coach's
  `_detect_test_command` finding Python tests (`tests/**/test_*.py`). Non-Python
  → returns `None` → **falls back to the existing stack-agnostic LLM
  `test-orchestrator` specialist** (runs `dotnet test`/`npm test`/`go test` via
  Bash). No hard Python assumption crashes a non-Python build.
- **Honest nuance:** the *can't-hang* benefit is **Python-first** today;
  non-Python keeps the LLM specialist (stack-agnostic, but retains the hang risk
  on a tool-call-shy model like gpt-oss). Rule-consistent
  (`.claude/rules/stack-plugin-architecture.md` — test *execution* is the
  legitimate per-stack case). **Optional follow-up:** teach the deterministic
  runner to detect `dotnet test`/`npm test`/`go test` so those stacks also get
  can't-hang execution. Not filed yet.

---

## 🖥️ BOX STATE → RESTORE WHEN READY

For the smoke runs, the `llama-swap-keepalive.timer` was **STOPPED** (OOM safety
for the gpt-oss exclusive run) and is **still inactive** — so the fleet
(qwen-graphiti / qwen36-workhorse / nomic-embed) is **paused** (Jarvis / graphiti
/ LPA paused). `llama-swap` (`:9000`, on-demand gpt-oss/gemma4-coach) is active.
To restore the fleet (**YOUR sudo — I can't run it**):

```bash
sudo systemctl start llama-swap-keepalive.timer
```

---

## 📋 OPEN ITEMS / NEXT STEPS

1. **HMIG-011 cutover close-out (operator/calendar, DEADLINE 2026-06-22)** —
   from the prior handoff, untouched this session: AC-005 announce → AC-006
   observation window → AC-008 mark complete + file Phase-3 dep removal
   (`TASK-HMIG-012`, remove `ClaudeSDKHarness` + `claude-agent-sdk`). Note: SDK
   path is now a *free* choice again (Anthropic cancelled the key cutoff), so
   Phase-3 removal is optional. Flip point: `selector.py` `DEFAULT_HARNESS`.
2. **(Optional) non-Python deterministic test execution** — extend AC-004's
   runner to `dotnet test`/`npm test`/`go test` so those stacks get can't-hang
   execution too. Clean follow-up; file if wanted.
3. **lpa-platform-poc** has an own-side gap: `requirements.poc.txt` omits
   `pytest-asyncio` (its `conftest.py` imports it). Not GuardKit's bug; a clean
   e2e autobuild on lpa needs lpa to declare it. The broken-env case is SAFE
   meanwhile (#4 → absent-signal → feedback). lpa `main` local @ `a31a783` (smoke
   task removed; **not pushed** — separate repo).
4. **The 3 CI follow-up tasks are DONE** (`ci-tests-yml-followups/`): wiring-gate
   gated in seam-tests, digest cross-counter, redundant pin removed. All in
   `tasks/completed/`.

---

## 🔗 KEY REFERENCES

- **Completed task (full root-cause + fixes + ACs):**
  `tasks/completed/TASK-AB-PERTASKFG01/TASK-AB-PERTASKFG01-per-task-verification-false-green.md`
- **Rule family (the lens):** `.claude/rules/absence-of-failure-is-not-success.md`,
  `per-task-green-is-not-feature-green.md`, `stack-plugin-architecture.md`.
- **Memory:** `[[gptoss-player-autobuild-traits]]` (updated: per-task false-green
  + structural-not-model + gemma4 corroboration), `[[ci-tests-yml-no-guardkitfactory]]`
  (CI substrate contract).
- **Retro:** `docs/retro/autobuild-retro-xref-2026-06-17.md` (updated 2026-06-18
  with the live per-task false-green find+fix).
- **Prior handoff (superseded):** `session-handoff-2026-06-16-faud-merged-hmig011-flipped.md`.
