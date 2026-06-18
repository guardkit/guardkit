# Cross-Reference: OLD-guardkit autobuild issues — fixed vs still-open in CURRENT guardkit

> **Generated:** 2026-06-17 via the `autobuild-retro-xref` multi-agent workflow.
> **Inputs:** 11 autobuild retros from two repos built with **cloud (Claude Agent SDK)** autobuild on an *older* guardkit (MacBook, 2026-06-13/14):
> - `lpa-platform-poc/docs/poc/retros/` — FEAT-5A64/POC-003, POC-004, POC-005, POC-006
> - `fleet-memory/docs/retros/` — FEAT-MEM-01 … FEAT-MEM-07
> **Method:** extract every documented issue, classify each against **current** guardkit
> source (verified in-tree, not from memory): already-fixed / still-open / usage-config.
> **Follow-ups filed:** the five still-open items are in `tasks/backlog/autobuild-retro-fixes/`.

---

## 1. Headline

The 11 retros record **~16 distinct issues**. After auditing current guardkit (HEAD on
`main`, post-COACHRUNPARITY01/EVBINST02/CKPTTESTRED01/HMIG-011), **9 are already fixed**
(a pull + re-run resolves them), **5 remain open** (need new fixes), and **2 are
usage/config, not guardkit bugs**.

The single most important takeaway: the dominant failure mode in every retro —
`unrecoverable_stall` on a *false* `tests: fail` signal — is now **substantially
defanged** in current guardkit (checkpoint tri-state, `claim_audit_unmodified` demoted
to `should_fix`, specialist 600s cap + watchdog, smoke-gate feed-back), so most of the
operator pain those retros document would not recur. Since the fixes live in the
**shared orchestrator** (above the harness), the SDK/cloud path gets them too. The
highest-value remaining gap is the **mocked-seam "green-but-broken" class**
(FEAT-POC-006) — the same `green ≠ correct` lesson FEAT-FAUD taught locally — and the
**plan-audit markdown-link-label false-positive** (FEAT-MEM-07).

## 2. Already fixed by current guardkit (re-run resolves)

| # | Issue (retro) | Repo / feature (recurrence) | Fix in current guardkit | Citation |
|---|---|---|---|---|
| A1 | **`unrecoverable_stall` on false `tests: fail`** when an UNKNOWN/absent oracle signal was counted as a failure | lpa POC-004, POC-005, FEAT-5A64; **recurs** fleet MEM-01, MEM-07 | Checkpoint signal is now **tri-state** (`Optional[bool]`); only an explicit `tests_passed is False` counts toward the pollution tally; `None` (no oracle ran) breaks the run | `worktree_checkpoints.py:698-747` (`should_rollback`, CKPTTESTRED01); `.claude/rules/absence-of-failure-is-not-success.md` |
| A2 | **Pollution guard early-exits despite an earlier passing checkpoint** | fleet MEM-07 Error 3 (RIP-007); lpa POC-005 | `should_rollback` only scans the **current-run** window (`from_prior_run` excluded); a passing/unknown checkpoint in the last-N window breaks the consecutive-failure run | `worktree_checkpoints.py:705-745` |
| A3 | **Honesty gate aborts evidence gathering** on files committed in earlier turns / orchestrator-managed paths (`coverage.json`, `.claude/task-plans/*`, pytest node-IDs) | fleet MEM-01 Error 8, MEM-07 Error 3; lpa POC-004 §3.3 | `claim_audit_unmodified` is now **`severity="should_fix"`** (non-turn-rejecting); test-file run-claims with no staged change suppressed (SPECVIOL01) | `coach_verification.py:693-718` |
| A4 | **plan-audit reads a grep command / prose path as a missing file** | fleet MEM-01 Error 3 (MEM-006); lpa POC-004 trigger | Scanner restricted to the **`## Acceptance Criteria` section** (PA-002), **skips bare basenames** (AC-001), skips glob tokens | `agent_invoker.py:8484-8606` (`_scan_ac_for_missing_paths`) |
| A5 | **60-second specialist timeout** nulls evidence → false `tests: fail`; `test-orchestrator`/`code-reviewer` hang | lpa POC-005 §4.2; fleet MEM-03 Error 4 | SDK timeout capped at **600s** (SPECHANG) + per-specialist **no-activity watchdog** (SPECHANG2) + **phase-budget bound** (SPECLAT01) | `specialist_invocations.py:75-119, 949-955`; commit `dacbed55` |
| A6 | **Smoke-gate failure terminates the feature with no Player feedback** (deadlock) | fleet MEM-01 Error 5; related lpa POC-006 | Post-wave smoke failure **fed back to the Player** as turn-1 `seed_feedback`, bounded by `GUARDKIT_SMOKE_GATE_MAX_RETRIES`; wave completed only when smoke-gated | `feature_orchestrator.py:2290,2351,2472,698`; `.claude/rules/smoke-gate-is-feedback-not-terminator.md` |
| A7 | **`guardkit autobuild complete` is a no-op** (Phase 2/3 placeholders) | fleet MEM-02 #3, MEM-03 #5, MEM-04 #4, MEM-05 #4 (recurs every fleet feature) | `complete` now drives a real `FeatureCompleteOrchestrator` (marks tasks complete, archives, cleans up) | `cli/autobuild.py:1109-1161` |
| A8 | **Spurious turn-1 pollution stall on `--resume`** (prior-run checkpoints counted as current failures) | fleet MEM-01/05/07 | `from_prior_run` checkpoints explicitly excluded from the pollution tally (F4A3) | `worktree_checkpoints.py:705-708,729` |
| A9 | **Graphiti context-load hang (~31 min / `Search request failed: timed out`)** dominating wall-clock | fleet MEM-02 #1 | Context-load search calls wrapped in **`asyncio.wait_for`** with a hard <2s budget + fallback-to-empty | `knowledge/graphiti_client.py:639,654,887,1209` |

## 3. Still open — new guardkit fixes needed (prioritised)

> Filed as task files in `tasks/backlog/autobuild-retro-fixes/`.

1. **Mocked-seam "green-but-broken" feature (highest value — the only *correctness* gap).**
   A whole feature passed every per-task Coach + 345 tests yet was non-functional, because
   router/"integration" tests `AsyncMock(spec=VoiceService)` the very seam they claim to
   integrate, and `main.py` constructs a service with the wrong/missing args. Current
   guardkit has `mocked_seam`/`UNWIRED_PATH` wiring evidence (`coach_evidence.py:204-239`)
   and a `direct_mode_wiring_gap` *must_fix* (`autobuild.py:6349-6369`), but that gate only
   fires on a **registered bin-entry in direct mode** — it does not assert "no in-loop
   integration test mocks the primary service seam" nor "`main.py` constructs each service
   with all required `__init__` args" for a normal feature wave. *Fix:* a post-wave wiring
   lint that (a) flags `AsyncMock(spec=Service)` of a primary in-repo service in an
   integration-tier test, and (b) diffs router `<svc>.<method>(` calls against the service
   surface + asserts composition-root constructor arity. **→ TASK-AB-WIREGATE01.**
2. **plan-audit extracts the markdown-link *label* (not the *href*) as a path.**
   `[relay/service.py](src/fleet_memory/relay/service.py)` → the scanner's
   `[\w./\-]+\.\w{1,5}` regex matches the label `relay/service.py` (has a `/`, so the
   basename-skip does not save it) → flagged missing → HIGH violation → stall. *Verified
   live: the regex returns both tokens.* `agent_invoker.py:8567`. *Fix:* resolve markdown
   links to their **href** before tokenizing, and resolve multi-segment tokens as path
   **suffixes** before declaring missing. **→ TASK-GK-PA-003.**
3. **Python 3.10 bootstrap trap.** `uv venv` is still invoked with **no `--python` flag**
   (`environment_bootstrap.py:1675-1681` + `_ensure_worktree_venv`), so on a host with a
   uv-managed cpython-3.10 it builds the worktree venv on 3.10 and hard-fails
   `requires-python >=3.12`. `get_requires_python()` exists (`:313,1328`) but is not
   threaded into venv interpreter selection. *Fix:* pass `--python` derived from the
   manifest's `requires-python`. **→ TASK-AB-BOOTPY01.**
4. **Stale Coach venv when a dependency is added *and consumed within the same wave*.**
   The venv is bootstrapped once per feature and re-bootstrapped *between* waves
   (`feature_orchestrator.py:2216`), so a dep added+used inside one wave (`tiktoken`,
   fleet MEM-05) `ModuleNotFoundError`s the Coach's pytest → rejects every AC → stall.
   *Fix:* detect a `pyproject` change during a turn and reinstall into the worktree venv
   before the Coach's independent run. **→ TASK-AB-COACHVENV01.**
5. **BDD runner surfaces a *synthetic failure* when no `.feature` file matches.** A missing
   gate input should be **neutral/not-applicable**, not `failed=1` (`bdd_runner.py:627,706`).
   Non-blocking alone but stacks into a stall (FEAT-MEM-07 Error 1). The conftest bridge
   template now ships, so a freshly-`init`'d project gets it, but a pre-existing repo
   without it still exit-4s. *Fix:* classify "no matching `.feature`" as `not_applicable`,
   and have `init`/bootstrap auto-drop `features/conftest.py`. **→ TASK-AB-BDDNEUTRAL01.**

## 4. Usage / config (not guardkit bugs)

- **`--fresh` used to "retry a task" destroyed approved work** (fleet MEM-07 Error 4):
  `--fresh` hard-resets the worktree to base, discarding worktree-branch commits.
  *Prevention:* use `--resume` to retry; reserve `--fresh` for a genuine from-scratch
  rebuild with fixes already on base.
- **Coach SDK test runner narrates "I'll run that test command…" and never runs pytest**
  (fleet MEM-01 Error 2; FEAT-5A64): local-model substrate behaviour of
  `coach_test_execution="sdk"` (still the default — `coach_validator.py:1308`).
  *Prevention:* set `.guardkit/config.yaml` → `autobuild.coach.test_execution: subprocess`.
  *(Borderline: making `subprocess` the default, or auto-falling-back when the SDK runner
  emits no Bash call, would be a legitimate guardkit improvement — TASK-AB-COACHSUBPROC01
  if pursued.)*
- **Launch hygiene:** unset env vars → test skips → "absent oracle" reject (MEM-01 Error 6);
  launching from inside the worktree → "Feature file not found" (POC-004, FEAT-5A64);
  `tee` masks the orchestrator exit code (MEM-01 Error 7). *Prevention:* export required
  env vars, launch from the main repo root, use `>> log 2>&1; echo EXIT_CODE=$?`.
- **`guardkit worktree cleanup` is an unknown command** (every fleet retro): no top-level
  `worktree` group is registered, yet `display.py:497` still prints it. Use raw
  `git worktree remove --force` + `git branch -d`. (Tiny fix candidate.)

## 5. Cross-cutting patterns

- **The recurring defect-class is exactly the existing meta-frame** — *"a binary verdict
  from a low-fidelity oracle that cannot distinguish 'no signal' from 'positive/negative
  signal'"* (`.claude/rules/absence-of-failure-is-not-success.md` + its five siblings).
  Every false `unrecoverable_stall` here (POC-004/005, FEAT-5A64, MEM-01/05/07) is an
  absence-of-failure / false-red instance. Current guardkit's A1-A5/A8 fixes are precisely
  the "pair the verdict with a positive-evidence precondition" remediation that rule
  prescribes — **no new rule needed**; these retros are strong **field validation** that
  the fixes work, on the SDK substrate, on real features.
- **The mocked-seam / wiring class (still-open #1)** extends
  `evidence-boundary-narrower-than-write-surface.md` and `stack-plugin-architecture.md`:
  per-task Coach isolation is an evidence aperture narrower than the *assembled-feature*
  write surface. Warrants either widening the wiring gate or a short companion rule —
  *"per-task-green is not feature-green; a mocked primary seam is absent integration
  evidence"* — under the same meta-frame. (The wiring lint must be **stack-agnostic** per
  `stack-plugin-architecture.md` — tree-sitter, not Python-`ast`.)
- **The plan-audit path-scanner false-positives** (A4 fixed-portion + still-open #2) are the
  inverse-shape sibling `path-string-mismatch-is-not-dishonesty.md`: a path-string miss
  treated as a hard failure. The markdown-link-label case is an un-patched corner of that
  same rule's surface — fits the existing meta-frame, needs only the href/path-suffix fix.

**Net:** pulling current guardkit and re-running these features would eliminate the
operator-time cost of A1-A9 (the bulk of every retro). The five still-open items are real
follow-ups, with #1 (mocked-seam wiring gate) being the only one that changes a
*correctness* outcome rather than operator friction.

---

## 8. Update 2026-06-18 — the `green ≠ correct` class found LIVE on the per-task path, and FIXED

A validation re-run (the recommendation to re-run a feature on current guardkit) surfaced
a **new live instance of this retro's dominant correctness risk** — not the
*feature-assembly* mocked-seam (still-open #1, FEAT-POC-006) but its **per-task sibling**:
`guardkit autobuild task` on the local **LangGraph / gpt-oss-120b / gemma4-coach** stack
**APPROVED a deliverable the pipeline never verified**. Filed + fixed as
**`TASK-AB-PERTASKFG01`** (now `tasks/completed/`; commits `3b3ba070`, `b793b2d2`,
`982a0209`; CI green `5e160198`).

**Chain (all four holes had to fail together):** the LLM `test-orchestrator` specialist
hung (gpt-oss emitted no tool call → watchdog 162s → `tests_run=0`) → the Player
`quality_gates` were **fabricated from narrative regex** (`all_passed:true, coverage:100,
tests_passed:0`) → the Coach's own independent test couldn't run (broken worktree venv)
and it **rationalised the env error and approved**. The code was correct *by luck*.

**Confirmed structural, not the Coach model** (settles this retro's open question on coach
quality): the LLM Coach merely narrated a deterministically-fabricated false-green; the
investigation also **corroborated `gemma4-31b` is slower / no better** than the MoE.
→ **Keep the `gemma4-coach` MoE; `TASK-DATA-COACHHARVEST` (fine-tuned coach) stays
deprioritized** as a false-green lever. The four fixes are all deterministic /
model-independent:

1. **#2** reconcile `quality_gates` vs the authoritative `phase_4` specialist record
   (`agent_invoker`) — the false-green never reaches the Coach.
2. **#3b** drop the `coverage is None` escape in the zero-test anomaly (`coach_validator`).
3. **#4** widen the `signal_absent` classifier for conftest/collection import failures
   (`coach_validator`) — re-arms the deterministic `_reconcile_absent_independent_test_signal`
   override the LLM can't bypass.
4. **AC-004** Phase-4 EXECUTION is now a deterministic venv-pinned `pytest` subprocess
   (`specialist_invocations`) reusing the Coach's runner — *"running tests must not be
   able to hang"* (root cause); env-revert `GUARDKIT_PHASE4_TEST_EXECUTION=sdk`.

**Live-validated:** the smoke that APPROVED on turn 1 now **FEEDBACKs** (the reconcile
warning fires) → not approved. +28 regression tests.

**Stack-agnostic preserved (verified empirically):** bootstrap still detects dotnet/node/
go/rust/flutter; the AC-004 deterministic runner is gated to projects with Python tests
and **falls back to the stack-agnostic LLM specialist** for non-Python — no Python lock.
The *can't-hang* benefit is Python-first today; extending the deterministic runner to
`dotnet test`/`npm test`/`go test` is a clean optional follow-up — the same
`stack-plugin-architecture.md` "execution is the legitimate per-stack case" framing this
retro already noted for the wiring lint.

> **Update 2026-06-18 — that follow-up landed: `TASK-AB-NPDET01`** (`tasks/completed/TASK-AB-NPDET01/`,
> commits `4dbbf925` + `3ab2504f`). New pure-stdlib `quality_gates/stack_test_execution.py`
> gives `dotnet`/`node`/`go` single-task waves the same can't-hang deterministic execution.
> Design adjudicated to a **declarative DATA registry, NOT a guardkitfactory ABC+loader
> plugin** — the letter-vs-spirit ruling on `stack-plugin-architecture.md`: that rule's
> plugin mandate is grounded in per-stack *report-format* parsing (the `bdd/` JUnit/.trx/
> cucumber-json case); this oracle's verdict is uniform `returncode==0`, so "a new stack =
> a DATA row." Absence-of-failure-safe (missing toolchain / zero-test → absent, never a
> pass); parallel-wave-guarded (whole-suite commands defer to the LLM specialist when
> `wave_size>1`). An **adversarial verification panel caught two real DATA-only holes**
> before merge: a node exit-0 zero-test false-green (`--passWithNoTests` / `echo`
> placeholder → fixed with a positive ran-marker precondition) and a `': not found'`
> false-red (incidental in passing output → dropped; toolchain-missing caught by rc 127).
> 419 tests green. **Residual:** non-Python *parallel* waves still use the LLM specialist
> (retain hang risk); per-task non-Python test filtering is a separate task.

**Relation to still-open #1:** distinct but same meta-frame. #1 is the *feature-assembly*
aperture (post-wave wiring, FEAT-POC-006); this is the *per-task* aperture (the Coach
can't see what it never ran). Both are `absence-of-failure-is-not-success` /
`per-task-green-is-not-feature-green` instances. This find+fix is the **field validation**
§1 anticipated — now with a concrete live reproduction and a landed, validated fix.

> **Handoff:** `docs/retro/session-handoff-2026-06-18-pertaskfg01-false-green-closed.md`.

## 9. FEAT-HMIG closed out — 2026-06-18

The LangGraph harness migration (**FEAT-HMIG**) is **fully closed** as of 2026-06-18:
the cutover shipped and is validated, the substrate is settled, and **no task is
genuinely open** — every one is completed, deferred-with-rationale, or optional. Two
items that first looked like an open tail were reality-checked against the code on
disk and found **already-done**.

### Disposition — all FEAT-HMIG tasks

| Task | Disposition | Note |
|---|---|---|
| HMIG-011 cutover ceremony | ✅ completed | Path-A / GO; LangGraph default shipped 2026-06-16 |
| HMIG-009 canary validation | ✅ completed — superseded | by 009A; canary question answered YES (83.3%) |
| HMIG-010 full-feature validation | ✅ completed — goal-met | GO verdict reached, executed by the cutover, proven by FEAT-9DDE + FEAT-FAUD green |
| HMIG-013 coach swap | ✅ completed — superseded | by COACHMOE01 (gemma4:26b in production) |
| REV-HM09 pilot review | ✅ completed — delivered | produced 009A/009B |
| FRESHRESET01 | ✅ completed — superseded | already fixed by FRESHCLEAN01 (`3b39764e`) — see meta-lesson |
| COACHBUDG01 | ✅ completed | stale snapshot; all cross-repo ACs landed — see meta-lesson |
| HMIG-012 2×-Spark optimization | ⏸️ deferred | hardware-gated (2nd Spark + ConnectX-7) |
| HMIG-014 Phase-3 SDK removal | 📋 optional | key cutoff cancelled → SDK fallback is free |
| COACHGRAMMAR (F24, Path 1A) | ⏸️ deferred | route-level GBNF — dead end |
| COACHSCHEMA (F24, Path 1B) | ⏸️ deferred | prompt-tightening — falsified |

### The F24 coach-substrate-reliability tail (deferred)

Settled resolution: **gemma4:26b (the 26B MoE) + the COACHSF01 synthetic-feedback
safety net**, which runs green in practice (FEAT-9DDE, FEAT-FAUD). Both native-reliability
fixes were empirically falsified, so COACHGRAMMAR + COACHSCHEMA are deferred (priority → low):

- **Route-level llama.cpp GBNF** (Path 1A) — **dead end**: llama.cpp bypasses
  `--grammar-file` whenever a request carries tools, and the DeepAgents Coach binds
  built-in tools on every call, so the grammar never reaches the Coach (run 13).
- **Prompt-tightening** (Path 1B) — **falsified by run 14**: more time + a decisive
  prompt made gemma4:26b *worse* (49,720 chars of reasoning, no verdict).
- **Gemma 4 31B dense escalation** (the run-14 recommendation) — **evaluated and
  rejected 2026-06-18**: "slower, no better than the 26B MoE."

Genuine residual: under `--reasoning auto`, gemma4:26b doesn't *natively* emit the
fenced-JSON verdict 100% of the time; COACHSF01 covers the gap (much of the runs-8→13
pain was operator-fixable substrate config — F20 `n_ctx`, grace-period constants —
since resolved). **Live forward option** if coach reliability ever becomes a felt pain:
a **toolless grammar-constrained verdict-synthesis call**
(`docs/research/dgx-spark/grammars/README.md`), or the deprioritized fine-tuned/distilled
coach (TASK-DATA-COACHHARVEST) — NOT route-level GBNF and NOT 31B. Recorded as a Graphiti
`guardkit__project_decisions` node.

### Meta-lesson — recurred twice in this closeout

Both **FRESHRESET01** and **COACHBUDG01** were parked in backlog as "open"/"BLOCKED" but
were **already done** once the code was checked:

- **FRESHRESET01** — superseded by **FRESHCLEAN01** (`3b39764e`, "--fresh force-cleans
  terminal features, not just incomplete ones"). The `is_incomplete` guard around
  `_clean_state` is gone; `feature_orchestrator.py` calls `_clean_state` unconditionally
  under `if self.fresh:`, and `_clean_state → reset_state` resets the per-task fields it
  asked for.
- **COACHBUDG01** — a stale 2026-06-06 snapshot that marked every cross-repo AC "BLOCKED
  ON guardkitfactory" (not on the box then). All have since landed + tested: per-role
  `max_tokens` (Coach 16384, `langgraph_harness.py:520-521`); `reasoning_content →
  reasoning_text` in `_aiter_events` (`:606-616`, `extract_last_ai_reasoning`);
  `MODEL_CONTEXT_WINDOWS` (`model_config.py`); tests in
  `tests/harness/test_langgraph_harness*.py` + `test_model_config.py`.

A backlog task's "BLOCKED"/"open" status is a claim about a *past moment*; **the code on
disk is the source of truth.** Reality-check the premise before running an implementation
workflow — it saved two no-op runs here.
