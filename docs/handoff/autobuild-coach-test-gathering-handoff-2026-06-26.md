# Handoff — AutoBuild Coach test-result-gathering flakiness (2026-06-26)

> **Purpose.** Pick this up in a fresh conversation and work the tasks below. The
> goal is to stop AutoBuild failing every run on a *different* verification-layer
> issue while the actual deliverables are correct. This document is self-contained:
> it has the diagnosis, the git state, the open tasks (new + pre-existing), the
> mental model you need, and a recommended order of work.
>
> **One-line summary.** AutoBuild's *deliverables* in FEAT-HARV are good; the
> *verification machinery* (the Coach's independent test gathering) is flaky and
> has a cross-wave runtime-parity bug. The net validated win this session is one
> bootstrap fix; everything else was reverted and refiled as proper tasks.

---

## 1. Where things stand (git)

Branch `main`, all commits **local, not pushed**. Newest first:

| Commit | Keep? | What |
|---|---|---|
| `0cbbe6fa` | ✅ revert | Reverts Defect B (runtime-parity after_wave) — refiled as a task |
| `c649e069` | ✅ revert | Reverts Defect A (SDK narration→absent) — it caused a regression |
| `437ebd8a` | ⛔ reverted | Defect A (do not reinstate as-is) |
| `5c95dd85` | ⛔ reverted | Defect B (sound, but refiled as TASK-FIX-PARITYWAVE01) |
| `a9f6646e` | ✅ keep | Rule doc: `uv-sources-must-survive-every-install-path.md` |
| `ff4b63ce` | ✅ **keep — the one validated win** | Bootstrap honours `[tool.uv.sources]` in per-dep extras |

**Net effect on production code = only `ff4b63ce`** (the bootstrap fix). Both
Coach-side experiments were reverted. The working tree also has the new/edited
**task files** from this handoff (commit them alongside this doc).

---

## 2. The one fix that landed and is validated: bootstrap uv-sources (`ff4b63ce`)

**Symptom:** FEAT-HARV wave-1 stalled; `nats_core` never installed in the worktree
venv. **Root cause:** the env_bootstrap *per-dependency* install path
(`_python_dep_commands`, used because `guardkit-py`'s dist name ≠ its `guardkit/`
dir) ran plain `pip install nats-core>=0.4,<1`, ignoring `[tool.uv.sources]` (a
uv-only mechanism). A **different public PyPI `nats-core`** (0.0.0/0.1.0/0.2.0)
shadowed the private sibling and failed the spec. **Fix:** redirect any
`[tool.uv.sources]` path-pinned dep to `pip install -e <sibling>`, fail-open to
plain pip. Validated end-to-end: the editable install runs and `import nats_core`
works standalone in a clean py3.11 venv. Rule: `.claude/rules/uv-sources-must-survive-every-install-path.md`.
**This one is done. Leave it.**

---

## 3. The mental model you need (read before touching Coach code)

AutoBuild runs each task through a Player→Coach loop. The Coach verifies via
**two** independent test executions:

1. **Deterministic subprocess pytest** — `coach_test_execution=subprocess`
   path / the Phase-4 deterministic run. **Reliable.** Runs real pytest, captures
   real output. (For FEAT-HARV-003 it reported `status=passed tests_run=8601
   tests_failed=0` every turn.)
2. **SDK independent test** — `_run_tests_via_sdk`, the **default**
   `coach_test_execution=sdk`. **Flaky.** It asks a Coach *agent* (LLM) to run
   pytest via Bash, but **the SDK harness does not yield a `ToolResultEvent`**, so
   the Bash stdout is never captured — only the agent's *assistant text*. When the
   agent just narrates ("I'll run the test command and show you the full output.")
   the captured `output_text` has **no pytest markers**.

**The conditional-approval mechanism** (THE thing to understand —
`coach_validator.py:2223`, TASK-ABFIX-005 / TASK-FIX-1D70): when the SDK
independent test **fails with a classified `failure_class`** (`infrastructure` /
`collection_error` / `parallel_contention` / `code`-in-parallel-wave) **AND all
Player quality gates pass**, the Coach grants **conditional approval**. This is
why flaky SDK failures normally don't block — and exactly why FEAT-HARV's wave-1
002/004 *approved* despite "SDK independent tests failed".

**The asymmetry that bites (the key insight):**
- classified failure + gates pass → **conditional approve** (tolerated)
- **absent** signal (`signal_absent=True`) → **Guard #6 hard-block** ("cannot
  approve when independent test produces no signal")

So an *absent* signal is treated as **stricter than a failure** — backwards. Any
change that routes the flaky no-marker SDK capture into the *absent* path will
**regress** tasks that previously passed. (That is precisely the Defect A
mistake; see §5.)

---

## 4. The open work — tasks to implement (this is what you asked for)

### 4a. NEW task filed this session

| Task | File | Status | Summary |
|---|---|---|---|
| **TASK-FIX-PARITYWAVE01** | `tasks/backlog/TASK-FIX-PARITYWAVE01-runtime-parity-after-wave-scope.md` | backlog | The per-task runtime-parity check runs a *later* wave's smoke command on an *earlier* wave. FEAT-HARV's wave-2 walker was run against the wave-3 `memory harvest` CLI (`No such command 'memory'`, exit 2) → blocked to max_turns. **The only genuinely-new defect from this session.** Fix sketch + tests included in the task (was validated, then reverted to go through process). |

### 4b. EXISTING tasks extended this session (the SDK test-gathering reliability)

| Task | File | Status | Summary |
|---|---|---|---|
| **TASK-REV-COSE** | `tasks/backlog/TASK-REV-COSE-diagnose-coach-sdk-test-execution-opaque-stderr.md` | backlog | Diagnose the SDK test-execution path. **Extended** with the narration-capture root cause (no `ToolResultEvent` → captures agent text not pytest stdout) and the two real fixes: **(a)** surface Bash stdout as a ToolResultEvent, or **(b)** default `coach_test_execution=subprocess`. Owns the *capture* side. |
| **TASK-FIX-DF44** | `tasks/backlog/coach-test-discovery-fix/TASK-FIX-DF44-collection-error-classification.md` | backlog | Add `collection_error` classification (FEAT-CTD's last unimplemented task). **Extended** to also classify the no-marker/narration SDK capture as conditional-approvable (not an absent hard-block), and to resolve/justify the absent-vs-classified asymmetry. Owns the *classification + approval* side. |

### 4c. OTHER pre-existing unimplemented tasks in this area (you asked to include these)

These were found in `tasks/backlog/` and are directly adjacent — review whether
any are now redundant with COSE/DF44 or should be done together:

- **FEAT-CTD** (`tasks/backlog/coach-test-discovery-fix/`) — 4/5 done; only
  **TASK-FIX-DF44** remains (above). (`7F48`, `1D70`, `3A01`, `7D71` are completed.)
- **FEAT-CRV** (`tasks/backlog/coach-runtime-verification/`) — 5/9 done; **still
  backlog:**
  - `TASK-CRV-3B1A-sdk-sessions-player-resume.md`
  - `TASK-CRV-7DBC-mcp-coach-integration.md`
  - `TASK-CRV-9914-extended-coach-validator.md`
  - `TASK-CRV-B275-rate-limit-invoke-with-role.md`
- Adjacent backlog folders worth a glance (may overlap): `coach-test-discovery-fix/`,
  `coach-runtime-verification/`, `autobuild-test-detection-fixes/`,
  `coach-runtime-verification` README (architecture), and the review
  `TASK-REV-A00F-design-simplified-quality-gate-profiles.md`.

---

## 5. What was tried and reverted (do NOT repeat)

- **Defect A (`437ebd8a`, reverted `c649e069`): reclassify the SDK narration as
  `signal_absent=True`.** _(Note: those two commit messages accidentally reused the
  ID `TASK-FIX-COACHNARR01`, which is an **unrelated completed task** — the "coach
  narrative reconciler", `tasks/completed/TASK-FIX-COACHNARR01/`. The SDK-narration
  work is owned by COSE + DF44, not that task. Ignore the ID in those commit
  subjects.)_ Looked right (narration genuinely isn't a test result),
  but it moved the flaky capture out of the *tolerated/conditional-approve* path
  and into the *absent hard-block* (Guard #6). Result: FEAT-HARV wave-1 002/004 —
  green in the prior run — both hit `max_turns_exceeded`. **Lesson:** the fix is
  NOT "make narration absent"; it's to either capture real output (COSE) or make
  the no-marker case conditional-approvable (DF44). The absent path is stricter
  than a failure, which is the bug to fix, not a place to route into.
- **Defect B (`5c95dd85`, reverted `0cbbe6fa`): inline runtime-parity wave
  gating.** The fix is correct but was authored ad hoc and never validated
  end-to-end. Refiled as **TASK-FIX-PARITYWAVE01** with the exact fix + tests.

---

## 6. FEAT-HARV specific status (the feature that surfaced all this)

- Feature: `.guardkit/features/FEAT-HARV.yaml` — reset to `status: planned`.
- A stale worktree may exist at `.guardkit/worktrees/FEAT-HARV` (and branch
  `autobuild/FEAT-HARV`). Before any `--fresh` rerun, clean it:
  `git worktree remove .guardkit/worktrees/FEAT-HARV --force && git branch -D autobuild/FEAT-HARV`
  (the orchestrator's own `--fresh` auto-cleanup currently fails when the branch
  is still bound to the worktree — a minor separate paper-cut worth a task).
- **The deliverables are GOOD** (this is the frustrating part — the code is fine,
  the verifier isn't):
  - TASK-HARV-002 (taxonomy/episode_id), TASK-HARV-004 (NATS publisher) — both
    *approved* in a clean run.
  - TASK-HARV-003 (walker) — `45 passed in 0.13s`, all gates pass; only blocked by
    the runtime-parity cross-wave bug (TASK-FIX-PARITYWAVE01) + the SDK capture
    flakiness.
- **Pragmatic option:** once TASK-FIX-PARITYWAVE01 lands (and ideally COSE option
  (b) makes the SDK path reliable), a single `--fresh` run should carry FEAT-HARV
  past wave 2. Alternatively the deliverables are verifiably correct and could be
  completed semi-manually if you want it done without waiting on the Coach work.
- Run logs: `.guardkit/autobuild/_runs/FEAT-HARV-sdk-fresh-*.log` (kept for
  evidence). Per-task evidence is in the (gitignored) worktree under
  `.guardkit/worktrees/FEAT-HARV/.guardkit/autobuild/TASK-HARV-*/coach_evidence_turn_*.json`
  — copy any you want to keep before removing the worktree.

---

## 7. Recommended order of work

1. **TASK-REV-COSE first (diagnostic).** Decide (a) capture-fix vs (b) subprocess
   default. **Strong prior: (b) default `coach_test_execution=subprocess`** — it's
   low-risk, removes the flaky LLM-mediated capture, and the deterministic path is
   already the reliable fallback. This likely fixes the *majority* of the
   "AutoBuild fails on a new verification issue every run" pain in one move.
2. **TASK-FIX-DF44** — implement `collection_error` classification AND the
   no-marker/absent → conditional-approvable handling + resolve the
   absent-vs-classified asymmetry. (If you do COSE (b), DF44's narration part
   becomes much smaller, but the asymmetry is still worth fixing for robustness.)
3. **TASK-FIX-PARITYWAVE01** — the runtime-parity wave-scope fix (independent of
   the SDK work; small and self-contained; fix sketch already in the task).
4. **Re-run FEAT-HARV `--fresh`** to validate end-to-end. Expect wave 1 (002/004)
   and wave 2 (003) to clear; then waves 3–5 (005 CLI → 006 acceptance → 007 live
   run, which is `operator_handoff` and skipped by AutoBuild).
5. Triage the FEAT-CRV backlog tasks (§4c) for overlap.

---

## 8. Guardrails / lessons for the next session

- **Check `tasks/` and recent git log before inventing a fix.** This session
  re-derived behaviour that the conditional-approval mechanism already owns, and
  one inline "fix" regressed it. The codebase has deep prior art here (the
  low-fidelity-oracle rule family in `.claude/rules/`: `absence-of-failure-is-not-success`,
  `absence-must-survive-every-reconciliation-layer`, `smoke-gate-is-feedback-not-terminator`,
  `per-task-green-is-not-feature-green`, `namespace-hygiene`).
- **`absent` is stricter than `fail` in the current approval path.** Any change
  touching `signal_absent` / Guard #6 / `_classify_test_failure` must reason about
  both buckets or it will regress.
- **The deterministic subprocess pytest is the source of truth**; the SDK
  independent path is a flaky convenience. When they disagree, trust subprocess.
- **Local env caveat (this machine):** guardkitfactory + langchain are installed,
  so harness-touching tests that don't pin `GUARDKIT_HARNESS=sdk` fail on
  langgraph auth (the `ci-tests-yml-no-guardkitfactory` hazard). Don't mistake
  those for regressions — confirm against a pre-change commit.

---

## 9. Quick reference

- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
  - SDK independent test: `_run_tests_via_sdk` (the `ToolResultEvent` note is the
    capture limitation)
  - Conditional approval: ~line 2223 (`conditional_approval = ...`)
  - Failure classifier: `_classify_test_failure()` (~2631)
- Per-task runtime parity threading: `feature_orchestrator.py::_execute_wave`
  (~line 3343, `TASK-AB-COACHRUNPARITY01 (arm b)`); `should_fire_for_wave` in
  `smoke_gates.py`.
- This session's commits: `ff4b63ce`, `a9f6646e`, (`5c95dd85`→`0cbbe6fa`),
  (`437ebd8a`→`c649e069`).
